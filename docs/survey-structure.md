# Survey Structure — AnkieterAI

## Przegląd

- **70 pól** na 5 stronach ankiety (63 oryginalne + 7 rozszerzonych)
- **71 nagłówków CSV** (1 Sygnatura czasowa + 70 pól)
- Źródło prawdy: `src/domain/field_specs.py`
- Modele danych: `src/domain/schemas.py` (MedicalSurvey)
- CSV export: `src/domain/csv_export.py` (CSV_HEADER generowany dynamicznie z ALL_FIELDS)

---

## Strona 1 — Demografia + styl życia (17 pól)

Pierwsza strona ankiety zawiera pytania demograficzne, informacje o pracy
oraz stylu życia respondenta.

| #  | Nazwa pola     | Etykieta                              | Typ    | Dozwolone wartości                                                                                         | Nagłówek CSV                                          |
|----|----------------|---------------------------------------|--------|------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| 1  | `p1_plec`      | 1. Płeć                               | select | Kobieta, Mężczyzna, Nie chcę podawać                                                                      | Płeć                                                  |
| 2  | `p2_wiek`      | 2. Wiek                               | number | 18-80 (dowolny tekst z regex `\d+`)                                                                        | Wiek                                                  |
| 3  | `p3_miejsce`   | 3. Miejsce zamieszkania               | select | Wieś, Miasto do 50 tys. mieszkańców, Miasto 50-100 tys. mieszkańców, Miasto powyżej 100 tys. mieszkańców    | Miejsce zamieszkania                                  |
| 4  | `p4_stan`      | 4. Stan cywilny                       | select | Panna/kawaler, W związku nieformalnym, Mężatka/żonaty, Rozwiedziona/rozwiedziony, Wdowa/wdowiec            | Stan cywilny                                          |
| 5  | `p5_forma`     | 5. Forma zamieszkania                 | select | Z rodziną, W akademiku, W wynajmowanym mieszkaniu/pokoju, Inne                                           | Forma zamieszkania w trakcie studiów                 |
| 6  | `p5_inne`      | 5a. Inne (zamieszkanie)               | text   | (dowolny tekst)                                                                                            | Inne (forma zamieszkania)                             |
| 7  | `p6_stopien`   | 6. Stopień studiów                    | select | Studia I stopnia, Studia II stopnia                                                                        | Stopień studiów                                       |
| 8  | `p7_uczelnia`  | 7. Uczelnia                           | text   | (dowolny tekst)                                                                                            | Na jakiej uczelni studiujesz?                          |
| 9  | `p8_praca`     | 8. Praca w trakcie studiów?            | select | Tak, w zawodzie medycznym, Tak, poza zawodem, Nie (Jeśli zaznaczyłaś/eś tą odpowiedź, przejdź do pytania nr 12) | Czy pracujesz zawodowo w trakcie studiów?    |
| 10 | `p9_system`    | 9. System pracy                       | select | Zmianowym, 12-godzinnym, Jednozmianowym, 8-godzinnym, Innym                                               | Jeśli pracujesz w zawodzie, to w jakim systemie       |
| 11 | `p9_inne`      | 9a. Inne (system pracy)               | text   | (dowolny tekst)                                                                                            | Inne (system pracy)                                   |
| 12 | `p10_oddzial`  | 10. Rodzaj oddziału                   | select | Zachowawczym, Zabiegowym, Inne                                                                             | Na jakim rodzaju oddziału pracujesz?                  |
| 13 | `p10_inne`     | 10a. Inne (oddział)                   | text   | (dowolny tekst)                                                                                            | Inne (oddział)                                        |
| 14 | `p11_staz`     | 11. Staż pracy                        | text   | (dowolny tekst)                                                                                            | Jaki jest Twój staż pracy                             |
| 15 | `p12_sen`      | 12. Średnia liczba godzin snu         | select | poniżej 5 godzin, 5-6 godzin, 7-8 godzin, Powyżej 8 godzin                                                | Jaka jest Twoja średnia liczba godzin snu w ciągu doby? |
| 16 | `p13_ekran`    | 13. Godziny przed ekranem             | select | Mniej niż 1 godzinę, 1-3 godziny, Powyżej 3 godzin                                                        | Ile godzin dziennie spędzasz przed ekranem             |
| 17 | `p14_kofeina`  | 14. Spożycie kofeiny                  | select | Nie, Tak, 1-2 porcje dziennie, Tak, 3 lub więcej porcji dziennie                                          | Czy pijesz napoje zawierające kofeinę (kawa, napoje energetyczne)? |

---

## Strona 2 — CES-D (20 pól)

**CES-D** (Center for Epidemiologic Studies Depression Scale) — skala depresji.
Odpowiedzi dotyczą odczuć i zachowań w **minionym tygodniu**.

**Skala odpowiedzi (4 opcje):**
- Rzadko lub wcale (mniej niż 1 dzień)
- Przez niedługi czas (1-2 dni)
- Czasem lub przez umiarkowany okres (3-4 dni)
- Przeważnie lub cały czas (5-7 dni)

| #  | Nazwa pola | Etykieta                                    | Nagłówek CSV                                                          |
|----|------------|---------------------------------------------|-----------------------------------------------------------------------|
| 1  | `depr_1`   | Przeszkadzały mi rzeczy…                    | Podczas minionego tygodnia   [Przeszkadzały mi rzeczy, które zazwyczaj mi nie przeszkadzają] |
| 2  | `depr_2`   | Nie miałem ochoty jeść…                     | Podczas minionego tygodnia   [Nie miałem ochoty jeść; mój apetyt był słaby] |
| 3  | `depr_3`   | Nie mogłem otrząsnąć się z chandry…         | Podczas minionego tygodnia   [Czułem, że nie mogę otrząsnąć się z chandry, nawet z pomocą rodziny lub przyjaciół] |
| 4  | `depr_4`   | Czułem, że jestem tak samo dobry…           | Podczas minionego tygodnia   [Czułem, że jestem tak samo dobry jak inni ludzie] |
| 5  | `depr_5`   | Ciężko mi się skoncentrować…               | Podczas minionego tygodnia   [Było mi ciężko skoncentrować się na tym co robię] |
| 6  | `depr_6`   | Czułem się przygnębiony                     | Podczas minionego tygodnia   [Czułem się przygnębiony]                  |
| 7  | `depr_7`   | Cokolwiek robię, wymaga wysiłku            | Podczas minionego tygodnia   [Czułem, że cokolwiek robię, wymaga wysiłku] |
| 8  | `depr_8`   | Optymistycznie patrzyłem w przyszłość       | Podczas minionego tygodnia   [Optymistycznie patrzyłem w przyszłość]    |
| 9  | `depr_9`   | Moje życie to porażka                       | Podczas minionego tygodnia   [Miałem poczucie, że moje życie to porażka] |
| 10 | `depr_10`  | Czułem strach                               | Podczas minionego tygodnia   [Czułem strach]                           |
| 11 | `depr_11`  | Mój sen był niespokojny                     | Podczas minionego tygodnia   [Mój sen był niespokojny]                 |
| 12 | `depr_12`  | Byłem szczęśliwy                            | Podczas minionego tygodnia   [Byłem szczęśliwy]                        |
| 13 | `depr_13`  | Mówiłem mniej niż zwykle                   | Podczas minionego tygodnia   [Mówiłem mniej niż zwykle]               |
| 14 | `depr_14`  | Czułem się samotny                          | Podczas minionego tygodnia   [Czułem się samotny]                      |
| 15 | `depr_15`  | Ludzie byli nieprzyjaźni                    | Podczas minionego tygodnia   [Ludzie byli nastawieni nieprzyjaźnie]    |
| 16 | `depr_16`  | Czerpałem radość z życia                    | Podczas minionego tygodnia   [Czerpałem radość z życia]                |
| 17 | `depr_17`  | Miałem napady płaczu                        | Podczas minionego tygodnia   [Miałem napady płaczu]                    |
| 18 | `depr_18`  | Było mi smutno                              | Podczas minionego tygodnia   [Było mi smutno]                          |
| 19 | `depr_19`  | Ludzie mnie nie lubią                       | Podczas minionego tygodnia   [Czułem, że ludzie mnie nie lubią]        |
| 20 | `depr_20`  | Nie mogłem się za nic zabrać                | Podczas minionego tygodnia   [Nie byłem w stanie się za nic zabrać]    |

---

## Strona 3 — Ateńska skala bezsenności (8 pól)

**Athens Insomnia Scale** — skala bezsenności. Pytania dotyczą **ostatnich
dwóch tygodni**.

| #  | Nazwa pola | Etykieta                    | Dozwolone wartości (4 opcje)                                                                                |
|----|------------|-----------------------------|-------------------------------------------------------------------------------------------------------------|
| 1  | `sen_1`    | Zasypianie                  | szybkie, nieznacznie opóźnione, opóźnione, bardzo opóźnione lub bezsenność przez całą noc                  |
| 2  | `sen_2`    | Budzenie się w nocy         | nie występuje, sporadycznie, często, bardzo często lub bezsenność przez całą noc                           |
| 3  | `sen_3`    | Wcześniejsze budzenie       | o zamierzonej godzinie, nieznacznie wcześniej, znacznie wcześniej, dużo wcześniej lub bezsenność przez całą noc |
| 4  | `sen_4`    | Całkowity czas snu          | wystarczający, nieznacznie niewystarczający, wyraźnie niewystarczający, całkowicie niewystarczający lub bezsenność przez całą noc |
| 5  | `sen_5`    | Jakość snu                  | satysfakcjonująca, nieznacznie niesatysfakcjonująca, wyraźnie niesatysfakcjonująca, całkowicie niesatysfakcjonująca |
| 6  | `sen_6`    | Samopoczucie nast. dnia     | dobre, nieznacznie gorsze, wyraźnie gorsze, **wybitnie gorsze**                                            |
| 7  | `sen_7`    | Sprawność nast. dnia        | niezaburzona, nieznacznie zaburzona, wyraźnie zaburzona, **wybitnie zaburzona**                             |
| 8  | `sen_8`    | Senność w ciągu dnia        | nie zdarza się, nieznaczna, wyraźna, bardzo nasilona                                                        |

> Uwaga: `sen_6` i `sen_7` mają 4 opcje (w tym "wybitnie gorsze" / "wybitnie zaburzona").

---

## Strona 4 — MFIS pozycje 1-15 (15 pól)

**MFIS** (Modified Fatigue Impact Scale) — skala wpływu zmęczenia.
Pytania dotyczą **ostatnich 4 tygodni**.

**Skala odpowiedzi (5 opcji, 0-4):**
- 0 — Nigdy
- 1 — Rzadko
- 2 — Czasami
- 3 — Często
- 4 — Prawie zawsze

| #  | Nazwa pola  | Etykieta                                                    | Nagłówek CSV                                                                                                  |
|----|-------------|-------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| 1  | `mfis_1`    | Czułam/em się mniej uważna/y                                | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Czułam/em się mniej uważna/y] |
| 2  | `mfis_2`    | Trudno było mi się skupić                                   | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się skupić przez dłuższą chwilę] |
| 3  | `mfis_3`    | Trudno było mi myśleć logicznie                             | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi myśleć logicznie] |
| 4  | `mfis_4`    | Byłam/em niezdarna/y                                        | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em niezdarna/y] |
| 5  | `mfis_5`    | Byłam/em zapominalska/ski                                   | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em zapominalska/ski] |
| 6  | `mfis_6`    | Musiałam/em wyznaczać tempo                                 | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em sama/sam wyznaczać sobie indywidualne tempo mojej pracy i aktywności fizycznej (bo nie mogłam/em nadążyć)] |
| 7  | `mfis_7`    | Trudno zmotywować się do aktywności fizycznej               | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do czegoś co wymagało aktywności fizycznej] |
| 8  | `mfis_8`    | Trudno zmotywować się do wyjścia                             | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do aktywnego uczestnictwa w zajęciach poza domem (spotkania itp.)] |
| 9  | `mfis_9`    | Nie czułam/em się zdolna/y do niczego poza domem            | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Nie czułam/em się zdolna/y do robienia czegokolwiek poza domem] |
| 10 | `mfis_10`   | Problem z utrzymaniem wysiłku fizycznego                     | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z utrzymaniem wysiłku fizycznego przez dłuższy czas] |
| 11 | `mfis_11`   | Trudności w podejmowaniu decyzji                            | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w podejmowaniu decyzji] |
| 12 | `mfis_12`   | Trudno zmusić się do myślenia                               | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmusić do zrobienia czegokolwiek co wymagało myślenia] |
| 13 | `mfis_13`   | Mięśnie jak z waty                                          | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em poczucie, że moje mięśnie są jakby "zrobione z waty"] |
| 14 | `mfis_14`   | Dyskomfort fizyczny                                         | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Odczuwałam/em dyskomfort fizyczny] |
| 15 | `mfis_15`   | Problem z ukończeniem zadania (myślenie)                    | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to myślenia] |

---

## Strona 5 — MFIS pozycje 16-21 + zdrowie (10 pól)

Kontynuacja skali MFIS (6 pól) oraz pytania o stan zdrowia (4 pola).

### MFIS 16-21 (skala 0-4)

| #  | Nazwa pola    | Etykieta                                                    | Nagłówek CSV                                                                                                  |
|----|---------------|-------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| 1  | `mfis_16`     | Trudności w uporządkowaniu myśli                            | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w uporządkowaniu myśli podczas pracy (w domu i poza domem)] |
| 2  | `mfis_17`     | Problem z ukończeniem zadania (wysiłek fiz.)                | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to wysiłku fizycznego] |
| 3  | `mfis_18`     | Myślenie spowolnione                                        | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em wrażenie, że moje myślenie uległo spowolnieniu ] |
| 4  | `mfis_19`     | Problemy z koncentracją                                     | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problemy z koncentracją] |
| 5  | `mfis_20`     | Musiałam/em ograniczyć aktywność                            | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em ograniczyć moją aktywność fizyczną] |
| 6  | `mfis_21`     | Musiałam/em odpoczywać częściej                             | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em odpoczywać częściej i przez dłuższy okres czasu] |

### Stan zdrowia

| #  | Nazwa pola          | Etykieta                      | Typ    | Dozwolone wartości | Nagłówek CSV                                               |
|----|---------------------|-------------------------------|--------|--------------------|-------------------------------------------------------------|
| 7  | `choroba_anemia`    | Czy stwierdzono anemię?       | select | TAK, NIE           | Czy w ostatnim czasie stwierdzono u Ciebie anemię?          |
| 8  | `choroba_tarczyca`  | Problemy z tarczycą?          | select | TAK, NIE           | Czy w ostatnim czasie stwierdzono u Ciebie problemy z tarczycą? |
| 9  | `tarczyca_jakie`    | Jakie problemy z tarczycą?    | text   | (dowolny tekst)    | Jeśli odpowiedź na poprzednie pytanie brzmiało "tak", to jakie problemy stwierdzono: |
| 10 | `choroba_inne`      | Inne choroby                  | text   | (dowolny tekst)    | Czy w ostatnim czasie stwierdzono u Ciebie inne choroby? Jeśli tak, to jakie: |

---

## Mapowanie CSV

Kolejność kolumn w pliku CSV:

| Pozycja | Zawartość |
|---------|-----------|
| 1 | Sygnatura czasowa (format: `YYYY-MM-DD HH:MM:SS`) |
| 2-71 | 70 pól zgodnie z kolejnością w `ALL_FIELDS` (strona 1 → strona 5) |

Encoding: **UTF-8 BOM** (`utf-8-sig`) dla poprawnego otwierania w Excelu.

---

## Walidacja (z `schemas.py` i `api.py`)

| Typ pola | Reguła walidacji backend | Wartość przy braku |
|----------|--------------------------|--------------------|
| `select` | Dokładne dopasowanie case-insensitive do dozwolonych wartości | `None` |
| `number` | Konwersja na `int`, zakres 18-80 (dla wieku) | `None` |
| `text` | `strip()`, zwraca string | `""` (pusty string) |

Frontend (React) dodatkowo waliduje przed wysłaniem — czerwone kropki przy błędach,
dwuetapowe zatwierdzanie (walidacja → jeśli błędy, pokaż kropki → "Zatwierdź mimo błędów").

---

## Podsumowanie: 70 pól

| Strona | Zakres | Liczba pól | Nazwy pól |
|--------|--------|-----------|-----------|
| 1 | Demografia + styl życia | 17 | `p1_plec` .. `p14_kofeina` (+ `p5_inne`, `p9_inne`, `p10_inne`) |
| 2 | CES-D (depresja) | 20 | `depr_1` .. `depr_20` |
| 3 | Athens (bezsenność) | 8 | `sen_1` .. `sen_8` |
| 4 | MFIS (zmęczenie 1-15) | 15 | `mfis_1` .. `mfis_15` |
| 5 | MFIS (16-21) + zdrowie | 10 | `mfis_16` .. `mfis_21` + `choroba_anemia` .. `choroba_inne` |
| **Razem** | | **70** | |
