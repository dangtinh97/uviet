# UViet

UViet là bộ gõ tiếng Việt Telex cho Ubuntu dùng IBus.

- **UViet (Telex, không gạch chân)** hiện từ đang gõ ở bảng IBus. Ô nhập chỉ nhận văn bản Unicode NFC khi chốt từ. UViet gửi nguyên từ cùng dấu cách hoặc dấu câu ASCII trong một lần, không cần xóa hoặc gõ lại chữ trong ô nhập.
- **UViet (Telex)** gõ trực tiếp trong ô nhập thường có hỗ trợ đọc và sửa chữ quanh con trỏ. Với các ô khác, UViet gửi chữ đang soạn cùng thuộc tính `Underline.NONE`. Ứng dụng hoặc compositor có thể áp dụng định dạng riêng.

## Cài đặt trên Ubuntu GNOME

Từ thư mục dự án, tạo và cài gói Debian:

```sh
make deb
sudo apt install ./dist/uviet_0.6.4_all.deb
```

Sau khi cài, đăng xuất khỏi Ubuntu rồi đăng nhập lại để IBus và GNOME nạp UViet. Nếu chỉ cập nhật bộ gõ trong phiên GNOME đang chạy, có thể khởi động lại dịch vụ IBus như bên dưới.

Khi phát triển hoặc thử mã nguồn trực tiếp, có thể cài bằng Makefile:

```sh
sudo apt install ibus python3-gi gir1.2-ibus-1.0 gir1.2-gtk-3.0 make
sudo make install
systemctl --user restart org.freedesktop.IBus.session.GNOME.service
```

Mở **Cài đặt → Bàn phím → Nguồn nhập → Thêm nguồn nhập**, chọn **Tiếng Việt → UViet (Telex)** để gõ ngay trong ô nhập, hoặc **UViet (Telex, không gạch chân)** nếu muốn xem từ đang gõ ở bảng IBus. Nếu chưa thấy UViet, đăng xuất rồi đăng nhập lại. Dùng **Super+Space** để chuyển nguồn nhập.

## Gõ thử

Dùng **UViet (Telex)** cho Terminal và các ô văn bản. Khi Chrome trên Wayland báo ô kiểu URL, UViet để Chrome xử lý Enter và gợi ý trực tiếp. UViet chỉ cập nhật dấu Telex trong ô URL khi ứng dụng cung cấp văn bản quanh con trỏ và phần chữ trước con trỏ khớp với từ vừa gõ. Khi Chrome còn chọn phần đuôi gợi ý, UViet giữ phím Telex trong bộ đệm và chỉ thử đổi dấu ở phím chữ tiếp theo hoặc Space sau khi vùng chọn biến mất. Enter vẫn đi thẳng vào Chrome.

Nếu dùng lối mở **Google Chrome (UViet)** đã cài trên máy, hãy thoát hẳn Chrome trước khi mở lại. Lối mở này bật đường nhập Wayland và dùng thanh địa chỉ gốc của Chrome để ô nhập báo đúng loại URL.

| Gõ | Kết quả |
| --- | --- |
| `Tieengs Vieetj` | Tiếng Việt |
| `Tooi ddang gox` | Tôi đang gõ |
| `dduwowngf` | đường |

Space, dấu câu, Enter và phím điều hướng chốt từ hiện tại. Ở chế độ **không gạch chân**, hãy chốt từ trước khi bấm chuột sang ô khác hoặc chuyển ứng dụng. Đổi tiêu điểm sẽ hủy từ còn đang soạn. Backspace xóa ký tự cuối của từ đang soạn. Esc hủy từ đang soạn. `z` bỏ dấu và chuyển các chữ Telex về ASCII.

Để kiểm tra lỗi gạch chân, gõ `tieengs` trong ứng dụng gặp lỗi, rồi nhấn Space. Trước Space, từ đang soạn xuất hiện ở bảng IBus. Sau Space, ô nhập phải có đủ **tiếng**, gồm cả chữ **t** đầu tiên. Đây là bản Telex đầu tiên. Để nhập tiếng Anh, có thể chuyển nguồn nhập bằng Super+Space. Bản này chưa có VNI, gõ tắt hay kiểm tra chính tả.

## Gỡ cài đặt

Bỏ UViet khỏi danh sách nguồn nhập. Nếu đã cài tệp Debian, chạy `sudo apt remove uviet`. Nếu đã cài bằng Makefile, chạy:

```sh
sudo make uninstall
systemctl --user restart org.freedesktop.IBus.session.GNOME.service
```

## Tắt Telex theo ứng dụng

Trên GNOME Shell 50, sau khi cài lần đầu hãy đăng xuất rồi đăng nhập lại và bật bộ chọn cửa sổ bằng `gnome-extensions enable app-picker@uviet.local`.

Tìm **UViet** trong menu ứng dụng hoặc chọn **Mở Cài đặt UViet…** trong menu bộ gõ trên thanh trên cùng. Kéo nút hình ống nhỏ giọt lên cửa sổ cần loại trừ rồi thả, hoặc bấm nút rồi chọn cửa sổ. Lặp lại cho từng ứng dụng. Để xóa một mục, bấm **Bật lại Telex** bên cạnh tên ứng dụng. UViet đọc thay đổi ngay mà không cần khởi động lại IBus.

UViet nhận diện theo lớp cửa sổ GNOME và lưu lựa chọn trong `~/.config/uviet/excluded-apps.json` theo mặc định. Quy tắc áp dụng cho các cửa sổ có cùng lớp. Nếu GNOME chưa cung cấp lớp cửa sổ, mục này sẽ bị vô hiệu hóa.

## Gợi ý thanh địa chỉ Chrome khi dùng Bamboo

Tiện ích `chrome-omnibox@uviet.local` dành cho GNOME Shell 50 trên Wayland. Khi Bamboo đang được chọn và cửa sổ Google Chrome báo ô nhập kiểu URL, tiện ích để Chrome nhận trực tiếp các phím, kể cả Enter. GNOME có thể báo cùng loại URL cho một ô trên trang web. Các ô nhập thông thường và các ứng dụng khác tiếp tục đi qua Bamboo.

```sh
gnome-extensions pack --extra-source=policy.js --out-dir=/tmp chrome-omnibox@uviet.local
gnome-extensions install /tmp/chrome-omnibox@uviet.local.shell-extension.zip
```

Đăng xuất và đăng nhập lại để GNOME nhận tiện ích mới, rồi chạy `gnome-extensions enable chrome-omnibox@uviet.local`. Có thể tắt bằng `gnome-extensions disable chrome-omnibox@uviet.local`.

## Chữ đang soạn trong ứng dụng GTK trên Wayland

GNOME Shell có thể bỏ qua định dạng `Underline.NONE` khi chuyển preedit qua Wayland. Với ứng dụng GTK có mô-đun IBus, mở một tiến trình mới bằng `env GTK_IM_MODULE=ibus tên-ứng-dụng` để thử dùng trực tiếp định dạng do UViet gửi. Chọn nguồn **UViet (Telex)** để chữ hiện trong dòng.

GNOME Terminal dùng tiến trình dịch vụ riêng. Đặt `Environment=GTK_IM_MODULE=ibus` trong mục `[Service]` của cấu hình bổ sung cho `gnome-terminal-server.service`, rồi chạy `systemctl --user daemon-reload`. Cấu hình có hiệu lực khi dịch vụ khởi động lại, chẳng hạn sau khi đăng xuất và đăng nhập lại.

## Phiên bản

Tăng giá trị `<version>` trong `uviet.xml` khi phát hành thay đổi. Makefile dùng cùng giá trị cho tên gói Debian và cửa sổ **Cài đặt UViet**.
