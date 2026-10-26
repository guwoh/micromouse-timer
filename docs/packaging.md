# Đóng gói và cài đặt

[← Trang chính](../README.md)

## Trạng thái

Cấu hình build hỗ trợ Windows x64 và Linux x64. Bản Linux 1.2.2 đã được build và kiểm tra khởi động ở môi trường phát triển; Windows cần được build/kiểm tra trên Windows. Repo không lưu installer trong Git và chưa xuất bản GitHub Release.

Bản đóng gói chứa Python và các gói Python cần cho app. Máy dùng app không cần cài riêng Python hay Conda, nhưng vẫn cần driver camera, hệ điều hành và thư viện hệ thống tương thích. Mỗi hệ điều hành cần một bản build riêng.

## Build bằng GitHub Actions

1. Mở **Actions → Build desktop app → Run workflow**.
2. Chọn nhánh cần build và chạy workflow.
3. Tải **Artifacts** của lần chạy thành công:
   - `MicromouseTimer-windows`: installer EXE và gói ZIP.
   - `MicromouseTimer-linux`: gói DEB và TAR.GZ.

Workflow chạy test trước khi đóng gói. Nó tạo artifact để tải về, không tự đăng một GitHub Release.

## Build tại máy

Dùng Python/môi trường ảo tương ứng với hệ điều hành đích. Chạy trong `microtimer/`:

```bash
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean packaging/MicromouseTimer.spec
```

PyInstaller tạo `dist/MicromouseTimer/`. Toàn bộ thư mục này phải được giữ cùng nhau; không chỉ chép một file executable.

Các tài nguyên được đóng gói gồm cấu hình mặc định, `assets/` và hai file video mẫu được liệt kê trong spec. Video khác trong `samples/`, kết quả, log và tùy chọn cá nhân không được đóng gói.

Nếu cần tạo lại icon:

```bash
python packaging/create_icon.py
```

Icon được ghi vào `assets/icons/`. Logo SRC nằm ở `assets/branding/club_logo.jpg`.

### Windows

Cài Inno Setup, sau đó biên dịch:

```powershell
ISCC.exe packaging/installer.iss
```

File đầu ra: `dist/MicromouseTimer-Setup-Windows.exe`. Installer cài cho người dùng hiện tại, tạo mục Start Menu, có tùy chọn shortcut desktop và hỗ trợ gỡ qua danh sách ứng dụng Windows.

Có thể chạy bản portable bằng `dist\MicromouseTimer\MicromouseTimer.exe`. Installer hiện chưa được ký chứng thư nhà phát hành.

### Linux

Trên Debian/Ubuntu có `dpkg-deb`:

```bash
python packaging/build_deb.py
sudo apt install ./dist/micromouse-timer_1.2.2_amd64.deb
```

Package yêu cầu glibc 2.39 trở lên và `libxcb-cursor0`; `apt` xử lý phụ thuộc của package. App xuất hiện trong menu ứng dụng và có thể gỡ bằng trình quản lý gói.

Tạo bản portable:

```bash
tar -czf dist/MicromouseTimer-linux.tar.gz -C dist MicromouseTimer
```

Giải nén rồi chạy `MicromouseTimer/MicromouseTimer`. Máy Linux vẫn cần desktop đồ họa và các thư viện Qt/OpenCV của hệ thống. Với X11, kiểm tra `libxcb-cursor.so.0` nếu Qt báo không tải được plugin `xcb`. Build trên môi trường nền phù hợp và kiểm tra trên máy đích; TAR.GZ không đảm bảo chạy trên mọi bản phân phối Linux.

## Nơi lưu dữ liệu

| Cách chạy | Thư mục dữ liệu |
| --- | --- |
| Từ mã nguồn | `microtimer/` |
| App Windows đã đóng gói | `%APPDATA%\MicromouseTimer\` |
| App Linux đã đóng gói | `${XDG_DATA_HOME:-~/.local/share}/MicromouseTimer/` |

Trong thư mục dữ liệu, `exports/` chứa CSV/XLSX, `logs/` chứa log và `preferences.json` chứa tham số lấy mẫu đã lưu. Các dữ liệu này không nằm trong installer và không được Git theo dõi.
