import re
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ─── Literal types ────────────────────────────────────────────────

Plec = Literal["Kobieta", "Mężczyzna"]
MiejsceZamieszkania = Literal[
    "Wieś",
    "Miasto do 50 tys. mieszkańców",
    "Miasto 50-100 tys. mieszkańców",
    "Miasto powyżej 100 tys. mieszkańców",
]
StanCywilny = Literal["Panna/kawaler", "W związku nieformalnym", "Mężatka/żonaty"]
FormaZamieszkania = Literal[
    "Z rodziną",
    "W wynajmowanym mieszkaniu/pokoju",
    "Własne mieszkanie",
    "We własnym mieszkaniu z partnerem",
    "z partnerem",
]
StopienStudiow = Literal["Studia I stopnia", "Studia II stopnia"]
PracaStatus = Literal["Nie", "Tak, w zawodzie medycznym", "Tak, poza zawodem"]
Oddzial = Literal["", "Przychodnia", "Zabiegowym", "Zachowawczym", "Pracownia"]
ZakresSnu = Literal["Poniżej 5 godzin", "5-6 godzin", "7-8 godzin", "Powyżej 8 godzin"]
ZakresEkranu = Literal["1-3 godziny", "Powyżej 3 godzin"]
Kofeina = Literal["Nie", "Tak, 1-2 porcje dziennie", "Tak, 3 lub więcej porcji dziennie"]
SkalaObjawow = Literal["Nigdy", "Rzadko", "Czasami", "Często", "Prawie zawsze"]
TakNie = Literal["Tak", "Nie"]
Zasypianie = Literal[
    "szybkie",
    "nieznacznie opóźnione",
    "opóźnione",
    "bardzo opóźnione lub bezsenność przez całą noc",
]
BudzenieNoc = Literal[
    "nie występuje",
    "sporadycznie",
    "często",
    "bardzo często lub bezsenność przez całą noc",
]
BudzenieRano = Literal[
    "o zamierzonej godzinie",
    "nieznacznie wcześniej",
    "znacznie wcześniej",
    "dużo wcześniej lub bezsenność przez całą noc",
]
CzasSnuJakosc = Literal[
    "wystarczający",
    "nieznacznie niewystarczający",
    "wyraźnie niewystarczający",
    "całkowicie niewystarczający lub bezsenność przez całą noc",
]
JakoscSnu = Literal[
    "satysfakcjonująca",
    "nieznacznie niesatysfakcjonująca",
    "wyraźnie niesatysfakcjonująca",
    "całkowicie niesatysfakcjonująca",
]
Samopoczucie = Literal["dobre", "nieznacznie gorsze", "wyraźnie gorsze"]
Sprawnosc = Literal["niezaburzona", "nieznacznie zaburzona", "wyraźnie zaburzona"]
Sennosc = Literal["nie zdarza się", "nieznaczna", "wyraźna", "bardzo nasilona"]
SkalaCESD = Literal[
    "Rzadko lub wcale (mniej niż 1 dzień)",
    "Przez niedługi czas (1-2 dni)",
    "Czasem lub przez umiarkowany okres (3-4 dni)",
    "Przeważnie lub cały czas (5-7 dni)",
]

# ─── CSV header (matches Google Forms export exactly) ─────────────

CSV_HEADER = [
    "Sygnatura czasowa",
    "Płeć",
    "Wiek",
    "Miejsce zamieszkania",
    "Stan cywilny",
    "Forma zamieszkania w trakcie studiów",
    "Stopień studiów",
    "Na jakiej uczelni studiujesz?",
    "Czy pracujesz zawodowo w trakcie studiów?",
    "Jeśli pracujesz w zawodzie, to w jakim systemie",
    "Na jakim rodzaju oddziału pracujesz?",
    "Jaki jest Twój staż pracy",
    "Jaka jest Twoja średnia liczba godzin snu w ciągu doby?",
    "Ile godzin dziennie spędzasz przed ekranem",
    "Czy pijesz napoje zawierające kofeinę (kawa, napoje energetyczne)?",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Czułam/em się mniej uważna/y]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się skupić przez dłuższą chwilę]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi myśleć logicznie]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em niezdarna/y]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em zapominalska/ski]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em sama/sam wyznaczać sobie indywidualne tempo mojej pracy i aktywności fizycznej (bo nie mogłam/em nadążyć)]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do czegoś co wymagało aktywności fizycznej]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do aktywnego uczestnictwa w zajęciach poza domem (spotkania itp.)]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Nie czułam/em się zdolna/y do robienia czegokolwiek poza domem]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z utrzymaniem wysiłku fizycznego przez dłuższy czas]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w podejmowaniu decyzji]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmusić do zrobienia czegokolwiek co wymagało myślenia]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em poczucie, że moje mięśnie są jakby \"zrobione z waty\"]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Odczuwałam/em dyskomfort fizyczny]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to myślenia]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w uporządkowaniu myśli podczas pracy (w domu i poza domem)]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to wysiłku fizycznego]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em wrażenie, że moje myślenie uległo spowolnieniu ]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problemy z koncentracją]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em ograniczyć moją aktywność fizyczną]",
    "Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em odpoczywać częściej i przez dłuższy okres czasu]",
    "Czy w ostatnim czasie stwierdzono u Ciebie anemię?",
    "Czy w ostatnim czasie stwierdzono u Ciebie problemy z tarczycą?",
    "Jeśli odpowiedź na poprzednie pytanie brzmiało \"tak\", to jakie problemy stwierdzono:",
    "Czy w ostatnim czasie stwierdzono u Ciebie inne choroby? Jeśli tak, to jakie:",
    "Zasypianie po położeniu się do łóżka i zgaszeniu światła",
    "Budzenie się podczas nocy",
    "Budzenie się rano wcześniej niż planowano",
    "Całkowity czas snu",
    "Jakość snu, niezależnie od czasu jego trwania",
    "Samopoczucie następnego dnia",
    "Sprawność psychiczna i fizyczna następnego dnia",
    "Senność w ciągu dnia",
    "Podczas minionego tygodnia   [Przeszkadzały mi rzeczy, które zazwyczaj mi nie przeszkadzają]",
    "Podczas minionego tygodnia   [Nie miałem ochoty jeść; mój apetyt był słaby]",
    "Podczas minionego tygodnia   [Czułem, że nie mogę otrząsnąć się z chandry, nawet z pomocą rodziny lub przyjaciół]",
    "Podczas minionego tygodnia   [Czułem, że jestem tak samo dobry jak inni ludzie]",
    "Podczas minionego tygodnia   [Było mi ciężko skoncentrować się na tym co robię]",
    "Podczas minionego tygodnia   [Czułem się przygnębiony]",
    "Podczas minionego tygodnia   [Czułem, że cokolwiek robię, wymaga wysiłku]",
    "Podczas minionego tygodnia   [Optymistycznie patrzyłem w przyszłość]",
    "Podczas minionego tygodnia   [Miałem poczucie, że moje życie to porażka]",
    "Podczas minionego tygodnia   [Czułem strach]",
    "Podczas minionego tygodnia   [Mój sen był niespokojny]",
    "Podczas minionego tygodnia   [Byłem szczęśliwy]",
    "Podczas minionego tygodnia   [Mówiłem mniej niż zwykle]",
    "Podczas minionego tygodnia   [Czułem się samotny]",
    "Podczas minionego tygodnia   [Ludzie byli nastawieni nieprzyjaźnie]",
    "Podczas minionego tygodnia   [Czerpałem radość z życia]",
    "Podczas minionego tygodnia   [Miałem napady płaczu]",
    "Podczas minionego tygodnia   [Było mi smutno]",
    "Podczas minionego tygodnia   [Czułem, że ludzie mnie nie lubią]",
    "Podczas minionego tygodnia   [Nie byłem w stanie się za nic zabrać]",
]

# ─── Field name → CSV header mapping for to_csv_row ───────────────

_FIELD_TO_CSV = [
    ("timestamp", "Sygnatura czasowa"),
    ("plec", "Płeć"),
    ("wiek", "Wiek"),
    ("miejsce_zamieszkania", "Miejsce zamieszkania"),
    ("stan_cywilny", "Stan cywilny"),
    ("forma_zamieszkania", "Forma zamieszkania w trakcie studiów"),
    ("stopien_studiow", "Stopień studiów"),
    ("uczelnia", "Na jakiej uczelni studiujesz?"),
    ("praca_status", "Czy pracujesz zawodowo w trakcie studiów?"),
    ("praca_system", "Jeśli pracujesz w zawodzie, to w jakim systemie"),
    ("oddzial", "Na jakim rodzaju oddziału pracujesz?"),
    ("staz_pracy", "Jaki jest Twój staż pracy"),
    ("sen_godziny", "Jaka jest Twoja średnia liczba godzin snu w ciągu doby?"),
    ("ekran_godziny", "Ile godzin dziennie spędzasz przed ekranem"),
    ("kofeina", "Czy pijesz napoje zawierające kofeinę (kawa, napoje energetyczne)?"),
    ("objaw_mniej_uwazna", CSV_HEADER[15]),
    ("objaw_trudno_skupic", CSV_HEADER[16]),
    ("objaw_trudno_myslec", CSV_HEADER[17]),
    ("objaw_niezdarna", CSV_HEADER[18]),
    ("objaw_zapominalska", CSV_HEADER[19]),
    ("objaw_wyznaczac_tempo", CSV_HEADER[20]),
    ("objaw_zmotywowac_fizycznie", CSV_HEADER[21]),
    ("objaw_zmotywowac_spotkania", CSV_HEADER[22]),
    ("objaw_nie_zdolna_poza_domem", CSV_HEADER[23]),
    ("objaw_wysilek_fizyczny", CSV_HEADER[24]),
    ("objaw_trudnosci_decyzyjne", CSV_HEADER[25]),
    ("objaw_zmusic_do_myslenia", CSV_HEADER[26]),
    ("objaw_miesnie_z_waty", CSV_HEADER[27]),
    ("objaw_dyskomfort_fizyczny", CSV_HEADER[28]),
    ("objaw_ukonczenie_myslenie", CSV_HEADER[29]),
    ("objaw_uporzadkowanie_mysli", CSV_HEADER[30]),
    ("objaw_ukonczenie_wysilek", CSV_HEADER[31]),
    ("objaw_myslenie_spowolnione", CSV_HEADER[32]),
    ("objaw_problemy_koncentracja", CSV_HEADER[33]),
    ("objaw_ograniczyc_aktywnosc", CSV_HEADER[34]),
    ("objaw_czesciej_odpoczywac", CSV_HEADER[35]),
    ("anemia", CSV_HEADER[36]),
    ("problemy_tarczyca", CSV_HEADER[37]),
    ("jaka_tarczyca", CSV_HEADER[38]),
    ("inne_choroby", CSV_HEADER[39]),
    ("zasypianie", CSV_HEADER[40]),
    ("budzenie_noc", CSV_HEADER[41]),
    ("budzenie_rano", CSV_HEADER[42]),
    ("czas_snu", CSV_HEADER[43]),
    ("jakosc_snu", CSV_HEADER[44]),
    ("samopoczucie", CSV_HEADER[45]),
    ("sprawnosc", CSV_HEADER[46]),
    ("sennosc", CSV_HEADER[47]),
    ("cesd_przeszkadzaly", CSV_HEADER[48]),
    ("cesd_brak_apetytu", CSV_HEADER[49]),
    ("cesd_chandra", CSV_HEADER[50]),
    ("cesd_tak_samo_dobry", CSV_HEADER[51]),
    ("cesd_ciezko_skoncentrowac", CSV_HEADER[52]),
    ("cesd_przygnebiony", CSV_HEADER[53]),
    ("cesd_wysilek", CSV_HEADER[54]),
    ("cesd_optymistycznie", CSV_HEADER[55]),
    ("cesd_zycie_porazka", CSV_HEADER[56]),
    ("cesd_strach", CSV_HEADER[57]),
    ("cesd_sen_niespokojny", CSV_HEADER[58]),
    ("cesd_szczesliwy", CSV_HEADER[59]),
    ("cesd_mowil_mniej", CSV_HEADER[60]),
    ("cesd_samotny", CSV_HEADER[61]),
    ("cesd_ludzie_nieprzyjazni", CSV_HEADER[62]),
    ("cesd_radosci", CSV_HEADER[63]),
    ("cesd_placzu", CSV_HEADER[64]),
    ("cesd_smutno", CSV_HEADER[65]),
    ("cesd_ludzie_nie_lubia", CSV_HEADER[66]),
    ("cesd_nic_nie_zabrac", CSV_HEADER[67]),
]

# ─── Helper: extract first number from a string ───────────────────

def _extract_age(raw: str | int) -> int:
    if isinstance(raw, int):
        return raw
    m = re.search(r"\d+", str(raw))
    return int(m.group()) if m else 22


# ─── MedicalSurvey ────────────────────────────────────────────────

class MedicalSurvey(BaseModel):
    # A. Demografia
    plec: Plec
    wiek: int = Field(ge=18, le=80)
    miejsce_zamieszkania: MiejsceZamieszkania
    stan_cywilny: StanCywilny
    forma_zamieszkania: FormaZamieszkania
    stopien_studiow: StopienStudiow
    uczelnia: str

    # B. Aktywność zawodowa
    praca_status: PracaStatus
    praca_system: str = ""
    oddzial: Oddzial = ""
    staz_pracy: str = ""

    # C. Styl życia
    sen_godziny: ZakresSnu
    ekran_godziny: ZakresEkranu
    kofeina: Kofeina

    # D. Objawy (21)
    objaw_mniej_uwazna: SkalaObjawow
    objaw_trudno_skupic: SkalaObjawow
    objaw_trudno_myslec: SkalaObjawow
    objaw_niezdarna: SkalaObjawow
    objaw_zapominalska: SkalaObjawow
    objaw_wyznaczac_tempo: SkalaObjawow
    objaw_zmotywowac_fizycznie: SkalaObjawow
    objaw_zmotywowac_spotkania: SkalaObjawow
    objaw_nie_zdolna_poza_domem: SkalaObjawow
    objaw_wysilek_fizyczny: SkalaObjawow
    objaw_trudnosci_decyzyjne: SkalaObjawow
    objaw_zmusic_do_myslenia: SkalaObjawow
    objaw_miesnie_z_waty: SkalaObjawow
    objaw_dyskomfort_fizyczny: SkalaObjawow
    objaw_ukonczenie_myslenie: SkalaObjawow
    objaw_uporzadkowanie_mysli: SkalaObjawow
    objaw_ukonczenie_wysilek: SkalaObjawow
    objaw_myslenie_spowolnione: SkalaObjawow
    objaw_problemy_koncentracja: SkalaObjawow
    objaw_ograniczyc_aktywnosc: SkalaObjawow
    objaw_czesciej_odpoczywac: SkalaObjawow

    # E. Stan zdrowia
    anemia: TakNie
    problemy_tarczyca: TakNie
    jaka_tarczyca: str = ""
    inne_choroby: str = ""

    # F. Jakość snu (PSQI-like)
    zasypianie: Zasypianie
    budzenie_noc: BudzenieNoc
    budzenie_rano: BudzenieRano
    czas_snu: CzasSnuJakosc
    jakosc_snu: JakoscSnu
    samopoczucie: Samopoczucie
    sprawnosc: Sprawnosc
    sennosc: Sennosc

    # G. CES-D (20)
    cesd_przeszkadzaly: SkalaCESD
    cesd_brak_apetytu: SkalaCESD
    cesd_chandra: SkalaCESD
    cesd_tak_samo_dobry: SkalaCESD
    cesd_ciezko_skoncentrowac: SkalaCESD
    cesd_przygnebiony: SkalaCESD
    cesd_wysilek: SkalaCESD
    cesd_optymistycznie: SkalaCESD
    cesd_zycie_porazka: SkalaCESD
    cesd_strach: SkalaCESD
    cesd_sen_niespokojny: SkalaCESD
    cesd_szczesliwy: SkalaCESD
    cesd_mowil_mniej: SkalaCESD
    cesd_samotny: SkalaCESD
    cesd_ludzie_nieprzyjazni: SkalaCESD
    cesd_radosci: SkalaCESD
    cesd_placzu: SkalaCESD
    cesd_smutno: SkalaCESD
    cesd_ludzie_nie_lubia: SkalaCESD
    cesd_nic_nie_zabrac: SkalaCESD

    # H. Metadane AI
    needs_review: dict[str, bool] = {}

    def to_csv_row(self) -> list:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [ts]
        for field_name, _ in _FIELD_TO_CSV[1:]:
            val = getattr(self, field_name, "")
            row.append(str(val) if val is not None else "")
        return row

    @classmethod
    def field_names(cls) -> list[str]:
        return [fn for fn, _ in _FIELD_TO_CSV[1:]]

    @classmethod
    def from_ai_json(cls, data: dict) -> "MedicalSurvey":
        kwargs = {}
        for field_name, _ in _FIELD_TO_CSV[1:]:
            raw = data.get(field_name, _default_for(field_name))
            if field_name == "wiek":
                raw = _extract_age(raw)
            kwargs[field_name] = _normalize_value(field_name, raw)
        return cls(**kwargs)


def _default_for(field_name: str):
    defaults = {
        "praca_system": "",
        "oddzial": "",
        "staz_pracy": "",
        "jaka_tarczyca": "",
        "inne_choroby": "",
    }
    return defaults.get(field_name, "")

_LITERAL_CHOICES: dict[str, list[str]] = {
    "plec": ["Kobieta", "Mężczyzna"],
    "miejsce_zamieszkania": ["Wieś", "Miasto do 50 tys. mieszkańców", "Miasto 50-100 tys. mieszkańców", "Miasto powyżej 100 tys. mieszkańców"],
    "stan_cywilny": ["Panna/kawaler", "W związku nieformalnym", "Mężatka/żonaty"],
    "forma_zamieszkania": ["Z rodziną", "W wynajmowanym mieszkaniu/pokoju", "Własne mieszkanie", "We własnym mieszkaniu z partnerem", "z partnerem"],
    "stopien_studiow": ["Studia I stopnia", "Studia II stopnia"],
    "praca_status": ["Nie", "Tak, w zawodzie medycznym", "Tak, poza zawodem"],
    "oddzial": ["", "Przychodnia", "Zabiegowym", "Zachowawczym", "Pracownia"],
    "sen_godziny": ["Poniżej 5 godzin", "5-6 godzin", "7-8 godzin", "Powyżej 8 godzin"],
    "ekran_godziny": ["1-3 godziny", "Powyżej 3 godzin"],
    "kofeina": ["Nie", "Tak, 1-2 porcje dziennie", "Tak, 3 lub więcej porcji dziennie"],
    "anemia": ["Tak", "Nie"],
    "problemy_tarczyca": ["Tak", "Nie"],
    "zasypianie": ["szybkie", "nieznacznie opóźnione", "opóźnione", "bardzo opóźnione lub bezsenność przez całą noc"],
    "budzenie_noc": ["nie występuje", "sporadycznie", "często", "bardzo często lub bezsenność przez całą noc"],
    "budzenie_rano": ["o zamierzonej godzinie", "nieznacznie wcześniej", "znacznie wcześniej", "dużo wcześniej lub bezsenność przez całą noc"],
    "czas_snu": ["wystarczający", "nieznacznie niewystarczający", "wyraźnie niewystarczający", "całkowicie niewystarczający lub bezsenność przez całą noc"],
    "jakosc_snu": ["satysfakcjonująca", "nieznacznie niesatysfakcjonująca", "wyraźnie niesatysfakcjonująca", "całkowicie niesatysfakcjonująca"],
    "samopoczucie": ["dobre", "nieznacznie gorsze", "wyraźnie gorsze"],
    "sprawnosc": ["niezaburzona", "nieznacznie zaburzona", "wyraźnie zaburzona"],
    "sennosc": ["nie zdarza się", "nieznaczna", "wyraźna", "bardzo nasilona"],
}

_OBJAWY_FIELDS_LIST = [
    "objaw_mniej_uwazna", "objaw_trudno_skupic", "objaw_trudno_myslec",
    "objaw_niezdarna", "objaw_zapominalska", "objaw_wyznaczac_tempo",
    "objaw_zmotywowac_fizycznie", "objaw_zmotywowac_spotkania",
    "objaw_nie_zdolna_poza_domem", "objaw_wysilek_fizyczny",
    "objaw_trudnosci_decyzyjne", "objaw_zmusic_do_myslenia",
    "objaw_miesnie_z_waty", "objaw_dyskomfort_fizyczny",
    "objaw_ukonczenie_myslenie", "objaw_uporzadkowanie_mysli",
    "objaw_ukonczenie_wysilek", "objaw_myslenie_spowolnione",
    "objaw_problemy_koncentracja", "objaw_ograniczyc_aktywnosc",
    "objaw_czesciej_odpoczywac",
]

_CESD_FIELDS_LIST = [
    "cesd_przeszkadzaly", "cesd_brak_apetytu", "cesd_chandra",
    "cesd_tak_samo_dobry", "cesd_ciezko_skoncentrowac", "cesd_przygnebiony",
    "cesd_wysilek", "cesd_optymistycznie", "cesd_zycie_porazka",
    "cesd_strach", "cesd_sen_niespokojny", "cesd_szczesliwy",
    "cesd_mowil_mniej", "cesd_samotny", "cesd_ludzie_nieprzyjazni",
    "cesd_radosci", "cesd_placzu", "cesd_smutno",
    "cesd_ludzie_nie_lubia", "cesd_nic_nie_zabrac",
]


def _normalize_value(field_name: str, raw: object) -> object:
    choices = _LITERAL_CHOICES.get(field_name)
    if choices is not None:
        if isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, str) and v in choices:
                    return v
            for v in raw.values():
                if isinstance(v, str):
                    for c in choices:
                        if v.lower().strip() == c.lower().strip():
                            return c
            return choices[0]
        if isinstance(raw, str):
            if raw in choices:
                return raw
            for c in choices:
                if raw.lower().strip() == c.lower().strip():
                    return c
            return choices[0]
        return choices[0]

    if field_name in _OBJAWY_FIELDS_LIST:
        choices = ["Nigdy", "Rzadko", "Czasami", "Często", "Prawie zawsze"]
        if isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, str) and v in choices:
                    return v
            return "Nigdy"
        if isinstance(raw, str):
            if raw in choices:
                return raw
            for c in choices:
                if raw.lower().strip().startswith(c.rstrip("ęóź").lower()[:3]):
                    return c
            return "Nigdy"
        return "Nigdy"

    if field_name in _CESD_FIELDS_LIST:
        choices = [
            "Rzadko lub wcale (mniej niż 1 dzień)",
            "Przez niedługi czas (1-2 dni)",
            "Czasem lub przez umiarkowany okres (3-4 dni)",
            "Przeważnie lub cały czas (5-7 dni)",
        ]
        if isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, str) and v in choices:
                    return v
            return choices[0]
        if isinstance(raw, str):
            if raw in choices:
                return raw
            return choices[0]
        return choices[0]

    if isinstance(raw, dict):
        return str(raw)
    return raw


# ─── SurveyResult ─────────────────────────────────────────────────

class SurveyResult(BaseModel):
    raw_response: str
    validated_data: MedicalSurvey
    confidence: float


# ─── SurveyGroup ──────────────────────────────────────────────────

class SurveyGroup(BaseModel):
    id: int
    files: list[Path]
    result: Optional[SurveyResult] = None
