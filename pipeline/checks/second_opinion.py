"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l)."""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    scfg = cfg["second_opinion"]
    conf_thresh = scfg["conf"]
    min_area_px = scfg["min_area_px"]
    fp_conf = scfg["fp_conf"]
    iou_missing = scfg["iou_missing"]
    iou_match = scfg["iou_match"]
    iou_loose = scfg["iou_loose"]
    n_classes = len(ds.classes)

    issues = []
    for img_p in ds.image_files():
        stem = img_p.stem
        if stem not in preds:
            continue
        raw_lines = ds.read_label_lines(stem)
        if raw_lines is None:
            continue
        img_size = ds.image_size(stem)
        if img_size is None:
            continue
        img_w, img_h = img_size

        valid_labels = []
        for line_no, text in raw_lines:
            try:
                b = parse_yolo_line(text)
            except (ValueError, OverflowError):
                continue
            if 0 <= b[0] < n_classes:
                valid_labels.append((line_no, b[0], (b[1], b[2], b[3], b[4])))

        img_preds = preds[stem]

        for r in img_preds:
            r_cls = int(r[0])
            r_conf = float(r[1])
            r_box = (float(r[2]), float(r[3]), float(r[4]), float(r[5]))
            area_px = (r_box[2] * img_w) * (r_box[3] * img_h)
            if r_conf < conf_thresh or area_px < min_area_px:
                continue

            cands = []
            for _, l_cls, l_box in valid_labels:
                iou = iou_xywh(r_box, l_box)
                if iou >= iou_missing:
                    cands.append((l_cls, iou))

            if not cands:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_MISSING",
                        stem,
                        f"model thấy lớp {r_cls} (conf={r_conf:.2f}) nhưng nhãn không có",
                        extra={"conf": round(r_conf, 4), "pred_cls": r_cls},
                    )
                )
                continue

            same_ious = [iou for l_cls, iou in cands if l_cls == r_cls]
            if same_ious:
                best_same = max(same_ious)
                if best_same < iou_loose:
                    issues.append(
                        Issue(
                            "second_opinion",
                            WARN,
                            "POSSIBLE_LOOSE_BOX",
                            stem,
                            f"box cùng lớp {r_cls} nhưng IoU={best_same:.2f} < {iou_loose}",
                            extra={"conf": round(r_conf, 4), "iou": round(best_same, 4)},
                        )
                    )
            else:
                best_other = max(iou for _, iou in cands)
                if best_other >= iou_match:
                    issues.append(
                        Issue(
                            "second_opinion",
                            WARN,
                            "POSSIBLE_WRONG_CLASS",
                            stem,
                            f"nhãn lệch lớp so với model (model: {r_cls}, IoU={best_other:.2f})",
                            extra={"conf": round(r_conf, 4), "iou": round(best_other, 4), "pred_cls": r_cls},
                        )
                    )

        fp_boxes = [
            (float(r[2]), float(r[3]), float(r[4]), float(r[5]))
            for r in img_preds
            if float(r[1]) >= fp_conf
        ]
        for line_no, _, l_box in valid_labels:
            best_iou = max((iou_xywh(l_box, p_box) for p_box in fp_boxes), default=0.0)
            if best_iou < iou_missing:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_FALSE_POS",
                        stem,
                        f"box nhãn dòng {line_no} không khớp dự đoán model (best IoU={best_iou:.2f})",
                        line=line_no,
                        extra={"iou": round(best_iou, 4)},
                    )
                )

    return issues
