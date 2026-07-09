import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from PIL import Image
from io import BytesIO
from ai_client import _image_to_base64, _merge_partial_results

def _test_img():
    img = Image.new("RGB", (1, 1), color="red")
    p = Path(__file__).parent / "_t.jpg"
    img.save(p, format="JPEG")
    return p

class TestImageToBase64:
    def test_returns_string(self):
        p = _test_img()
        r = _image_to_base64(p)
        p.unlink(missing_ok=True)
        assert isinstance(r, str) and len(r) > 0
    def test_valid_base64(self):
        import base64
        p = _test_img()
        r = _image_to_base64(p)
        p.unlink(missing_ok=True)
        assert len(base64.b64decode(r)) > 0
    def test_rgba_to_rgb(self):
        img = Image.new("RGBA", (1, 1), color="red")
        p = Path(__file__).parent / "_tr.png"
        img.save(p, format="PNG")
        r = _image_to_base64(p)
        p.unlink(missing_ok=True)
        assert isinstance(r, str)

class TestMergePartialResults:
    def test_merges_fields(self):
        parts = [{"plec": "Kobieta", "wiek": 23}, {"praca_status": "Nie"}]
        m = _merge_partial_results(parts)
        assert m["plec"] == "Kobieta" and m["wiek"] == 23 and m["praca_status"] == "Nie"
    def test_first_wins_on_conflict(self):
        parts = [{"plec": "Kobieta", "wiek": 23}, {"plec": "Mezczyzna"}]
        m = _merge_partial_results(parts)
        assert m["plec"] == "Kobieta" and m["wiek"] == 23
    def test_merges_needs_review(self):
        parts = [{"p": "a", "needs_review": {"p": False}}, {"q": "b", "needs_review": {"q": True}}]
        m = _merge_partial_results(parts)
        assert m["needs_review"] == {"p": False, "q": True}
    def test_handles_missing_needs_review(self):
        assert _merge_partial_results([{"p": "a"}])["needs_review"] == {}
    def test_handles_none_needs_review(self):
        assert _merge_partial_results([{"p": "a", "needs_review": None}])["needs_review"] == {}
