"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN."""
from collections import defaultdict
import yaml

from ..common import ERROR, parse_yolo_line

DROP_LINE_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_IMAGE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def fix(ds, issues, cfg):
    fixes = []
    errs = [i for i in issues if i.severity == ERROR]

    removed_stems = set()
    for iss in errs:
        if iss.code in REMOVE_IMAGE_CODES or iss.code.startswith("DUP_IMAGE_"):
            stem = iss.image
            if stem in removed_stems:
                continue
            removed_stems.add(stem)
            img_p = ds.image_path(stem)
            lbl_p = ds.label_path(stem)
            before_name = img_p.name if img_p is not None else stem
            if img_p is not None and img_p.exists():
                img_p.unlink()
            if lbl_p.exists():
                lbl_p.unlink()
            fixes.append({
                "image": stem,
                "line": "",
                "action": "remove_image",
                "before": before_name,
                "after": "đã xoá ảnh và nhãn",
            })

    if any(i.code == "BAD_CLASS_NAME" for i in errs):
        data = {}
        if ds.yaml_path.exists():
            data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
        before_names = data.get("names")
        target_classes = list(cfg["classes"])
        if before_names != target_classes:
            data["names"] = target_classes
            data["nc"] = len(target_classes)
            ds.yaml_path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            fixes.append({
                "image": "data.yaml",
                "line": "",
                "action": "rename_classes",
                "before": str(before_names),
                "after": str(target_classes),
            })

    seen_missing = set()
    for iss in errs:
        if iss.code == "MISSING_LABEL_FILE" and iss.image not in removed_stems:
            if iss.image in seen_missing:
                continue
            seen_missing.add(iss.image)
            fixes.append({
                "image": iss.image,
                "line": "",
                "action": "needs_label",
                "before": "(không có file)",
                "after": "chuyển người gán",
            })

    drop_by_stem = defaultdict(set)
    clip_by_stem = defaultdict(set)
    for iss in errs:
        stem = iss.image
        if stem in removed_stems or iss.line is None:
            continue
        if iss.code in DROP_LINE_CODES:
            drop_by_stem[stem].add(iss.line)
        elif iss.code == "BOX_OUT_OF_IMAGE":
            clip_by_stem[stem].add(iss.line)

    for stem in sorted(set(drop_by_stem) | set(clip_by_stem)):
        lp = ds.label_path(stem)
        if not lp.exists():
            continue
        raw_lines = lp.read_text(encoding="utf-8", errors="replace").splitlines()
        drop_lines = drop_by_stem[stem]
        clip_lines = clip_by_stem[stem]
        new_lines = []
        changed = False

        for line_no, raw_text in enumerate(raw_lines, 1):
            if line_no in drop_lines:
                changed = True
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "drop_line",
                    "before": raw_text.strip(),
                    "after": "",
                })
                continue

            if line_no in clip_lines:
                try:
                    cls_id, cx, cy, w, h = parse_yolo_line(raw_text)
                except (ValueError, OverflowError):
                    changed = True
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": raw_text.strip(),
                        "after": "",
                    })
                    continue

                x1 = max(0.0, min(1.0, cx - w / 2.0))
                y1 = max(0.0, min(1.0, cy - h / 2.0))
                x2 = max(0.0, min(1.0, cx + w / 2.0))
                y2 = max(0.0, min(1.0, cy + h / 2.0))
                nw = x2 - x1
                nh = y2 - y1

                if nw <= 0.0 or nh <= 0.0:
                    changed = True
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": raw_text.strip(),
                        "after": "",
                    })
                    continue

                ncx = (x1 + x2) / 2.0
                ncy = (y1 + y2) / 2.0
                new_text = f"{cls_id} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}"
                new_lines.append(new_text)
                if new_text != raw_text.strip():
                    changed = True
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "clip_box",
                    "before": raw_text.strip(),
                    "after": new_text,
                })
                continue

            new_lines.append(raw_text)

        if changed:
            content = "\n".join(new_lines) + ("\n" if new_lines else "")
            lp.write_text(content, encoding="utf-8")

    return fixes
