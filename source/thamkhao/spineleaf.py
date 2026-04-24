#!/usr/bin/env python3
"""
MÔ HÌNH BÀI TẬP: BORDER-SPINE-LEAF PURE IPV6 INTERNAL + NAT64 TAYGA
- Kiến trúc vật lý: Lõi mạng (Spine) và Tầng mọc (Leaf) hoạt động hoàn toàn dựa trên IPv6 (Pure IPv6 Data Center).
- Kiến trúc bên ngoài: R1 đóng vai trò Border Router, gắn bộ dịch thuật NAT64 (Tayga) nối thông với IPv4 Internet.
- Giao thức định tuyến: OSPFv3 (thông qua FRRouting) chạy trên toàn bộ Spine/Leaf để học đường đi.
- Công nghệ mạng lõi: Ứng dụng mô hình Overlay VXLAN (L3VNI) giúp các Host giao tiếp không cần biết mạng vật lý.
"""
import os
import sys
import time

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI

class TechVerseCLI(CLI):
    """
    Tuỳ biến dòng lệnh Mininet CLI (dấu nhắc mininet>).
    Cho phép tạo thêm các lệnh tiện ích giúp quản trị viên kích hoạt nhanh các tính năng tường lửa, NAT, hay test lỗi.
    """
    def default(self, line):
        first, args, text = self.parseline(line)
        
        # MẸO NHỎ (HACK): Hỗ trợ ping ngược từ ngoài Internet (IPv4) vào mạng IPv6 bằng hệ thống NAT64 tĩnh.
        # Ở đây ta thay thế ngay trên chuỗi lệnh dòng tên miền để trả về IPv4 Map của Tayga.
        if hasattr(self, 'mn') and first in self.mn and args and args.strip().startswith('ping '):
            node = self.mn[first]
            if first in ['internet', 'serverhcm']:
                args = args.replace('web_server1', '192.168.255.11')
                args = args.replace('web_server2', '192.168.255.12')
                args = args.replace('dns_server1', '192.168.255.21')
                args = args.replace('dns_server2', '192.168.255.22')
                args = args.replace('db_server1', '192.168.255.31')
                args = args.replace('db_server2', '192.168.255.32')
                args = args.replace('serverhcm', '203.162.1.1')
                args = args.replace('internet', '8.8.8.8')
            node.sendCmd(args)
            self.waitForNode(node)
            return

        # Bắt dính lệnh ping6 để tránh Mininet tự động dịch hostname sang IPv4 làm hỏng cấu trúc IPv6.
        if hasattr(self, 'mn') and first in self.mn and args and args.strip().startswith('ping6 '):
            node = self.mn[first]
            node.sendCmd(args)
            self.waitForNode(node)
            return
        super(TechVerseCLI, self).default(line)

    def do_acl(self, line):
        """Khởi động mô hình Tường Lửa Micro-segmentation (Zero Trust) cho IPv6 bằng cách gọi file Script tách rời."""
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'microsegment.sh')
        os.system(f'chmod +x {script} && bash {script}')
        
    def do_failtest(self, line):
        """Giả lập sự cố cúp điện / đứt cáp Spine để xem hệ thống hội tụ."""
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'failover_test.sh')
        os.system(f'chmod +x {script} && bash {script}')

    def do_dropacl(self, line):
        """Lệnh dọn dẹp (Flush) rào chắn Firewall ip6tables. Phục hồi trạng thái mặc định cho phép mọi gói tin đi qua."""
        nodes = ['web_server1', 'web_server2', 'dns_server1', 'dns_server2', 'db_server1', 'db_server2', 's3', 's4', 's5']
        for node in nodes:
            os.system(f"ip netns exec {node} ip6tables -F INPUT 2>/dev/null")
            os.system(f"ip netns exec {node} ip6tables -F FORWARD 2>/dev/null")
        print("Đã xóa hoàn toàn vách ngăn Micro-segmentation! (Cho phép Ping chéo thả ga)")
        
    def do_dropnat(self, line):
        """Lệnh phá hủy module NAT64 Tayga và xoá bảng chuyển tiếp NAT trên con R1."""
        os.system("ip netns exec r1 iptables -t nat -F POSTROUTING 2>/dev/null")
        os.system("ip netns exec r1 killall -9 tayga 2>/dev/null")
        os.system("ip netns exec r1 ip link del nat64 2>/dev/null")
        print("Đã đánh sập Hầm NAT64 và Tường lửa SNAT! (Các máy chủ đã bị chặt đứt đường ra Internet)")

    def do_acl_status(self, line):
        """Lệnh in nguyên trạng thái Filter/Log của ip6tables trên các host quan trọng."""
        for node in ['web_server1', 'dns_server1', 'db_server1', 's3', 's4', 's5']:
            print(f'\n=== {node.upper()} ===')
            print(self.mn[node].cmd('ip6tables -nvL'))
            
    def do_nat(self, line):
        """Khởi động lại tiến trình Tayga NAT64 trên R1."""
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nat_setup.sh')
        os.system(f'chmod +x {script} && bash {script}')

class FRRouter(Node):
    """
    Lớp thiết bị Định tuyến (FRRouter) - Hoạt động độc lập như một Router xịn (dùng mã nguồn FRRouting).
    Kế thừa từ `Node` của Mininet.
    """
    def config(self, **params):
        super(FRRouter, self).config(**params)
        
        # === CẤU HÌNH KERNEL LINUX BẮT BUỘC ===
        # Cho phép Router chịu trách nhiệm chuyển tiếp gói tin (Forwarding) không phải của hệ thống nó.
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
        self.cmd('sysctl -w net.ipv6.conf.all.forwarding=1')
        
        # BẬT TÍNH NĂNG CHIA TẢI ECMP: Multi-path Hash
        # Nếu đường đi (routes) có độ ưu tiên ngang nhau (Equal Cost), cho phép thuật toán băm IP và Băm Port L4
        # để chia đôi băng thông.
        self.cmd('sysctl -w net.ipv4.fib_multipath_hash_policy=1')
        self.cmd('sysctl -w net.ipv6.fib_multipath_hash_policy=1') # Bật L4 Hash cho IPv6 (Rất quan trọng cho VXLAN)
        
        # Tắt việc rà soát IP trùng lặp (DAD) của IPv6 để tiến trình OSPF khởi chạy mạng tức thời (tối ưu hóa).
        self.cmd('sysctl -w net.ipv6.conf.all.accept_dad=0')

        # Dọn dẹp không gian thư mục tạm (/tmp/têntrạm) để lưu cấu hình.
        confDir = f'/tmp/{self.name}'
        self.cmd(f'rm -rf {confDir} && mkdir -p {confDir}')
        self.cmd(f'chmod 777 {confDir}')

        # Khung file config FRR cơ bản (Base Configuration)
        base_conf = (
            f"hostname {self.name}\n"
            "log stdout\n"
            "service advanced-vty\n"
            "!\n"
            "line vty\n"
            " no login\n" # Không cần pass khi truy cập console CLI của Router
            "!\n"
        )
        with open(f'{confDir}/zebra.conf', 'w') as f: f.write(base_conf)
        with open(f'{confDir}/ospf6d.conf', 'w') as f: f.write(base_conf)
        self.cmd(f'chown -R frr:frr {confDir}')
        
        # Khởi chạy Zombie Daemon Zebra (quản lý interface phần cứng gốc) và OSPF6D (động cơ tính toán Routing IPv6)
        self.cmd(f'/usr/lib/frr/zebra -d -u frr -g frr -A 127.0.0.1 -f {confDir}/zebra.conf -i {confDir}/zebra.pid')
        self.cmd(f'/usr/lib/frr/ospf6d -d -u frr -g frr -A 127.0.0.1 -f {confDir}/ospf6d.conf -i {confDir}/ospf6d.pid')

    def terminate(self):
        # Lúc tắt Mininet, tiến hành ám sát các tiến trình chạy ngầm FRR để không nghẽn RAM máy chính.
        self.cmd(f'kill `cat /tmp/{self.name}/ospf6d.pid` 2> /dev/null')
        self.cmd(f'kill `cat /tmp/{self.name}/zebra.pid` 2> /dev/null')
        super(FRRouter, self).terminate()

class LogicNetworkTopo(Topo):
    """
    Bức tranh bản đồ Mạng lưới Topo khổng lồ (Spine - Leaf) xây dựng trên thư viện Mininet Topo.
    Hàm build() sẽ giăng ra các Switch, Host và Dây cáp màng.
    """
    def build(self):
        # 1. Khai báo dàn siêu Router (Core, Spine, Leaf, Border)
        # Tại đây gán nhẵn IP IPv4 ảo (ip='.../32') chỉ để cho mininet khởi chạy hàm mà không bị crash, 
        # Lát nữa sẽ cấp IPv6 thật sau.
        s1 = self.addHost('s1', cls=FRRouter, ip='1.1.1.1/32') # Spine 1 (Lõi chia tải)
        s2 = self.addHost('s2', cls=FRRouter, ip='2.2.2.2/32') # Spine 2 (Lõi chia tải)
        s3 = self.addHost('s3', cls=FRRouter, ip='3.3.3.3/32') # Leaf 3 (Cụm máy chủ Web)
        s4 = self.addHost('s4', cls=FRRouter, ip='4.4.4.4/32') # Leaf 4 (Cụm máy chủ DNS)
        s5 = self.addHost('s5', cls=FRRouter, ip='5.5.5.5/32') # Leaf 5 (Cụm máy chủ Database)
        s7 = self.addHost('s7', cls=FRRouter, ip='7.7.7.7/32') # Core Router Trung tâm Data Center
        r1 = self.addHost('r1', cls=FRRouter, ip='100.100.100.100/32') # Mép mạng Border NAT

        # 2. Khai báo các máy chủ con (End-device IPv6) thuộc từng phân vùng Leaf 
        # Để ip=None vì ta sẽ config IPv6 100% bằng tay chứ không theo chuẩn Mininet IPv4
        web_server1 = self.addHost('web_server1', ip=None)
        web_server2 = self.addHost('web_server2', ip=None)
        dns_server1 = self.addHost('dns_server1', ip=None)
        dns_server2 = self.addHost('dns_server2', ip=None)
        db_server1 = self.addHost('db_server1', ip=None)
        db_server2 = self.addHost('db_server2', ip=None)
        
        # 3. Khai báo Cụm máy chủ Bên ngoài cõi Internet (Sống bằng IPv4)
        serverhcm = self.addHost('serverhcm', ip='203.162.1.1/24', defaultRoute='via 203.162.1.254')
        internet = self.addHost('internet', ip='8.8.8.8/24', defaultRoute='via 8.8.8.254')

        # 4. Kéo cáp từ Core S7 nối về Spines S1, S2 và Border R1
        self.addLink(s7, s1, intfName1='s7-eth0', intfName2='s1-eth0')
        self.addLink(s7, s2, intfName1='s7-eth1', intfName2='s2-eth0')
        self.addLink(s7, r1, intfName1='s7-eth2', intfName2='r1-eth0')
        
        # 5. Kéo cáp cấu trúc Full-Mesh giữa Spine và Leaf (S1 và S2 kết nối đan chéo toàn bộ S3,S4,S5)
        # Spine 1 - Leafs
        self.addLink(s1, s3, intfName1='s1-eth1', intfName2='s3-eth0')
        self.addLink(s1, s4, intfName1='s1-eth2', intfName2='s4-eth0')
        self.addLink(s1, s5, intfName1='s1-eth3', intfName2='s5-eth0')
        # Spine 2 - Leafs
        self.addLink(s2, s3, intfName1='s2-eth1', intfName2='s3-eth1')
        self.addLink(s2, s4, intfName1='s2-eth2', intfName2='s4-eth1')
        self.addLink(s2, s5, intfName1='s2-eth3', intfName2='s5-eth1')
        
        # 6. Kéo cáp truy cập từ Leaf cắm xuống các Server đầu cuối
        self.addLink(s3, web_server1, intfName1='s3-eth2', intfName2='web-eth0')
        self.addLink(s3, web_server2, intfName1='s3-eth3', intfName2='web-eth1')
        self.addLink(s4, dns_server1, intfName1='s4-eth2', intfName2='dns-eth0')
        self.addLink(s4, dns_server2, intfName1='s4-eth3', intfName2='dns-eth1')
        self.addLink(s5, db_server1, intfName1='s5-eth2', intfName2='db-eth0')
        self.addLink(s5, db_server2, intfName1='s5-eth3', intfName2='db-eth1')
        
        # 7. Kéo cáp cõi Internet IPv4 cho Router biên
        self.addLink(r1, serverhcm, intfName1='r1-eth1', intfName2='serverhcm-eth0')
        self.addLink(r1, internet, intfName1='r1-eth2', intfName2='internet-eth0')

def configure_network(net):
    """
    Phần linh hồn của hệ thống. Nạp cấu hình IP, định tuyến và VXLAN lên xương sống Mininet.
    """
    info('*** Liên kết Network Namespace...\n')
    os.system('mkdir -p /var/run/netns')
    # Ánh xạ PID của từng Node trong Mininet vào hệ thống namespace chuẩn của linux (/var/run/netns)
    # Điều này cho phép ta có thể dùng lệnh "ip netns exec [tên]" bên ngoài terminal để tuỳ biến
    for name_str, n in net.nameToNode.items():
        if hasattr(n, 'pid'):
            pid = getattr(n, 'pid')
            os.system(f'ln -sf /proc/{pid}/ns/net /var/run/netns/{name_str}')

    info('*** Gán IPv6 cho Internal Network...\n')
    routers = ['s1', 's2', 's3', 's4', 's5', 's7', 'r1']
    
    # [LOOPBACK]: Mỗi con Router được gán 1 địa chỉ /128 gắn trên Loopback giả lập (mô phỏng Router-ID cực kỳ ổn định).
    for r in routers:
        node = net[r]
        node.cmd("ip -6 addr add fc00:1111::%s/128 dev lo" % (r.replace('s', '').replace('r', '9')))
        
    s1, s2, s3, s4, s5, s7, r1 = [net[x] for x in routers]
    
    # [POINT-TO-POINT]: Cấp địa chỉ IPv6 tĩnh theo chuẩn Subnet /126 cho các liên kết cáp P2P Lõi.
    # Nhánh Core - Spine/Border
    s7.cmd('ip -6 addr add fc00:3::1/126 dev s7-eth0'); s1.cmd('ip -6 addr add fc00:3::2/126 dev s1-eth0')
    s7.cmd('ip -6 addr add fc00:3::5/126 dev s7-eth1'); s2.cmd('ip -6 addr add fc00:3::6/126 dev s2-eth0')
    s7.cmd('ip -6 addr add fc00:3::9/126 dev s7-eth2'); r1.cmd('ip -6 addr add fc00:3::10/126 dev r1-eth0')
    
    # Nhánh Spine S1 - Leaf (3,4,5)
    s1.cmd('ip -6 addr add fc00:1::1/126 dev s1-eth1'); s3.cmd('ip -6 addr add fc00:1::2/126 dev s3-eth0')
    s1.cmd('ip -6 addr add fc00:1::5/126 dev s1-eth2'); s4.cmd('ip -6 addr add fc00:1::6/126 dev s4-eth0')
    s1.cmd('ip -6 addr add fc00:1::9/126 dev s1-eth3'); s5.cmd('ip -6 addr add fc00:1::10/126 dev s5-eth0')
    
    # Nhánh Spine S2 - Leaf (3,4,5)
    s2.cmd('ip -6 addr add fc00:2::1/126 dev s2-eth1'); s3.cmd('ip -6 addr add fc00:2::2/126 dev s3-eth1')
    s2.cmd('ip -6 addr add fc00:2::5/126 dev s2-eth2'); s4.cmd('ip -6 addr add fc00:2::6/126 dev s4-eth1')
    s2.cmd('ip -6 addr add fc00:2::9/126 dev s2-eth3'); s5.cmd('ip -6 addr add fc00:2::10/126 dev s5-eth1')
    
    # [GATEWAY]: Khai báo địa chỉ Gateway mạng nội bộ trên chân của Leaf Switch túc trực.
    s3.cmd('ip -6 addr add fd00:10::254/64 dev s3-eth2; ip -6 addr add fd00:10::254/64 dev s3-eth3')
    s4.cmd('ip -6 addr add fd00:20::254/64 dev s4-eth2; ip -6 addr add fd00:20::254/64 dev s4-eth3')
    s5.cmd('ip -6 addr add fd00:30::254/64 dev s5-eth2; ip -6 addr add fd00:30::254/64 dev s5-eth3')
    
    # [HOSTS]: Gán địa chỉ tĩnh và điều khiển Hướng định tuyến mặc định của các máy trạm đi qua cửa ngõ Gateway.
    net['web_server1'].cmd('ip -6 addr add fd00:10::1/64 dev web-eth0; ip -6 route add default via fd00:10::254')
    net['web_server2'].cmd('ip -6 addr add fd00:10::2/64 dev web-eth1; ip -6 route add default via fd00:10::254')
    net['dns_server1'].cmd('ip -6 addr add fd00:20::1/64 dev dns-eth0; ip -6 route add default via fd00:20::254')
    net['dns_server2'].cmd('ip -6 addr add fd00:20::2/64 dev dns-eth1; ip -6 route add default via fd00:20::254')
    net['db_server1'].cmd('ip -6 addr add fd00:30::1/64 dev db-eth0; ip -6 route add default via fd00:30::254')
    net['db_server2'].cmd('ip -6 addr add fd00:30::2/64 dev db-eth1; ip -6 route add default via fd00:30::254')

    # [BRIDGE L2 LÊN L3]: Giải bài toán gom chân Switch cho các Host.
    # Leaf s3 có 2 máy tính cắm vào cổng eth2 và eth3.
    # Để bọn chúng thông với nhau, sinh ra bộ "Cầu nối ảo - Br0", gom eth2 và eth3 vào Bridge. 
    # Địa chỉ Gateway bây giờ sẽ chuyển lên cắm trên bộ Bridge thay vì từng cổng lẻ tẻ.
    for leaf, net_ip, eth2, eth3 in [(s3, 'fd00:10::254/64', 's3-eth2', 's3-eth3'),
                                     (s4, 'fd00:20::254/64', 's4-eth2', 's4-eth3'),
                                     (s5, 'fd00:30::254/64', 's5-eth2', 's5-eth3')]:
        leaf.cmd('ip link add name br0 type bridge')
        leaf.cmd('ip link set br0 up')
        leaf.cmd(f'ip link set {eth2} master br0') # Cắm dây vào switch ảo br0
        leaf.cmd(f'ip link set {eth3} master br0')
        leaf.cmd(f'ip -6 addr add {net_ip} dev br0') # Trả chùm IP Gateway về Lõi Switch (SVI)
        leaf.cmd(f'ip -6 addr flush dev {eth2}')    # Tẩy trắng IP trên dây thực (Do Bridge xử lý rồi)
        leaf.cmd(f'ip -6 addr flush dev {eth3}')
        
    # [ROUTER XUYÊN MẠNG INTERNET]: Thiết lập IP tĩnh trên R1 đóng vai trò Internet biên.
    r1.cmd('ifconfig r1-eth1 203.162.1.254/24')
    r1.cmd('ifconfig r1-eth2 8.8.8.254/24')
    # Bổ sung ép default route chuẩn để giải quyết lỗi "Network is unreachable" khi gọi chéo.
    net['serverhcm'].cmd('ip route add default via 203.162.1.254 2>/dev/null')
    net['internet'].cmd('ip route add default via 8.8.8.254 2>/dev/null')
    
    net['serverhcm'].cmd('ip route add 192.168.255.0/24 via 203.162.1.254')
    net['internet'].cmd('ip route add 192.168.255.0/24 via 8.8.8.254')
    
    info('*** Không bật NAT mặc định. Hãy dùng lệnh: mininet> nat ...\n')
    time.sleep(2)
    
    info('*** Cấu hình OSPFv3 (ospf6d) cho định tuyến mạng IPv6...\n')
    
    # [HÀM BƠM CẤU HÌNH FRR TỰ ĐỘNG]: Kết nối Netcat (nc) tcp port 2606 trực tiếp với OSPF6 Daemon.
    # Mọi cấu hình Interface/Area0 sẽ được lập trình gõ lệnh như Cisco IOS mà không cần thao tác bằng tay.
    def config_ospf6_via_tcp(node, rid, infts, r_extra=""):
        cmds = f"enable\nconf t\nrouter ospf6\nospf6 router-id {rid}\nexit\n"
        for i in infts:
            if i == 'lo' or i == 'br0':
                cmds += f"interface {i}\nipv6 ospf6 area 0\nexit\n"
            else:
                cmds += f"interface {i}\nipv6 ospf6 area 0\nipv6 ospf6 network point-to-point\nexit\n" # Kéo các cổng vật lý vào Spine-Leaf P2P (Triệt tiêu độ trễ DR/BDR)
        if r_extra:
            cmds += f"router ospf6\n{r_extra}\nexit\n"
        cmds += "end\nwr\nexit\n"
        # Bơm chuỗi lệnh qua TCP 2606 (Port mặc định của OSPF6D VTY) 
        node.cmd(f'echo -e "{cmds}" | nc -w 1 127.0.0.1 2606 | tr -cd \'\\11\\12\\15\\40-\\176\'')

    # Bắn Cấu trúc vào từng Node
    config_ospf6_via_tcp(s7, '7.7.7.7', ['s7-eth0', 's7-eth1', 's7-eth2', 'lo'])
    config_ospf6_via_tcp(s1, '1.1.1.1', ['s1-eth0', 's1-eth1', 's1-eth2', 's1-eth3', 'lo'])
    config_ospf6_via_tcp(s2, '2.2.2.2', ['s2-eth0', 's2-eth1', 's2-eth2', 's2-eth3', 'lo'])
    
    # Ở đây chúng ta BẮT BUỘC phải tiếp tục đưa `br0` vào OSPF. 
    # Lý do: Con Border R1 (cục móp ngoài cùng) KHÔNG HỀ tham gia hầm VXLAN. Nếu không chạy OSPF thả `br0` bay ra ngoài, R1 sẽ mù tịt không biết mạng `fd00:10,20,30` nằm đâu để trả gói tin NAT64 từ Internet về.
    # Trong khi đó, gói tin nội bộ Tenant-to-Tenant giữa S3/S4/S5 vẫn chắc chắn rớt xuống hầm VXLAN vì ta đã cấu hình IP Static MAC Metric 10 (mạnh hơn OSPF).
    config_ospf6_via_tcp(s3, '3.3.3.3', ['s3-eth0', 's3-eth1', 'br0', 'lo'])
    config_ospf6_via_tcp(s4, '4.4.4.4', ['s4-eth0', 's4-eth1', 'br0', 'lo'])
    config_ospf6_via_tcp(s5, '5.5.5.5', ['s5-eth0', 's5-eth1', 'br0', 'lo'])
    
    # [INTERNET ADVERTISEMENT]: Cấu hình cực chuẩn mực của Data Center NAT Router.
    # Quả cầu r1 thay vì chỉ học đường đi, nó phải là kẻ **Tiêm một mũi tiêm (Redistribute Static/Default)** 
    # lan tỏa một tuyến đường Mặc định (::/0) đè xuống toàn bộ Spine-Leaf. 
    # Nhờ vậy máy chủ Server tự biết đường mà quăng các gói tin NAT64 ra r1 mà không bị drop (No Route).
    config_ospf6_via_tcp(r1, '100.100.100.100', ['r1-eth0', 'lo'], "redistribute static\nredistribute kernel\ndefault-information originate always")

    info('*** OSPFv3 đang hội tụ (Tạm đợi 15s)...\n')
    time.sleep(15)
    
    info('*** Thiết lập Tàu Ngầm Overlay VXLAN (VNI 100) chạy trên giao diện Loopback...\n')
    # [VXLAN]: Leaf s3, s4, s5 đóng vai trò VTEP (Các trạm thu phát của đường hầm).
    for leaf, ip, v6_lo in [('s3', 'fc00:100::3/64', 'fc00:1111::3'), 
                            ('s4', 'fc00:100::4/64', 'fc00:1111::4'), 
                            ('s5', 'fc00:100::5/64', 'fc00:1111::5')]:
        node = net[leaf]
        # Tạo đường ống VXLAN (ID 100), đóng gói bọc Frame lại và định tuyến dựa trên IP Nguồn VTEP (local v6_lo)
        node.cmd(f'ip -6 link add vxlan100 type vxlan id 100 dstport 4789 local {v6_lo}')
        node.cmd('ip link set vxlan100 up')
        node.cmd(f'ip -6 addr add {ip} dev vxlan100')

    # [BẢNG FDB ĐA CHIỀU (MESH MAPPING)]: Vì không có Controller ngoài, ta phải chỉ rõ đích đến cho VXLAN (Unicast)
    # Nếu đang ở S3, ngõ ra VXLAN sẽ được băm hướng về Loopback của S4(..::4) hoặc S5(..::5)
    s3.cmd('bridge fdb append 00:00:00:00:00:00 dev vxlan100 dst fc00:1111::4')
    s3.cmd('bridge fdb append 00:00:00:00:00:00 dev vxlan100 dst fc00:1111::5')
    
    s4.cmd('bridge fdb append 00:00:00:00:00:00 dev vxlan100 dst fc00:1111::3')
    s4.cmd('bridge fdb append 00:00:00:00:00:00 dev vxlan100 dst fc00:1111::5')

    s5.cmd('bridge fdb append 00:00:00:00:00:00 dev vxlan100 dst fc00:1111::3')
    s5.cmd('bridge fdb append 00:00:00:00:00:00 dev vxlan100 dst fc00:1111::4')
    
    info('*** Cấu hình L3VNI (Điều hướng Gói tin của Server đi qua Đường hầm VXLAN)...\n')
    # Ở giai đoạn này: Thay vì cho phép OSPF dẫn gói tin User băng ngang lõi Spine (Metric 20 mặc định),
    # Ta ép các Subnet đích cưỡng chế phải bị nhét vào ống VXLAN bằng IP Route tĩnh (Metric 10 nhỏ hơn -> Ưu tiên hơn).
    
    # S3 (Cụm Web) muốn qua DNS (20) hoặc DB (30), phải trườn vào ống vxlan!
    s3.cmd('ip -6 route add fd00:20::/64 via fc00:100::4 dev vxlan100 metric 10')
    s3.cmd('ip -6 route add fd00:30::/64 via fc00:100::5 dev vxlan100 metric 10')

    # S4 (Cụm DNS) muốn qua Web (10) hoặc DB (30), ngóc đầu qua vxlan!
    s4.cmd('ip -6 route add fd00:10::/64 via fc00:100::3 dev vxlan100 metric 10')
    s4.cmd('ip -6 route add fd00:30::/64 via fc00:100::5 dev vxlan100 metric 10')

    # S5 (Cụm DB) truy vết ngược về Web(10) và DNS(20) thông qua hầm!
    s5.cmd('ip -6 route add fd00:10::/64 via fc00:100::3 dev vxlan100 metric 10')
    s5.cmd('ip -6 route add fd00:20::/64 via fc00:100::4 dev vxlan100 metric 10')
    
    info('*** Cấy ghép DNS nội bộ (Local /etc/hosts) giả lập cho toàn bộ Môi trường...\n')
    # Ánh xạ tên miền (Domain Name) -> Địa chỉ IP (A/AAAA Record). 
    # Áp dụng chung cho file host của hệ thống để lệnh 'ping6 db_server1' phân giải thành chữ hoàn chỉnh.
    hosts_entries = (
        "\n# MININET-DNS-MAPPING-START\n"
        "fd00:10::1 web_server1\n"
        "fd00:10::2 web_server2\n"
        "fd00:20::1 dns_server1\n"
        "fd00:20::2 dns_server2\n"
        "fd00:30::1 db_server1\n"
        "fd00:30::2 db_server2\n"
        "64:ff9b::203.162.1.1 serverhcm\n" # Cấu hình ánh xạ NAT64 Public ảo
        "64:ff9b::808:808 internet\n"      # Ánh xạ Internet ảo qua IPv6 NAT64
        "# MININET-DNS-MAPPING-END\n"
    )
    # Cắt xén sạch rác cũ (nếu có) và đóng dấu khối dữ liệu mới.
    os.system("sed -i '/# MININET-DNS-MAPPING-START/,/# MININET-DNS-MAPPING-END/d' /etc/hosts")
    with open('/etc/hosts', 'a') as f:
        f.write(hosts_entries)

def mn_cleanup():
    """Bộ càn quét khổng lồ: Thanh trừng tất cả process Zombie rác, nhả lại RAM và Network sau khi ấn Ctrl+C."""
    info('*** Dọn rác hệ thống (Flush Clean)...\n')
    os.system('rm -rf /var/run/netns/web* /var/run/netns/dns* /var/run/netns/db* 2>/dev/null')
    os.system("sed -i '/# MININET-DNS-MAPPING-START/,/# MININET-DNS-MAPPING-END/d' /etc/hosts 2>/dev/null")
    os.system('sudo mn -c 2>/dev/null')
    os.system('sudo killall -9 zebra ospf6d tayga 2>/dev/null')

def run():
    """Hàm Khởi Nguồn: Cầm trịch toàn bộ quá trình dựng hình và điều hướng."""
    topo = LogicNetworkTopo()
    # Mininet sinh ra Topo không cần thiết lập Controller tập trung (POX/RYU).
    # Vì sao? Vì trí não của Mạng nằm tự phân tán tại các Router chạy OSPF (Distributed Routing).
    net = Mininet(topo=topo, controller=None)
    net.start()
    
    # Kích quy trình gán IP + Mở Cáp
    configure_network(net)
    
    # In ra một số lời thì thầm chào mời để user biết phải xài cái gì.
    info('    mininet> web_server1 ping6 dns_server1  (Khảo sát IPv6 East-West Routing)\n')
    info('    mininet> web_server1 ping 203.162.1.1   (Test Biên dịch Dữ liệu NAT64 To IPv4 Public)\n')
    info('    mininet> acl                            (Trải nghiệm Tường lửa vi mô theo Zero Trust)\n')
    
    # Neo màn hình tại Command Line tự tạo
    TechVerseCLI(net)
    
    # Kết xuất, rút quân!
    net.stop()

if __name__ == '__main__':
    # Chỉ định màn in Mức Thông báo (Info) để debug
    setLogLevel('info')
    
    # Bắt tín hiệu cờ Dọn Rác từ Argument terminal
    if '--clean' in sys.argv or '-c' in sys.argv:
        mn_cleanup()
        sys.exit(0)
    
    # Bức nền Mininet yêu cầu quyền tối cao (Root - Sudo) để tạo Network Namespace ẩn (Veth pairs)
    if os.geteuid() != 0:
        print('Cảnh báo Quyền Truy cập: Hãy sử dụng quyền ROOT để chạy (sudo python3 topology.py)')
        sys.exit(1)
        
    mn_cleanup()
    run()
