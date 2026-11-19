"""CHECK BỔ SUNG (+3 thưởng) — phát hiện box có tỉ lệ khung hình quá lệch (aspect ratio)."""

from ..common import WARN, Issue, parse_yolo_line


def run(ds, cfg):
    acfg = cfg.get("aspect_ratio", {})
    max_ratio = float(acfg.get("max_aspect_ratio", 8.0))
    issues = []

    for lf in ds.label_files():
        stem = lf.stem
        lines = ds.read_label_lines(stem) or []
        img_size = ds.image_size(stem)

        for line_no, text in lines:
            try:
                _, _, _, w, h = parse_yolo_line(text)
            except (ValueError, OverflowError):
                continue
            if w <= 0 or h <= 0:
                continue

            if img_size is not None:
                bw = w * img_size[0]
                bh = h * img_size[1]
            else:
                bw, bh = w, h

            if bw <= 0 or bh <= 0:
                continue

            ratio = max(bw / bh, bh / bw)
            if ratio > max_ratio:
                extra = {"aspect_ratio": round(ratio, 4)}
                if img_size is not None:
                    extra["w_px"] = round(bw, 1)
                    extra["h_px"] = round(bh, 1)
                issues.append(
                    Issue(
                        "aspect_ratio",
                        WARN,
                        "BOX_EXTREME_ASPECT",
                        stem,
                        f"tỉ lệ khung hình {ratio:.2f} > {max_ratio:g}",
                        line=line_no,
                        extra=extra,
                    )
                )
    return issues
