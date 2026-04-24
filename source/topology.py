#!/usr/bin/env python3
import os
import sys
import time
from mininet.net import Mininet
from mininet.node import Host, OVSSwitch, DefaultController
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

# Import các file cấu hình chi tiết
import config_backbone
import config_branch1
import config_branch2
import config_branch3

def check_dependencies():
    info('*** Cân chỉnh Kernel chuẩn bị cho MPLS/VPLS...\n')
    os.system('modprobe mpls_router >/dev/null 2>&1')
    os.system('modprobe mpls_iptunnel >/dev/null 2>&1')
    os.system('sysctl -w net.mpls.platform_labels=100000 >/dev/null 2>&1')
    os.system('sysctl -w net.ipv4.conf.all.rp_filter=0 >/dev/null 2>&1')
    os.system('sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1')

class LinuxRouter(Host):
    def config(self, **params):
        super().config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        super().terminate()

class FRRRouter(LinuxRouter):
    def config(self, **params):
        super().config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
        self.cmd('sysctl -w net.mpls.conf.lo.input=1')
        # Cách ly thư mục socket và cấu hình của FRR
        self.cmd('mkdir -p /var/run/frr')
        self.cmd('mount -t tmpfs tmpfs /var/run/frr')
        self.cmd('chown frr:frrvty /var/run/frr 2>/dev/null')
        self.cmd('chmod 777 /var/run/frr')
        
        # Cách ly thư mục /etc/frr
        self.cmd('mkdir -p /etc/frr')
        self.cmd('mount -t tmpfs tmpfs /etc/frr')
        self.cmd('chown frr:frrvty /etc/frr 2>/dev/null')
        self.cmd('chmod 777 /etc/frr')
        
        # Cấu hình các daemon cần chạy
        daemons_config = "zebra=yes\\nospfd=yes\\nldpd=yes\\nbgpd=yes\\nvtysh_enable=yes\\nfrr_profile=datacenter\\n"
        self.cmd(f'echo -e "{daemons_config}" > /etc/frr/daemons')
        self.cmd('touch /etc/frr/vtysh.conf')
        self.cmd('echo "service integrated-vtysh-config" > /etc/frr/vtysh.conf')
        self.cmd('chown frr:frrvty /etc/frr/daemons /etc/frr/vtysh.conf 2>/dev/null')

    def terminate(self):
        self.cmd('/usr/lib/frr/frrinit.sh stop 2>/dev/null')
        self.cmd('umount /etc/frr 2>/dev/null')
        self.cmd('umount /var/run/frr 2>/dev/null')
        super().terminate()

def build_net():
    check_dependencies()
    info('*** Đang xây dựng Topology Metro Ethernet MPLS...\n')
    net = Mininet(controller=DefaultController, link=TCLink, autoSetMacs=True)
    
    # ==========================================
    # 1. LÕI BACKBONE MPLS (Core Area)
    # ==========================================
    info('*** Thêm các Router lõi P và PE...\n')
    p1 = net.addHost('p1', cls=FRRRouter, ip='10.1.0.2/30')
    p2 = net.addHost('p2', cls=FRRRouter, ip='10.1.0.6/30')
    p3 = net.addHost('p3', cls=FRRRouter, ip='10.1.0.14/30')
    p4 = net.addHost('p4', cls=FRRRouter, ip='10.1.0.18/30')
    pe1 = net.addHost('pe1', cls=FRRRouter, ip='10.1.0.1/30')
    pe2 = net.addHost('pe2', cls=FRRRouter, ip='10.1.0.10/30')
    pe3 = net.addHost('pe3', cls=FRRRouter, ip='10.1.0.26/30')

    # Nối PE1 với P1 và P3
    net.addLink(pe1, p1, intfName1='eth1', intfName2='eth0', bw=1000)
    net.addLink(pe1, p3, intfName1='eth2', intfName2='eth0', bw=1000)
    
    # Nối PE2 với P3 và P4
    net.addLink(pe2, p3, intfName1='eth1', intfName2='eth1', bw=1000)
    net.addLink(pe2, p4, intfName1='eth2', intfName2='eth0', bw=1000)
    
    # Nối PE3 với P2 và P4
    net.addLink(pe3, p2, intfName1='eth1', intfName2='eth0', bw=1000)
    net.addLink(pe3, p4, intfName1='eth2', intfName2='eth1', bw=1000)

    # Nối lưới 4 Router P (Core P-P Full-Mesh)
    net.addLink(p1, p2, intfName1='eth1', intfName2='eth1', bw=1000)
    net.addLink(p1, p3, intfName1='eth2', intfName2='eth2', bw=1000)
    net.addLink(p2, p4, intfName1='eth2', intfName2='eth2', bw=1000)
    net.addLink(p3, p4, intfName1='eth3', intfName2='eth3', bw=1000)
    net.addLink(p1, p4, intfName1='eth3', intfName2='eth4', bw=1000)
    net.addLink(p2, p3, intfName1='eth3', intfName2='eth4', bw=1000)

    # --- 2. CE ROUTERS ---
    info('*** Thêm các Router khách hàng CE...\n')
    ce1 = net.addHost('ce1', cls=LinuxRouter, ip='192.168.100.1/24')
    ce2 = net.addHost('ce2', cls=FRRRouter, ip='192.168.100.2/24')
    ce3 = net.addHost('ce3', cls=FRRRouter, ip='192.168.100.3/24')
    
    net.addLink(ce1, pe1, intfName1='eth0', intfName2='eth0', bw=1000)
    net.addLink(ce2, pe2, intfName1='eth0', intfName2='eth0', bw=1000)
    net.addLink(ce3, pe3, intfName1='eth0', intfName2='eth0', bw=1000)

    # ==========================================
    # 2. LAN CHI NHÁNH 1 (FLAT NETWORK)
    # ==========================================
    info('*** Cấu hình LAN Chi nhánh 1 (Flat)...\n')
    sw_b1_1 = net.addSwitch('sw1_1', failMode='standalone', stp=True)
    sw_b1_2 = net.addSwitch('sw1_2', failMode='standalone', stp=True)

    h1 = net.addHost('h1', ip='192.168.1.11/24', defaultRoute='via 192.168.1.1')
    h2 = net.addHost('h2', ip='192.168.1.12/24', defaultRoute='via 192.168.1.1')
    h3 = net.addHost('h3', ip='192.168.1.13/24', defaultRoute='via 192.168.1.1')
    h4 = net.addHost('h4', ip='192.168.1.14/24', defaultRoute='via 192.168.1.1')

    net.addLink(ce1, sw_b1_1, intfName1='eth1', bw=1000)
    net.addLink(sw_b1_1, sw_b1_2, bw=1000)
    
    net.addLink(h1, sw_b1_1, bw=100)
    net.addLink(h2, sw_b1_1, bw=100)
    net.addLink(h3, sw_b1_2, bw=100)
    net.addLink(h4, sw_b1_2, bw=100)

    # ==========================================
    # 3. LAN CHI NHÁNH 2 (3-LAYER ARCHITECTURE)
    # ==========================================
    info('*** Cấu hình LAN Chi nhánh 2 (3-Layer)...\n')
    core1 = net.addHost('core1', cls=FRRRouter, ip='192.168.20.2/24')
    core2 = net.addHost('core2', cls=FRRRouter, ip='192.168.20.3/24')
    dist1 = net.addSwitch('dist1', failMode='standalone', stp=True)
    dist2 = net.addSwitch('dist2', failMode='standalone', stp=True)
    acc1 = net.addSwitch('acc1', failMode='standalone', stp=True)
    acc2 = net.addSwitch('acc2', failMode='standalone', stp=True)
    acc3 = net.addSwitch('acc3', failMode='standalone', stp=True)

    h5 = net.addHost('h5', ip='192.168.20.15/24', defaultRoute='via 192.168.20.1')
    h6 = net.addHost('h6', ip='192.168.20.16/24', defaultRoute='via 192.168.20.1')
    h7 = net.addHost('h7', ip='192.168.20.17/24', defaultRoute='via 192.168.20.1')
    h8 = net.addHost('h8', ip='192.168.20.18/24', defaultRoute='via 192.168.20.1')
    h9 = net.addHost('h9', ip='192.168.20.19/24', defaultRoute='via 192.168.20.1')
    h10 = net.addHost('h10', ip='192.168.20.20/24', defaultRoute='via 192.168.20.1')

    # CE2 nối với 2 Core
    net.addLink(ce2, core1, intfName1='eth1', intfName2='eth0', bw=1000)
    net.addLink(ce2, core2, intfName1='eth2', intfName2='eth0', bw=1000)

    # Nối chéo Core và Distribution
    net.addLink(core1, dist1, intfName1='eth1', bw=1000)
    net.addLink(core1, dist2, intfName1='eth2', bw=1000)
    net.addLink(core2, dist1, intfName1='eth1', bw=1000)
    net.addLink(core2, dist2, intfName1='eth2', bw=1000)

    # Nối Distribution tới Access
    net.addLink(dist1, acc1, bw=1000)
    net.addLink(dist2, acc1, bw=1000)
    net.addLink(dist1, acc2, bw=1000)
    net.addLink(dist2, acc2, bw=1000)
    net.addLink(dist1, acc3, bw=1000)
    net.addLink(dist2, acc3, bw=1000)

    # Nối Access tới Hosts
    net.addLink(h5, acc1, bw=100)
    net.addLink(h6, acc1, bw=100)
    net.addLink(h7, acc2, bw=100)
    net.addLink(h8, acc2, bw=100)
    net.addLink(h9, acc3, bw=100)
    net.addLink(h10, acc3, bw=100)

    # ==========================================
    # 4. LAN CHI NHÁNH 3 (SPINE-LEAF)
    # ==========================================
    info('*** Cấu hình LAN Chi nhánh 3 (Spine-Leaf)...\n')
    spine1 = net.addHost('sp1', cls=FRRRouter, ip='10.3.0.1/32')
    spine2 = net.addHost('sp2', cls=FRRRouter, ip='10.3.0.2/32')
    leaf1 = net.addHost('lf1', cls=FRRRouter, ip='10.3.0.11/32')
    leaf2 = net.addHost('lf2', cls=FRRRouter, ip='10.3.0.12/32')
    leaf3 = net.addHost('lf3', cls=FRRRouter, ip='10.3.0.13/32')
    leaf4 = net.addHost('lf4', cls=FRRRouter, ip='10.3.0.14/32')

    s1 = net.addHost('s1', ip='192.168.30.11/24', defaultRoute='via 192.168.30.1')
    s2 = net.addHost('s2', ip='192.168.30.12/24', defaultRoute='via 192.168.30.1')
    s3 = net.addHost('s3', ip='192.168.30.13/24', defaultRoute='via 192.168.30.1')
    s4 = net.addHost('s4', ip='192.168.30.14/24', defaultRoute='via 192.168.30.1')
    s5 = net.addHost('s5', ip='192.168.30.15/24', defaultRoute='via 192.168.30.1')
    s6 = net.addHost('s6', ip='192.168.30.16/24', defaultRoute='via 192.168.30.1')

    # CE3 nối trực tiếp vào Leaf1
    net.addLink(ce3, leaf1,
    intfName1='eth1',
    intfName2='eth0',
    bw=1000)

    # Nối Spine tới tất cả các Leaf
    for lf_idx, leaf in enumerate([leaf1, leaf2, leaf3, leaf4]):
        if leaf == leaf1:
            net.addLink(spine1, leaf, intfName1=f'eth{lf_idx}', intfName2='eth1', bw=1000)
            net.addLink(spine2, leaf, intfName1=f'eth{lf_idx}', intfName2='eth2', bw=1000)
        else:
            net.addLink(spine1, leaf, intfName1=f'eth{lf_idx}', intfName2='eth0', bw=1000)
            net.addLink(spine2, leaf, intfName1=f'eth{lf_idx}', intfName2='eth1', bw=1000)

    # Nối Host Servers vào Leaf2, Leaf3, Leaf4
    net.addLink(s1, leaf2, intfName2='eth2', bw=100)
    net.addLink(s2, leaf2, intfName2='eth3', bw=100)
    net.addLink(s3, leaf3, intfName2='eth2', bw=100)
    net.addLink(s4, leaf3, intfName2='eth3', bw=100)
    net.addLink(s5, leaf4, intfName2='eth2', bw=100)
    net.addLink(s6, leaf4, intfName2='eth3', bw=100)

    # ==========================================
    # KHỞI CHẠY HỆ THỐNG
    # ==========================================
    info('*** Khởi chạy Hệ thống Mạng...\n')
    net.start()

    info('*** Áp dụng cấu hình giao thức định tuyến (IP, OSPF, LDP, VPLS)...\n')
    try:
        config_backbone.apply_config(net)
        config_branch1.apply_config(net)
        config_branch2.apply_config(net)
        config_branch3.apply_config(net)
    except Exception as e:
        info(f'*** Cảnh báo: Các script config có thể cần cập nhật lại theo các Host mới tạo: {e}\n')

    info('*** Hoàn tất! TRỌNG YẾU: Cần chờ 20 giây để STP Switch Blocks Loop và OSPF định tuyến hội tụ.\n')
    CLI(net)
    net.stop()
    os.system('mn -c >/dev/null 2>&1')

if __name__ == '__main__':
    setLogLevel('info')
    os.system('mn -c >/dev/null 2>&1')
    build_net()
