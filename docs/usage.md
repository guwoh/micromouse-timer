# Hướng dẫn sử dụng

[← Trang chính](../README.md)

## Nguồn hình

Chọn nguồn ở thanh **Live camera**, mở **Configure** để nhập thông tin, sau đó **Connect**.

| Nguồn | Giá trị nhập | Cách dùng |
| --- | --- | --- |
| USB camera | Chỉ số camera, ví dụ `0`, `1` | Dùng camera được hệ điều hành nhận diện |
| IP stream | URL stream hoặc đường dẫn video | OpenCV mở nguồn bằng backend có trên máy |
| Mock video | Đường dẫn video, có nút **Browse** | Giải mã video thật, phát theo FPS của file và lặp khi hết |

Mock mặc định là `samples/mock_run_real.mp4`, video mê cung thực 1920 × 1080, 30 FPS, dài khoảng 13,8 giây. **Next Run** tua mock về đầu và đưa timer vào trạng thái chờ xuất phát. Có thể chọn video riêng qua Browse; không cần chép nó vào repo.

Khả năng mở RTSP, HTTP hay định dạng video phụ thuộc backend/codec OpenCV và camera. App không cam kết hỗ trợ mọi giao thức hoặc mọi thiết bị.

## Đặt các vùng ROI

Đặt vùng khi chưa bắt đầu phiên thi:

- **Kéo chuột trái:** vẽ đường xuất phát. Hướng đi mặc định được suy ra từ vị trí Goal; dùng vùng A/B thủ công nếu cần hướng khác.
- **Kéo chuột phải:** vẽ hình chữ nhật Goal.
- **Reset ROIs:** khôi phục ROI theo `config/default.yaml`; mặc định xuất phát ở góc dưới trái, đích ở giữa ảnh.

App tự tạo hai vùng so sánh quanh đường xuất phát và một dải ngoài Goal. Có thể chỉnh riêng bằng bộ chọn phía trên video:

| Lựa chọn | Ý nghĩa |
| --- | --- |
| Quick draw · Start / Goal | Trái đặt Start, phải đặt Goal |
| Start · line | Vẽ lại đường xuất phát và tạo lại A/B tự động |
| Start A · before line | Vùng robot ở trước khi xuất phát |
| Start B · after line | Vùng robot đi vào sau khi vượt đường xuất phát |
| Goal · inner region | Vùng trong của đích |
| Goal · outer region | Hình chữ nhật bao ngoài vùng đích |

A và B phải tách nhau; hình chữ nhật Goal outer phải chứa Goal inner. Phần **OUT** được tính bằng outer trừ inner. Khi phiên thi đang chạy, app khóa thay đổi ROI và tham số nhận diện. ROI thủ công được giữ khi kết nối lại trong cùng lần mở app với cùng kích thước frame. Khi đổi độ phân giải hoặc khởi động lại app, cần kiểm tra và đặt lại vùng.

## Điều kiện bắt đầu và về đích

Start cần chuyển động theo thứ tự **A → B**. Goal cần bằng chứng chuyển động **OUT → IN**, sau đó giữ xác nhận trong khoảng thời gian đã đặt. Chuyển động ngược chiều hoặc chỉ thay đổi bên trong Goal không được coi là về đích.

Robot có thể chiếm cả hai vùng trong cùng một mẫu. Khi đó, app kiểm tra hướng di chuyển bằng các điểm ảnh được theo dõi trước/sau. Phần ảnh đệm quanh ROI giúp tránh cắt mất robot ở mép vùng; các pixel đệm không được tính vào tỷ lệ IN/OUT. Thay đổi lớn đồng thời ở cả hai vùng bị loại.

Bù rung căn chỉnh ảnh để phân tích và chiếu đường ROI theo camera. Video hiển thị vẫn là frame gốc, không bị warp để bù rung. Khi đổi số lượt, trạng thái hay đồng hồ, vị trí và kích thước vùng video không thay đổi.

## Lấy mẫu và trạng thái

Mở **Sampling / Detection…** trước phiên thi:

| Tham số | Mặc định | Ý nghĩa |
| --- | --- | --- |
| Requested sampling period | 30 ms | Khoảng tối thiểu giữa hai frame được phân tích |
| Goal confirmation hold | 80 ms | Thời gian bằng chứng vào đích phải duy trì liên tục |
| Maximum A → B / outside → inside | 1500 ms | Thời hạn giữa hai bước chuyển vùng |

Chu kỳ yêu cầu không phải cam kết tốc độ xử lý: camera 30 FPS không thể cung cấp frame mới mỗi 5 ms. **Configure → Sampling** hiển thị khoảng lấy mẫu đo thực tế và Hz tương ứng; thanh cuối màn hình cũng hiển thị nhịp phân tích. Các giá trị thay đổi được lưu trong `preferences.json` của người dùng.

Đợi **Vision: Ready** sau khi kết nối hoặc chỉnh ROI; thời gian hiệu chuẩn mặc định là 500 ms. **Goal gate** hiển thị bước hiện tại: chờ OUT → IN, đang xác nhận, đã xác nhận hoặc thay đổi chung bị loại. `Goal in/out` là tỷ lệ foreground của từng vùng, không phải xác suất robot đã về đích.

Thời gian hold được tính bằng timestamp, không phải số frame. Sau khi xác nhận, app dùng timestamp IN đầu tiên đủ điều kiện nên không cộng thêm toàn bộ thời gian hold vào kết quả. Đây là timestamp frame nhận tại máy, không phải timestamp phơi sáng của camera.

Nếu mất căn chỉnh, camera dịch chuyển quá xa hoặc có khoảng gián đoạn lấy mẫu lớn, app xóa bằng chứng chuyển tiếp đang chờ và chặn tín hiệu đo mới. Đồng hồ đang chạy vẫn tiếp tục; kiểm tra lại vị trí camera, ROI và ánh sáng theo thông báo Vision.

## Điều khiển phiên

1. Nhập **Team** và **Duration**, bấm **Start Session**.
2. Dùng **Arm** hoặc **Next Run** để chờ robot xuất phát. **Next Run** xóa trạng thái lượt hiện tại; lượt đã hoàn tất được lưu trước khi chuẩn bị lượt mới.
3. Khi phát hiện Start, timer chuyển **ARMED → RUNNING**; nhận Goal hợp lệ thì chuyển **FINISHED** và thêm một hàng vào lịch sử.
4. **Reset** xóa trạng thái timer hiện tại. Với mock, Reset cũng tua video về đầu. Kết quả đã ghi trong phiên được giữ.
5. **Stop Session** kết thúc phiên sớm và xuất Excel. Hết thời lượng hoặc đóng cửa sổ chính cũng kết thúc/xuất phiên đang chạy.

Lượt nhanh nhất được đánh dấu **Best**. Lịch sử còn hiển thị sau khi kết thúc phiên và được xóa khi bắt đầu phiên mới. CSV dự phòng được ghi khi thêm lượt; XLSX được tạo khi phiên kết thúc. Một lượt chưa hoàn tất không được tự tính là kết quả.

Popup Configure/Detection mở/đóng nhẹ với nền tối; video vẫn được xử lý phía sau. **Apply**, **Cancel**, Escape và nút đóng giữ hành vi bình thường. Dialog chọn file và thông báo hệ thống dùng giao diện của hệ điều hành.

## Nếu timer không dừng

- Kiểm tra **Goal gate**, không chỉ `Goal in/out`.
- Kiểm tra outer chứa inner và có đủ khoảng cho robot đi từ OUT vào IN.
- Tránh hiệu chuẩn khi robot hoặc tay đang che vùng đo; đợi Ready rồi chạy lại.
- Kiểm tra hướng xuất phát, nhịp lấy mẫu đo thực tế và trạng thái bù rung.
- Dùng **Next Run** để phát lại mock từ đầu sau khi sửa vùng.

Không tăng độ nhạy chỉ để ép một tỷ lệ IN thành tín hiệu về đích. Tay, bóng đổ hoặc thay đổi cảnh vẫn có thể tạo foreground; cần thử nhiều lượt với điều kiện camera thực tế trước khi dùng để thi.
