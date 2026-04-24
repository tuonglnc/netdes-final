#!/usr/bin/env python3
"""
MÔ HÌNH 1: MẠNG PHẲNG (FLAT NETWORK)
Tất cả 69 host chung 10.0.0.0/16 | r1 = Edge Router + WAN Gateway
s1 (Block A): admin1-5, lab1-20, r1-LAN, trunk  (27/48 port)
s2 (Block B): dorm1-40, srv1-4, trunk            (45/48 port)
"""

import os, sys, subprocess, time
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from mininet.net import Mininet
from mininet.node import Host, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

GRAPH_OUTPUT = 'level1_flat_topology.png'

class LinuxRouter(Host):
    def config(self, **params):
        super().config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        super().terminate()

def cleanup_mininet():
    info('*** mn -c cleanup...\n')
    subprocess.run(['sudo','mn','-c'], capture_output=True, timeout=30)

def draw_topology_graph():
    G = nx.Graph()
    nodes = {
        'r1':        ('router',  'r1\n10.0.0.254\n(GW+WAN)'),
        's1':        ('switch',  's1 (Block A)\n27/48 port'),
        's2':        ('switch',  's2 (Block B)\n45/48 port'),
        'serverhcm': ('wan',     'serverhcm\n203.162.1.1'),
        'ADMIN\n(5)':('admin',   'admin1-5\n10.0.1.x/16'),
        'LAB\n(20)': ('lab',     'lab1-20\n10.0.2.x/16'),
        'DORM\n(40)':('dorm',    'dorm1-40\n10.0.3.x/16'),
        'SRV\n(4)':  ('srv',     'srv1-4\n10.0.4.x/16'),
    }
    for n,(t,lbl) in nodes.items(): G.add_node(n, type=t, label=lbl)
    G.add_edge('serverhcm','r1')
    G.add_edge('r1','s1')
    G.add_edge('s1','s2')
    G.add_edge('s1','ADMIN\n(5)')
    G.add_edge('s1','LAB\n(20)')
    G.add_edge('s2','DORM\n(40)')
    G.add_edge('s2','SRV\n(4)')
    pos = {'serverhcm':(0,4),'r1':(0,3),'s1':(-2,2),'s2':(2,2),
           'ADMIN\n(5)':(-4,0),'LAB\n(20)':(-1,0),
           'DORM\n(40)':(1,0),'SRV\n(4)':(4,0)}
    colors = {'router':'#9B59B6','switch':'#E63946','wan':'#C0392B',
              'admin':'#457B9D','lab':'#2A9D8F','dorm':'#E9C46A','srv':'#264653'}
    nc = [colors[G.nodes[n]['type']] for n in G.nodes()]
    fig,ax = plt.subplots(figsize=(14,8))
    fig.patch.set_facecolor('#1a1a2e'); ax.set_facecolor('#1a1a2e')
    nx.draw(G, pos, ax=ax, node_color=nc, node_size=2000,
            labels={n:G.nodes[n]['label'] for n in G.nodes()},
            font_size=7, font_color='white', font_weight='bold',
            edge_color='#aaaaaa', width=2)
    ax.set_title('MÔ HÌNH 1: MẠNG PHẲNG | 10.0.0.0/16 | 1 Broadcast Domain',
                 color='#E63946', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(GRAPH_OUTPUT, dpi=120, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close()
    info(f'*** Topology saved: {GRAPH_OUTPUT}\n')

# ── BUILD NET: dùng bởi test.py (import cauhinh1; net = cauhinh1.build_net()) ──
def build_net():
    """Build + configure mạng phẳng, trả về net object (KHÔNG gọi CLI)."""
    cleanup_mininet()
    net = Mininet(controller=None, link=TCLink, autoSetMacs=True)
    r1 = net.addHost('r1', cls=LinuxRouter, ip='10.0.0.254/16')
    s1 = net.addSwitch('s1', cls=OVSSwitch, failMode='standalone')
    s2 = net.addSwitch('s2', cls=OVSSwitch, failMode='standalone')
    serverhcm = net.addHost('serverhcm', ip='203.162.1.1/24')
    for i in range(1, 6):
        net.addHost(f'admin{i}', ip=f'10.0.1.{i}/16', defaultRoute='via 10.0.0.254')
    for i in range(1, 21):
        net.addHost(f'lab{i}', ip=f'10.0.2.{i}/16', defaultRoute='via 10.0.0.254')
    for i in range(1, 41):
        net.addHost(f'dorm{i}', ip=f'10.0.3.{i}/16', defaultRoute='via 10.0.0.254')
    for i in range(1, 5):
        net.addHost(f'srv{i}', ip=f'10.0.4.{i}/16', defaultRoute='via 10.0.0.254')
    net.addLink(r1, s1, intfName1='r1-eth0', bw=1000)
    net.addLink(r1, serverhcm, intfName1='r1-eth1', intfName2='hcm-eth0', bw=200, delay='10ms')
    net.addLink(s1, s2, bw=1000)
    for i in range(1, 6):  net.addLink(net.get(f'admin{i}'), s1, bw=100)
    for i in range(1, 21): net.addLink(net.get(f'lab{i}'),   s1, bw=1000)
    for i in range(1, 41): net.addLink(net.get(f'dorm{i}'),  s2, bw=50)
    for i in range(1, 5):  net.addLink(net.get(f'srv{i}'),   s2, bw=1000)
    info('*** Starting network...\n')
    net.start()
    r1.cmd('ip link set r1-eth0 up; ip addr flush dev r1-eth0; ip addr add 10.0.0.254/16 dev r1-eth0')
    r1.cmd('ip link set r1-eth1 up; ip addr flush dev r1-eth1; ip addr add 203.162.1.254/24 dev r1-eth1')
    r1.cmd('sysctl -w net.ipv4.ip_forward=1')
    r1.cmd('for f in /proc/sys/net/ipv4/conf/*/rp_filter; do echo 0 > $f; done')
    serverhcm.cmd('ip link set hcm-eth0 up; ip addr flush dev hcm-eth0; ip addr add 203.162.1.1/24 dev hcm-eth0')
    serverhcm.cmd('ip route del default 2>/dev/null; ip route add default via 203.162.1.254')
    serverhcm.cmd('ip route add 10.0.0.0/16 via 203.162.1.254 2>/dev/null || true')
    serverhcm.cmd('for f in /proc/sys/net/ipv4/conf/*/rp_filter; do echo 0 > $f; done')
    info('*** Network ready.\n')
    time.sleep(2)
    return net

# ── RUN: chạy trực tiếp python3 cauhinh1.py → CLI ──
def run():
    draw_topology_graph()
    net = build_net()
    info('\n=== MÔ HÌNH 1: MẠNG PHẲNG ===\n')
    info(' s1: 27/48 port | s2: 45/48 port\n')
    info(' GW: 10.0.0.254 | WAN: 200Mbps/10ms\n')
    info(' Test: pingall | admin1 ping 203.162.1.1\n')
    CLI(net)
    net.stop()
    cleanup_mininet()

if __name__ == '__main__':
    setLogLevel('info')
    if os.geteuid() != 0:
        print('sudo python3 cauhinh1.py')
        sys.exit(1)
    run()