# Survey Structure — AnkieterAI

## Przegląd

- **63 pól** na 5 stronach ankiety
- **68 nagłówków CSV** (1 Sygnatura czasowa + 63 pola + 4 metadane/placeholder*)
- Źródło prawdy: `src/domain/field_specs.py`
- Modele danych: `src/domain/schemas.py` (MedicalSurvey)
- CSV export: `src/domain/csv_export.py`

*Uwaga: `CSV_HEADER` w `csv_export.py` generowany jest dynamicznie z `ALL_FIELDS`.
Dokładna liczba nagłówków zależy od implementacji — do weryfikacji przy uzupełnianiu.*

---

## Strona 1 — Demografia + styl życia (14 pól)

Pierwsza strona ankiety zawiera pytania demograficzne, informacje o pracy
oraz stylu życia respondenta.

| #  | Nazwa pola              | Etykieta                              | Typ    | Dozwolone wartości                                                                                         | Nagłówek CSV                                          |
|----|-------------------------|---------------------------------------|--------|------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| 1  | `plec`                  | Płeć                                  | select | Kobieta, Mężczyzna, Nie chcę podawać                                                                      | Płeć                                                  |
| 2  | `wiek`                  | Wiek                                  | number | 18-80                                                                                                      | Wiek                                                  |
| 3  | `miejsce_zamieszkania`  | Miejsce zamieszkania                  | select | Wieś, Miasto do 50 tys. mieszkańców, Miasto 50-100 tys. mieszkańców, Miasto powyżej 100 tys. mieszkańców    | Miejsce zamieszkania                                  |
| 4  | `stan_cywilny`          | Stan cywilny                          | select | Panna/kawaler, W związku nieformalnym, Mężatka/żonaty, Rozwiedziona/rozwiedziony, Wdowa/wdowiec            | Stan cywilny                                          |
| 5  | `forma_zamieszkania`    | Forma zamieszkania                    | select | Z rodziną, W akademiku, W wynajmowanym mieszkaniu/pokoju, Własne mieszkanie, We własnym mieszkaniu z partnerem, z partnerem, Inne | Forma zamieszkania w trakcie studiów |
| 6  | `stopien_studiow`       | Stopień studiów                       | select | Studia I stopnia, Studia II stopnia                                                                        | Stopień studiów                                       |
| 7  | `uczelnia`              | Uczelnia                              | text   | (dowolny tekst)                                                                                            | Na jakiej uczelni studiujesz?                         |
| 8  | `praca_status`          | Praca w trakcie studiów?              | select | Nie, Tak w zawodzie medycznym, Tak poza zawodem                                                            | Czy pracujesz zawodowo w trakcie studiów?             |
| 9  | `praca_system`          | System pracy                          | text   | (dowolny tekst)                                                                                            | Jeśli pracujesz w zawodzie, to w jakim systemie       |
| 10 | `oddzial`               | Rodzaj oddziału                       | select | (pusty), Przychodnia, Zabiegowym, Zachowawczym, Pracownia, Inne                                           | Na jakim rodzaju oddziału pracujesz?                  |
| 11 | `staz_pracy`            | Staż pracy                            | text   | (dowolny tekst)                                                                                            | Jaki jest Twój staż pracy                             |
| 12 | `sen_godziny`           | Średnia liczba godzin snu             | select | Poniżej 5 godzin, 5-6 godzin, 7-8 godzin, Powyżej 8 godzin                                               | Jaka jest Twoja średnia liczba godzin snu w ciągu doby? |
| 13 | `ekran_godziny`         | Godziny przed ekranem                 | select | 1-3 godziny, Powyżej 3 godzin                                                                              | Ile godzin dziennie spędzasz przed ekranem             |
| 14 | `kofeina`               | Spożycie kofeiny                       | select | Nie, Tak 1-2 porcje dziennie, Tak 3 lub więcej porcji dziennie                                             | Czy pijesz napoje zawierające kofeinę?                |

---

## Strona 2 — CES-D (20 pól)

**CES-D** (Center for Epidemiologic Studies Depression Scale) — skala depresji.
Odpowiedzi dotyczą odczuć i zachowań w **minionym tygodniu**.

**Skala odpowiedzi (4 opcje):**
- Rzadko lub wcale (mniej niż 1 dzień)
- Przez niedługi czas (1-2 dni)
- Czasem lub przez umiarkowany okres (3-4 dni)
- Przeważnie lub cały czas (5-7 dni)

| #  | Nazwa pola                   | Etykieta                                    | Nagłówek CSV                                                          |
|----|------------------------------|---------------------------------------------|-----------------------------------------------------------------------|
| 1  | `cesd_przeszkadzaly`        | Przeszkadzały mi rzeczy…                    | Podczas minionego tygodnia [Przeszkadzały mi rzeczy, które zazwyczaj mi nie przeszkadzają] |
| 2  | `cesd_brak_apetytu`         | Nie miałem ochoty jeść…                     | Podczas minionego tygodnia [Nie miałem ochoty jeść; mój apetyt był słaby] |
| 3  | `cesd_chandra`              | Nie mogłem otrząsnąć się z chandry…         | Podczas minionego tygodnia [Czułem, że nie mogę otrząsnąć się z chandry, nawet z pomocą rodziny lub przyjaciół] |
| 4  | `cesd_tak_samo_dobry`       | Czułem, że jestem tak samo dobry…           | Podczas minionego tygodnia [Czułem, że jestem tak samo dobry jak inni ludzie] |
| 5  | `cesd_ciezko_skoncentrowac` | Ciężko mi się skoncentrować…               | Podczas minionego tygodnia [Było mi ciężko skoncentrować się na tym co robię] |
| 6  | `cesd_przygnebiony`         | Czułem się przygnębiony                     | Podczas minionego tygodnia [Czułem się przygnębiony]                  |
| 7  | `cesd_wysilek`              | Cokolwiek robię, wymaga wysiłku            | Podczas minionego tygodnia [Czułem, że cokolwiek robię, wymaga wysiłku] |
| 8  | `cesd_optymistycznie`       | Optymistycznie patrzyłem w przyszłość       | Podczas minionego tygodnia [Optymistycznie patrzyłem w przyszłość]    |
| 9  | `cesd_zycie_porazka`        | Moje życie to porażka                       | Podczas minionego tygodnia [Miałem poczucie, że moje życie to porażka] |
| 10 | `cesd_strach`               | Czułem strach                               | Podczas minionego tygodnia [Czułem strach]                           |
| 11 | `cesd_sen_niespokojny`      | Mój sen był niespokojny                     | Podczas minionego tygodnia [Mój sen był niespokojny]                 |
| 12 | `cesd_szczesliwy`           | Byłem szczęśliwy                            | Podczas minionego tygodnia [Byłem szczęśliwy]                        |
| 13 | `cesd_mowil_mniej`          | Mówiłem mniej niż zwykle                   | Podczas minionego tygodnia [Mówiłem mniej niż zwykle]               |
| 14 | `cesd_samotny`              | Czułem się samotny                          | Podczas minionego tygodnia [Czułem się samotny]                      |
| 15 | `cesd_ludzie_nieprzyjazni`  | Ludzie byli nieprzyjaźni                    | Podczas minionego tygodnia [Ludzie byli nastawieni nieprzyjaźnie]    |
| 16 | `cesd_radosci`              | Czerpałem radość z życia                    | Podczas minionego tygodnia [Czerpałem radość z życia]                |
| 17 | `cesd_placzu`               | Miałem napady płaczu                        | Podczas minionego tygodnia [Miałem napady płaczu]                    |
| 18 | `cesd_smutno`               | Było mi smutno                              | Podczas minionego tygodnia [Było mi smutno]                          |
| 19 | `cesd_ludzie_nie_lubia`     | Ludzie mnie nie lubią                       | Podczas minionego tygodnia [Czułem, że ludzie mnie nie lubią]        |
| 20 | `cesd_nic_nie_zabrac`       | Nie mogłem się za nic zabrać                | Podczas minionego tygodnia [Nie byłem w stanie się za nic zabrać]    |

---

## Strona 3 — Ateńska skala bezsenności (8 pól)

**Athens Insomnia Scale** — skala bezsenności. Pytania dotyczą **ostatnich
dwóch tygodni**.

| #  | Nazwa pola      | Etykieta                    | Dozwolone wartości                                                                                   |
|----|-----------------|-----------------------------|------------------------------------------------------------------------------------------------------|
| 1  | `zasypianie`    | Zasypianie                  | szybkie, nieznacznie opóźnione, opóźnione, bardzo opóźnione lub bezsenność przez całą noc           |
| 2  | `budzenie_noc`  | Budzenie się w nocy         | nie występuje, sporadycznie, często, bardzo często lub bezsenność przez całą noc                    |
| 3  | `budzenie_rano` | Wcześniejsze budzenie       | o zamierzonej godzinie, nieznacznie wcześniej, znacznie wcześniej, dużo wcześniej lub bezsenność przez całą noc |
| 4  | `czas_snu`      | Całkowity czas snu          | wystarczający, nieznacznie niewystarczający, wyraźnie niewystarczający, całkowicie niewystarczający lub bezsenność przez całą noc |
| 5  | `jakosc_snu`    | Jakość snu                  | satysfakcjonująca, nieznacznie niesatysfakcjonująca, wyraźnie niesatysfakcjonująca, całkowicie niesatysfakcjonująca |
| 6  | `samopoczucie`  | Samopoczucie nast. dnia     | dobre, nieznacznie gorsze, wyraźnie gorsze                                                           |
| 7  | `sprawnosc`     | Sprawność nast. dnia        | niezaburzona, nieznacznie zaburzona, wyraźnie zaburzona                                              |
| 8  | `sennosc`       | Senność w ciągu dnia        | nie zdarza się, nieznaczna, wyraźna, bardzo nasilona                                                 |

---

## Strona 4 — MFIS pozycje 1-15 (15 pól)

**MFIS** (Modified Fatigue Impact Scale) — skala wpływu zmęczenia.
Pytania dotyczą **ostatnich 4 tygodni**.

**Skala odpowiedzi (5 opcji):**
- Nigdy
- Rzadko
- Czasami
- Często
- Prawie zawsze

| #  | Nazwa pola                      | Etykieta                                                    |
|----|---------------------------------|-------------------------------------------------------------|
| 1  | `objaw_mniej_uwazna`           | Czułam/em się mniej uważna/y                                |
| 2  | `objaw_trudno_skupic`           | Trudno było mi się skupić                                   |
| 3  | `objaw_trudno_myslec`           | Trudno było mi myśleć logicznie                             |
| 4  | `objaw_niezdarna`               | Byłam/em niezdarna/y                                        |
| 5  | `objaw_zapominalska`            | Byłam/em zapominalska/ski                                   |
| 6  | `objaw_wyznaczac_tempo`         | Musiałam/em wyznaczać tempo                                 |
| 7  | `objaw_zmotywowac_fizycznie`    | Trudno zmotywować się do aktywności fizycznej               |
| 8  | `objaw_zmotywowac_spotkania`    | Trudno zmotywować się do wyjścia                             |
| 9  | `objaw_nie_zdolna_poza_domem`   | Nie czułam/em się zdolna/y do niczego poza domem            |
| 10 | `objaw_wysilek_fizyczny`        | Problem z utrzymaniem wysiłku fizycznego                     |
| 11 | `objaw_trudnosci_decyzyjne`     | Trudności w podejmowaniu decyzji                            |
| 12 | `objaw_zmusic_do_myslenia`      | Trudno zmusić się do myślenia                               |
| 13 | `objaw_miesnie_z_waty`          | Mięśnie jak z waty                                          |
| 14 | `objaw_dyskomfort_fizyczny`     | Dyskomfort fizyczny                                         |
| 15 | `objaw_ukonczenie_myslenie`     | Problem z ukończeniem zadania (myślenie)                    |

---

## Strona 5 — MFIS pozycje 16-21 + zdrowie (10 pól)

Kontynuacja skali MFIS (6 pól) oraz pytania o stan zdrowia (4 pola).

### MFIS 16-21 (skala jak strona 4)

| #  | Nazwa pola                      | Etykieta                                                    |
|----|---------------------------------|-------------------------------------------------------------|
| 1  | `objaw_uporzadkowanie_mysli`   | Trudności w uporządkowaniu myśli                            |
| 2  | `objaw_ukonczenie_wysilek`     | Problem z ukończeniem zadania (wysiłek fiz.)                |
| 3  | `objaw_myslenie_spowolnione`   | Myślenie spowolnione                                        |
| 4  | `objaw_problemy_koncentracja`  | Problemy z koncentracją                                     |
| 5  | `objaw_ograniczyc_aktywnosc`   | Musiałam/em ograniczyć aktywność                            |
| 6  | `objaw_czesciej_odpoczywac`    | Musiałam/em odpoczywać częściej                             |

### Stan zdrowia

| #  | Nazwa pola             | Etykieta                      | Typ    | Dozwolone wartości | Nagłówek CSV                                               |
|----|------------------------|-------------------------------|--------|--------------------|-------------------------------------------------------------|
| 7  | `anemia`               | Czy stwierdzono anemię?       | select | Tak, Nie           | Czy w ostatnim czasie stwierdzono u Ciebie anemię?          |
| 8  | `problemy_tarczyca`    | Problemy z tarczycą?          | select | Tak, Nie           | Czy w ostatnim czasie stwierdzono u Ciebie problemy z tarczycą? |
| 9  | `jaka_tarczyca`        | Jakie problemy z tarczycą?    | text   | (dowolny tekst)    | Jeśli odpowiedź na poprzednie pytanie brzmiało "tak", to jakie problemy stwierdzono |
| 10 | `inne_choroby`         | Inne choroby                  | text   | (dowolny tekst)    | Czy w ostatnim czasie stwierdzono u Ciebie inne choroby? Jeśli tak, to jakie |

---

## Mapowanie CSV

Kolejność kolumn w pliku CSV:

| Pozycja | Zawartość |
|---------|-----------|
| 1 | Sygnatura czasowa (format: `YYYY-MM-DD HH:MM:SS`) |
| 2-64 | 63 pól zgodnie z kolejnością w `ALL_FIELDS` (strona 1 → strona 5) |

Encoding: **UTF-8 BOM** (`utf-8-sig`) dla poprawnego otwierania w Excelu.

---

## Walidacja (z schemas.py)

| Typ pola | Reguła walidacji | Wartość przy braku |
|----------|------------------|--------------------|
| `select` | Dopasowanie case-insensitive do dozwolonych wartości | `None` |
| `number` | Konwersja na `int`, zakres 18-80 (dla wieku) | `None` |
| `text` | `strip()`, zwraca string | `""` (pusty string) |

---

## Sekcje do uzupełnienia przez agenta

Dokument ten jest szkieletem. Inny agent powinien uzupełnić:

### 1. Pytania — pełna treść
Dla każdego pola podać pełną treść pytania z papierowej ankiety
(wersja polska, z oryginalnym formatowaniem).

### 2. Kontekst diagnostyczny
- **Strona 1:** Dane demograficzne, aktywność zawodowa, styl życia
  — profil respondenta, czynniki ryzyka
- **Strona 2:** CES-D — skala depresji
  — Center for Epidemiologic Studies Depression Scale
  — 20 pytań, 4-stopniowa skala częstotliwości
- **Strona 3:** Athens — skala bezsenności
  — Athens Insomnia Scale
  — 8 pytań, ocena jakości snu
- **Strona 4-5:** MFIS — skala zmęczenia
  — Modified Fatigue Impact Scale
  — 21 pytań, 5-stopniowa skala
- **Strona 5:** Pytania o stan zdrowia
  — anemia, tarczyca, inne choroby

### 3. Interpretacja wyników
- **CES-D:** Normy, progi (np. score ≥16 = istotne objawy depresyjne)
- **Athens:** Normy, progi (np. score ≥6 = kliniczna bezsenność)
- **MFIS:** Normy, progi (np. score ≥36 = istotne zmęczenie)
- **Ogólne:** Jak interpretować wyniki w kontekście badania

### 4. Kontekst badania
- Do czego służy ta ankieta (research context)
- Grupa docelowa (studenci medycyny?)
- Jak wyniki będą wykorzystywane
