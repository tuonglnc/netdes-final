#!/usr/bin/env python3
import os, time, re, threading, datetime
import tkinter as tk
from tkinter import ttk, scrolledtext
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "system.log")

# ================= AUTO DETECT NODES =================
def get_nodes():
    # Lấy từ tiến trình Mininet
    out = os.popen("ps aux | grep mnexec | grep -v grep").read()

    nodes = set()
    for line in out.split("\n"):
        m = re.search(r'-n (\w+)', line)
        if m:
            nodes.add(m.group(1))

    nodes = sorted(list(nodes))

    # Fallback nếu detect fail
    if not nodes:
        nodes = [
            "h1","h2","h3","h4",
            "h5","h6","h7","h8","h9","h10",
            "s1","s2","s3","s4","s5","s6",
            "ce1","ce2","ce3",
            "pe1","pe2","pe3",
            "p1","p2","p3","p4"
        ]

    return nodes

# ================= CORE =================
def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n")

def exec_cmd(node, cmd):
    return os.popen(f"sudo mnexec -a $(pgrep -f 'mininet:{node}') {cmd} 2>/dev/null").read()

def get_ip(node):
    out = exec_cmd(node, "hostname -I")
    ips = out.strip().split()
    return ips[0] if ips else None

# ================= TEST =================
def ping_test(src, dst):
    ip = get_ip(dst)
    if not ip:
        return -1, 100, "No IP"

    out = exec_cmd(src, f"ping -c 4 {ip}")

    rtt = re.search(r'=\s*[\d\.]+/([\d\.]+)/', out)
    loss = re.search(r'(\d+)% packet loss', out)

    return float(rtt.group(1)) if rtt else -1, int(loss.group(1)) if loss else 100, out

def traceroute_test(src, dst):
    ip = get_ip(dst)
    if not ip:
        return "No IP"

    return exec_cmd(src, f"traceroute -n -m 6 {ip}")

def throughput_test(src, dst):
    ip = get_ip(dst)
    if not ip:
        return 0

    exec_cmd(dst, "pkill iperf")
    exec_cmd(dst, "iperf -s -D")
    time.sleep(1)

    out = exec_cmd(src, f"iperf -c {ip} -t 4 -f m")
    m = re.search(r'([\d\.]+)\s*Mbits/sec', out)

    exec_cmd(dst, "pkill iperf")
    return float(m.group(1)) if m else 0

# ================= GUI =================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MPLS Metro Monitoring Tool")
        self.geometry("900x600")

        self.nodes = get_nodes()

        # Combo
        frame = tk.Frame(self)
        frame.pack()

        self.cb_src = ttk.Combobox(frame, values=self.nodes, width=20)
        self.cb_dst = ttk.Combobox(frame, values=self.nodes, width=20)

        if self.nodes:
            self.cb_src.set(self.nodes[0])
            self.cb_dst.set(self.nodes[-1])

        self.cb_src.pack(side=tk.LEFT, padx=5)
        self.cb_dst.pack(side=tk.LEFT, padx=5)

        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack()

        ttk.Button(btn_frame, text="Ping", command=self.ping).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Traceroute", command=self.trace).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Throughput", command=self.bw).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Stress Test", command=self.stress).pack(side=tk.LEFT, padx=5)

        # Log
        self.txt = scrolledtext.ScrolledText(self, bg="black", fg="lime")
        self.txt.pack(expand=True, fill=tk.BOTH)

    def log(self, msg):
        self.txt.insert(tk.END, msg + "\n")
        self.txt.see(tk.END)
        log(msg)

    def ping(self):
        threading.Thread(target=self._ping).start()

    def _ping(self):
        s, d = self.cb_src.get(), self.cb_dst.get()
        rtt, loss, _ = ping_test(s, d)
        self.log(f"{s} -> {d} | RTT={rtt} ms | Loss={loss}%")

    def trace(self):
        threading.Thread(target=self._trace).start()

    def _trace(self):
        s, d = self.cb_src.get(), self.cb_dst.get()
        out = traceroute_test(s, d)
        self.log(out)

    def bw(self):
        threading.Thread(target=self._bw).start()

    def _bw(self):
        s, d = self.cb_src.get(), self.cb_dst.get()
        bw = throughput_test(s, d)
        self.log(f"{s} -> {d} | BW={bw} Mbps")

    def stress(self):
        threading.Thread(target=self._stress).start()

    def _stress(self):
        s, d = self.cb_src.get(), self.cb_dst.get()
        self.log("Running stress test...")

        ip = get_ip(d)
        if not ip:
            self.log("No IP for destination")
            return

        exec_cmd(d, "pkill iperf")
        exec_cmd(d, "iperf -s -D")
        exec_cmd(s, f"iperf -c {ip} -t 10 -P 4 &")

        rtts = []
        for _ in range(10):
            rtt, _, _ = ping_test(s, d)
            rtts.append(rtt if rtt > 0 else 0)
            time.sleep(1)

        plt.plot(rtts)
        path = os.path.join(LOG_DIR, "stress.png")
        plt.savefig(path)
        plt.close()

        exec_cmd(d, "pkill iperf")

        self.log(f"Saved graph: {path}")

# ================= MAIN =================
if __name__ == "__main__":
    app = App()
    app.mainloop()