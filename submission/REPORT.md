# Báo cáo Day 09 — LuongDucManh, 2A202603155

## 1. Kết luận trước
Pipeline kết luận **Hold** (mã thoát `10`). Trong **224** ảnh thô đưa vào, cửa vào loại **22** ảnh (ảnh hỏng, kích thước nhỏ, trùng và rò rỉ tập test), nhận **202** ảnh xuất thành bản nháp `submission/export/clean_v1`. Lý do chưa **Release**: tuy không còn lỗi bắt buộc (`0` error), nhưng sau khi dùng hết ngân sách duyệt **80/125** ảnh, vẫn còn **38/202** ảnh (**18.81%**) có cảnh báo chưa được người duyệt — vượt ngưỡng `warn_ratio_hold = 10.00%`.

## 2. Lỗi và phân việc
Tổng hợp từ `submission/reports/02_error_list_v1.csv` (trên 202 ảnh đã qua cửa vào + 22 ảnh loại ở Bước 1):

| Mã lỗi | Số dòng / ảnh | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `CORRUPT_IMAGE` | 2 dòng / 2 ảnh | Máy (`intake`/`autofix`) | Ảnh hỏng không đọc được, cần loại bỏ |
| `BAD_SIZE` | 3 dòng / 3 ảnh | Máy (`intake`/`autofix`) | Cạnh ngắn < 250 px, vi phạm chuẩn đầu vào |
| `LEAK_TEST` | 5 dòng / 5 ảnh | Máy (`intake`/`autofix`) | Trùng kho test/gold_val, phải loại để tránh rò rỉ |
| `DUP_IMAGE_EXACT` | 8 dòng / 8 ảnh | Máy (`intake`/`autofix`) | Trùng từng byte MD5, loại bản dư |
| `DUP_IMAGE_NEAR` | 4 dòng / 4 ảnh | Máy (`intake`/`autofix`) | Gần trùng (`phash_dist <= 10`), loại bản dư |
| `BAD_CLASS_NAME` | 2 dòng / `data.yaml` | Máy (`autofix`) | Chuẩn hoá lại tên lớp (`Person`→`person`, `Bus`→`bus`) theo config |
| `BAD_CLASS_ID` | 6 dòng / 6 ảnh | Máy (`autofix`) | ID lớp ngoài `0..3` không hợp lệ, xoá dòng an toàn |
| `BAD_FORMAT` | 3 dòng / 3 ảnh | Máy (`autofix`) | Sai 5 cột hoặc `nan/inf`, không khôi phục được, xoá dòng |
| `BOX_ZERO` | 4 dòng / 4 ảnh | Máy (`autofix`) | Chiều rộng/cao `<= 0`, xoá dòng |
| `DUP_BOX` | 7 dòng / 7 ảnh | Máy (`autofix`) | Trùng lặp box cùng lớp (`IoU > 0.9`), xoá dòng sau |
| `BOX_OUT_OF_IMAGE` | 8 dòng / 8 ảnh | Máy (`autofix`) | Cắt (clip) toạ độ tràn biên về `[0, 1]` |
| `MISSING_LABEL_FILE` | 6 dòng / 6 ảnh | Người (hàng đợi) | Máy không được bịa nhãn; chuyển người gán (`needs_label`) |
| `POSSIBLE_MISSING` | 53 dòng / 52 ảnh | Người (hàng đợi) | Nghi sót nhãn theo `yolo26l`, cần mắt người xác nhận |
| `POSSIBLE_FALSE_POS` | 29 dòng / 27 ảnh | Người (hàng đợi) | Nhãn không khớp dự đoán model, có thể là nhiễu hoặc model sót |
| `POSSIBLE_LOOSE_BOX` | 28 dòng / 24 ảnh | Người (hàng đợi) | Box cùng lớp nhưng `IoU < 0.5`, người xem để chỉnh biên |
| `POSSIBLE_WRONG_CLASS` | 18 dòng / 18 ảnh | Người (hàng đợi) | Nghi nhầm lớp so với model lớn, người quyết định lớp đúng |
| `EMPTY_LABEL` | 12 dòng / 12 ảnh | Người (hàng đợi) | Cần phân biệt ảnh nền thật hay người gán bỏ sót |
| `BOX_TINY` | 6 dòng / 4 ảnh | Người (hàng đợi) | Cạnh ngắn `< 12 px`, dễ là nhiễu hoặc vật quá xa |
| `BOX_HUGE` | 3 dòng / 3 ảnh | Người (hàng đợi) | Box chiếm `> 95%` diện tích ảnh, cần kiểm tra có bị vẽ trùm không |
| `CLASS_RARE` | 4 dòng / `<dataset>` | Cảnh báo thống kê | Nhắc theo dõi số box theo lớp ở mức dataset |

`05_review_queue.csv` xếp ưu tiên theo tổng điểm trọng số lỗi nhân độ tự tin `(1 + conf)`: các ảnh chưa có nhãn (`NEEDS_LABEL`, trọng số `10.0`) và ảnh vừa bị máy sửa mạnh kèm nhiều cảnh báo ngữ nghĩa như `img_0020` (`priority = 11.524`, `FIXED_DROP_LINE;POSSIBLE_MISSING;POSSIBLE_WRONG_CLASS`) được đưa lên đầu. Với ngân sách **80/125** ảnh, người duyệt đã xử lý được toàn bộ **6** ảnh thiếu nhãn và **74** ảnh mang lỗi ngữ nghĩa (`POSSIBLE_*`).

## 3. Calibration (2 ngưỡng)

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---:|---:|---|---|
| `duplicates.phash_dist` | 2 | 10 | `DUP_IMAGE_EXACT`: `1.00/1.00` → `1.00/1.00`; `DUP_IMAGE_NEAR`: `1.00/0.50` → `1.00/0.67` | Tăng `2 → 10` bắt thêm ảnh gần trùng mà không gây xoá nhầm; tránh tăng lên `20` vì trên calib Recall của `DUP_IMAGE_EXACT` tụt xuống `0.33` |
| `second_opinion.conf` | 0.25 | 0.6 | `WRONG_CLASS`: `0.56/0.83` → `0.62/0.83`; `MISSING`: `0.50/1.00` → `0.57/1.00` | Giữ nguyên Recall tối đa (`1.00` cho MISSING, `0.83` cho WRONG_CLASS) đồng thời giảm báo động giả trước khi Recall tụt ở `0.7–0.8` |

**Một chỗ calibration có thể đánh lừa:** Tập `calib` chỉ có 39 ảnh nên tại `phash_dist = 16`, Precision của `DUP_IMAGE_NEAR` vẫn hiển thị `1.00` (Recall `0.83`), dễ làm hiểu nhầm rằng chọn `16` hoàn toàn an toàn. Trên 224 ảnh thực tế đa dạng góc đường ở `raw`, ngưỡng Hamming lớn làm tăng rủi ro loại nhầm 2 ảnh khác nhau hoặc gắn nhầm `LEAK_TEST`; ngoài ra `calib` cũng không chứa ca `LEAK_TEST` và có phân bố lỗi lớp khác với `raw`. Với `phash_dist = 10`, cả 4 ca `DUP_IMAGE_NEAR` bị loại ở `01_intake.csv` (`dist` = 0, 0, 6, 10) đều nằm trong vùng hợp lý.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
- **(a) Chứng minh gate chặn đúng:** Chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không có người duyệt nên 6 ảnh `MISSING_LABEL_FILE` vẫn giữ nguyên): pipeline kết luận **Rework**, mã thoát **20**, `exported: null` và **không** tạo thư mục xuất dataset.
- **(b) Điểm mù của pipeline:**
  1. *Box lỏng nhẹ trong vùng `IoU >= 0.5`:* Vì `iou_loose = 0.5`, các box có độ trùng `0.5 <= IoU < 0.75` sẽ không bị cờ `POSSIBLE_LOOSE_BOX`; trên tập calib tại `conf = 0.6`, Recall của `POSSIBLE_LOOSE_BOX` chỉ đạt `0.20` (bỏ sót `4/5` ca).
  2. *Lỗi ngữ nghĩa mà model kiểm định (`yolo26l`) cũng nhầm hoặc bỏ sót, và ảnh trùng biến đổi mạnh:* Tại `conf = 0.6`, `POSSIBLE_WRONG_CLASS` vẫn sót `1/6` ca trên calib (`Recall = 0.83`), và 2 ca `DUP_IMAGE_NEAR` biến đổi mạnh vượt `phash_dist = 10` (`Recall = 0.67`) cũng lọt qua bước kiểm trùng.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Huấn luyện bằng `yolo26n.pt`, `30` epoch, `imgsz=640`, `batch=16`, `2` seed (`0`, `1`) trên Tesla T4 GPU (`raw`: 224 ảnh gốc — Ultralytics bỏ 11 ảnh lỗi còn 213; `clean`: 202 ảnh sau pipeline):

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---:|---:|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 202 | 2 | 0.701 ± 0.025 | 0.487 ± 0.008 | 0.759 ± 0.003 | 0.625 ± 0.019 |

- **Kết luận trung thực:** Chênh lệch `mAP50 (clean − raw) = -0.025`, đúng bằng **1 độ lệch chuẩn** của `clean` (`±0.025`), tức là dao động nằm trong độ nhiễu giữa các seed — **chưa đủ cơ sở kết luận `clean` cải thiện hơn `raw`** (thậm chí đang thấp nhẹ trong 2 seed thử nghiệm).
- **Giả thuyết giải thích:**
  1. *Rò rỉ tập test (`LEAK_TEST`) và số lượng ảnh:* `raw` chứa **5 ảnh trùng trực tiếp với tập test** (đã bị `intake` loại ở `clean`) cùng một số ảnh trùng nội bộ, nên model train trên `raw` hưởng lợi thế rò rỉ khi đo trên tập test 100 ảnh; `clean` cũng ít hơn 11 ảnh train thực tế (`202` vs `213`).
  2. *Nhiễu ở lớp hiếm trên tập test nhỏ (100 ảnh):* `clean` vẫn đang ở trạng thái **Hold** (còn `38` ảnh cảnh báo chưa được duyệt) và lớp `truck` chỉ có `41` box — riêng AP50 của `truck` ở `clean_seed1` tụt xuống `0.4856` (so với `0.5898` ở `clean_seed0`), kéo trung bình `clean` giảm và tăng độ lệch chuẩn lên `±0.025`.
- **Cách kiểm chứng:** Đánh giá lại trên tập `test` đã loại bỏ 5 ảnh rò rỉ, tăng số seed (`0, 1, 2, 3`) để thu hẹp sai số ngẫu nhiên, và duyệt nốt 38 ảnh cảnh báo còn lại để đạt `Release` trước khi train lại.

## 6. Quyết định và ghi chú AI
- **(a) Quyết định cuối:** Giữ kết luận **Hold** (`18.81% >= 10.00%`), chưa phát hành chính thức `clean_v1`. Để đạt **Release**, cần bổ sung ngân sách duyệt thêm ít nhất ~18 ảnh có cảnh báo nữa (giảm số ảnh cảnh báo chưa duyệt từ `38/202` xuống `< 21/202`), ưu tiên xử lý hết các ca `POSSIBLE_WRONG_CLASS` (3) và `POSSIBLE_MISSING` (13) còn lại trong `07_error_list_v3.txt`.
- **(b) Ghi chú sử dụng AI:**
  - *Prompt chính:* Yêu cầu viết 4 module (`label_format`, `gate`, `autofix`, `second_opinion`) kèm mô tả rõ đầu vào/đầu ra, mã lỗi, cấu hình `cfg` và các ca biên.
  - *Cách kiểm code AI:* Đối chiếu từng dòng với docstring và `pipeline/common.py`, chạy toàn bộ 79 test (`pytest -q`), kiểm chứng trên tập calib (`pipeline.calibrate`), chạy thực tế trên `raw` (`pipeline.run`) và thử `--budget 0` cho Gate `Rework`.
  - *1 lần AI sai / cần chỉnh kỹ:* Xử lý ưu tiên khi 1 dòng dính 2 lỗi (ví dụ vừa `BOX_OUT_OF_IMAGE` vừa `DUP_BOX` thì chỉ `drop_line`, không ghi thêm `clip_box`) và bảo toàn số dòng gốc khi file nhãn có dòng trống xen giữa.
- **(c) CVAT lọc box nhỏ (mục 6b theo `docs/CVAT_FILTER.md` — phần thưởng +2):** Đã tạo project/task trên CVAT (`cvat/labels.json`), nạp 24 ảnh đầu hàng đợi + `BOX_TINY` dạng YOLO 1.1 và bật bộ lọc `Width < 20`. Duyệt **6 ảnh** đều cho kết quả khớp, tổng **18 box** (`person`): `img_0020.jpg` (3 box), `img_0026.jpg` (6 box), `img_0030.jpg` (1 box), `img_0051.jpg` (3 box), `img_0069.jpg` (2 box), `img_0161.jpg` (3 box). **Đối chiếu `BOX_TINY` của pipeline:** `img_0161` khớp đủ 3/3 dòng `BOX_TINY` (`10.3–11.9 px`), `img_0030` khớp 1/1 dòng (`9.8 px`), `img_0026`/`img_0051`/`img_0069` mỗi ảnh có 1 box `< 12 px` (`11.4`, `8.9`, `11.2 px`), còn các box dư trên CVAT (và 3 box ở `img_0020`) có bề rộng `12–19 px` nên lọt qua ngưỡng `< 12 px` của pipeline; riêng `img_0069` cho thấy box nhỏ bị gán nhầm lên cột đèn đường sắt. **Về thuộc tính `can_review`:** Người gán tick `can_review` trên CVAT khi gặp box nhỏ/mơ hồ cần người kiểm duyệt lọc (`attr["can_review"]==true`) xem lại; trong pipeline, cơ chế tương đương là danh sách ảnh nghi ngờ ở `05_review_queue.csv` kèm cột `reviewed` trong `06_review_log.csv`. Ảnh chụp bộ lọc lưu tại: `submission/cvat_evidence/cvat_filter_1.png`, `submission/cvat_evidence/cvat_filter_2.png`, `submission/cvat_evidence/cvat_filter_3.png`, `submission/cvat_evidence/cvat_filter_4.png`, `submission/cvat_evidence/cvat_filter_5.png`, `submission/cvat_evidence/cvat_filter_6.png`.
- **(d) Check mới tự viết (phần thưởng +3):** Đã bổ sung module `pipeline/checks/aspect_ratio.py` (mã cảnh báo `BOX_EXTREME_ASPECT`, tính theo tỉ lệ cạnh pixel thực `max(w_px/h_px, h_px/w_px) > 8.0`, không sửa các file đã ghim SHA1) kèm **6 unit test** trong `tests/test_aspect_ratio.py` (tổng **85 passed**). Khi chạy độc lập trên tập gốc: phát hiện **3** box có tỉ lệ khung hình > 8.0 trên `data/raw` (ví dụ: `img_0042` (dòng 5, ratio=9.6), `img_0076` (dòng 5, ratio=9.2), `img_0155` (dòng 2, ratio=9.8)).
