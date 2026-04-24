# 🎨 Hướng dẫn chỉnh sửa sơ đồ LOGIC.drawio
- File LOGIC.drawio là sơ đồ mẫu. Để khớp với sơ đồ mạng (topology) riêng của bạn, hãy làm theo các bước chi tiết sau:

## Bước 1: Chuẩn bị file
- Truy cập vào thư mục image/ trong repository này.

- Tải file LOGIC.drawio về máy tính của bạn.

## Bước 2: Mở Draw.io và Import
- Truy cập vào trang web: app.diagrams.net.

- Khi bảng hiện ra, chọn Open Existing Diagram (Mở sơ đồ đã có).

- Tìm và chọn file LOGIC.drawio bạn vừa tải về.

- Hoặc: Bạn chỉ cần kéo (drag & drop) file từ thư mục máy tính thả trực tiếp vào trình duyệt đang mở Draw.io.

## Bước 3: Chỉnh sửa để khớp với Topology cá nhân
- Dựa trên sơ đồ mạng thực tế bạn thiết kế (ví dụ trong Mininet hoặc Cisco Packet Tracer), hãy thực hiện:

- Thay đổi IP/MAC: Nhấp đúp vào các nhãn văn bản (label) trên các đường truyền hoặc thiết bị để sửa thông số IP phù hợp.

- Thêm/Xóa thiết bị: * Nhấn phím Delete để xóa các Switch/Host thừa.

- Kéo các biểu tượng từ thư viện bên trái (thường dùng bộ thư viện Networking hoặc Cisco) để thêm thiết bị mới.

- Kết nối lại các cổng (Port): Di chuyển các đầu mũi tên để nối đúng vào Interface (ví dụ: eth0, s1-eth1) như trong cấu hình code của bạn.

## Bước 4: Lưu và Xuất file
- Sau khi chỉnh sửa xong, bạn cần lưu lại 2 định dạng:

- Lưu file gốc: Vào File > Save (để giữ file .drawio dùng cho lần sửa sau).

- Xuất file ảnh (để báo cáo):

- Vào File > Export as > PNG...

- Ở bảng hiện ra, hãy tích chọn ô Include a copy of my diagram (quan trọng: để sau này bạn có thể ném file ảnh này vào Draw.io để sửa tiếp).

- Nhấn Export và lưu về máy.

## Bước 5: Cập nhật lên GitHub
Sau khi có file ảnh mới, hãy chèn vào thư mục image/ và cập nhật đường dẫn trong README.md:

```Markdown
![My Topology](./image/ten-anh-moi-cua-ban.png)
```
Lưu ý: Nếu các bạn gặp lỗi font hoặc không thấy thư viện thiết bị, hãy vào More Shapes (góc dưới bên trái) và tích chọn Networking hoặc Cisco
