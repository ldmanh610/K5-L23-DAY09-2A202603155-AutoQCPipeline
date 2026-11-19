"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework."""
from ..common import ERROR, WARN


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    reviewed_set = set(reviewed)

    in_ds = [i for i in issues if i.image in stems]
    n_errors = sum(1 for i in in_ds if i.severity == ERROR)
    warn_images = {i.image for i in in_ds if i.severity == WARN and i.image not in reviewed_set}
    n_warn_images = len(warn_images)
    n_images = len(stems)

    raw_ratio = (n_warn_images / n_images) if n_images > 0 else 0.0
    warn_ratio = round(raw_ratio, 4)
    hold_thresh = cfg["gate"]["warn_ratio_hold"]

    if n_errors > 0:
        decision = "Rework"
        reasons = [f"Còn {n_errors} lỗi bắt buộc trong {n_images} ảnh chưa được xử lý"]
    elif n_images > 0 and raw_ratio >= hold_thresh:
        decision = "Hold"
        reasons = [f"Tỉ lệ ảnh còn cảnh báo chưa duyệt {n_warn_images}/{n_images} ({warn_ratio:.2%}) >= ngưỡng {hold_thresh:.2%}"]
    else:
        decision = "Release"
        reasons = [f"Không còn lỗi bắt buộc; ảnh cảnh báo chưa duyệt {n_warn_images}/{n_images} ({warn_ratio:.2%}) < ngưỡng {hold_thresh:.2%}"]

    return {
        "decision": decision,
        "n_errors": n_errors,
        "n_warn_images": n_warn_images,
        "n_images": n_images,
        "warn_ratio": warn_ratio,
        "reasons": reasons,
    }
