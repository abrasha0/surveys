from dataclasses import dataclass
from typing import Any

@dataclass
class FieldSpec:
    name: str
    label: str
    page: int
    kind: str  # 'select', 'text', 'number'
    choices: list[str] | None = None
    min: int | None = None
    max: int | None = None
    default: Any = ""
    csv_header: str | None = None

    def get_csv_header(self):
        return self.csv_header or self.label


# ============================================================
# Strona 1 – Demografia + styl życia
# ============================================================
PAGE0_FIELDS = [
    FieldSpec("plec", "1. Płeć", 0, "select",
              ["Kobieta", "Mężczyzna", "Nie chcę podawać"],
              csv_header="Płeć"),
    FieldSpec("wiek", "2. Wiek", 0, "number", min=18, max=80, csv_header="Wiek"),
    FieldSpec("miejsce_zamieszkania", "3. Miejsce zamieszkania", 0, "select",
              ["Wieś", "Miasto do 50 tys. mieszkańców", "Miasto 50-100 tys. mieszkańców",
               "Miasto powyżej 100 tys. mieszkańców"],
              csv_header="Miejsce zamieszkania"),
    FieldSpec("stan_cywilny", "4. Stan cywilny", 0, "select",
              ["Panna/kawaler", "W związku nieformalnym", "Mężatka/żonaty",
               "Rozwiedziona/rozwiedziony", "Wdowa/wdowiec"],
              csv_header="Stan cywilny"),
    FieldSpec("forma_zamieszkania", "5. Forma zamieszkania", 0, "select",
              ["Z rodziną", "W akademiku", "W wynajmowanym mieszkaniu/pokoju",
               "Własne mieszkanie", "We własnym mieszkaniu z partnerem",
               "z partnerem", "Inne"],
              csv_header="Forma zamieszkania w trakcie studiów"),
    FieldSpec("stopien_studiow", "6. Stopień studiów", 0, "select",
              ["Studia I stopnia", "Studia II stopnia"],
              csv_header="Stopień studiów"),
    FieldSpec("uczelnia", "7. Uczelnia", 0, "text", csv_header="Na jakiej uczelni studiujesz?"),
    FieldSpec("praca_status", "8. Praca w trakcie studiów?", 0, "select",
              ["Nie", "Tak, w zawodzie medycznym", "Tak, poza zawodem"],
              csv_header="Czy pracujesz zawodowo w trakcie studiów?"),
    FieldSpec("praca_system", "9. System pracy", 0, "text",
              csv_header="Jeśli pracujesz w zawodzie, to w jakim systemie"),
    FieldSpec("oddzial", "10. Rodzaj oddziału", 0, "select",
              ["", "Przychodnia", "Zabiegowym", "Zachowawczym", "Pracownia", "Inne"],
              csv_header="Na jakim rodzaju oddziału pracujesz?"),
    FieldSpec("staz_pracy", "11. Staż pracy", 0, "text", csv_header="Jaki jest Twój staż pracy"),
    FieldSpec("sen_godziny", "12. Średnia liczba godzin snu", 0, "select",
              ["Poniżej 5 godzin", "5-6 godzin", "7-8 godzin", "Powyżej 8 godzin"],
              csv_header="Jaka jest Twoja średnia liczba godzin snu w ciągu doby?"),
    FieldSpec("ekran_godziny", "13. Godziny przed ekranem", 0, "select",
              ["1-3 godziny", "Powyżej 3 godzin"],
              csv_header="Ile godzin dziennie spędzasz przed ekranem"),
    FieldSpec("kofeina", "14. Spożycie kofeiny", 0, "select",
              ["Nie", "Tak, 1-2 porcje dziennie", "Tak, 3 lub więcej porcji dziennie"],
              csv_header="Czy pijesz napoje zawierające kofeinę (kawa, napoje energetyczne)?"),
]


# ============================================================
# Strona 2 – CES-D (3 opcje – zgodnie z papierową ankietą)
# ============================================================
_CESD_CHOICES = [
    "Rzadko lub wcale (mniej niż 1 dzień)",
    "Przez niedługi czas (1-2 dni)",
    "Czasem lub przez umiarkowany okres (3-4 dni)",
    "Przeważnie lub cały czas (5-7 dni)",
]

PAGE1_FIELDS = [
    FieldSpec("cesd_przeszkadzaly", "Przeszkadzały mi rzeczy…", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Przeszkadzały mi rzeczy, które zazwyczaj mi nie przeszkadzają]"),
    FieldSpec("cesd_brak_apetytu", "Nie miałem ochoty jeść…", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Nie miałem ochoty jeść; mój apetyt był słaby]"),
    FieldSpec("cesd_chandra", "Nie mogłem otrząsnąć się z chandry…", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem, że nie mogę otrząsnąć się z chandry, nawet z pomocą rodziny lub przyjaciół]"),
    FieldSpec("cesd_tak_samo_dobry", "Czułem, że jestem tak samo dobry…", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem, że jestem tak samo dobry jak inni ludzie]"),
    FieldSpec("cesd_ciezko_skoncentrowac", "Ciężko mi się skoncentrować…", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Było mi ciężko skoncentrować się na tym co robię]"),
    FieldSpec("cesd_przygnebiony", "Czułem się przygnębiony", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem się przygnębiony]"),
    FieldSpec("cesd_wysilek", "Cokolwiek robię, wymaga wysiłku", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem, że cokolwiek robię, wymaga wysiłku]"),
    FieldSpec("cesd_optymistycznie", "Optymistycznie patrzyłem w przyszłość", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Optymistycznie patrzyłem w przyszłość]"),
    FieldSpec("cesd_zycie_porazka", "Moje życie to porażka", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Miałem poczucie, że moje życie to porażka]"),
    FieldSpec("cesd_strach", "Czułem strach", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem strach]"),
    FieldSpec("cesd_sen_niespokojny", "Mój sen był niespokojny", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Mój sen był niespokojny]"),
    FieldSpec("cesd_szczesliwy", "Byłem szczęśliwy", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Byłem szczęśliwy]"),
    FieldSpec("cesd_mowil_mniej", "Mówiłem mniej niż zwykle", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Mówiłem mniej niż zwykle]"),
    FieldSpec("cesd_samotny", "Czułem się samotny", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem się samotny]"),
    FieldSpec("cesd_ludzie_nieprzyjazni", "Ludzie byli nieprzyjaźni", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Ludzie byli nastawieni nieprzyjaźnie]"),
    FieldSpec("cesd_radosci", "Czerpałem radość z życia", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czerpałem radość z życia]"),
    FieldSpec("cesd_placzu", "Miałem napady płaczu", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Miałem napady płaczu]"),
    FieldSpec("cesd_smutno", "Było mi smutno", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Było mi smutno]"),
    FieldSpec("cesd_ludzie_nie_lubia", "Ludzie mnie nie lubią", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem, że ludzie mnie nie lubią]"),
    FieldSpec("cesd_nic_nie_zabrac", "Nie mogłem się za nic zabrać", 1, "select", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Nie byłem w stanie się za nic zabrać]"),
]


# ============================================================
# Strona 3 – Ateńska skala bezsenności
# ============================================================
PAGE2_FIELDS = [
    FieldSpec("zasypianie", "Zasypianie", 2, "select",
              ["szybkie", "nieznacznie opóźnione", "opóźnione",
               "bardzo opóźnione lub bezsenność przez całą noc"],
              csv_header="Zasypianie po położeniu się do łóżka i zgaszeniu światła"),
    FieldSpec("budzenie_noc", "Budzenie się w nocy", 2, "select",
              ["nie występuje", "sporadycznie", "często",
               "bardzo często lub bezsenność przez całą noc"],
              csv_header="Budzenie się podczas nocy"),
    FieldSpec("budzenie_rano", "Wcześniejsze budzenie", 2, "select",
              ["o zamierzonej godzinie", "nieznacznie wcześniej", "znacznie wcześniej",
               "dużo wcześniej lub bezsenność przez całą noc"],
              csv_header="Budzenie się rano wcześniej niż planowano"),
    FieldSpec("czas_snu", "Całkowity czas snu", 2, "select",
              ["wystarczający", "nieznacznie niewystarczający", "wyraźnie niewystarczający",
               "całkowicie niewystarczający lub bezsenność przez całą noc"],
              csv_header="Całkowity czas snu"),
    FieldSpec("jakosc_snu", "Jakość snu", 2, "select",
              ["satysfakcjonująca", "nieznacznie niesatysfakcjonująca",
               "wyraźnie niesatysfakcjonująca", "całkowicie niesatysfakcjonująca"],
              csv_header="Jakość snu, niezależnie od czasu jego trwania"),
    FieldSpec("samopoczucie", "Samopoczucie nast. dnia", 2, "select",
              ["dobre", "nieznacznie gorsze", "wyraźnie gorsze"],
              csv_header="Samopoczucie następnego dnia"),
    FieldSpec("sprawnosc", "Sprawność nast. dnia", 2, "select",
              ["niezaburzona", "nieznacznie zaburzona", "wyraźnie zaburzona"],
              csv_header="Sprawność psychiczna i fizyczna następnego dnia"),
    FieldSpec("sennosc", "Senność w ciągu dnia", 2, "select",
              ["nie zdarza się", "nieznaczna", "wyraźna", "bardzo nasilona"],
              csv_header="Senność w ciągu dnia"),
]


# ============================================================
# Strona 4 – MFIS (1-15)
# ============================================================
_MFIS_CHOICES = ["Nigdy", "Rzadko", "Czasami", "Często", "Prawie zawsze"]

PAGE3_FIELDS = [
    FieldSpec("objaw_mniej_uwazna", "Czułam/em się mniej uważna/y", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Czułam/em się mniej uważna/y]"),
    FieldSpec("objaw_trudno_skupic", "Trudno było mi się skupić", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się skupić przez dłuższą chwilę]"),
    FieldSpec("objaw_trudno_myslec", "Trudno było mi myśleć logicznie", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi myśleć logicznie]"),
    FieldSpec("objaw_niezdarna", "Byłam/em niezdarna/y", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em niezdarna/y]"),
    FieldSpec("objaw_zapominalska", "Byłam/em zapominalska/ski", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em zapominalska/ski]"),
    FieldSpec("objaw_wyznaczac_tempo", "Musiałam/em wyznaczać tempo", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em sama/sam wyznaczać sobie indywidualne tempo mojej pracy i aktywności fizycznej (bo nie mogłam/em nadążyć)]"),
    FieldSpec("objaw_zmotywowac_fizycznie", "Trudno zmotywować się do aktywności fizycznej", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do czegoś co wymagało aktywności fizycznej]"),
    FieldSpec("objaw_zmotywowac_spotkania", "Trudno zmotywować się do wyjścia", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do aktywnego uczestnictwa w zajęciach poza domem (spotkania itp.)]"),
    FieldSpec("objaw_nie_zdolna_poza_domem", "Nie czułam/em się zdolna/y do niczego poza domem", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Nie czułam/em się zdolna/y do robienia czegokolwiek poza domem]"),
    FieldSpec("objaw_wysilek_fizyczny", "Problem z utrzymaniem wysiłku fizycznego", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z utrzymaniem wysiłku fizycznego przez dłuższy czas]"),
    FieldSpec("objaw_trudnosci_decyzyjne", "Trudności w podejmowaniu decyzji", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w podejmowaniu decyzji]"),
    FieldSpec("objaw_zmusic_do_myslenia", "Trudno zmusić się do myślenia", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmusić do zrobienia czegokolwiek co wymagało myślenia]"),
    FieldSpec("objaw_miesnie_z_waty", "Mięśnie jak z waty", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em poczucie, że moje mięśnie są jakby \"zrobione z waty\"]"),
    FieldSpec("objaw_dyskomfort_fizyczny", "Dyskomfort fizyczny", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Odczuwałam/em dyskomfort fizyczny]"),
    FieldSpec("objaw_ukonczenie_myslenie", "Problem z ukończeniem zadania (myślenie)", 3, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to myślenia]"),
]


# ============================================================
# Strona 5 – MFIS (16-21) + zdrowie
# ============================================================
PAGE4_FIELDS = [
    FieldSpec("objaw_uporzadkowanie_mysli", "Trudności w uporządkowaniu myśli", 4, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w uporządkowaniu myśli podczas pracy (w domu i poza domem)]"),
    FieldSpec("objaw_ukonczenie_wysilek", "Problem z ukończeniem zadania (wysiłek fiz.)", 4, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to wysiłku fizycznego]"),
    FieldSpec("objaw_myslenie_spowolnione", "Myślenie spowolnione", 4, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em wrażenie, że moje myślenie uległo spowolnieniu ]"),
    FieldSpec("objaw_problemy_koncentracja", "Problemy z koncentracją", 4, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problemy z koncentracją]"),
    FieldSpec("objaw_ograniczyc_aktywnosc", "Musiałam/em ograniczyć aktywność", 4, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em ograniczyć moją aktywność fizyczną]"),
    FieldSpec("objaw_czesciej_odpoczywac", "Musiałam/em odpoczywać częściej", 4, "select", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em odpoczywać częściej i przez dłuższy okres czasu]"),
    FieldSpec("anemia", "Czy stwierdzono anemię?", 4, "select", ["Tak", "Nie"],
              csv_header="Czy w ostatnim czasie stwierdzono u Ciebie anemię?"),
    FieldSpec("problemy_tarczyca", "Problemy z tarczycą?", 4, "select", ["Tak", "Nie"],
              csv_header="Czy w ostatnim czasie stwierdzono u Ciebie problemy z tarczycą?"),
    FieldSpec("jaka_tarczyca", "Jakie problemy z tarczycą?", 4, "text",
              csv_header="Jeśli odpowiedź na poprzednie pytanie brzmiało \"tak\", to jakie problemy stwierdzono:"),
    FieldSpec("inne_choroby", "Inne choroby", 4, "text",
              csv_header="Czy w ostatnim czasie stwierdzono u Ciebie inne choroby? Jeśli tak, to jakie:"),
]


# ============================================================
# Zbiór wszystkich pól
# ============================================================
ALL_FIELDS = (
    PAGE0_FIELDS +
    PAGE1_FIELDS +
    PAGE2_FIELDS +
    PAGE3_FIELDS +
    PAGE4_FIELDS
)

# Słownik do szybkiego dostępu po nazwie
FIELD_SPEC_BY_NAME = {f.name: f for f in ALL_FIELDS}

# Mapowanie strony -> lista pól (do użycia w promptach i UI)
PAGE_MAP = {
    0: PAGE0_FIELDS,
    1: PAGE1_FIELDS,
    2: PAGE2_FIELDS,
    3: PAGE3_FIELDS,
    4: PAGE4_FIELDS,
}