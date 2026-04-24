#!/usr/bin/env python3
"""
MÔ HÌNH 2: MẠNG 3 LỚP TRUYỀN THỐNG (HIERARCHICAL L3)
Core(s1) → Distribution(s2-s5) → Access(s6-s19)

Đúng chuẩn Cisco 3-Tier:
  Access (L2): VLAN tagging, cắm host
  Distribution (L3): Inter-VLAN Routing (SVI/OpenFlow), chính sách, ACL
  Core (L2/L3): Chuyển mạch tốc độ cao, kết nối tòa nhà
  Edge (r1): WAN gateway, NAT, Default Route → serverhcm

Traffic Flow:
  Intra-VLAN: host → access_sw → (same L2 domain) → host
  Inter-VLAN: host → access → dist(L3 routing) → access → host
  WAN:        host → access → dist → core(s1) → r1 → serverhcm

Dist switches dùng OVS Internal Port làm SVI (Switch Virtual Interface)
để đóng vai trò Default Gateway cho từng VLAN.

STP: Lab access dual-home → d_a1(s2) + d_a2(s3) → STP block 1 uplink
"""

import os, sys, subprocess, time
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from mininet.net import Mininet
from mininet.node import Host, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

GRAPH_OUTPUT = 'level2_hierarchical_topology.png'

class LinuxRouter(Host):
    def config(self, **params):
        super().config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        super().terminate()

def cleanup_mininet():
    info('*** mn -c...\n')
    subprocess.run(['sudo','mn','-c'], capture_output=True, timeout=30)

# ── Draw ──────────────────────────────────────────────────────────────────
def draw_topology_graph():
    G = nx.Graph()
    nodes = {
        'wan':('wan','serverhcm\n203.162.1.1'),
        'r1':('router','r1\nEdge Router\n(WAN only)'),
        's1':('core','s1\nCore1\n(Root Bridge)'),
        's20':('core','s20\nCore2\n(Backup)'),
        's2':('dist','s2 (d_a1)\nDist L3\nSVI: VLAN10,20'),
        's3':('dist','s3 (d_a2)\nDist L3\n(Redundant)'),
        's4':('dist','s4 (d_b1)\nDist L3\nSVI: VLAN30'),
        's5':('dist','s5 (d_srv)\nDist L3\nSVI: VLAN99'),
        's6':('acc','s6\nAcc Admin'), 's19':('acc','s19\nAcc Srv'),
        'H_adm':('host','admin1-5\nVLAN10'), 'H_lab':('host','lab1-20\nVLAN20'),
        'H_dorm':('host','dorm1-40\nVLAN30'), 'H_srv':('host','srv1-4\nVLAN99'),
    }
    for i in range(4):  nodes[f's{7+i}']  = ('acc',f's{7+i}\nLab{i+1}')
    for i in range(8):  nodes[f's{11+i}'] = ('acc',f's{11+i}')
    for n,(t,lbl) in nodes.items(): G.add_node(n, type=t, label=lbl)
    G.add_edge('wan','r1',et='wan')
    G.add_edge('r1','s1',et='edge');  G.add_edge('r1','s20',et='edge')
    G.add_edge('s1','s20',et='core_link')
    for s in ['s2','s3','s4','s5']:
        G.add_edge('s1',s,et='bb');  G.add_edge('s20',s,et='bb')
    G.add_edge('s2','s6',et='ul'); G.add_edge('s6','H_adm',et='h')
    for i in range(4):
        G.add_edge('s2',f's{7+i}',et='ul_active')
        G.add_edge('s3',f's{7+i}',et='ul_stp')
    G.add_edge('s7','H_lab',et='h')
    for i in range(8): G.add_edge('s4',f's{11+i}',et='ul')
    G.add_edge('s11','H_dorm',et='h')
    G.add_edge('s5','s19',et='ul'); G.add_edge('s19','H_srv',et='h')
    pos = {'wan':(0,10),'r1':(0,8.5),'s1':(-1.5,7),'s20':(1.5,7),
           's2':(-5,5),'s3':(-2,5),'s4':(2,5),'s5':(5,5),
           's6':(-7,3),'H_adm':(-7,1),'H_lab':(-3,1),'H_dorm':(2,1),'H_srv':(6.5,1),
           's19':(6.5,3)}
    for i in range(4):  pos[f's{7+i}']  = (-5.2+i*1.1,3)
    for i in range(8):  pos[f's{11+i}'] = (-0.5+i*0.9,3)
    fig,ax = plt.subplots(figsize=(24,13))
    fig.patch.set_facecolor('#1a1a2e'); ax.set_facecolor('#1a1a2e')
    estyles = {
        'wan':('#E63946',3,'dashed'),'edge':('#FF6B35',3,'solid'),
        'core_link':('#FFD700',3.5,'solid'),
        'bb':('#FF6B35',2,'solid'),'ul':('#4a9eff',1.5,'solid'),
        'ul_active':('#2ECC71',2,'solid'),'ul_stp':('#E63946',2,'dotted'),
        'h':('#888',0.8,'solid')
    }
    for et,(c,w,s) in estyles.items():
        el = [(u,v) for u,v,d in G.edges(data=True) if d.get('et')==et]
        if el: nx.draw_networkx_edges(G,pos,edgelist=el,ax=ax,edge_color=c,width=w,style=s,alpha=0.9)
    cmap = {'core':'#E63946','dist':'#FF6B35','router':'#9B59B6','wan':'#C0392B','acc':'#2A9D8F','host':'#F7DC6F'}
    nc = [cmap.get(G.nodes[n]['type'],'#aaa') for n in G.nodes()]
    ns = [2200 if G.nodes[n]['type'] in ('core',) else
          1800 if G.nodes[n]['type'] in ('dist','router','wan') else
          900  if G.nodes[n]['type']=='acc' else 700 for n in G.nodes()]
    nx.draw_networkx_nodes(G,pos,ax=ax,node_color=nc,node_size=ns,edgecolors='white',linewidths=0.6)
    lbl = {n:G.nodes[n]['label'] for n in G.nodes()}
    nx.draw_networkx_labels(G,pos,labels=lbl,ax=ax,font_size=6,font_color='white',font_weight='bold')
    legend = [
        mpatches.Patch(color='#E63946', label='Dual Core: s1(Root) + s20(Backup)'),
        mpatches.Patch(color='#FFD700', label='Inter-Core Link s1↔s20'),
        mpatches.Patch(color='#FF6B35', label='Distribution s2-s5 – L3 Inter-VLAN (SVI)'),
        mpatches.Patch(color='#9B59B6', label='r1 – Edge Router (nối cả 2 Core)'),
        mpatches.Patch(color='#2ECC71', label='Uplink Active (STP Forwarding)'),
        mpatches.Patch(color='#E63946', label='STP BLOCK – Lab dual-homing'),
    ]
    ax.legend(handles=legend,loc='upper left',fontsize=8.5,facecolor='#16213e',edgecolor='#555',labelcolor='white')
    ax.set_title('MÔ HÌNH 2: MẠNG 3 LỚP | Dual Core + Distribution L3 (SVI)\n'
                 'Traffic: Host → Access(L2) → Dist(L3) → Core(s1/s20) → r1(WAN)\n'
                 '⚠ STP khóa 1 uplink Lab + 1 Core path → Dự phòng nhưng lãng phí BW',
                 color='#FF6B35',fontsize=11,fontweight='bold')
    ax.axis('off'); plt.tight_layout()
    plt.savefig(GRAPH_OUTPUT,dpi=120,bbox_inches='tight',facecolor='#1a1a2e'); plt.close()
    info(f'*** Saved: {GRAPH_OUTPUT}\n')

# ── BUILD NET: dùng bởi test.py (import cauhinh2; net = cauhinh2.build_net()) ──
def build_net():
    """Build + configure mạng 3 lớp, trả về net object (KHÔNG gọi CLI)."""
    cleanup_mininet()
    net = Mininet(controller=None, link=TCLink, autoSetMacs=True)
    r1        = net.addHost('r1', cls=LinuxRouter, ip='127.0.0.1/8')
    serverhcm = net.addHost('serverhcm', ip='203.162.1.1/24')
    s1  = net.addSwitch('s1',  cls=OVSSwitch, failMode='standalone', stp=True)
    s20 = net.addSwitch('s20', cls=OVSSwitch, failMode='standalone', stp=True)
    s2  = net.addSwitch('s2',  cls=OVSSwitch, failMode='standalone', stp=True)
    s3  = net.addSwitch('s3',  cls=OVSSwitch, failMode='standalone', stp=True)
    s4  = net.addSwitch('s4',  cls=OVSSwitch, failMode='standalone', stp=True)
    s5  = net.addSwitch('s5',  cls=OVSSwitch, failMode='standalone', stp=True)
    s6  = net.addSwitch('s6',  cls=OVSSwitch, failMode='standalone', stp=True)
    s7  = net.addSwitch('s7',  cls=OVSSwitch, failMode='standalone', stp=True)
    s8  = net.addSwitch('s8',  cls=OVSSwitch, failMode='standalone', stp=True)
    s9  = net.addSwitch('s9',  cls=OVSSwitch, failMode='standalone', stp=True)
    s10 = net.addSwitch('s10', cls=OVSSwitch, failMode='standalone', stp=True)
    s11 = net.addSwitch('s11', cls=OVSSwitch, failMode='standalone', stp=True)
    s12 = net.addSwitch('s12', cls=OVSSwitch, failMode='standalone', stp=True)
    s13 = net.addSwitch('s13', cls=OVSSwitch, failMode='standalone', stp=True)
    s14 = net.addSwitch('s14', cls=OVSSwitch, failMode='standalone', stp=True)
    s15 = net.addSwitch('s15', cls=OVSSwitch, failMode='standalone', stp=True)
    s16 = net.addSwitch('s16', cls=OVSSwitch, failMode='standalone', stp=True)
    s17 = net.addSwitch('s17', cls=OVSSwitch, failMode='standalone', stp=True)
    s18 = net.addSwitch('s18', cls=OVSSwitch, failMode='standalone', stp=True)
    s19 = net.addSwitch('s19', cls=OVSSwitch, failMode='standalone', stp=True)
    lab_sw  = [s7,s8,s9,s10]
    dorm_sw = [s11,s12,s13,s14,s15,s16,s17,s18]
    for i in range(1,6):  net.addHost(f'admin{i}', ip=f'10.0.10.{i}/24', defaultRoute='via 10.0.10.254')
    for i in range(1,21): net.addHost(f'lab{i}',   ip=f'10.0.20.{i}/24', defaultRoute='via 10.0.20.254')
    for i in range(1,41): net.addHost(f'dorm{i}',  ip=f'10.0.30.{i}/24', defaultRoute='via 10.0.30.254')
    for i in range(1,5):  net.addHost(f'srv{i}',   ip=f'10.0.99.{i}/24', defaultRoute='via 10.0.99.254')
    net.addLink(r1, s1,  intfName1='r1-eth0', bw=1000)
    net.addLink(r1, s1,  intfName1='r1-eth2', bw=1000)
    net.addLink(r1, s1,  intfName1='r1-eth3', bw=1000)
    net.addLink(r1, s1,  intfName1='r1-eth4', bw=1000)
    net.addLink(r1, s20, intfName1='r1-eth5', bw=1000)
    net.addLink(r1, serverhcm, intfName1='r1-eth1', bw=200, delay='10ms')
    net.addLink(s1, s20, bw=1000)
    net.addLink(s1, s2, bw=1000);   net.addLink(s20, s2, bw=1000)
    net.addLink(s1, s3, bw=1000);   net.addLink(s20, s3, bw=1000)
    net.addLink(s1, s4, bw=1000);   net.addLink(s20, s4, bw=1000)
    net.addLink(s1, s5, bw=1000);   net.addLink(s20, s5, bw=1000)
    net.addLink(s6, s2, bw=1000)
    for i in range(1,6):   net.addLink(net.get(f'admin{i}'), s6, bw=100)
    for sw in lab_sw:
        net.addLink(sw, s2, bw=1000)
        net.addLink(sw, s3, bw=1000)
    for i in range(1,21):  net.addLink(net.get(f'lab{i}'), lab_sw[(i-1)//5], bw=1000)
    for sw in dorm_sw:     net.addLink(sw, s4, bw=1000)
    for i in range(1,41):  net.addLink(net.get(f'dorm{i}'), dorm_sw[(i-1)//5], bw=50)
    net.addLink(s19, s5, bw=1000)
    for i in range(1,5):   net.addLink(net.get(f'srv{i}'), s19, bw=1000)
    info('*** Starting network...\n')
    net.start()
    s1.cmd('ovs-vsctl set Bridge s1 other_config:stp-priority=4096')
    s20.cmd('ovs-vsctl set Bridge s20 other_config:stp-priority=8192')
    info('*** Waiting STP convergence 15s...\n')
    time.sleep(15)
    r1.cmd('sysctl -w net.ipv4.ip_forward=1')
    r1.cmd('for f in /proc/sys/net/ipv4/conf/*/rp_filter; do echo 0 > $f; done')
    for eth, ip in [('r1-eth0','10.0.10.254/24'),('r1-eth2','10.0.20.254/24'),
                    ('r1-eth3','10.0.30.254/24'),('r1-eth4','10.0.99.254/24'),
                    ('r1-eth5','10.0.0.253/24'), ('r1-eth1','203.162.1.254/24')]:
        r1.cmd(f'ip link set {eth} up')
        r1.cmd(f'ip addr flush dev {eth}')
        r1.cmd(f'ip addr add {ip} dev {eth}')
    serverhcm.cmd('ip route del default 2>/dev/null; ip route add default via 203.162.1.254')
    for sub in ['10.0.10.0/24','10.0.20.0/24','10.0.30.0/24','10.0.99.0/24']:
        serverhcm.cmd(f'ip route add {sub} via 203.162.1.254 2>/dev/null || true')
    info('*** Network ready!\n')
    return net

# ── RUN: chạy trực tiếp python3 cauhinh2.py → CLI ──
def run():
    draw_topology_graph()
    net = build_net()
    info('\n' + '='*70 + '\n')
    info('  MÔ HÌNH 2: MẠNG 3 LỚP – Dual Core + Distribution L3 (SVI)\n')
    info('='*70 + '\n')
    info(' Test: pingall | admin1 ping srv1 | admin1 ping 203.162.1.1\n')
    CLI(net)
    net.stop()
    cleanup_mininet()

if __name__ == '__main__':
    setLogLevel('info')
    if os.geteuid() != 0:
        print('sudo python3 cauhinh2.py')
        sys.exit(1)
    run()