from pipeline.checks import aspect_ratio
from pipeline.common import Dataset


def find(issues, code):
    return [(i.image, i.line) for i in issues if i.code == code]


def test_normal_boxes_pass(make_ds, cfg):
    ds = make_ds(
        images={"a": 1},
        labels={"a": ["0 0.5 0.5 0.2 0.2", "1 0.3 0.4 0.1 0.3"]},
        size=(640, 480),
    )
    assert aspect_ratio.run(ds, cfg) == []


def test_extreme_wide_and_tall_boxes(make_ds, cfg):
    ds = make_ds(
        images={"a": 1},
        labels={
            "a": [
                "0 0.5 0.5 0.5 0.02",
                "1 0.5 0.5 0.01 0.5",
                "0 0.5 0.5 0.2 0.2",
            ]
        },
        size=(640, 480),
    )
    iss = aspect_ratio.run(ds, cfg)
    assert find(iss, "BOX_EXTREME_ASPECT") == [("a", 1), ("a", 2)]
    assert all(i.severity == "warn" for i in iss)


def test_uses_pixel_ratio_over_normalized(make_ds, cfg):
    # Ảnh 1000x100: box 0.1x0.1 (vuông theo chuẩn hoá) thực chất là 100x10 px -> tỷ lệ 10.0 > 8.0
    # Còn box 0.05x0.5 (1:10 theo chuẩn hoá) thực chất là 50x50 px -> tỷ lệ 1.0 <= 8.0
    ds = make_ds(
        images={"w": 1},
        labels={"w": ["0 0.5 0.5 0.1 0.1", "1 0.5 0.5 0.05 0.5"]},
        size=(1000, 100),
    )
    iss = aspect_ratio.run(ds, cfg)
    assert find(iss, "BOX_EXTREME_ASPECT") == [("w", 1)]


def test_custom_threshold_from_cfg(make_ds, cfg):
    ds = make_ds(
        images={"a": 1},
        labels={"a": ["0 0.5 0.5 0.5 0.1"]},
        size=(400, 400),
    )
    assert aspect_ratio.run(ds, cfg) == []
    custom_cfg = {**cfg, "aspect_ratio": {"max_aspect_ratio": 4.0}}
    iss = aspect_ratio.run(ds, custom_cfg)
    assert find(iss, "BOX_EXTREME_ASPECT") == [("a", 1)]


def test_malformed_and_zero_lines_do_not_crash(make_ds, cfg):
    ds = make_ds(
        images={"a": 1},
        labels={"a": ["", "bad line", "0 nan 0.5 0.2 0.2", "0 0.5 0.5 0.0 0.2", "1 0.5 0.5 -0.1 0.2"]},
        size=(640, 480),
    )
    assert aspect_ratio.run(ds, cfg) == []


def test_missing_image_falls_back_to_normalized(tmp_path, cfg):
    (tmp_path / "images").mkdir()
    (tmp_path / "labels").mkdir()
    (tmp_path / "labels" / "noimg.txt").write_text("0 0.5 0.5 0.9 0.05\n", encoding="utf-8")
    ds = Dataset(tmp_path, cfg["classes"])
    iss = aspect_ratio.run(ds, cfg)
    assert find(iss, "BOX_EXTREME_ASPECT") == [("noimg", 1)]
