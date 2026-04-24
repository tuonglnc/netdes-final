def apply_config(net):
    ce1 = net.get('ce1')
    pe1 = net.get('pe1')

    # Dọn dẹp IP rác mặc định của Mininet trên CE1
    ce1.cmd("for i in $(ls /sys/class/net/ | grep -v lo); do ip addr flush dev $i 2>/dev/null; ip link set $i up 2>/dev/null; done")

    # ==========================================
    # Cấu hình WAN Link giữa CE1 và PE1
    # ==========================================
    # PE1(eth0) nằm trong VRF_BRANCH. Đặt IP cho kết nối P2P
    pe1.cmd('ip addr add 10.100.1.1/30 dev eth0')
    
    # CE1(eth0) nối lên WAN PE1
    ce1.cmd('ip addr add 10.100.1.2/30 dev eth0')
    
    # ==========================================
    # Cấu hình mạng LAN (Flat Network)
    # ==========================================
    # Đặt Gateway IP cho các host H1 -> H4
    ce1.cmd('ip addr add 192.168.1.1/24 dev eth1')
    
    # ==========================================
    # Cấu hình Routing
    # ==========================================
    # Định tuyến Mặc định (Default Route) đẩy toàn bộ traffic từ Branch 1 lên PE1
    ce1.cmd('ip route add default via 10.100.1.1')
    
    # Quảng bá mạng LAN 192.168.1.0/24 vào VRF của PE1
    # Do CE1 trỏ default route lên PE1, ta dùng Static Route trên PE1 VRF_BRANCH đẩy về CE1
    pe1.cmd('ip route add 192.168.1.0/24 via 10.100.1.2 dev eth0 table 10')
    # Table 10 là bảng định tuyến của VRF_BRANCH (được tạo ở config_backbone.py)
