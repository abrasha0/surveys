import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from schemas import MedicalSurvey, SurveyResult, SurveyGroup, _extract_age, _normalize_value, _FIELD_TO_CSV, CSV_HEADER

class TestExtractAge:
    def test_int_input(self): assert _extract_age(25) == 25
    def test_string_with_number(self): assert _extract_age("23 lata") == 23
    def test_string_only_number(self): assert _extract_age("30") == 30
    def test_no_number_fallback(self): assert _extract_age("nie wiem") == 22

class TestNormalizeValue:
    def test_literal_exact_match(self): assert _normalize_value("plec", "Kobieta") == "Kobieta"
    def test_literal_case_insensitive(self): assert _normalize_value("plec", "kobieta") == "Kobieta"
    def test_literal_fallback_to_first(self):
        result = _normalize_value("plec", "Nieznane")
        assert result == "Kobieta"
    def test_objaw_dict_value(self): assert _normalize_value("objaw_mniej_uwazna", {"value": "Czasami"}) == "Czasami"
    def test_string_field_passthrough(self): assert _normalize_value("uczelnia", "PANS") == "PANS"

class TestMedicalSurveyFromAI:
    def test_from_ai_json_parses_correctly(self, ai_json_response):
        survey = MedicalSurvey.from_ai_json(ai_json_response)
        assert survey.plec == "Kobieta"
        assert survey.wiek == 23
        assert survey.needs_review["wiek"] is True
    def test_from_ai_json_sets_age_as_int(self, ai_json_response):
        survey = MedicalSurvey.from_ai_json(ai_json_response)
        assert isinstance(survey.wiek, int) and survey.wiek == 23

class TestMedicalSurveyToCSV:
    def test_to_csv_row_returns_68_elements(self, sample_survey):
        assert len(sample_survey.to_csv_row()) == 68
    def test_to_csv_row_matches_header_length(self, sample_survey):
        assert len(sample_survey.to_csv_row()) == len(CSV_HEADER)
    def test_to_csv_row_values_match(self, sample_survey):
        row = sample_survey.to_csv_row()
        assert row[1] == "Kobieta" and str(row[2]) == "23" and row[7] == "PANS"

class TestFieldNames:
    def test_field_names_count(self): assert len(MedicalSurvey.field_names()) == 67
    def test_field_names_exclude_timestamp(self):
        names = MedicalSurvey.field_names()
        assert "timestamp" not in names and "plec" in names

class TestSurveyResult:
    def test_survey_result_creation(self, sample_survey):
        r = SurveyResult(raw_response="{}", validated_data=sample_survey, confidence=0.95)
        assert r.confidence == 0.95 and r.validated_data.plec == "Kobieta"

class TestSurveyGroup:
    def test_survey_group_creation(self):
        g = SurveyGroup(id=0, files=[Path("a.jpg"), Path("b.jpg")])
        assert g.id == 0 and len(g.files) == 2 and g.result is None
    def test_survey_group_with_result(self, sample_survey):
        r = SurveyResult(raw_response="{}", validated_data=sample_survey, confidence=0.9)
        g = SurveyGroup(id=1, files=[Path("t.jpg")], result=r)
        assert g.result.confidence == 0.9
