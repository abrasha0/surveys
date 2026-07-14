import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from domain.csv_export import CSV_HEADER


class TestCSVHeaderIntegrity:
    def test_csv_header_has_71_columns(self):
        assert len(CSV_HEADER) == 71

    def test_first_header_is_sygnatura_czasowa(self):
        assert CSV_HEADER[0] == "Sygnatura czasowa"


class TestCSVRowMatchesHeaders:
    def test_row_length_matches(self, sample_survey):
        assert len(sample_survey.to_csv_row()) == len(CSV_HEADER)


class TestHeadersUniqueness:
    def test_all_headers_unique(self):
        assert len(CSV_HEADER) == len(set(CSV_HEADER))
