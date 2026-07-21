import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import csv
import pytest
from fastapi.testclient import TestClient
from main import app
from worker import get_worker
from worker.state import SurveyState
from config import config


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    client.post("/api/auth/login", json={"password": ""})
    return client


@pytest.fixture
def worker_with_ready_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="ready",
                     result={"p1_plec": "Kobieta", "p2_wiek": 22}),
    ]
    worker.state.global_state.total = 1
    worker.state.global_state.processed = 1
    return worker


@pytest.fixture
def worker_with_processing_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="processing"),
    ]
    return worker


@pytest.fixture
def worker_with_queued_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="queued"),
    ]
    return worker


@pytest.fixture
def worker_with_error_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="error",
                     error_message="OCR failed"),
    ]
    return worker


@pytest.fixture
def worker_with_verified_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="verified"),
    ]
    return worker


SAMPLE_VALUES = {
    "p1_plec": "Kobieta",
    "p2_wiek": 23,
    "p3_miejsce": "Wieś",
    "p4_stan": "Panna/kawaler",
    "p5_forma": "Z rodziną",
    "p5_inne": "",
    "p6_stopien": "Studia I stopnia",
    "p7_uczelnia": "PANS",
    "p8_praca": "Nie (Jeśli zaznaczyłaś/eś tą odpowiedź, przejdź do pytania nr 12)",
    "p9_system": None,
    "p9_inne": "",
    "p10_oddzial": None,
    "p10_inne": "",
    "p11_staz": "",
    "p12_sen": "7-8 godzin",
    "p13_ekran": "Powyżej 3 godzin",
    "p14_kofeina": "Tak, 1-2 porcje dziennie",
    "mfis_1": "2", "mfis_2": "3", "mfis_3": "1", "mfis_4": "0",
    "mfis_5": "2", "mfis_6": "1", "mfis_7": "3", "mfis_8": "0",
    "mfis_9": "0", "mfis_10": "1", "mfis_11": "2", "mfis_12": "1",
    "mfis_13": "0", "mfis_14": "2", "mfis_15": "1", "mfis_16": "2",
    "mfis_17": "0", "mfis_18": "1", "mfis_19": "3", "mfis_20": "0",
    "mfis_21": "1",
    "choroba_anemia": "NIE",
    "choroba_tarczyca": "NIE",
    "tarczyca_jakie": "",
    "choroba_inne": "",
    "sen_1": "szybkie", "sen_2": "nie występuje",
    "sen_3": "o zamierzonej godzinie", "sen_4": "wystarczający",
    "sen_5": "satysfakcjonująca", "sen_6": "dobre",
    "sen_7": "niezaburzona", "sen_8": "nie zdarza się",
    "depr_1": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_2": "Przez niedługi czas (1-2 dni)",
    "depr_3": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_4": "Czasem lub przez umiarkowany okres (3-4 dni)",
    "depr_5": "Przez niedługi czas (1-2 dni)",
    "depr_6": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_7": "Przez niedługi czas (1-2 dni)",
    "depr_8": "Czasem lub przez umiarkowany okres (3-4 dni)",
    "depr_9": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_10": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_11": "Przez niedługi czas (1-2 dni)",
    "depr_12": "Czasem lub przez umiarkowany okres (3-4 dni)",
    "depr_13": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_14": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_15": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_16": "Czasem lub przez umiarkowany okres (3-4 dni)",
    "depr_17": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_18": "Przez niedługi czas (1-2 dni)",
    "depr_19": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_20": "Rzadko lub wcale (mniej niż 1 dzień)",
}


class TestSaveEndpointHappyPath:
    def test_save_ready_survey_returns_200(self, auth_client, worker_with_ready_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 200
        assert response.json()["status"] == "saved"

    def test_save_creates_csv_row(self, auth_client, worker_with_ready_survey, tmp_path):
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_output.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            auth_client.post("/api/surveys/0/save",
                              json={"values": SAMPLE_VALUES})
            assert csv_path.exists()
            content = csv_path.read_text(encoding="utf-8-sig")
            assert "Kobieta" in content
        finally:
            config.app["csv_results"] = orig

    def test_save_sets_verified_status(self, auth_client, worker_with_ready_survey):
        auth_client.post("/api/surveys/0/save",
                          json={"values": SAMPLE_VALUES})
        worker = get_worker()
        assert worker.state.get_survey_state(0).status == "verified"

    def test_save_clears_result_from_memory(self, auth_client, worker_with_ready_survey):
        worker = get_worker()
        assert worker.state.get_survey_state(0).result is not None
        auth_client.post("/api/surveys/0/save",
                          json={"values": SAMPLE_VALUES})
        assert worker.state.get_survey_state(0).result is None


class TestSaveEndpointValidation:
    def test_save_without_force_returns_422_on_errors(self, auth_client, worker_with_ready_survey):
        bad_values = SAMPLE_VALUES.copy()
        bad_values["p1_plec"] = "NieznanaWartosc"
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": bad_values})
        assert response.status_code == 422
        assert "errors" in response.json()["detail"]

    def test_save_force_with_validation_errors_returns_200(self, auth_client, worker_with_ready_survey):
        bad_values = SAMPLE_VALUES.copy()
        bad_values["p1_plec"] = "NieznanaWartosc"
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": bad_values, "force": True})
        assert response.status_code == 200
        assert response.json()["status"] == "saved"

    def test_save_force_writes_none_for_invalid_select(self, auth_client, worker_with_ready_survey, tmp_path):
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_force.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            bad_values = SAMPLE_VALUES.copy()
            bad_values["p1_plec"] = "NieznanaWartosc"
            auth_client.post("/api/surveys/0/save",
                              json={"values": bad_values, "force": True})
            content = csv_path.read_text(encoding="utf-8-sig")
            rows = list(csv.reader(content.strip().split("\n")))
            assert len(rows) == 2
        finally:
            config.app["csv_results"] = orig


class TestSaveEndpointEdgeCases:
    def test_save_nonexistent_survey_returns_404(self, auth_client, worker_with_ready_survey):
        response = auth_client.post("/api/surveys/999/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 404

    def test_save_processing_survey_returns_400(self, auth_client, worker_with_processing_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 400

    def test_save_queued_survey_returns_400(self, auth_client, worker_with_queued_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 400

    def test_save_error_survey_returns_400(self, auth_client, worker_with_error_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 400

    def test_save_already_verified_returns_400(self, auth_client, worker_with_verified_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 400


class TestSaveEndpointCSVFormat:
    def test_save_csv_has_bom_encoding(self, auth_client, worker_with_ready_survey, tmp_path):
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_bom.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            auth_client.post("/api/surveys/0/save",
                              json={"values": SAMPLE_VALUES})
            assert csv_path.read_bytes()[:3] == b"\xef\xbb\xbf"
        finally:
            config.app["csv_results"] = orig

    def test_save_csv_has_correct_column_count(self, auth_client, worker_with_ready_survey, tmp_path):
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_cols.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            auth_client.post("/api/surveys/0/save",
                              json={"values": SAMPLE_VALUES})
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                rows = list(reader)
                assert len(rows[0]) == 71
                assert len(rows[1]) == 71
        finally:
            config.app["csv_results"] = orig

    def test_save_csv_header_written_once(self, auth_client, worker_with_ready_survey, tmp_path):
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_once.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            worker = get_worker()
            worker.state.surveys.append(
                SurveyState(id=1, files=[Path("test2.jpg")], status="ready",
                             result={"p1_plec": "Mężczyzna"})
            )
            auth_client.post("/api/surveys/0/save",
                              json={"values": SAMPLE_VALUES})
            auth_client.post("/api/surveys/1/save",
                              json={"values": SAMPLE_VALUES})
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                rows = list(reader)
                assert rows[0][0] == "Sygnatura czasowa"
                assert rows[1][0] != "Sygnatura czasowa"
                assert rows[2][0] != "Sygnatura czasowa"
                assert len(rows) == 3
        finally:
            config.app["csv_results"] = orig