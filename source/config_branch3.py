import os
import time

def setup_spine_leaf(node, router_id, role, loopback_ip, peer_loopbacks=None):
    os.system(f'mkdir -p /tmp/{node.name}')
    
    # Enable L4 hashing for ECMP and VXLAN
    node.cmd('sysctl -w net.ipv4.fib_multipath_hash_policy=1')
    
    frr_conf = f"frr version 7.2\nfrr defaults traditional\nhostname {node.name}\n!\n"
    frr_conf += f"router ospf\n ospf router-id {router_id}\n network 10.3.0.0/16 area 0\n"
    if node.name == 'lf1':
        frr_conf += "!\ninterface eth0\n ip address 10.3.255.2/30\n no shutdown\n!\n"
        frr_conf += " default-information originate always\n!\n"
        frr_conf += "ip route 0.0.0.0/0 10.3.255.1\n"
    else:
        frr_conf += "!\n"
    
    # BGP L2VPN EVPN Overlay
    as_num = 65003
    bgp_conf = f"""router bgp {as_num}
 bgp router-id {router_id}
 no bgp ebgp-requires-policy
 no bgp network import-check
"""
    if role == 'spine':
        bgp_conf += " bgp cluster-id 10.3.0.100\n"
        for peer in peer_loopbacks:
            bgp_conf += f" neighbor {peer} remote-as {as_num}\n"
            bgp_conf += f" neighbor {peer} update-source {loopback_ip}\n"
        bgp_conf += " !\n address-family l2vpn evpn\n"
        for peer in peer_loopbacks:
            bgp_conf += f"  neighbor {peer} activate\n"
            bgp_conf += f"  neighbor {peer} route-reflector-client\n"
        bgp_conf += " exit-address-family\n"

    elif role == 'leaf':
        for peer in peer_loopbacks:
            bgp_conf += f" neighbor {peer} remote-as {as_num}\n"
            bgp_conf += f" neighbor {peer} update-source {loopback_ip}\n"
        bgp_conf += " !\n address-family l2vpn evpn\n"
        for peer in peer_loopbacks:
            bgp_conf += f"  neighbor {peer} activate\n"
        bgp_conf += "  advertise-all-vni\n"
        bgp_conf += " exit-address-family\n"
        
        if node.name == 'lf1':
            bgp_conf += """ !
 address-family ipv4 unicast
  redistribute ospf
 exit-address-family
"""
    
    frr_conf += bgp_conf
    
    with open(f'/tmp/{node.name}/frr.conf', 'w') as f:
        f.write(frr_conf)

    node.cmd(f'cp /tmp/{node.name}/frr.conf /etc/frr/frr.conf')
    node.cmd('chown frr:frrvty /etc/frr/frr.conf 2>/dev/null')
    node.cmd('chmod 644 /etc/frr/frr.conf')
    node.cmd('/usr/lib/frr/frrinit.sh start 2>/dev/null')

def apply_config(net):
    pe3 = net.get('pe3')
    ce3 = net.get('ce3')
    sp1 = net.get('sp1')
    sp2 = net.get('sp2')
    lf1 = net.get('lf1')
    lf2 = net.get('lf2')
    lf3 = net.get('lf3')
    lf4 = net.get('lf4')
    
    leafs = [lf1, lf2, lf3, lf4]
    spines = [sp1, sp2]

    # Xóa IP rác Mininet
    for node in spines + leafs + [ce3]:
        node.cmd("for i in $(ls /sys/class/net/ | grep -v lo); do ip addr flush dev $i 2>/dev/null; ip link set $i up 2>/dev/null; done")

    # WAN Link: PE3 - CE3
    pe3.cmd('ip addr add 10.100.3.1/30 dev eth0')
    ce3.cmd('ip addr add 10.100.3.2/30 dev eth0')
    
    # Border Link: CE3 - Leaf1
    ce3.cmd('ip addr flush dev eth1 2>/dev/null')
    ce3.cmd('ip addr add 10.3.255.1/30 dev eth1')
    ce3.cmd('ip link set eth1 up')
    lf1.cmd('ip addr flush dev eth0 2>/dev/null')
    lf1.cmd('ip addr add 10.3.255.2/30 dev eth0') # Leaf1 eth0 nối CE3
    lf1.cmd('ip link set eth0 up')
    
    # Ép Route trực tiếp vào Linux Kernel để đảm bảo Data Plane thông suốt ngay lập tức
    ce3.cmd('ip route add 192.168.30.0/24 via 10.3.255.2 dev eth1 2>/dev/null')
    lf1.cmd('ip route add default via 10.3.255.1 dev eth0 2>/dev/null')
    
    # Cấu hình IP P2P Spine-Leaf Underlay (Subnet 10.3.1.x)
    subnet_idx = 1
    for sp_idx, sp in enumerate(spines):
        for lf_idx, lf in enumerate(leafs):
            ip_sp = f"10.3.{subnet_idx}.1/30"
            ip_lf = f"10.3.{subnet_idx}.2/30"
            sp.cmd(f'ip addr flush dev eth{lf_idx} 2>/dev/null')
            sp.cmd(f'ip addr add {ip_sp} dev eth{lf_idx}')
            
            if lf == lf1:
                # lf1 có eth0 nối CE3, nên các kết nối spine bị lùi lại 1 interface (eth1, eth2)
                lf.cmd(f'ip addr flush dev eth{sp_idx + 1} 2>/dev/null')
                lf.cmd(f'ip addr add {ip_lf} dev eth{sp_idx + 1}')
            else:
                lf.cmd(f'ip addr flush dev eth{sp_idx} 2>/dev/null')
                lf.cmd(f'ip addr add {ip_lf} dev eth{sp_idx}')
            subnet_idx += 1

    # Loopbacks
    sp_loops = ['10.3.0.1', '10.3.0.2']
    lf_loops = ['10.3.0.11', '10.3.0.12', '10.3.0.13', '10.3.0.14']
    for idx, sp in enumerate(spines): sp.cmd(f'ip addr add {sp_loops[idx]}/32 dev lo')
    for idx, lf in enumerate(leafs):  lf.cmd(f'ip addr add {lf_loops[idx]}/32 dev lo')

    # Cấu hình VTEP (VXLAN) trên các Leaf
    for idx, lf in enumerate(leafs):
        # Tạo Bridge L2 để cắm VXLAN và Server
        lf.cmd('ip link add br0 type bridge')
        lf.cmd('ip link set br0 up')
        # Gateway cho mạng Server (Chỉ đặt trên Border Leaf để tránh đụng độ IP)
        if lf == lf1:
            lf.cmd('ip addr add 192.168.30.1/24 dev br0')
        
        # Cắm các port nối Host vào Bridge (eth2, eth3)
        if lf != lf1: # Leaf 1 là Border, không có Host
            lf.cmd('ip link set eth2 up')
            lf.cmd('ip link set eth3 up')
            lf.cmd('ip link set eth2 master br0')
            lf.cmd('ip link set eth3 master br0')

        # Tạo VNI 100 và cắm vào Bridge
        lf.cmd(f'ip link add vxlan100 type vxlan id 100 dstport 4789 local {lf_loops[idx]} nolearning')
        lf.cmd('ip link set vxlan100 up')
        lf.cmd('ip link set vxlan100 master br0')
        
        # BUM Replication (Cực kỳ quan trọng để ARP chạy qua VXLAN)
        for other_idx, other_lf in enumerate(leafs):
            if idx != other_idx:
                lf.cmd(f'bridge fdb append 00:00:00:00:00:00 dev vxlan100 dst {lf_loops[other_idx]}')

    # Khởi chạy OSPF và BGP EVPN
    setup_spine_leaf(sp1, sp_loops[0], 'spine', sp_loops[0], lf_loops)
    setup_spine_leaf(sp2, sp_loops[1], 'spine', sp_loops[1], lf_loops)
    
    for idx, lf in enumerate(leafs):
        setup_spine_leaf(lf, lf_loops[idx], 'leaf', lf_loops[idx], sp_loops)

    # ==========================================
    # Cấu hình BGP CE3 -> PE3
    # ==========================================
    # CE3 chạy BGP kết nối với L3VPN VRF_BRANCH trên PE3
    # CE3 cũng quảng bá dải 192.168.30.0/24 của Branch 3
    ce3_bgp = f"""frr version 7.2
frr defaults traditional
hostname ce3
!
interface eth1
 ip address 10.3.255.1/30
!
router bgp 65003
  bgp router-id 30.30.30.1
 neighbor 10.100.3.1 remote-as 65000
 address-family ipv4 unicast
  network 192.168.30.0/24
  redistribute static
  redistribute kernel
  redistribute connected
 exit-address-family
!
ip route 192.168.30.0/24 10.3.255.2
"""
    os.system('mkdir -p /tmp/ce3')
    with open('/tmp/ce3/frr.conf', 'w') as f: f.write(ce3_bgp)
    ce3.cmd('cp /tmp/ce3/frr.conf /etc/frr/frr.conf')
    ce3.cmd('chown frr:frrvty /etc/frr/frr.conf 2>/dev/null')
    ce3.cmd('chmod 644 /etc/frr/frr.conf')
    ce3.cmd('/usr/lib/frr/frrinit.sh start 2>/dev/null')

    time.sleep(2)
    ce3.cmd('ip route replace 192.168.30.0/24 via 10.3.255.2 dev eth1')
    ce3.cmd('ip route replace default via 10.100.3.1 dev eth0')

    # Đảm bảo route Linux được thêm (như một lớp dự phòng)
    ce3.cmd('ip route add 192.168.30.0/24 via 10.3.255.2 dev eth1 2>/dev/null')
    
    # Định tuyến BGP trên PE3 (VRF_BRANCH) nhận Route từ CE3
    pe3.cmd('vtysh -c "conf t" -c "router bgp 65000 vrf VRF_BRANCH" -c "neighbor 10.100.3.2 remote-as 65003" -c "address-family ipv4 unicast" -c "neighbor 10.100.3.2 activate"')

    # FIX CỰC KỲ QUAN TRỌNG: Đảm bảo lại IP eth0 và Default Route cho Leaf1 
    # (Vì một số lý do tiến trình FRR/Zebra có thể đã flush IP của eth0 khi khởi động)
    lf1.cmd('ip addr add 10.3.255.2/30 dev eth0 2>/dev/null')
    lf1.cmd('ip link set eth0 up')
    lf1.cmd('ip route add default via 10.3.255.1 dev eth0 2>/dev/null')


    ce3.cmd('ip addr replace 10.3.255.1/30 dev eth1')
    ce3.cmd('ip link set eth1 up')

    lf1.cmd('ip addr replace 10.3.255.2/30 dev eth0')
    lf1.cmd('ip link set eth0 up')