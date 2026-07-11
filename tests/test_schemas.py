import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from domain.schemas import MedicalSurvey, SurveyGroup
from domain.csv_export import CSV_HEADER
from domain.field_specs import ALL_FIELDS


class TestMedicalSurveyFromAI:
    def test_from_ai_json_parses_correctly(self, ai_json_response):
        survey = MedicalSurvey.from_ai_json(ai_json_response)
        assert survey.plec == "Kobieta"
        assert survey.wiek == 23
        assert survey.needs_review["wiek"] is True

    def test_from_ai_json_sets_age_as_int(self, ai_json_response):
        survey = MedicalSurvey.from_ai_json(ai_json_response)
        assert isinstance(survey.wiek, int) and survey.wiek == 23

    def test_from_ai_json_normalizes_select_values(self, ai_json_response):
        ai_json_response["plec"] = "kobieta"
        survey = MedicalSurvey.from_ai_json(ai_json_response)
        assert survey.plec == "Kobieta"

    def test_from_ai_json_returns_none_for_unknown_select(self, ai_json_response):
        ai_json_response["plec"] = "Nieznane"
        survey = MedicalSurvey.from_ai_json(ai_json_response)
        assert survey.plec is None

    def test_from_ai_json_returns_none_for_unparseable_age(self, ai_json_response):
        ai_json_response["wiek"] = "nie wiem"
        survey = MedicalSurvey.from_ai_json(ai_json_response)
        assert survey.wiek is None


class TestMedicalSurveyToCSV:
    def test_to_csv_row_returns_68_elements(self, sample_survey):
        assert len(sample_survey.to_csv_row()) == 68

    def test_to_csv_row_matches_header_length(self, sample_survey):
        assert len(sample_survey.to_csv_row()) == len(CSV_HEADER)

    def test_to_csv_row_values_match(self, sample_survey):
        row = sample_survey.to_csv_row()
        assert row[1] == "Kobieta" and str(row[2]) == "23" and row[7] == "PANS"


class TestFieldCount:
    def test_all_fields_count(self):
        assert len(ALL_FIELDS) == 67


class TestSurveyGroup:
    def test_survey_group_creation(self):
        g = SurveyGroup(id=0, files=[Path("a.jpg"), Path("b.jpg")])
        assert g.id == 0 and len(g.files) == 2
