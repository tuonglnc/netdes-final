# Network Design Final Project 
## Thiết kế và triển khai mạng Metro Ethernet sử dụng MPLS cho kết nối đa chi nhánh doanh nghiệp

Đồ án cuối kỳ môn Thiết kế mạng (HK2/25-26) thực hiện bởi 52300266 - Lê Nguyễn Cát Tường.

## 📌 Giới thiệu
Mô tả ngắn gọn về đồ án (Ví dụ: Mô phỏng mạng doanh nghiệp sử dụng SDN/Mininet hoặc Spine-Leaf architecture).

## 📂 Cấu trúc thư mục
- `source/`: Mã nguồn chính của dự án (Python/Shell scripts).
- `docs/`: Tài liệu hướng dẫn và báo cáo chi tiết.
- `image/`: Sơ đồ thiết kế mạng và hình ảnh minh họa kết quả.
- `test_commands.md`: Danh sách các lệnh dùng để kiểm tra và vận hành hệ thống.

## 🚀 Hướng dẫn cài đặt & Chạy
1. **Yêu cầu hệ thống:** - Ubuntu/WSL2
   - Mininet / Ryu Controller (hoặc công cụ bạn dùng)
   - Python 3.x
   - Chạy lệnh setup
   ```bash
   # Đứng tại thư mục /source chạy: 
   sudo bash /setup/auto_fix_env.sh

   # Những lần sau có thể chạy check_env để check không cần setup lại
   sudo bash /setup/check_env.sh
   ```
   
2. **Chạy mô phỏng:**
   ```bash
   cd source
   sudo python3 <ten_file_chinh>.py
   ```

3. Kiểm tra kết nối:
Tham khảo các lệnh test tại test_commands.md.

## 📊 Kết quả

### Sơ đồ hệ thống (Topology)
![Network Topology](./image/netdes-final-hihi.drawio.png)

> **LƯU Ý:** Bạn có thể xem file thiết kế gốc tại thư mục `image/` để chỉnh sửa bằng draw.io.
> *PHẢI SỬA CHO ĐÚNG VỚI BÀI, DỰA TRÊN topology.py của riêng bạn nhé !*

---
### Thông tin tác giả
* **Họ tên:** Lê Nguyễn Cát Tường
* **Tổ chức:** Tôn Đức Thắng University (TDTU)
* **Năm thực hiện:** © 2026

