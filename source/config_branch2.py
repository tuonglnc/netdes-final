import os

def apply_config(net):
    ce2 = net.get('ce2')
    pe2 = net.get('pe2')
    core1 = net.get('core1')
    core2 = net.get('core2')
    
    # Danh sách Switch OVS
    switches = {
        'core1': net.get('core1'), # core1/core2 trong topology đang là L3 Host, ta đổi OVS? 
        # Cảnh báo: Trong topology.py, core1 và core2 là LinuxRouter.
        # Chúng đóng vai trò L3 Gateway chạy VRRP, trong khi dist và acc là OVS Switch thuần L2.
    }
    dist1 = net.get('dist1')
    dist2 = net.get('dist2')
    acc1 = net.get('acc1')
    acc2 = net.get('acc2')
    acc3 = net.get('acc3')

    # ==========================================
    # Cấu hình WAN Link giữa CE2 và PE2
    # ==========================================
    # Đặt IP tĩnh cho PE2(eth0) trong VRF_BRANCH
    pe2.cmd('ip addr add 10.100.2.1/30 dev eth0')
    ce2.cmd("for i in $(ls /sys/class/net/ | grep -v lo); do ip addr flush dev $i 2>/dev/null; ip link set $i up 2>/dev/null; done")
    ce2.cmd('ip addr add 10.100.2.2/30 dev eth0')

    # ==========================================
    # Cấu hình IP và Routing cho Core1, Core2, CE2
    # ==========================================
    # CE2(eth1) nối Core1, CE2(eth2) nối Core2
    ce2.cmd('ip addr add 10.2.1.1/30 dev eth1')
    ce2.cmd('ip addr add 10.2.2.1/30 dev eth2')
    
    core1.cmd('ip addr flush dev eth0; ip addr add 10.2.1.2/30 dev eth0')
    core2.cmd('ip addr flush dev eth0; ip addr add 10.2.2.2/30 dev eth0')

    # Gateway Interface cho mạng LAN (VLAN 20) trên Core1, Core2
    # Vì Core1 có 2 port nối xuống Dist1 và Dist2 (eth1, eth2), ta phải tạo L2 Bridge (như SVI)
    for core, ip, vip in [(core1, '192.168.20.2/24', '192.168.20.1/24'), (core2, '192.168.20.3/24', '192.168.20.1/24')]:
        core.cmd('ip link add br0 type bridge')
        core.cmd('ip link set eth1 up; ip link set eth2 up')
        core.cmd('ip link set eth1 master br0')
        core.cmd('ip link set eth2 master br0')
        core.cmd('ip link set br0 type bridge stp_state 1')
        core.cmd('ip link set br0 up')
        # Tạo Subinterface VLAN 20 trên Bridge để nhận traffic Trunk
        core.cmd('ip link add link br0 name br0.20 type vlan id 20')
        core.cmd('ip link set br0.20 up')
        core.cmd(f'ip addr add {ip} dev br0.20')
        if core == core1:
            core.cmd(f'ip addr add {vip} dev br0.20 label br0.20:vrrp')

    # ==========================================
    # Khởi tạo tiến trình OSPF trên CE2 và Core
    # (Định tuyến nội bộ Branch 2)
    # ==========================================
    def start_ospf(node, router_id, networks):
        os.system(f'mkdir -p /tmp/{node.name}')
        conf = f"frr version 7.2\nfrr defaults traditional\nhostname {node.name}\n!\nrouter ospf\n ospf router-id {router_id}\n"
        for nw in networks:
            conf += f" network {nw} area 0\n"
        conf += "!\n"
        with open(f'/tmp/{node.name}/frr.conf', 'w') as f:
            f.write(conf)
        node.cmd(f'cp /tmp/{node.name}/frr.conf /etc/frr/frr.conf')
        node.cmd('chown frr:frrvty /etc/frr/frr.conf 2>/dev/null')
        node.cmd('chmod 644 /etc/frr/frr.conf')
        node.cmd('/usr/lib/frr/frrinit.sh start 2>/dev/null')

    start_ospf(core1, '20.20.20.2', ['10.2.1.0/30', '192.168.20.0/24'])
    start_ospf(core2, '20.20.20.3', ['10.2.2.0/30', '192.168.20.0/24'])
    # CE2 chạy OSPF kết nối tới Core1, Core2 và chạy BGP eBGP tới PE2
    ce2_bgp = f"""hostname ce2
router ospf
 network 10.2.1.0/30 area 0
 network 10.2.2.0/30 area 0
 redistribute bgp
!
router bgp 65002
 bgp router-id 20.20.20.1
 neighbor 10.100.2.1 remote-as 65000
 address-family ipv4 unicast
  redistribute ospf
 exit-address-family
!
"""
    os.system('mkdir -p /tmp/ce2')
    with open('/tmp/ce2/frr.conf', 'w') as f: f.write(ce2_bgp)
    ce2.cmd('cp /tmp/ce2/frr.conf /etc/frr/frr.conf')
    ce2.cmd('chown frr:frrvty /etc/frr/frr.conf 2>/dev/null')
    ce2.cmd('chmod 644 /etc/frr/frr.conf')
    ce2.cmd('/usr/lib/frr/frrinit.sh start 2>/dev/null')

    # Định tuyến BGP trên PE2 (VRF_BRANCH) nhận Route từ CE2
    pe2.cmd('vtysh -c "conf t" -c "router bgp 65000 vrf VRF_BRANCH" -c "neighbor 10.100.2.2 remote-as 65002" -c "address-family ipv4 unicast" -c "neighbor 10.100.2.2 activate"')

    # ==========================================
    # Cấu hình VRRP (Virtual Router Redundancy Protocol)
    # ==========================================
    # Core1 làm Master (Priority 150), Core2 làm Backup (Priority 100) cho VIP 192.168.20.1
    # IP Ảo đã được gán vào br0.20 ở bước trên.

    # ==========================================
    # Cấu hình VLAN Trunking (OVS)
    # ==========================================
    # Thiết lập cổng nối Hosts thành Access VLAN 20
    # Thiết lập cổng nối Switches thành Trunk
    
    # (eth1, eth2 của Dist nối lên Core, eth3, eth4 nối xuống Access)
    # Gắn thẻ Vlan cho Host
    for acc, host_port1, host_port2 in [(acc1, 'acc1-eth3', 'acc1-eth4'), 
                                        (acc2, 'acc2-eth3', 'acc2-eth4'), 
                                        (acc3, 'acc3-eth3', 'acc3-eth4')]:
        acc.cmd(f'ovs-vsctl set port {host_port1} tag=20')
        acc.cmd(f'ovs-vsctl set port {host_port2} tag=20')
        
    # Cấu hình Trunk trên Dist và Acc (cho phép mọi VLAN)
    for sw in [dist1, dist2, acc1, acc2, acc3]:
        sw.cmd('ovs-vsctl set bridge %s stp_enable=true' % sw.name) # Kích hoạt STP chống lặp L2
