#!/bin/bash

# ===============================================

# AUTO FIX ENV FOR MININET + MPLS + EVPN LAB

# ===============================================

echo "==============================================="
echo "   AUTO FIX ENV - MININET MPLS EVPN LAB"
echo "==============================================="

# 1. Check Root

if [ "$EUID" -ne 0 ]; then
echo "[ LỖI ] Vui lòng chạy với sudo: sudo bash auto_fix_env.sh"
exit 1
fi

# 2. Update system

echo "[ INFO ] Updating package list..."
apt update -y

# 3. Install required packages

echo "[ INFO ] Installing required packages..."
apt install -y 
mininet 
openvswitch-switch 
frr frr-pythontools 
iperf 
traceroute 
bridge-utils 
python3-tk 
python3-matplotlib 
net-tools 
lsof

# 4. Enable OVS

echo "[ INFO ] Restarting Open vSwitch..."
systemctl enable openvswitch-switch
systemctl restart openvswitch-switch

# 5. Enable FRR service

echo "[ INFO ] Enabling FRRouting..."
systemctl enable frr
systemctl restart frr

# 6. Load MPLS modules

echo "[ INFO ] Loading MPLS kernel modules..."
modprobe mpls_router
modprobe mpls_iptunnel

# Persist modules

echo "mpls_router" >> /etc/modules-load.d/mpls.conf
echo "mpls_iptunnel" >> /etc/modules-load.d/mpls.conf

# 7. Enable VXLAN

modprobe vxlan
echo "vxlan" >> /etc/modules-load.d/vxlan.conf

# 8. Sysctl tuning (CRITICAL)

echo "[ INFO ] Applying sysctl settings..."

sysctl -w net.ipv4.ip_forward=1
sysctl -w net.mpls.platform_labels=100000
sysctl -w net.ipv4.conf.all.rp_filter=0
sysctl -w net.ipv4.conf.default.rp_filter=0

# Persist sysctl

cat <<EOF > /etc/sysctl.d/99-mpls-evpn.conf
net.ipv4.ip_forward=1
net.mpls.platform_labels=100000
net.ipv4.conf.all.rp_filter=0
net.ipv4.conf.default.rp_filter=0
EOF

sysctl --system >/dev/null 2>&1

# 9. Fix FRR daemon config (enable needed services)

echo "[ INFO ] Configuring FRR daemons..."

sed -i 's/zebra=no/zebra=yes/g' /etc/frr/daemons
sed -i 's/bgpd=no/bgpd=yes/g' /etc/frr/daemons
sed -i 's/ospfd=no/ospfd=yes/g' /etc/frr/daemons
sed -i 's/ldpd=no/ldpd=yes/g' /etc/frr/daemons

systemctl restart frr

# 10. Cleanup Mininet (avoid conflict)

echo "[ INFO ] Cleaning old Mininet state..."
mn -c >/dev/null 2>&1

# 11. Kill leftover processes

echo "[ INFO ] Killing leftover processes..."
killall -9 ovs-vswitchd ovsdb-server mnexec 2>/dev/null

# Restart OVS again after kill

systemctl restart openvswitch-switch

# 12. Check port conflicts (iperf)

if lsof -i:5001 >/dev/null 2>&1; then
echo "[ WARNING ] Port 5001 đang bị chiếm → killing..."
fuser -k 5001/tcp 2>/dev/null
fi

# 13. Final verification

echo "[ INFO ] Running quick test..."
mn --test pingall >/dev/null 2>&1

if [ $? -eq 0 ]; then
echo "[ OK ] Mininet hoạt động OK."
else
echo "[ WARNING ] Mininet test fail (có thể do VM yếu hoặc network delay)."
fi

echo "==============================================="
echo "[ DONE ] Môi trường đã được cấu hình hoàn tất!"
echo "==============================================="

echo ""
echo "👉 Gợi ý chạy lab:"
echo "   sudo mn -c"
echo "   sudo python3 your_topology.py"
