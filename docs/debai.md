# Đề tài Mạng cảm biến và Thiết kế xây dựng mạng

## Thông tin chung

-   **Trường**: Đại học Tôn Đức Thắng
-   **Ngành**: Mạng máy tính và truyền thông dữ liệu

## Đề tài

**Thiết kế và triển khai mạng Metro Ethernet sử dụng MPLS cho kết nối đa
chi nhánh doanh nghiệp**

------------------------------------------------------------------------

## 1. Mục tiêu

Xây dựng và mô phỏng mô hình mạng Metro Ethernet (MAN) sử dụng MPLS nhằm
kết nối nhiều chi nhánh doanh nghiệp thông qua hạ tầng mạng của nhà cung
cấp dịch vụ (ISP).

### Nội dung chính:

-   Đánh giá hiệu năng mạng
-   Phân tích khả năng định tuyến của MPLS
-   So sánh các kiến trúc mạng LAN khác nhau

### Triển khai trên:

-   Mininet Network Emulator

### Mục đích:

-   Phân tích khả năng kết nối giữa các chi nhánh
-   Đánh giá hiệu năng truyền dữ liệu
-   So sánh ảnh hưởng của kiến trúc mạng LAN

------------------------------------------------------------------------

## 2. Yêu cầu triển khai mô hình

### 2.1 Kiến trúc mạng nội bộ

-   **Chi nhánh 1**: Mạng phẳng (Flat Network)
-   **Chi nhánh 2**: Mạng 3 lớp (Core -- Distribution -- Access)
-   **Chi nhánh 3**: Mạng 2 lớp (Leaf-Spine)

Kết nối thông qua router CE.

### 2.2 Hạ tầng Metro Ethernet

Nhà cung cấp dịch vụ triển khai:

-   MPLS Backbone
-   Router:
    -   PE (Provider Edge)
    -   P (Provider)

### MPLS dùng để:

-   Tăng tốc chuyển mạch
-   Phân tách lưu lượng
-   Hỗ trợ định tuyến hiệu quả

### 2.3 Mô phỏng hệ thống

-   Nền tảng: Mininet
-   Thành phần:
    -   Router P, PE, CE
    -   Switch
    -   Host

### 2.4 Kiểm tra

-   Lưu lượng
-   Độ trễ

------------------------------------------------------------------------

## 3. Nội dung nghiên cứu

1.  Kiến trúc Metro Ethernet MAN\
2.  Nguyên lý MPLS Label Switching\
3.  Cấu hình router P -- PE -- CE\
4.  Kết nối các chi nhánh qua MPLS\
5.  Mô phỏng trên Mininet\
6.  Đo lường và phân tích hiệu năng

------------------------------------------------------------------------

## 4. Kết quả cần đạt

### 4.1 Thống kê hiệu năng

-   Throughput
-   Delay
-   Packet loss
-   Jitter

### 4.2 Đồ thị so sánh

-   Throughput giữa các chi nhánh
-   Độ trễ
-   Packet loss khi tải tăng

### 4.3 Phân tích kiến trúc mạng

So sánh: - Mạng phẳng - Mạng 2 lớp - Mạng 3 lớp

### 4.4 Đánh giá MPLS

-   Quá trình label switching
-   Đường đi gói tin
-   So sánh với IP routing truyền thống
