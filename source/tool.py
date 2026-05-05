#!/usr/bin/env python3
import sys, os, time, re, threading, datetime, csv
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LOG_DIR = os.path.join(os.getcwd(), "test_results")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "system_report.log")

def log_to_file(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")

IP_MAP = {
    'h1': '192.168.1.11', 'h2': '192.168.1.12',
    'h5': '192.168.20.15', 'h6': '192.168.20.16',
    's1': '192.168.30.11', 's2': '192.168.30.12'
}
NODES = list(IP_MAP.keys())

def exec_netns(node, cmd):
    # Lấy PID của quá trình bash đang chạy trong node Mininet
    cmd_get_pid = f"ps -aef | grep -E 'mininet:{node}($|\\s)' | grep -v grep | awk '{{print $2}}'"
    pid = os.popen(cmd_get_pid).read().strip()
    if pid:
        pid = pid.split('\n')[0]
        # Dùng nsenter để xâm nhập vào network namespace (-n) của PID đó
        full_cmd = f"sudo nsenter -t {pid} -n {cmd} 2>/dev/null"
        return os.popen(full_cmd).read()
    else:
        # Dự phòng nếu không tìm thấy, thử dùng ip netns (trường hợp đã link sẵn namespace)
        return os.popen(f"sudo ip netns exec {node} {cmd} 2>/dev/null").read()

def measure_rtt(src, dst):
    ip = IP_MAP[dst]
    out = exec_netns(src, f"ping -c 4 -W 1 -q {ip}")
    m = re.search(r'rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)', out)
    # Ubuntu ping output có thể khác xíu (min/avg/max/mdev)
    if not m: m = re.search(r'min/avg/max/[^=]+=\s*([\d\.]+)/([\d\.]+)/', out)
    loss_m = re.search(r'(\d+)% packet loss', out)
    loss = int(loss_m.group(1)) if loss_m else 100
    if m:
        avg_rtt = float(m.group(2))
        jitter = float(m.group(4)) if len(m.groups()) >= 4 else 0.0
        return avg_rtt, loss, jitter, out
    return -1.0, loss, 0.0, out

def measure_throughput(src, dst):
    ip = IP_MAP[dst]
    exec_netns(dst, "killall -9 iperf >/dev/null 2>&1")
    exec_netns(src, "killall -9 iperf >/dev/null 2>&1")
    exec_netns(dst, "iperf -s -D >/dev/null 2>&1")
    time.sleep(1)
    out = exec_netns(src, f"iperf -c {ip} -t 5 -f m")
    m = re.search(r'([\d\.]+)\s*Mbits/sec', out)
    exec_netns(dst, "killall -9 iperf >/dev/null 2>&1")
    return float(m.group(1)) if m else 0.0

def measure_path(src, dst):
    ip = IP_MAP[dst]
    out = exec_netns(src, f"traceroute -n -m 5 {ip} | tail -n +2")
    return out.strip()


class AppTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Công cụ Đo lường Metro Ethernet MPLS")
        self.geometry("950x650")
        self.configure(bg="#2d2d2d")
        
        lbl_title = tk.Label(self, text="HỆ THỐNG KIỂM THỬ MẠNG", font=("Arial", 16, "bold"), fg="white", bg="#2d2d2d", pady=15)
        lbl_title.pack()
        
        main_frame = tk.Frame(self, bg="#2d2d2d")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
        
        left_panel = tk.LabelFrame(main_frame, text=" Tương tác & Log ", bg="#f0f0f0", font=("Arial", 11, "bold"), padx=10, pady=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        f_srcdst = tk.Frame(left_panel, bg="#f0f0f0")
        f_srcdst.pack(fill=tk.X, pady=5)
        
        tk.Label(f_srcdst, text="Nguồn:", bg="#f0f0f0").grid(row=0, column=0)
        self.cb_src = ttk.Combobox(f_srcdst, values=NODES, state="readonly", width=10)
        self.cb_src.set(NODES[0])
        self.cb_src.grid(row=0, column=1, padx=5)
        
        tk.Label(f_srcdst, text="Đích:", bg="#f0f0f0").grid(row=0, column=2, padx=(10,0))
        self.cb_dst = ttk.Combobox(f_srcdst, values=NODES, state="readonly", width=10)
        self.cb_dst.set(NODES[-1])
        self.cb_dst.grid(row=0, column=3, padx=5)
        
        f_btn = tk.Frame(left_panel, bg="#f0f0f0")
        f_btn.pack(fill=tk.X, pady=15)
        ttk.Button(f_btn, text="Ping Test", command=lambda: self.run_test('ping')).pack(side=tk.LEFT, padx=5)
        ttk.Button(f_btn, text="[YC 4.4] Traceroute MPLS", command=lambda: self.run_test('path')).pack(side=tk.LEFT, padx=5)
        ttk.Button(f_btn, text="Iperf Throughput", command=lambda: self.run_test('bw')).pack(side=tk.LEFT, padx=5)
        
        self.txt_log = scrolledtext.ScrolledText(left_panel, width=50, height=15, bg="black", fg="#00ff00", font=("Consolas", 10))
        self.txt_log.pack(fill=tk.BOTH, expand=True, pady=5)
        
        right_panel = tk.LabelFrame(main_frame, text=" KẾT QUẢ THEO ĐỀ TÀI (MỤC 4) ", bg="#f0f0f0", font=("Arial", 11, "bold"), padx=10, pady=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=5)
        
        ttk.Button(right_panel, text="[YC 4.1] Bảng Thống kê Hiệu năng (CSV)", command=self.export_stats).pack(fill=tk.X, pady=5)
        ttk.Button(right_panel, text="[YC 4.2] Biểu đồ Băng thông Chi nhánh", command=self.chart_throughput).pack(fill=tk.X, pady=5)
        ttk.Button(right_panel, text="[YC 4.2] Biểu đồ Độ trễ & Loss", command=self.chart_delay).pack(fill=tk.X, pady=5)
        ttk.Button(right_panel, text="[YC 4.2] Biểu đồ Stress Test Nặng", command=self.stress_test).pack(fill=tk.X, pady=5)
        ttk.Button(right_panel, text="[YC 4.3] Báo cáo Phân tích LAN (MD)", command=self.generate_lan_report).pack(fill=tk.X, pady=5)
        
        self.log_ui("HỆ THỐNG ĐÃ SẴN SÀNG.")
        self.log_ui(f"Kết quả tự động lưu tại: {LOG_DIR}")
        
    def log_ui(self, msg):
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)
        self.update()
        log_to_file(msg)
        
    def run_test(self, action):
        src, dst = self.cb_src.get(), self.cb_dst.get()
        if src == dst:
            messagebox.showerror("Lỗi", "Nguồn và đích phải khác nhau!")
            return
            
        def task():
            self.log_ui(f"--- Đang chạy bài kiểm tra [{action.upper()}] từ {src} -> {dst} ---")
            if action == 'ping':
                rtt, loss, jitter, out = measure_rtt(src, dst)
                self.log_ui(f"RTT Avg: {rtt} ms | Jitter (mdev): {jitter} ms | Packet Loss: {loss}%")
                if loss > 0: self.log_ui(f"Log thô:\n{out}")
            elif action == 'path':
                pth = measure_path(src, dst)
                self.log_ui(f"Traceroute:\n{pth}")
            elif action == 'bw':
                bw = measure_throughput(src, dst)
                self.log_ui(f"Thông lượng: {bw} Mbps")
                
        threading.Thread(target=task, daemon=True).start()
        
    def chart_throughput(self):
        def task():
            self.log_ui("Đang đo lường băng thông giữa các chi nhánh...")
            cases = [('h1', 'h5'), ('h1', 's1'), ('h5', 's1')]
            bws = []
            labels = []
            for src, dst in cases:
                bw = measure_throughput(src, dst)
                bws.append(bw)
                labels.append(f"{src} -> {dst}")
                self.log_ui(f" {src}->{dst}: {bw} Mbps")
                
            fig, ax = plt.subplots(figsize=(6,4))
            ax.bar(labels, bws, color=['#E63946', '#457B9D', '#2A9D8F'])
            ax.set_ylabel("Băng thông (Mbps)")
            ax.set_title("Biểu đồ So sánh Băng thông Liên Chi nhánh")
            for i, v in enumerate(bws): ax.text(i, v+0.5, str(v), ha='center')
            
            p = os.path.join(LOG_DIR, "throughput_comparison.png")
            fig.savefig(p)
            plt.close(fig)
            self.log_ui(f"Đã lưu biểu đồ: {p}")
            messagebox.showinfo("Hoàn thành", "Đã kết xuất biểu đồ băng thông!")
            
        threading.Thread(target=task, daemon=True).start()
        
    def chart_delay(self):
        def task():
            self.log_ui("Đang đo lường độ trễ (Delay) và Ping...")
            cases = [('h1', 'h5'), ('h1', 's1'), ('h5', 's1')]
            rtts = []
            labels = []
            for src, dst in cases:
                rtt, _, _, _ = measure_rtt(src, dst)
                rtts.append(rtt if rtt > 0 else 0)
                labels.append(f"{src} -> {dst}")
                self.log_ui(f" {src}->{dst}: RTT Avg = {rtt} ms")
                
            fig, ax = plt.subplots(figsize=(6,4))
            ax.bar(labels, rtts, color=['#F4A261', '#E9C46A', '#E76F51'])
            ax.set_ylabel("Độ trễ trung bình - RTT (ms)")
            ax.set_title("Biểu đồ So sánh Độ trễ (Delay)")
            for i, v in enumerate(rtts): ax.text(i, v+0.5, str(v), ha='center')
            
            p = os.path.join(LOG_DIR, "delay_comparison.png")
            fig.savefig(p)
            plt.close(fig)
            self.log_ui(f"Đã lưu biểu đồ: {p}")
            messagebox.showinfo("Hoàn thành", "Đã kết xuất biểu đồ độ trễ!")
            
        threading.Thread(target=task, daemon=True).start()

    def export_stats(self):
        def task():
            self.log_ui("Đang thu thập số liệu thống kê hiệu năng (Throughput, Delay, Loss, Jitter)...")
            cases = [('h1', 'h5'), ('h1', 's1'), ('h5', 's1')]
            stats_file = os.path.join(LOG_DIR, "performance_stats.csv")
            with open(stats_file, 'w', newline='', encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Source", "Destination", "Throughput_Mbps", "Delay_ms", "Jitter_ms", "Packet_Loss_%"])
                for src, dst in cases:
                    self.log_ui(f"  Đo lường {src} -> {dst}...")
                    bw = measure_throughput(src, dst)
                    rtt, loss, jitter, _ = measure_rtt(src, dst)
                    w.writerow([src, dst, bw, rtt, jitter, loss])
                    self.log_ui(f"    => BW: {bw} Mbps, RTT: {rtt} ms, Jitter: {jitter} ms, Loss: {loss}%")
            self.log_ui(f"Đã xuất bảng thống kê: {stats_file}")
            messagebox.showinfo("Hoàn thành", f"Đã lưu thống kê ra file {stats_file}!")
        threading.Thread(target=task, daemon=True).start()

    def stress_test(self):
        def task():
            self.log_ui("Khởi chạy Stress Test bằng ngập lụt Ping + Iperf...")
            # Mở một luồng iperf gây quá tải băng thông
            exec_netns('s1', "iperf -s -D >/dev/null 2>&1")
            exec_netns('h1', "iperf -c 192.168.30.11 -t 15 -P 4 >/dev/null 2>&1 &")
            
            self.log_ui("Đang đo Ping RTT và Packet Loss khi có tải liên tục 10s...")
            rtts = []
            losses = []
            times = []
            for i in range(10):
                rtt, loss, _, _ = measure_rtt('h5', 's1')
                rtts.append(max(0, rtt))
                losses.append(loss)
                times.append(i)
                time.sleep(1)
                
            exec_netns('s1', "killall -9 iperf >/dev/null 2>&1")
            exec_netns('h1', "killall -9 iperf >/dev/null 2>&1")
            
            fig, ax1 = plt.subplots(figsize=(6,4))
            ax1.plot(times, rtts, marker='o', linestyle='-', color='red', label='Độ trễ (ms)')
            ax1.set_xlabel("Thời gian (s)")
            ax1.set_ylabel("Độ trễ (ms)", color='red')
            ax1.tick_params(axis='y', labelcolor='red')
            
            ax2 = ax1.twinx()
            ax2.plot(times, losses, marker='x', linestyle='--', color='blue', label='Packet Loss (%)')
            ax2.set_ylabel("Packet Loss (%)", color='blue')
            ax2.tick_params(axis='y', labelcolor='blue')
            
            plt.title("Biến động Độ trễ & Packet Loss khi Stress Mạng")
            ax1.grid(True)
            
            p = os.path.join(LOG_DIR, "stress_test_metrics.png")
            fig.savefig(p)
            plt.close(fig)
            
            with open(os.path.join(LOG_DIR, "stress_test.csv"), 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Time_s", "Delay_ms", "PacketLoss_%"])
                for idx, t in enumerate(times): w.writerow([t, rtts[idx], losses[idx]])
                
            self.log_ui(f"Stress test hoàn thành. Export: {p} và data CSV.")
            messagebox.showinfo("Hoàn thành", "Stress test đã xong!")
            
        threading.Thread(target=task, daemon=True).start()

    def generate_lan_report(self):
        def task():
            self.log_ui("Đang đo lường và sinh báo cáo phân tích LAN (YC 4.3)...")
            
            # Đo đạc Branch 1 (Mạng phẳng)
            self.log_ui(" Đo lường Chi nhánh 1 (h1 -> h2)...")
            b1_rtt, _, _, _ = measure_rtt('h1', 'h2')
            b1_bw = measure_throughput('h1', 'h2')
            b1_path = len(measure_path('h1', 'h2').strip().split('\n')) if b1_rtt > 0 else 0
            
            # Đo đạc Branch 2 (Mạng 3 lớp)
            self.log_ui(" Đo lường Chi nhánh 2 (h5 -> h6)...")
            b2_rtt, _, _, _ = measure_rtt('h5', 'h6')
            b2_bw = measure_throughput('h5', 'h6')
            b2_path = len(measure_path('h5', 'h6').strip().split('\n')) if b2_rtt > 0 else 0
            
            # Đo đạc Branch 3 (Spine-Leaf)
            self.log_ui(" Đo lường Chi nhánh 3 (s1 -> s2)...")
            b3_rtt, _, _, _ = measure_rtt('s1', 's2')
            b3_bw = measure_throughput('s1', 's2')
            b3_path = len(measure_path('s1', 's2').strip().split('\n')) if b3_rtt > 0 else 0
            
            report_file = os.path.join(LOG_DIR, "LAN_Architecture_Analysis.md")
            
            report_content = f"""# Phân tích Kiến trúc LAN (Yêu cầu 4.3)

*Báo cáo này được tạo tự động dựa trên số liệu đo lường trực tiếp từ Topology Mininet.*

## 1. Chi nhánh 1 (Mạng phẳng - Flat Network)
- **Đo lường nội bộ (h1 -> h2):** Độ trễ RTT: `{b1_rtt} ms` | Thông lượng: `{b1_bw} Mbps` | Số lượng Hop (Traceroute): `{b1_path}`
- **Đặc điểm:** Tất cả thiết bị chung 1 Broadcast Domain, dùng STP.
- **Phân tích:** Do các máy tính kết nối trực tiếp qua Switch L2 (0 hop routing), độ trễ nội bộ rất thấp. Tuy nhiên cấu hình đơn giản này dễ xảy ra Broadcast storm, hội tụ STP chậm. Không tối ưu cho số lượng thiết bị lớn.
- **Tương tác MPLS:** Khi ping qua mạng MPLS Backbone, độ trễ và thông lượng sẽ bị ảnh hưởng nếu mạng nội bộ đang bị tắc nghẽn ARP.

## 2. Chi nhánh 2 (Mạng 3 lớp - Core/Distribution/Access)
- **Đo lường nội bộ (h5 -> h6):** Độ trễ RTT: `{b2_rtt} ms` | Thông lượng: `{b2_bw} Mbps` | Số lượng Hop (Traceroute): `{b2_path}`
- **Đặc điểm:** Chia tầng rõ rệt, định tuyến OSPF nội bộ.
- **Phân tích:** Khả năng mở rộng cực cao, dự phòng tốt, kiểm soát luồng giao thông hiệu quả. 
- **Tương tác MPLS:** Rất phù hợp để tích hợp với BGP Edge của ISP (Router PE).

## 3. Chi nhánh 3 (Mạng Spine-Leaf 2 lớp)
- **Đo lường nội bộ (s1 -> s2):** Độ trễ RTT: `{b3_rtt} ms` | Thông lượng: `{b3_bw} Mbps` | Số lượng Hop (Traceroute): `{b3_path}`
- **Đặc điểm:** Mọi Switch Access (Leaf) kết nối tới tất cả Switch Lõi (Spine) tạo thành Full-mesh.
- **Phân tích:** Băng thông nội bộ cực cao (East-West traffic), ECMP load-balancing siêu tốc. Bất kỳ 2 host nào cũng chỉ cách nhau 1 hop Spine nên mức độ trễ rất ổn định và thông lượng tiệm cận giới hạn cáp.
- **Tương tác MPLS:** Kiến trúc này kết hợp hoàn hảo với MPLS Backbone để đẩy dữ liệu lớn từ cụm Server nội bộ ra chi nhánh khác với thông lượng cao nhất.
"""
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            self.log_ui("==============================")
            self.log_ui("ĐÃ XUẤT BÁO CÁO PHÂN TÍCH LAN (MD):")
            self.log_ui(" - File: " + report_file)
            self.log_ui("==============================")
            messagebox.showinfo("Hoàn thành", f"Đã kết xuất báo cáo phân tích LAN ra file:\n{report_file}")
            
        threading.Thread(target=task, daemon=True).start()

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("Lưu ý: Bạn nên chạy tool bằng quyền SUDO hoặc tool sẽ tự nhúng sudo.")
    app = AppTool()
    app.mainloop()
