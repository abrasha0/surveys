import csv, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pytest
from ingestion.file_grouping import group_files_by_survey
from domain.csv_export import save_survey_to_csv
from data_handler import save_cache, load_cache
from domain.csv_export import CSV_HEADER
from domain.schemas import MedicalSurvey


class FakeUploadedFile:
    def __init__(self, name, content=b"test"):
        self.name = name
        self._content = content
    def getbuffer(self):
        return self._content


class TestGroupFilesBySurvey:
    def test_groups_five_files(self):
        files = [FakeUploadedFile(f"p_{i}.jpg") for i in range(5)]
        groups, warnings = group_files_by_survey(files)
        assert len(groups) == 1 and len(groups[0]) == 5

    def test_groups_multiple_surveys(self):
        files = [FakeUploadedFile(f"p_{i}.jpg") for i in range(10)]
        groups, warnings = group_files_by_survey(files)
        assert len(groups) == 2

    def test_writes_files_to_disk(self):
        files = [FakeUploadedFile("t.jpg", b"content")]
        groups, warnings = group_files_by_survey(files)
        assert groups[0][0].read_bytes() == b"content"

    def test_sorts_files_alphabetically(self):
        files = [FakeUploadedFile("z.jpg"), FakeUploadedFile("a.jpg")]
        groups, warnings = group_files_by_survey(files)
        assert groups[0][0].name == "a.jpg"


class TestSaveSurveyToCSV:
    def test_creates_file_with_header(self, sample_survey, tmp_path):
        p = tmp_path / "t.csv"
        save_survey_to_csv(sample_survey, str(p))
        c = p.read_text(encoding="utf-8-sig")
        assert "Kobieta" in c

    def test_csv_has_bom(self, sample_survey, tmp_path):
        p = tmp_path / "t.csv"
        save_survey_to_csv(sample_survey, str(p))
        assert p.read_bytes()[:3] == b"\xef\xbb\xbf"


class TestCache:
    def test_save_and_load_cache_roundtrip(self, sample_survey, tmp_path):
        from config import config
        orig = config.app["cache_file"]
        config.app["cache_file"] = str(tmp_path / "c.json")
        r = {"raw_response": "{}", "validated_data": sample_survey.model_dump(), "confidence": 0.95}
        save_cache({0: r})
        loaded = load_cache()
        assert 0 in loaded and loaded[0]["confidence"] == 0.95
        config.app["cache_file"] = orig

    def test_load_cache_returns_empty_when_no_file(self):
        from config import config
        orig = config.app["cache_file"]
        config.app["cache_file"] = "noexist.json"
        assert load_cache() == {}
        config.app["cache_file"] = orig
