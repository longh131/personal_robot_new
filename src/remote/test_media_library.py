# -*- coding: utf-8 -*-
from pathlib import Path

from remote import media_library as ml


def test_resolve_rejects_traversal(tmp_path, monkeypatch):
    root = tmp_path / "photos"
    root.mkdir()
    (root / "ok.jpg").write_bytes(b"x")
    (tmp_path / "secret.txt").write_text("nope")
    monkeypatch.setitem(ml.CATEGORIES, "remote_photos", {
        **ml.CATEGORIES["remote_photos"],
        "default": root,
        "key": ("media", "photos_test"),
    })
    monkeypatch.setattr(
        "remote.media_library.robot_get",
        lambda *_a, default=None, **_k: str(root),
    )
    assert ml.resolve_file("remote_photos", "ok.jpg") == (root / "ok.jpg").resolve()
    assert ml.resolve_file("remote_photos", "../secret.txt") is None
    assert ml.resolve_file("remote_photos", "/etc/passwd") is None
    assert ml.resolve_file("remote_photos", "") is None
    assert ml.resolve_file("nope", "ok.jpg") is None


def test_list_and_delete(tmp_path, monkeypatch):
    root = tmp_path / "photos"
    root.mkdir()
    a = root / "a.jpg"
    b = root / "b.mp3"
    a.write_bytes(b"img")
    b.write_bytes(b"aud")
    monkeypatch.setattr(
        "remote.media_library.robot_get",
        lambda *_a, default=None, **_k: str(root),
    )
    out = ml.list_category("remote_photos")
    assert out["ok"] and out["count"] == 2
    names = {i["name"] for i in out["items"]}
    assert names == {"a.jpg", "b.mp3"}
    kinds = {i["name"]: i["kind"] for i in out["items"]}
    assert kinds["a.jpg"] == "image"
    assert kinds["b.mp3"] == "audio"
    deleted = ml.delete_file("remote_photos", "a.jpg")
    assert deleted["ok"]
    assert not a.exists()
    assert ml.delete_file("remote_photos", "missing.jpg")["ok"] is False


def test_content_type_mjpeg():
    assert "jpeg" in ml.content_type(Path("clip.mjpeg"))
