import os
import time

def setup_frr(node, router_id, role, loopback_ip, neighbors=None):
    os.system(f'mkdir -p /tmp/{node.name}')
    node.cmd('sysctl -w net.mpls.platform_labels=1048575 2>/dev/null')
    node.cmd('for i in $(ls /sys/class/net/); do sysctl -w net.mpls.conf.$i.input=1 2>/dev/null; done')

    # BGP AS number cho Backbone
    as_number = 65000

    frr_conf = f"""frr version 7.2
frr defaults traditional
hostname {node.name}
password en
enable password en
!
interface lo
 ip address {loopback_ip}
!
router ospf
 ospf router-id {router_id}
 network 10.0.0.0/8 area 0
 network {loopback_ip} area 0
!
mpls ldp
 router-id {router_id}
 !
 address-family ipv4
  discovery transport-address {router_id}
  interface eth0
  interface eth1
  interface eth2
  interface eth3
  interface eth4
 !
!
"""

    if role == 'PE':
        frr_conf += f"""router bgp {as_number}
 bgp router-id {router_id}
 no bgp ebgp-requires-policy
 no bgp network import-check
"""
        if neighbors:
            for n in neighbors:
                frr_conf += f" neighbor {n} remote-as {as_number}\n"
                frr_conf += f" neighbor {n} update-source {router_id}\n"
            
            frr_conf += " !\n address-family ipv4 vpn\n"
            for n in neighbors:
                frr_conf += f"  neighbor {n} activate\n"
                frr_conf += f"  neighbor {n} send-community extended\n"
            frr_conf += " exit-address-family\n!\n"
            
            frr_conf += f"""router bgp {as_number} vrf VRF_BRANCH
 no bgp ebgp-requires-policy
 !
 address-family ipv4 unicast
  redistribute connected
  redistribute static
  redistribute kernel
  label vpn export auto
  rd vpn export {router_id}:1
  rt vpn both 65000:1
  export vpn
  import vpn
 exit-address-family
!
"""

    os.system(f'mkdir -p /tmp/{node.name}')
    with open(f'/tmp/{node.name}/frr.conf', 'w') as f:
        f.write(frr_conf)
    
    # Copy file config vào không gian ảo /etc/frr của node
    node.cmd(f'cp /tmp/{node.name}/frr.conf /etc/frr/frr.conf')
    node.cmd('chown frr:frrvty /etc/frr/frr.conf 2>/dev/null')
    node.cmd('chmod 644 /etc/frr/frr.conf')
    
    # Khởi chạy toàn bộ FRR bằng init script chuẩn
    node.cmd('/usr/lib/frr/frrinit.sh start 2>/dev/null')

def apply_config(net):
    p1 = net.get('p1')
    p2 = net.get('p2')
    p3 = net.get('p3')
    p4 = net.get('p4')
    pe1 = net.get('pe1')
    pe2 = net.get('pe2')
    pe3 = net.get('pe3')

    # Quy hoạch IP Loopback: 1.1.1.x/32
    loopbacks = {
        'p1': '1.1.1.2', 'p2': '1.1.1.3', 'p3': '1.1.1.4', 'p4': '1.1.1.5',
        'pe1': '1.1.1.11', 'pe2': '1.1.1.12', 'pe3': '1.1.1.13'
    }

    # Xóa IP rác và cấp IP tĩnh cho lõi
    for node in [p1, p2, p3, p4, pe1, pe2, pe3]:
        node.cmd("for i in $(ls /sys/class/net/ | grep -v lo); do ip addr flush dev $i 2>/dev/null; ip link set $i up 2>/dev/null; done")
        node.cmd(f"ip addr add {loopbacks[node.name]}/32 dev lo")

    # IP Backbone P2P
    # Link 1: PE1 - P1 (10.1.0.0/30)
    pe1.cmd('ip addr add 10.1.0.1/30 dev eth1')
    p1.cmd('ip addr add 10.1.0.2/30 dev eth0')
    # Link 2: PE1 - P3 (10.1.0.4/30)
    pe1.cmd('ip addr add 10.1.0.5/30 dev eth2')
    p3.cmd('ip addr add 10.1.0.6/30 dev eth0')
    # Link 3: PE2 - P3 (10.1.0.8/30)
    pe2.cmd('ip addr add 10.1.0.9/30 dev eth1')
    p3.cmd('ip addr add 10.1.0.10/30 dev eth1')
    # Link 4: PE2 - P4 (10.1.0.12/30)
    pe2.cmd('ip addr add 10.1.0.13/30 dev eth2')
    p4.cmd('ip addr add 10.1.0.14/30 dev eth0')
    # Link 5: PE3 - P2 (10.1.0.16/30)
    pe3.cmd('ip addr add 10.1.0.17/30 dev eth1')
    p2.cmd('ip addr add 10.1.0.18/30 dev eth0')
    # Link 6: PE3 - P4 (10.1.0.20/30)
    pe3.cmd('ip addr add 10.1.0.21/30 dev eth2')
    p4.cmd('ip addr add 10.1.0.22/30 dev eth1')
    # Link 7: P1 - P2 (10.1.0.24/30)
    p1.cmd('ip addr add 10.1.0.25/30 dev eth1')
    p2.cmd('ip addr add 10.1.0.26/30 dev eth1')
    # Link 8: P1 - P3 (10.1.0.28/30)
    p1.cmd('ip addr add 10.1.0.29/30 dev eth2')
    p3.cmd('ip addr add 10.1.0.30/30 dev eth2')
    # Link 9: P2 - P4 (10.1.0.32/30)
    p2.cmd('ip addr add 10.1.0.33/30 dev eth2')
    p4.cmd('ip addr add 10.1.0.34/30 dev eth2')
    # Link 10: P3 - P4 (10.1.0.36/30)
    p3.cmd('ip addr add 10.1.0.37/30 dev eth3')
    p4.cmd('ip addr add 10.1.0.38/30 dev eth3')
    # Link 11: P1 - P4 (10.1.0.40/30)
    p1.cmd('ip addr add 10.1.0.41/30 dev eth3')
    p4.cmd('ip addr add 10.1.0.42/30 dev eth4')
    # Link 12: P2 - P3 (10.1.0.44/30)
    p2.cmd('ip addr add 10.1.0.45/30 dev eth3')
    p3.cmd('ip addr add 10.1.0.46/30 dev eth4')

    # Tăng MTU do bọc header MPLS/VPN
    for node in [p1, p2, p3, p4, pe1, pe2, pe3]:
        for i in range(5):
            node.cmd(f'ip link set eth{i} mtu 1520 2>/dev/null')

    # Thiết lập VRF để tách biệt luồng traffic L3VPN
    for pe in [pe1, pe2, pe3]:
        # Cấu hình Linux VRF có tên là VRF_BRANCH
        pe.cmd('ip link add VRF_BRANCH type vrf table 10')
        pe.cmd('ip link set VRF_BRANCH up')
        # Gắn cổng kết nối xuống khách hàng (CE) vào VRF
        pe.cmd('ip link set eth0 master VRF_BRANCH')
        pe.cmd('sysctl -w net.ipv4.conf.eth0.forwarding=1')

    # Khởi chạy OSPF, LDP, MP-BGP
    setup_frr(p1, loopbacks['p1'], 'P', f"{loopbacks['p1']}/32")
    setup_frr(p2, loopbacks['p2'], 'P', f"{loopbacks['p2']}/32")
    setup_frr(p3, loopbacks['p3'], 'P', f"{loopbacks['p3']}/32")
    setup_frr(p4, loopbacks['p4'], 'P', f"{loopbacks['p4']}/32")
    
    setup_frr(pe1, loopbacks['pe1'], 'PE', f"{loopbacks['pe1']}/32", neighbors=[loopbacks['pe2'], loopbacks['pe3']])
    setup_frr(pe2, loopbacks['pe2'], 'PE', f"{loopbacks['pe2']}/32", neighbors=[loopbacks['pe1'], loopbacks['pe3']])
    setup_frr(pe3, loopbacks['pe3'], 'PE', f"{loopbacks['pe3']}/32", neighbors=[loopbacks['pe1'], loopbacks['pe2']])
