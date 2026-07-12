import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
import base64
from PIL import Image
from io import BytesIO
from ai.client import _image_to_base64, preprocess_image, _MAX_IMAGE_DIMENSION


def _test_img(path: Path | None = None, size=(1, 1), mode="RGB", fmt="JPEG") -> Path:
    img = Image.new(mode, size, color="red")
    p = path or (Path(__file__).parent / "_t.jpg")
    img.save(p, format=fmt)
    return p


def _cleanup(*paths):
    for p in paths:
        p.unlink(missing_ok=True)


class TestImageToBase64:
    def test_returns_string(self):
        p = _test_img()
        r = _image_to_base64(p)
        _cleanup(p)
        assert isinstance(r, str) and len(r) > 0

    def test_valid_base64(self):
        p = _test_img()
        r = _image_to_base64(p)
        _cleanup(p)
        assert len(base64.b64decode(r)) > 0

    def test_rgba_to_rgb(self):
        img = Image.new("RGBA", (1, 1), color="red")
        p = Path(__file__).parent / "_tr.png"
        img.save(p, format="PNG")
        r = _image_to_base64(p)
        _cleanup(p)
        assert isinstance(r, str)


class TestPreprocessImage:
    def test_returns_jpeg_bytes(self):
        p = _test_img()
        raw = preprocess_image(p)
        _cleanup(p)
        assert raw[:2] == b'\xff\xd8'  # JPEG magic bytes

    def test_max_dimension_respected(self):
        p = _test_img(size=(4000, 3000))
        raw = preprocess_image(p)
        _cleanup(p)
        img = Image.open(BytesIO(raw))
        assert max(img.size) <= _MAX_IMAGE_DIMENSION
        img.close()

    def test_aspect_ratio_preserved(self):
        p = _test_img(size=(4000, 2000))
        raw = preprocess_image(p)
        _cleanup(p)
        img = Image.open(BytesIO(raw))
        w, h = img.size
        assert abs(w / h - 2.0) < 0.01
        img.close()

    def test_small_image_not_upscaled(self):
        p = _test_img(size=(100, 50))
        raw = preprocess_image(p)
        _cleanup(p)
        img = Image.open(BytesIO(raw))
        assert img.size == (100, 50)
        img.close()

    def test_output_is_grayscale(self):
        p = _test_img(size=(200, 200))
        raw = preprocess_image(p)
        _cleanup(p)
        img = Image.open(BytesIO(raw))
        assert img.mode == "L"
        img.close()


class TestPayloadConfig:
    def test_keep_alive_and_temperature_present(self):
        from ai.client import AIClient, _OLLAMA_KEEP_ALIVE, _OLLAMA_TEMPERATURE, _OLLAMA_NUM_CTX
        assert _OLLAMA_KEEP_ALIVE == "5m"
        assert _OLLAMA_TEMPERATURE == 0.0
        assert _OLLAMA_NUM_CTX == 8192

    def test_client_has_two_models(self):
        from ai.client import AIClient
        client = AIClient()
        assert hasattr(client, "vlm_model")
        assert hasattr(client, "text_model")
        assert client.vlm_model == "deepseek-ocr"
        assert client.text_model == "llama3.1"


class TestVLMPrompt:
    def test_returns_string(self):
        from ai.prompts import build_vlm_prompt
        result = build_vlm_prompt(0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_page_number(self):
        from ai.prompts import build_vlm_prompt
        result = build_vlm_prompt(2)
        assert "3" in result

    def test_no_json_instruction(self):
        from ai.prompts import build_vlm_prompt
        result = build_vlm_prompt(0)
        assert "JSON" not in result.upper() or "BEZ" in result.upper()


class TestTextFormatPrompt:
    def test_injects_raw_text(self):
        from ai.prompts import build_text_format_prompt
        result = build_text_format_prompt(0, "Płeć: Kobieta, Wiek: 23")
        assert "Płeć: Kobieta, Wiek: 23" in result

    def test_returns_string(self):
        from ai.prompts import build_text_format_prompt
        result = build_text_format_prompt(0, "test")
        assert isinstance(result, str)
