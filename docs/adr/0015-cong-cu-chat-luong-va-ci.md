# ADR-0015: Công cụ chất lượng (pytest, ruff, mypy, import-linter, coverage) và CI trên GitHub Actions

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-11-21
- **Liên quan:** ADR-0013, ADR-0014, [testing-strategy.md](../architecture/testing-strategy.md)

## Bối cảnh
- [ĐO] Môi trường chưa có công cụ test/lint/type nào.
- Kiểm chứng hiện dựa vào chạy thật trên LDPlayer và 2 script hồi quy (đang pass 13/13 và 34/34).
- Fixture ảnh (97 MB) bị `.gitignore`.
- Repo có remote GitHub.

## Quyết định
- Thêm nhóm dependency **dev**: `pytest`, `ruff`, `mypy`, `import-linter`, `coverage`. Không thêm dependency runtime.
- Áp luật **nghiêm** (ruff đầy đủ, `mypy --strict`, ngưỡng coverage) chỉ cho `src/aowbot`. Mã cũ chỉ kiểm lỗi cú pháp và tên chưa định nghĩa.
- CI: GitHub Actions `windows-latest`, Python 3.12, chạy mọi test trừ marker `device`/`ocr`.
- Chọn mypy thay pyright vì cài bằng pip, không cần Node.

## Phương án đã cân nhắc
- **A. Không CI, chỉ chạy local.** Nhược: không có cổng chặn khi đổi code.
- **B. CI Linux.** Ưu: nhanh hơn. Nhược: khác môi trường thật (Windows, đường dẫn, LDPlayer).
- **C. Windows CI + phạm vi nghiêm chỉ cho mã mới (chọn).** Tránh sửa hàng loạt mã cũ chạy ổn chỉ để thỏa linter.

## Hệ quả
- Tốt: mỗi thay đổi có cổng tự động; mã mới luôn có type và test.
- Xấu / chi phí: CI Windows chậm hơn Linux; hồi quy ảnh chưa chạy được trên CI cho tới khi chủ dự án chọn phương án fixture (testing-strategy §5).
- Việc phải làm theo: bước S0; CI chỉ hoạt động khi chủ dự án push; ghi lệnh chạy local tương đương CI vào README.
