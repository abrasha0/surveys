from dataclasses import dataclass


@dataclass
class FieldSpec:
    name: str
    label: str
    page: int
    kind: str  # 'radio', 'text', 'number'
    choices: list[str] | None = None
    min: int | None = None
    max: int | None = None
    conditional: str | None = None
    csv_header: str | None = None

    def get_csv_header(self):
        return self.csv_header or self.label


# ============================================================
# Strona 1 – Demografia + styl życia
# ============================================================
PAGE0_FIELDS = [
    FieldSpec("p1_plec", "1. Płeć", 0, "radio",
              ["Kobieta", "Mężczyzna", "Nie chcę podawać"],
              csv_header="Płeć"),
    FieldSpec("p2_wiek", "2. Wiek", 0, "number", min=18, max=80, csv_header="Wiek"),
    FieldSpec("p3_miejsce", "3. Miejsce zamieszkania", 0, "radio",
              ["Wieś", "Miasto do 50 tys. mieszkańców", "Miasto 50-100 tys. mieszkańców",
               "Miasto powyżej 100 tys. mieszkańców"],
              csv_header="Miejsce zamieszkania"),
    FieldSpec("p4_stan", "4. Stan cywilny", 0, "radio",
              ["Panna/kawaler", "W związku nieformalnym", "Mężatka/żonaty",
               "Rozwiedziona/rozwiedziony", "Wdowa/wdowiec"],
              csv_header="Stan cywilny"),
    FieldSpec("p5_forma", "5. Forma zamieszkania", 0, "radio",
              ["Z rodziną", "W akademiku", "W wynajmowanym mieszkaniu/pokoju", "Inne"],
              csv_header="Forma zamieszkania w trakcie studiów"),
    FieldSpec("p5_inne", "5a. Inne (zamieszkanie)", 0, "text",
              conditional="p5_forma=Inne",
              csv_header="Inne (forma zamieszkania)"),
    FieldSpec("p6_stopien", "6. Stopień studiów", 0, "radio",
              ["Studia I stopnia", "Studia II stopnia"],
              csv_header="Stopień studiów"),
    FieldSpec("p7_uczelnia", "7. Uczelnia", 0, "text", csv_header="Na jakiej uczelni studiujesz?"),
    FieldSpec("p8_praca", "8. Praca w trakcie studiów?", 0, "radio",
              ["Tak, w zawodzie medycznym", "Tak, poza zawodem",
               "Nie (Jeśli zaznaczyłaś/eś tą odpowiedź, przejdź do pytania nr 12)"],
              csv_header="Czy pracujesz zawodowo w trakcie studiów?"),
    FieldSpec("p9_system", "9. System pracy", 0, "radio",
              ["Zmianowym, 12-godzinnym", "Jednozmianowym, 8-godzinnym", "Innym"],
              csv_header="Jeśli pracujesz w zawodzie, to w jakim systemie"),
    FieldSpec("p9_inne", "9a. Inne (system pracy)", 0, "text",
              conditional="p9_system=Innym",
              csv_header="Inne (system pracy)"),
    FieldSpec("p10_oddzial", "10. Rodzaj oddziału", 0, "radio",
              ["Zachowawczym", "Zabiegowym", "Inne"],
              csv_header="Na jakim rodzaju oddziału pracujesz?"),
    FieldSpec("p10_inne", "10a. Inne (oddział)", 0, "text",
              conditional="p10_oddzial=Inne",
              csv_header="Inne (oddział)"),
    FieldSpec("p11_staz", "11. Staż pracy", 0, "text", csv_header="Jaki jest Twój staż pracy"),
    FieldSpec("p12_sen", "12. Średnia liczba godzin snu", 0, "radio",
              ["poniżej 5 godzin", "5-6 godzin", "7-8 godzin", "Powyżej 8 godzin"],
              csv_header="Jaka jest Twoja średnia liczba godzin snu w ciągu doby?"),
    FieldSpec("p13_ekran", "13. Godziny przed ekranem", 0, "radio",
              ["Mniej niż 1 godzinę", "1-3 godziny", "Powyżej 3 godzin"],
              csv_header="Ile godzin dziennie spędzasz przed ekranem"),
    FieldSpec("p14_kofeina", "14. Spożycie kofeiny", 0, "radio",
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
    FieldSpec("depr_1", "Przeszkadzały mi rzeczy…", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Przeszkadzały mi rzeczy, które zazwyczaj mi nie przeszkadzają]"),
    FieldSpec("depr_2", "Nie miałem ochoty jeść…", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Nie miałem ochoty jeść; mój apetyt był słaby]"),
    FieldSpec("depr_3", "Nie mogłem otrząsnąć się z chandry…", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem, że nie mogę otrząsnąć się z chandry, nawet z pomocą rodziny lub przyjaciół]"),
    FieldSpec("depr_4", "Czułem, że jestem tak samo dobry…", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem, że jestem tak samo dobry jak inni ludzie]"),
    FieldSpec("depr_5", "Ciężko mi się skoncentrować…", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Było mi ciężko skoncentrować się na tym co robię]"),
    FieldSpec("depr_6", "Czułem się przygnębiony", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem się przygnębiony]"),
    FieldSpec("depr_7", "Cokolwiek robię, wymaga wysiłku", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem, że cokolwiek robię, wymaga wysiłku]"),
    FieldSpec("depr_8", "Optymistycznie patrzyłem w przyszłość", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Optymistycznie patrzyłem w przyszłość]"),
    FieldSpec("depr_9", "Moje życie to porażka", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Miałem poczucie, że moje życie to porażka]"),
    FieldSpec("depr_10", "Czułem strach", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem strach]"),
    FieldSpec("depr_11", "Mój sen był niespokojny", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Mój sen był niespokojny]"),
    FieldSpec("depr_12", "Byłem szczęśliwy", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Byłem szczęśliwy]"),
    FieldSpec("depr_13", "Mówiłem mniej niż zwykle", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Mówiłem mniej niż zwykle]"),
    FieldSpec("depr_14", "Czułem się samotny", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem się samotny]"),
    FieldSpec("depr_15", "Ludzie byli nieprzyjaźni", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Ludzie byli nastawieni nieprzyjaźnie]"),
    FieldSpec("depr_16", "Czerpałem radość z życia", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czerpałem radość z życia]"),
    FieldSpec("depr_17", "Miałem napady płaczu", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Miałem napady płaczu]"),
    FieldSpec("depr_18", "Było mi smutno", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Było mi smutno]"),
    FieldSpec("depr_19", "Ludzie mnie nie lubią", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Czułem, że ludzie mnie nie lubią]"),
    FieldSpec("depr_20", "Nie mogłem się za nic zabrać", 4, "radio", _CESD_CHOICES,
              csv_header="Podczas minionego tygodnia   [Nie byłem w stanie się za nic zabrać]"),
]


# ============================================================
# Strona 3 – Ateńska skala bezsenności
# ============================================================
PAGE2_FIELDS = [
    FieldSpec("sen_1", "Zasypianie", 1, "radio",
              ["szybkie", "nieznacznie opóźnione", "opóźnione",
               "bardzo opóźnione lub bezsenność przez całą noc"],
              csv_header="Zasypianie po położeniu się do łóżka i zgaszeniu światła"),
    FieldSpec("sen_2", "Budzenie się w nocy", 1, "radio",
              ["nie występuje", "sporadycznie", "często",
               "bardzo często lub bezsenność przez całą noc"],
              csv_header="Budzenie się podczas nocy"),
    FieldSpec("sen_3", "Wcześniejsze budzenie", 1, "radio",
              ["o zamierzonej godzinie", "nieznacznie wcześniej", "znacznie wcześniej",
               "dużo wcześniej lub bezsenność przez całą noc"],
              csv_header="Budzenie się rano wcześniej niż planowano"),
    FieldSpec("sen_4", "Całkowity czas snu", 1, "radio",
              ["wystarczający", "nieznacznie niewystarczający", "wyraźnie niewystarczający",
               "całkowicie niewystarczający lub bezsenność przez całą noc"],
              csv_header="Całkowity czas snu"),
    FieldSpec("sen_5", "Jakość snu", 1, "radio",
              ["satysfakcjonująca", "nieznacznie niesatysfakcjonująca",
               "wyraźnie niesatysfakcjonująca", "całkowicie niesatysfakcjonująca"],
              csv_header="Jakość snu, niezależnie od czasu jego trwania"),
    FieldSpec("sen_6", "Samopoczucie nast. dnia", 1, "radio",
              ["dobre", "nieznacznie gorsze", "wyraźnie gorsze", "wybitnie gorsze"],
              csv_header="Samopoczucie następnego dnia"),
    FieldSpec("sen_7", "Sprawność nast. dnia", 1, "radio",
              ["niezaburzona", "nieznacznie zaburzona", "wyraźnie zaburzona", "wybitnie zaburzona"],
              csv_header="Sprawność psychiczna i fizyczna następnego dnia"),
    FieldSpec("sen_8", "Senność w ciągu dnia", 1, "radio",
              ["nie zdarza się", "nieznaczna", "wyraźna", "bardzo nasilona"],
              csv_header="Senność w ciągu dnia"),
]


# ============================================================
# Strona 4 – MFIS (1-15)
# ============================================================
_MFIS_CHOICES = ["0", "1", "2", "3", "4"]

PAGE3_FIELDS = [
    FieldSpec("mfis_1", "Czułam/em się mniej uważna/y", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Czułam/em się mniej uważna/y]"),
    FieldSpec("mfis_2", "Trudno było mi się skupić", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się skupić przez dłuższą chwilę]"),
    FieldSpec("mfis_3", "Trudno było mi myśleć logicznie", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi myśleć logicznie]"),
    FieldSpec("mfis_4", "Byłam/em niezdarna/y", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em niezdarna/y]"),
    FieldSpec("mfis_5", "Byłam/em zapominalska/ski", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em zapominalska/ski]"),
    FieldSpec("mfis_6", "Musiałam/em wyznaczać tempo", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em sama/sam wyznaczać sobie indywidualne tempo mojej pracy i aktywności fizycznej (bo nie mogłam/em nadążyć)]"),
    FieldSpec("mfis_7", "Trudno zmotywować się do aktywności fizycznej", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do czegoś co wymagało aktywności fizycznej]"),
    FieldSpec("mfis_8", "Trudno zmotywować się do wyjścia", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do aktywnego uczestnictwa w zajęciach poza domem (spotkania itp.)]"),
    FieldSpec("mfis_9", "Nie czułam/em się zdolna/y do niczego poza domem", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Nie czułam/em się zdolna/y do robienia czegokolwiek poza domem]"),
    FieldSpec("mfis_10", "Problem z utrzymaniem wysiłku fizycznego", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z utrzymaniem wysiłku fizycznego przez dłuższy czas]"),
    FieldSpec("mfis_11", "Trudności w podejmowaniu decyzji", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w podejmowaniu decyzji]"),
    FieldSpec("mfis_12", "Trudno zmusić się do myślenia", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmusić do zrobienia czegokolwiek co wymagało myślenia]"),
    FieldSpec("mfis_13", "Mięśnie jak z waty", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em poczucie, że moje mięśnie są jakby \"zrobione z waty\"]"),
    FieldSpec("mfis_14", "Dyskomfort fizyczny", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Odczuwałam/em dyskomfort fizyczny]"),
    FieldSpec("mfis_15", "Problem z ukończeniem zadania (myślenie)", 2, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to myślenia]"),
]


# ============================================================
# Strona 5 – MFIS (16-21) + zdrowie
# ============================================================
PAGE4_FIELDS = [
    FieldSpec("mfis_16", "Trudności w uporządkowaniu myśli", 3, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w uporządkowaniu myśli podczas pracy (w domu i poza domem)]"),
    FieldSpec("mfis_17", "Problem z ukończeniem zadania (wysiłek fiz.)", 3, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to wysiłku fizycznego]"),
    FieldSpec("mfis_18", "Myślenie spowolnione", 3, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em wrażenie, że moje myślenie uległo spowolnieniu ]"),
    FieldSpec("mfis_19", "Problemy z koncentracją", 3, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problemy z koncentracją]"),
    FieldSpec("mfis_20", "Musiałam/em ograniczyć aktywność", 3, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em ograniczyć moją aktywność fizyczną]"),
    FieldSpec("mfis_21", "Musiałam/em odpoczywać częściej", 3, "radio", _MFIS_CHOICES,
              csv_header="Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em odpoczywać częściej i przez dłuższy okres czasu]"),
    FieldSpec("choroba_anemia", "Czy stwierdzono anemię?", 3, "radio", ["NIE", "TAK"],
              csv_header="Czy w ostatnim czasie stwierdzono u Ciebie anemię?"),
    FieldSpec("choroba_tarczyca", "Problemy z tarczycą?", 3, "radio", ["NIE", "TAK"],
              csv_header="Czy w ostatnim czasie stwierdzono u Ciebie problemy z tarczycą?"),
    FieldSpec("tarczyca_jakie", "Jakie problemy z tarczycą?", 3, "text",
              conditional="choroba_tarczyca=TAK",
              csv_header="Jeśli odpowiedź na poprzednie pytanie brzmiało \"tak\", to jakie problemy stwierdzono:"),
    FieldSpec("choroba_inne", "Inne choroby", 3, "text",
              csv_header="Czy w ostatnim czasie stwierdzono u Ciebie inne choroby? Jeśli tak, to jakie:"),
]


# ============================================================
# Kolejność kolumn dla exportu CSV: Demografia → MFIS → Health → Sen → CES-D
# ============================================================
CSV_FIELDS = (
    PAGE0_FIELDS +                                           # Demografia (17)
    PAGE3_FIELDS +                                           # MFIS 1-15
    [f for f in PAGE4_FIELDS if f.name.startswith("mfis_")] +  # MFIS 16-21
    [f for f in PAGE4_FIELDS if not f.name.startswith("mfis_")] +  # Health (4)
    PAGE2_FIELDS +                                           # Sen (8)
    PAGE1_FIELDS                                             # CES-D (20)
)

# ============================================================
# Zbiór wszystkich pól (do UI / promptów / walidacji)
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
    1: PAGE2_FIELDS,
    2: PAGE3_FIELDS,
    3: PAGE4_FIELDS,
    4: PAGE1_FIELDS,
}
