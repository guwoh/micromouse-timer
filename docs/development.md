# Phát triển và kiểm thử

[← Trang chính](../README.md)

## Môi trường

Dùng Python 3.11 trở lên, với PyQt6 và OpenCV. Từ thư mục gốc repo:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r microtimer/requirements-dev.txt
```

Trên Windows PowerShell, kích hoạt bằng `.venv\Scripts\Activate.ps1`. Cũng có thể gọi trực tiếp `.venv\Scripts\python.exe` nếu không dùng script kích hoạt.

Nếu dùng Conda:

```bash
conda env create -f microtimer/environment.yml
conda activate micromouse-timer
```

Chạy giao diện từ `microtimer/`:

```bash
cd microtimer
python -m app.main
```

| File phụ thuộc | Phục vụ |
| --- | --- |
| `microtimer/requirements.txt` | Chạy ứng dụng |
| `microtimer/requirements-dev.txt` | Chạy ứng dụng và kiểm thử |
| `microtimer/requirements-build.txt` | Kiểm thử, PyInstaller và tạo icon |
| `microtimer/environment.yml` | Môi trường Conda cho phát triển |

## Các lớp chính

| Thư mục | Vai trò |
| --- | --- |
| `app/` | Nạp YAML, lưu tùy chọn lấy mẫu, xác định đường dẫn tài nguyên/dữ liệu |
| `core/` | Máy trạng thái timer, snapshot an toàn giữa luồng, phiên thi, CSV/XLSX |
| `pipeline/` | CaptureWorker lấy frame; ProcessWorker phân tích frame mới theo chu kỳ |
| `vision/camera/` | Nguồn USB, IP và trình đọc/tua video |
| `vision/` | Bù rung, ComparisonZone, MouseDetector và overlay |
| `ui/` | Dashboard PyQt6, hiển thị frame, vẽ ROI và hộp thoại |
| `assets/branding/`, `assets/icons/` | Tài nguyên giao diện dùng chung cho source và installer |

CaptureWorker công bố frame mới nhất có timestamp và chỉ số frame. ProcessWorker kiểm tra giãn cách lấy mẫu, căn chỉnh ảnh và chạy bộ nhận diện theo trạng thái FSM. UI đọc snapshot để hiển thị và ghi kết quả, không dùng trạng thái đang bị thay đổi giữa chừng bởi luồng xử lý.

Vùng video được cấp kích thước từ vùng cửa sổ, độc lập với size hint của ảnh và nội dung nhãn. Hiệu ứng tương tác chỉ vẽ trên nút, dialog và lớp nền tối; không chụp hoặc áp hiệu ứng lên widget video.

## Kiểm thử

Chạy từ thư mục gốc repo:

```bash
python -m pytest -q
```

`pytest.ini` khai báo đường dẫn import và thư mục test. Bộ GUI dùng `QT_QPA_PLATFORM=offscreen` trên Linux và plugin `windows` trên Windows để nạp đúng font hệ thống. Test gửi sự kiện bằng QtTest và dùng video local, không cần thao tác thủ công hay camera thật.

Một số lệnh phục vụ kiểm tra cụ thể trên Linux:

```bash
python -m pytest microtimer/tests/test_mouse_detector.py -q
python -m pytest microtimer/tests/test_gui.py microtimer/tests/test_interaction.py -q
QT_SCALE_FACTOR=1.5 python -m pytest microtimer/tests/test_interaction.py -q
```

Các nhóm test bao gồm hướng chuyển vùng, Goal hold theo timestamp, bỏ mẫu, rung/xoay camera, thay đổi ánh sáng, mẫu video thực, ghi kết quả đúng một lần, ổn định vùng video và vòng đời popup. Hai video mẫu trong `samples/` cần có khi chạy toàn bộ test.

Test không thay thế việc đo trên camera thật. Cần kiểm tra độ trễ, codec, ánh sáng và các góc đặt camera trên máy thi thực tế.

## Công cụ hỗ trợ

Chạy trong `microtimer/`:

```bash
python scripts/list_usb_cameras.py
python scripts/record_sample.py --source 0 --out sample.mp4 --seconds 10
python scripts/create_mock_video.py
```

Video do script tạo được Git bỏ qua. `create_mock_video.py` tạo file mới tại thư mục đang chạy, không ghi đè video mẫu trong `samples/` trừ khi bạn chủ động đổi đường dẫn đầu ra.

## Quy ước dữ liệu

Cấu hình mặc định công khai nằm ở `config/default.yaml`. Không đặt URL có mật khẩu hoặc dữ liệu đội thi vào file này. Dùng trường nguồn trong Configure cho nguồn riêng; `.env*`, `config/local.*`, `private/`, kết quả, log và video tự ghi được `.gitignore` loại khỏi commit. App không tự đọc `.env` hoặc `config/local.*`; các đường dẫn đó chỉ dành cho cấu hình local nếu bạn cần lưu riêng.

Giữ mã nguồn và tài nguyên dùng chung trong repo. Bộ cài, cache, video cá nhân và kết quả thi nằm ngoài phần được theo dõi. PyInstaller chỉ đưa vào hai sample đã chỉ định, tránh đóng gói nhầm video riêng. Xem [hướng dẫn build](packaging.md) khi đổi đường dẫn asset hoặc thêm tài nguyên công khai.
