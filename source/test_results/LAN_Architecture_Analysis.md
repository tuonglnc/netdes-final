# Phân tích Kiến trúc LAN (Yêu cầu 4.3)

*Báo cáo này được tạo tự động dựa trên số liệu đo lường trực tiếp từ Topology Mininet.*

## 1. Chi nhánh 1 (Mạng phẳng - Flat Network)
- **Đo lường nội bộ (h1 -> h2):** Độ trễ RTT: `0.103 ms` | Thông lượng: `93.9 Mbps` | Số lượng Hop (Traceroute): `1`
- **Đặc điểm:** Tất cả thiết bị chung 1 Broadcast Domain, dùng STP.
- **Phân tích:** Do các máy tính kết nối trực tiếp qua Switch L2 (0 hop routing), độ trễ nội bộ rất thấp. Tuy nhiên cấu hình đơn giản này dễ xảy ra Broadcast storm, hội tụ STP chậm. Không tối ưu cho số lượng thiết bị lớn.
- **Tương tác MPLS:** Khi ping qua mạng MPLS Backbone, độ trễ và thông lượng sẽ bị ảnh hưởng nếu mạng nội bộ đang bị tắc nghẽn ARP.

## 2. Chi nhánh 2 (Mạng 3 lớp - Core/Distribution/Access)
- **Đo lường nội bộ (h5 -> h6):** Độ trễ RTT: `0.267 ms` | Thông lượng: `93.7 Mbps` | Số lượng Hop (Traceroute): `1`
- **Đặc điểm:** Chia tầng rõ rệt, định tuyến OSPF nội bộ.
- **Phân tích:** Khả năng mở rộng cực cao, dự phòng tốt, kiểm soát luồng giao thông hiệu quả. 
- **Tương tác MPLS:** Rất phù hợp để tích hợp với BGP Edge của ISP (Router PE).

## 3. Chi nhánh 3 (Mạng Spine-Leaf 2 lớp)
- **Đo lường nội bộ (s1 -> s2):** Độ trễ RTT: `0.066 ms` | Thông lượng: `94.4 Mbps` | Số lượng Hop (Traceroute): `1`
- **Đặc điểm:** Mọi Switch Access (Leaf) kết nối tới tất cả Switch Lõi (Spine) tạo thành Full-mesh.
- **Phân tích:** Băng thông nội bộ cực cao (East-West traffic), ECMP load-balancing siêu tốc. Bất kỳ 2 host nào cũng chỉ cách nhau 1 hop Spine nên mức độ trễ rất ổn định và thông lượng tiệm cận giới hạn cáp.
- **Tương tác MPLS:** Kiến trúc này kết hợp hoàn hảo với MPLS Backbone để đẩy dữ liệu lớn từ cụm Server nội bộ ra chi nhánh khác với thông lượng cao nhất.
