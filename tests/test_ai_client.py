import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from PIL import Image
from io import BytesIO
from ai.client import _image_to_base64


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
