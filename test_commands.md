# Danh sách các lệnh kiểm tra (Test Commands) mạng MPLS & EVPN

## 1. Kiểm tra Mạng Lõi MPLS (Backbone)
- **Kiểm tra láng giềng OSPF trên Core:**
```bash
mininet> p1 vtysh -c "show ip ospf neighbor"
```
- **Kiểm tra tiến trình LDP và Nhãn MPLS:**
```bash
mininet> p1 vtysh -c "show mpls ldp neighbor"
mininet> p1 vtysh -c "show mpls ldp binding"
```
- **Kiểm tra Kernel Linux có nạp nhãn MPLS thành công không:**
```bash
mininet> p1 ip -f mpls route
```
- **Kiểm tra BGP VPNv4 giữa các PE (Trao đổi định tuyến khách hàng):**
```bash
mininet> pe1 vtysh -c "show bgp ipv4 vpn"
mininet> pe1 vtysh -c "show ip route vrf VRF_BRANCH"
```

## 2. Kiểm tra LAN Branch 1 (Flat Network)
- **Ping nội bộ cùng Switch (h1 -> h2):**
```bash
mininet> h1 ping -c 2 h2
```
- **Ping khác Switch (h1 -> h3, h4):**
```bash
mininet> h1 ping -c 2 h3
mininet> h1 ping -c 2 h4
```
- **Ping tới Gateway (Mặt trong CE1):**
```bash
mininet> h1 ping -c 2 192.168.1.1
```
- **Ping tới cổng WAN (CE1) và PE1:**
```bash
mininet> h1 ping -c 2 10.100.1.2
mininet> h1 ping -c 2 10.100.1.1
```

## 3. Kiểm tra LAN Branch 2 (3-Layer Architecture)
- **Ping nội bộ cùng Access Switch (h5 -> h6):**
```bash
mininet> h5 ping -c 2 h6
```
- **Ping nội bộ khác Access Switch (h5 -> h9):**
```bash
mininet> h5 ping -c 2 h9
```
- **Kiểm tra cấu hình VLAN và STP trên OpenvSwitch (Access/Dist):**
```bash
mininet> acc1 ovs-vsctl show
mininet> dist1 ovs-vsctl get bridge dist1 stp_enable
```
- **Kiểm tra IP Gateway ảo (VRRP) trên Core:**
```bash
mininet> core1 ip addr | grep 192.168.20.1
mininet> core2 ip addr | grep 192.168.20.1
```
- **Ping tới Gateway dự phòng (VRRP VIP):**
```bash
mininet> h5 ping -c 2 192.168.20.1
```
- **Ping lên cổng WAN CE2 và PE2:**
```bash
mininet> h5 ping -c 2 10.100.2.2
mininet> h5 ping -c 2 10.100.2.1
```
- **Kiểm tra OSPF và eBGP trên CE2:**
```bash
mininet> ce2 vtysh -c "show ip route ospf"
mininet> ce2 vtysh -c "show ip bgp summary"
```

## 4. Kiểm tra LAN Branch 3 (Spine-Leaf EVPN)
- **Kiểm tra OSPF Underlay và ECMP (Nhiều Nexthop):**
```bash
mininet> sp1 vtysh -c "show ip ospf neighbor"
mininet> sp1 ip route
```
- **Kiểm tra BGP L2VPN EVPN (Trao đổi MAC/IP):**
```bash
mininet> sp1 vtysh -c "show bgp l2vpn evpn"
```
- **Kiểm tra các cổng VXLAN đã được gắn vào Bridge:**
```bash
mininet> lf2 ip link show master br0
```
- **Ping nội bộ giữa các Server trong Datacenter:**
```bash
mininet> s1 ping -c 2 s2
mininet> s1 ping -c 2 s5
```
- **Ping ra Gateway và Border Leaf:**
```bash
mininet> s1 ping -c 2 192.168.30.1
mininet> s1 ping -c 2 10.3.255.2
```

## 5. Kiểm tra Kết nối Liên Chi nhánh (End-to-End MPLS VPN)
- **Ping từ Branch 1 (Flat) sang Branch 2 (3-Layer):**
```bash
mininet> h1 ping -c 4 h5
```
- **Ping từ Branch 1 (Flat) sang Branch 3 (Datacenter):**
```bash
mininet> h1 ping -c 4 s1
```
- **Ping từ Branch 2 sang Branch 3:**
```bash
mininet> h5 ping -c 4 s1
```
- **Kiểm tra đường đi qua MPLS Backbone (Traceroute):**
```bash
mininet> h1 traceroute h5
mininet> h5 traceroute s1
```
*(Nếu thành công, kết quả traceroute sẽ hiển thị các chặng đi qua các IP P2P của Backbone MPLS)*
