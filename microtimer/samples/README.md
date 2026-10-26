# Video mẫu

Hai fixture công khai được giữ trong Git và đưa vào installer:

| File | Nội dung |
| --- | --- |
| `mock_run_real.mp4` | Robot chạy trong mê cung thực, 1920 × 1080, 30 FPS, khoảng 13,8 giây; nguồn Mock mặc định |
| `mock_run.mp4` | Video thử tổng hợp của dự án, 1000 × 1000, 30 FPS, khoảng 5 giây |

App giải mã các file bằng OpenCV. **Connect** phát video, cuối file tự lặp và **Next Run** tua về đầu. Đặt ROI đúng theo góc quay trước khi bắt đầu phiên.

Video thử thêm của người dùng được Git bỏ qua và không được spec đóng gói. Dùng **Configure → Browse** để chọn file riêng ở bất kỳ thư mục nào.

Xem [hướng dẫn sử dụng](../../docs/usage.md) và [kiểm thử](../../docs/development.md).
