"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp."""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    c = cfg["label_format"]
    overflow_tol = c["overflow_tol"]
    min_box_px = c["min_box_px"]
    max_box_frac = c["max_box_frac"]
    dup_box_iou = c["dup_box_iou"]
    n_classes = len(ds.classes)

    issues = []
    for lp in ds.label_files():
        stem = lp.stem
        lines = ds.read_label_lines(stem) or []
        img_size = ds.image_size(stem)
        seen_boxes = []

        for line_no, text in lines:
            try:
                cls_id, cx, cy, w, h = parse_yolo_line(text)
            except (ValueError, OverflowError) as e:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, f"dòng sai định dạng: {e}", line=line_no))
                continue

            if not (0 <= cls_id < n_classes):
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem, f"id lớp {cls_id} ngoài 0..{n_classes - 1}", line=line_no))
                continue

            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, f"kích thước box <= 0 ({w}, {h})", line=line_no))
                continue

            x1, y1 = cx - w / 2.0, cy - h / 2.0
            x2, y2 = cx + w / 2.0, cy + h / 2.0
            overflow = max(0.0, -x1, -y1, x2 - 1.0, y2 - 1.0)
            if overflow > overflow_tol:
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BOX_OUT_OF_IMAGE",
                        stem,
                        f"box tràn khỏi ảnh ({overflow:.4f})",
                        line=line_no,
                        extra={"overflow": round(overflow, 6)},
                    )
                )

            cur_box = (cx, cy, w, h)
            if any(prev_cls == cls_id and iou_xywh(cur_box, prev_box) > dup_box_iou for prev_cls, prev_box in seen_boxes):
                issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, f"box trùng với dòng trước (lớp {cls_id})", line=line_no))
            seen_boxes.append((cls_id, cur_box))

            if img_size is not None:
                img_w, img_h = img_size
                short_px = min(w * img_w, h * img_h)
                if short_px < min_box_px:
                    issues.append(
                        Issue(
                            "label_format",
                            WARN,
                            "BOX_TINY",
                            stem,
                            f"cạnh ngắn {short_px:.1f}px < {min_box_px}px",
                            line=line_no,
                        )
                    )

            if w * h > max_box_frac:
                issues.append(
                    Issue(
                        "label_format",
                        WARN,
                        "BOX_HUGE",
                        stem,
                        f"diện tích box {w * h:.3f} > {max_box_frac}",
                        line=line_no,
                    )
                )

    return issues
