import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from schemas import CSV_HEADER, _FIELD_TO_CSV, MedicalSurvey

class TestCSVHeaderIntegrity:
    def test_csv_header_has_68_columns(self): assert len(CSV_HEADER) == 68
    def test_first_header_is_sygnatura_czasowa(self): assert CSV_HEADER[0] == "Sygnatura czasowa"

class TestFieldToCSVIntegrity:
    def test_field_to_csv_has_68_entries(self): assert len(_FIELD_TO_CSV) == 68
    def test_first_entry_is_timestamp(self):
        assert _FIELD_TO_CSV[0] == ("timestamp", "Sygnatura czasowa")
    def test_field_names_match(self):
        assert [fn for fn in MedicalSurvey.field_names()] == [fn for fn, _ in _FIELD_TO_CSV[1:]]

class TestCSVRowMatchesHeaders:
    def test_row_length_matches(self, sample_survey):
        assert len(sample_survey.to_csv_row()) == len(CSV_HEADER)
    def test_mapping_covers_all_headers(self):
        csv_names = [name for _, name in _FIELD_TO_CSV]
        assert csv_names == CSV_HEADER

class TestHeadersUniqueness:
    def test_all_headers_unique(self): assert len(CSV_HEADER) == len(set(CSV_HEADER))
