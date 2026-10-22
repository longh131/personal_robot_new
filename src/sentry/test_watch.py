from io import BytesIO

from PIL import Image

from sentry.watch import events_in_hour, gray_small, mean_abs_diff, pick_main


def _jpeg(color: int) -> bytes:
    im = Image.new("L", (64, 48), color=color)
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_diff_detects_change():
    a = gray_small(_jpeg(10))
    b = gray_small(_jpeg(200))
    assert a and b
    assert mean_abs_diff(a, a) < 2
    assert mean_abs_diff(a, b) > 40


def test_pick_main_highest_score():
    shots = [
        {"path": "a.jpg", "score": 3.0},
        {"path": "b.jpg", "score": 22.0},
        {"path": "c.jpg", "score": 9.0},
    ]
    assert pick_main(shots)["path"] == "b.jpg"


def test_hour_cap():
    now = 10_000.0
    stamps = [now - 4000, now - 10, now - 5]
    assert events_in_hour(stamps, now) == 2
