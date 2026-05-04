# Phân tích Kiến trúc LAN (Yêu cầu 4.3)

## 1. Chi nhánh 1 (Mạng phẳng - Flat Network)
- **Đặc điểm:** Tất cả thiết bị chung 1 Broadcast Domain, dùng STP.
- **Ưu điểm:** Cấu hình đơn giản, phù hợp chi nhánh siêu nhỏ.
- **Nhược điểm:** Dễ xảy ra Broadcast storm, hội tụ STP chậm. Không tối ưu cho số lượng thiết bị lớn.
- **Tương tác MPLS:** Khi ping qua mạng MPLS Backbone, độ trễ và thông lượng sẽ bị ảnh hưởng nếu mạng nội bộ đang bị tắc nghẽn ARP.

## 2. Chi nhánh 2 (Mạng 3 lớp - Core/Distribution/Access)
- **Đặc điểm:** Chia tầng rõ rệt, định tuyến OSPF nội bộ.
- **Ưu điểm:** Khả năng mở rộng cao, dự phòng tốt.
- **Nhược điểm:** Cấu hình phức tạp, chi phí cao. 
- **Tương tác MPLS:** Số hop count nội bộ nhiều hơn mạng phẳng, nhưng kiểm soát luồng giao thông cực tốt. Rất phù hợp để tích hợp với BGP Edge của nhà mạng (Router PE).

## 3. Chi nhánh 3 (Mạng Spine-Leaf 2 lớp)
- **Đặc điểm:** Mọi Switch Access (Leaf) kết nối tới tất cả Switch Lõi (Spine) tạo thành Full-mesh.
- **Ưu điểm:** Băng thông nội bộ cực cao (East-West traffic), ECMP load-balancing siêu tốc. Bất kỳ 2 host nào cũng chỉ cách nhau 1 hop Spine.
- **Tương tác MPLS:** Kiến trúc này kết hợp hoàn hảo với MPLS Backbone để đẩy dữ liệu lớn từ cụm Server nội bộ ra chi nhánh khác với thông lượng (Throughput) cao nhất, độ trễ thấp nhất.
