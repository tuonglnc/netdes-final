#!/bin/bash

# ===============================================

# CHECK ENV FOR MININET + MPLS + EVPN LAB

# ===============================================

echo "==============================================="
echo "   KIỂM TRA MÔI TRƯỜNG MININET & FRROUTING"
echo "==============================================="

# 1. Check Root

if [ "$EUID" -ne 0 ]; then
echo "[ LỖI ] Bạn phải chạy bằng quyền root: sudo bash check_env.sh"
exit 1
fi
echo "[ OK ] Đang chạy với quyền Root."

# 2. Mininet

if command -v mn >/dev/null 2>&1; then
echo "[ OK ] Mininet đã được cài."
else
echo "[ LỖI ] Thiếu Mininet: sudo apt install mininet"
fi

# 3. Open vSwitch

if command -v ovs-vsctl >/dev/null 2>&1; then
echo "[ OK ] Open vSwitch đã được cài."
else
echo "[ LỖI ] Thiếu Open vSwitch: sudo apt install openvswitch-switch"
fi

# 4. FRRouting

if command -v vtysh >/dev/null 2>&1; then
echo "[ OK ] FRRouting đã được cài."
else
echo "[ LỖI ] Thiếu FRR: sudo apt install frr frr-pythontools"
fi

# FRR version

FRR_VERSION=$(vtysh -c "show version" 2>/dev/null | head -n 1)
echo "[ INFO ] $FRR_VERSION"

# LDP daemon

if [ -f "/usr/lib/frr/ldpd" ]; then
echo "[ OK ] LDP daemon tồn tại."
else
echo "[ LỖI ] Không có ldpd (thiếu MPLS support trong FRR?)"
fi

# 5. MPLS Kernel

modprobe mpls_router 2>/dev/null
modprobe mpls_iptunnel 2>/dev/null

if lsmod | grep -q mpls_router; then
echo "[ OK ] MPLS Router module loaded."
else
echo "[ LỖI ] MPLS Router chưa load."
fi

if lsmod | grep -q mpls_iptunnel; then
echo "[ OK ] MPLS IP Tunnel loaded."
else
echo "[ LỖI ] MPLS IP Tunnel chưa load."
fi

# MPLS label space

if [ "$(sysctl -n net.mpls.platform_labels 2>/dev/null)" -gt 0 ]; then
echo "[ OK ] MPLS label space OK."
else
echo "[ LỖI ] MPLS label chưa set → sudo sysctl -w net.mpls.platform_labels=100000"
fi

# 6. VXLAN

modprobe vxlan 2>/dev/null
if lsmod | grep -q vxlan; then
echo "[ OK ] VXLAN supported."
else
echo "[ LỖI ] VXLAN không hỗ trợ."
fi

# 7. IP Forwarding

if [ "$(sysctl -n net.ipv4.ip_forward)" -eq 1 ]; then
echo "[ OK ] IP Forwarding ON."
else
echo "[ LỖI ] IP Forwarding OFF → sudo sysctl -w net.ipv4.ip_forward=1"
fi

# 8. rp_filter

if [ "$(sysctl -n net.ipv4.conf.all.rp_filter)" -eq 0 ]; then
echo "[ OK ] rp_filter OFF."
else
echo "[ CẢNH BÁO ] rp_filter ON → nên tắt:"
echo "           sudo sysctl -w net.ipv4.conf.all.rp_filter=0"
fi

# 9. bridge command

if command -v bridge >/dev/null 2>&1; then
echo "[ OK ] bridge command OK."
else
echo "[ LỖI ] Thiếu bridge (iproute2)."
fi

# 10. Python libs

echo "[ INFO ] Checking Python3..."

if python3 -c "import tkinter" >/dev/null 2>&1; then
echo "[ OK ] tkinter OK."
else
echo "[ LỖI ] Thiếu tkinter → sudo apt install python3-tk"
fi

if python3 -c "import matplotlib" >/dev/null 2>&1; then
echo "[ OK ] matplotlib OK."
else
echo "[ LỖI ] Thiếu matplotlib → sudo apt install python3-matplotlib"
fi

PY_VER=$(python3 -c 'import sys; print(sys.version.split()[0])')
echo "[ INFO ] Python version: $PY_VER"

# 11. Network tools

for cmd in iperf traceroute ping killall; do
if command -v $cmd >/dev/null 2>&1; then
echo "[ OK ] $cmd OK."
else
echo "[ LỖI ] Thiếu $cmd → sudo apt install $cmd"
fi
done

# 12. OVS service

if pgrep -x "ovs-vswitchd" >/dev/null; then
echo "[ OK ] OVS daemon running."
else
echo "[ CẢNH BÁO ] OVS daemon chưa chạy."
fi

# 13. Port check (iperf)

if lsof -i:5001 >/dev/null 2>&1; then
echo "[ CẢNH BÁO ] Port 5001 đang dùng (iperf có thể lỗi)."
fi

# 14. Mininet quick test

echo "[ INFO ] Running Mininet quick test..."
mn --test pingall >/dev/null 2>&1
if [ $? -eq 0 ]; then
echo "[ OK ] Mininet hoạt động bình thường."
else
echo "[ CẢNH BÁO ] Mininet test fail → thử mn -c rồi chạy lại."
fi

echo "==============================================="
echo " Nếu tất cả [ OK ] → môi trường sẵn sàng chạy lab!"
echo "==============================================="
