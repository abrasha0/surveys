# Survey structure

The survey has **5 pages** and **70 fields**. The field definitions in
`src/backend/domain/field_specs.py` are the single source of truth: they drive the
verification form, server-side validation, the CSV columns and (together with the
`page_N_json_schema` prompts in the config) AI extraction.

Field names are stable identifiers. Labels, choices and CSV headers are the Polish
texts used in the UI and in the exported CSV, and must match the paper survey and the
prompts exactly.

Field types:

- **choice**: exactly one of the listed answers (a radio group in the form)
- **number**: an integer, optionally limited to a range
- **text**: free text

Some text fields are marked as conditional: they are meant to be filled in only when
another field has a given answer (for example `p5_inne` when `p5_forma` is `Inne`).
The form hides such a field while the condition is not met, unless the field already
holds a value; then it stays visible with a warning. The server does not check the
condition: a filled field is saved as it is.

## Summary

| Page | Content | Fields | Field names |
|---|---|---|---|
| 1 | Demographics, employment, lifestyle | 17 | `p1_plec` … `p14_kofeina`, including `p5_inne`, `p9_inne`, `p10_inne` |
| 2 | Athens Insomnia Scale | 8 | `sen_1` … `sen_8` |
| 3 | MFIS (Modified Fatigue Impact Scale), items 1-15 | 15 | `mfis_1` … `mfis_15` |
| 4 | MFIS items 16-21 and health | 10 | `mfis_16` … `mfis_21`, `choroba_anemia`, `choroba_tarczyca`, `tarczyca_jakie`, `choroba_inne` |
| 5 | CES-D (Center for Epidemiologic Studies Depression Scale) | 20 | `depr_1` … `depr_20` |
| **Total** | | **70** | |

## Page 1: demographics, employment and lifestyle

| Field | Label | Type | Allowed values | CSV header |
|---|---|---|---|---|
| `p1_plec` | 1. Płeć | choice | Kobieta; Mężczyzna; Nie chcę podawać | Płeć |
| `p2_wiek` | 2. Wiek | number | 18-80 | Wiek |
| `p3_miejsce` | 3. Miejsce zamieszkania | choice | Wieś; Miasto do 50 tys. mieszkańców; Miasto 50-100 tys. mieszkańców; Miasto powyżej 100 tys. mieszkańców | Miejsce zamieszkania |
| `p4_stan` | 4. Stan cywilny | choice | Panna/kawaler; W związku nieformalnym; Mężatka/żonaty; Rozwiedziona/rozwiedziony; Wdowa/wdowiec | Stan cywilny |
| `p5_forma` | 5. Forma zamieszkania | choice | Z rodziną; W akademiku; W wynajmowanym mieszkaniu/pokoju; Inne | Forma zamieszkania w trakcie studiów |
| `p5_inne` | 5a. Inne (zamieszkanie) | text | free text (if `p5_forma` = Inne) | Inne (forma zamieszkania) |
| `p6_stopien` | 6. Stopień studiów | choice | Studia I stopnia; Studia II stopnia | Stopień studiów |
| `p7_uczelnia` | 7. Uczelnia | text | free text | Na jakiej uczelni studiujesz? |
| `p8_praca` | 8. Praca w trakcie studiów? | choice | Tak, w zawodzie medycznym; Tak, poza zawodem; Nie (Jeśli zaznaczyłaś/eś tą odpowiedź, przejdź do pytania nr 12) | Czy pracujesz zawodowo w trakcie studiów? |
| `p9_system` | 9. System pracy | choice | Zmianowym, 12-godzinnym; Jednozmianowym, 8-godzinnym; Innym | Jeśli pracujesz w zawodzie, to w jakim systemie |
| `p9_inne` | 9a. Inne (system pracy) | text | free text (if `p9_system` = Innym) | Inne (system pracy) |
| `p10_oddzial` | 10. Rodzaj oddziału | choice | Zachowawczym; Zabiegowym; Inne | Na jakim rodzaju oddziału pracujesz? |
| `p10_inne` | 10a. Inne (oddział) | text | free text (if `p10_oddzial` = Inne) | Inne (oddział) |
| `p11_staz` | 11. Staż pracy | text | free text | Jaki jest Twój staż pracy |
| `p12_sen` | 12. Średnia liczba godzin snu | choice | poniżej 5 godzin; 5-6 godzin; 7-8 godzin; Powyżej 8 godzin | Jaka jest Twoja średnia liczba godzin snu w ciągu doby? |
| `p13_ekran` | 13. Godziny przed ekranem | choice | Mniej niż 1 godzinę; 1-3 godziny; Powyżej 3 godzin | Ile godzin dziennie spędzasz przed ekranem |
| `p14_kofeina` | 14. Spożycie kofeiny | choice | Nie; Tak, 1-2 porcje dziennie; Tak, 3 lub więcej porcji dziennie | Czy pijesz napoje zawierające kofeinę (kawa, napoje energetyczne)? |

## Page 2: Athens Insomnia Scale

All items have four answers, from best to worst sleep.

| Field | Label | Allowed values | CSV header |
|---|---|---|---|
| `sen_1` | Zasypianie | szybkie; nieznacznie opóźnione; opóźnione; bardzo opóźnione lub bezsenność przez całą noc | Zasypianie po położeniu się do łóżka i zgaszeniu światła |
| `sen_2` | Budzenie się w nocy | nie występuje; sporadycznie; często; bardzo często lub bezsenność przez całą noc | Budzenie się podczas nocy |
| `sen_3` | Wcześniejsze budzenie | o zamierzonej godzinie; nieznacznie wcześniej; znacznie wcześniej; dużo wcześniej lub bezsenność przez całą noc | Budzenie się rano wcześniej niż planowano |
| `sen_4` | Całkowity czas snu | wystarczający; nieznacznie niewystarczający; wyraźnie niewystarczający; całkowicie niewystarczający lub bezsenność przez całą noc | Całkowity czas snu |
| `sen_5` | Jakość snu | satysfakcjonująca; nieznacznie niesatysfakcjonująca; wyraźnie niesatysfakcjonująca; całkowicie niesatysfakcjonująca | Jakość snu, niezależnie od czasu jego trwania |
| `sen_6` | Samopoczucie nast. dnia | dobre; nieznacznie gorsze; wyraźnie gorsze; wybitnie gorsze | Samopoczucie następnego dnia |
| `sen_7` | Sprawność nast. dnia | niezaburzona; nieznacznie zaburzona; wyraźnie zaburzona; wybitnie zaburzona | Sprawność psychiczna i fizyczna następnego dnia |
| `sen_8` | Senność w ciągu dnia | nie zdarza się; nieznaczna; wyraźna; bardzo nasilona | Senność w ciągu dnia |

## Page 3: MFIS, items 1-15

Every MFIS item uses the scale `0`-`4`, shown in the form as 0 Nigdy (never),
1 Rzadko (rarely), 2 Czasami (sometimes), 3 Często (often), 4 Prawie zawsze (almost
always). The items refer to the last 4 weeks.

| Field | Label | Type | CSV header |
|---|---|---|---|
| `mfis_1` | Czułam/em się mniej uważna/y | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Czułam/em się mniej uważna/y] |
| `mfis_2` | Trudno było mi się skupić | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się skupić przez dłuższą chwilę] |
| `mfis_3` | Trudno było mi myśleć logicznie | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi myśleć logicznie] |
| `mfis_4` | Byłam/em niezdarna/y | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em niezdarna/y] |
| `mfis_5` | Byłam/em zapominalska/ski | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Byłam/em zapominalska/ski] |
| `mfis_6` | Musiałam/em wyznaczać tempo | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em sama/sam wyznaczać sobie indywidualne tempo mojej pracy i aktywności fizycznej (bo nie mogłam/em nadążyć)] |
| `mfis_7` | Trudno zmotywować się do aktywności fizycznej | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do czegoś co wymagało aktywności fizycznej] |
| `mfis_8` | Trudno zmotywować się do wyjścia | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmotywować do aktywnego uczestnictwa w zajęciach poza domem (spotkania itp.)] |
| `mfis_9` | Nie czułam/em się zdolna/y do niczego poza domem | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Nie czułam/em się zdolna/y do robienia czegokolwiek poza domem] |
| `mfis_10` | Problem z utrzymaniem wysiłku fizycznego | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z utrzymaniem wysiłku fizycznego przez dłuższy czas] |
| `mfis_11` | Trudności w podejmowaniu decyzji | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w podejmowaniu decyzji] |
| `mfis_12` | Trudno zmusić się do myślenia | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Trudno było mi się zmusić do zrobienia czegokolwiek co wymagało myślenia] |
| `mfis_13` | Mięśnie jak z waty | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em poczucie, że moje mięśnie są jakby "zrobione z waty"] |
| `mfis_14` | Dyskomfort fizyczny | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Odczuwałam/em dyskomfort fizyczny] |
| `mfis_15` | Problem z ukończeniem zadania (myślenie) | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to myślenia] |

## Page 4: MFIS items 16-21 and health

The MFIS items use the same `0`-`4` scale as page 3.

| Field | Label | Type | CSV header |
|---|---|---|---|
| `mfis_16` | Trudności w uporządkowaniu myśli | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em trudności w uporządkowaniu myśli podczas pracy (w domu i poza domem)] |
| `mfis_17` | Problem z ukończeniem zadania (wysiłek fiz.) | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problem z ukończeniem określonego zadania bo wymagało to wysiłku fizycznego] |
| `mfis_18` | Myślenie spowolnione | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em wrażenie, że moje myślenie uległo spowolnieniu ] |
| `mfis_19` | Problemy z koncentracją | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Miałam/em problemy z koncentracją] |
| `mfis_20` | Musiałam/em ograniczyć aktywność | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em ograniczyć moją aktywność fizyczną] |
| `mfis_21` | Musiałam/em odpoczywać częściej | choice | Czy w ciągu ostatnich 4 tygodni doświadczyłaś/eś którykolwiek z objawów? Jeśli tak, zaznacz odpowiednią rubrykę [Musiałam/em odpoczywać częściej i przez dłuższy okres czasu] |
| `choroba_anemia` | Czy stwierdzono anemię? | choice: NIE; TAK | Czy w ostatnim czasie stwierdzono u Ciebie anemię? |
| `choroba_tarczyca` | Problemy z tarczycą? | choice: NIE; TAK | Czy w ostatnim czasie stwierdzono u Ciebie problemy z tarczycą? |
| `tarczyca_jakie` | Jakie problemy z tarczycą? | text (if `choroba_tarczyca` = TAK) | Jeśli odpowiedź na poprzednie pytanie brzmiało "tak", to jakie problemy stwierdzono: |
| `choroba_inne` | Inne choroby | text | Czy w ostatnim czasie stwierdzono u Ciebie inne choroby? Jeśli tak, to jakie: |

## Page 5: CES-D

The items refer to the past week. Every item uses the same four answers:

- Rzadko lub wcale (mniej niż 1 dzień)
- Przez niedługi czas (1-2 dni)
- Czasem lub przez umiarkowany okres (3-4 dni)
- Przeważnie lub cały czas (5-7 dni)

| Field | Label | Type | CSV header |
|---|---|---|---|
| `depr_1` | Przeszkadzały mi rzeczy… | choice | Podczas minionego tygodnia   [Przeszkadzały mi rzeczy, które zazwyczaj mi nie przeszkadzają] |
| `depr_2` | Nie miałem ochoty jeść… | choice | Podczas minionego tygodnia   [Nie miałem ochoty jeść; mój apetyt był słaby] |
| `depr_3` | Nie mogłem otrząsnąć się z chandry… | choice | Podczas minionego tygodnia   [Czułem, że nie mogę otrząsnąć się z chandry, nawet z pomocą rodziny lub przyjaciół] |
| `depr_4` | Czułem, że jestem tak samo dobry… | choice | Podczas minionego tygodnia   [Czułem, że jestem tak samo dobry jak inni ludzie] |
| `depr_5` | Ciężko mi się skoncentrować… | choice | Podczas minionego tygodnia   [Było mi ciężko skoncentrować się na tym co robię] |
| `depr_6` | Czułem się przygnębiony | choice | Podczas minionego tygodnia   [Czułem się przygnębiony] |
| `depr_7` | Cokolwiek robię, wymaga wysiłku | choice | Podczas minionego tygodnia   [Czułem, że cokolwiek robię, wymaga wysiłku] |
| `depr_8` | Optymistycznie patrzyłem w przyszłość | choice | Podczas minionego tygodnia   [Optymistycznie patrzyłem w przyszłość] |
| `depr_9` | Moje życie to porażka | choice | Podczas minionego tygodnia   [Miałem poczucie, że moje życie to porażka] |
| `depr_10` | Czułem strach | choice | Podczas minionego tygodnia   [Czułem strach] |
| `depr_11` | Mój sen był niespokojny | choice | Podczas minionego tygodnia   [Mój sen był niespokojny] |
| `depr_12` | Byłem szczęśliwy | choice | Podczas minionego tygodnia   [Byłem szczęśliwy] |
| `depr_13` | Mówiłem mniej niż zwykle | choice | Podczas minionego tygodnia   [Mówiłem mniej niż zwykle] |
| `depr_14` | Czułem się samotny | choice | Podczas minionego tygodnia   [Czułem się samotny] |
| `depr_15` | Ludzie byli nieprzyjaźni | choice | Podczas minionego tygodnia   [Ludzie byli nastawieni nieprzyjaźnie] |
| `depr_16` | Czerpałem radość z życia | choice | Podczas minionego tygodnia   [Czerpałem radość z życia] |
| `depr_17` | Miałem napady płaczu | choice | Podczas minionego tygodnia   [Miałem napady płaczu] |
| `depr_18` | Było mi smutno | choice | Podczas minionego tygodnia   [Było mi smutno] |
| `depr_19` | Ludzie mnie nie lubią | choice | Podczas minionego tygodnia   [Czułem, że ludzie mnie nie lubią] |
| `depr_20` | Nie mogłem się za nic zabrać | choice | Podczas minionego tygodnia   [Nie byłem w stanie się za nic zabrać] |

## Validation

The same rules apply when AI results are loaded and when a reviewer saves a survey:

| Type | Rule | Empty value |
|---|---|---|
| choice | Must match an allowed answer, ignoring case and surrounding whitespace. Other AI output is dropped; on save it is a validation error | `null` |
| number | Integer within the range (AI output: the first number in the text). Values outside the range are dropped from AI output; on save they are a validation error | `null` |
| text | Trimmed | `""` |

Empty fields are allowed. On save the server returns `422` with the invalid fields
unless the request is forced.

## CSV columns

The CSV has 71 columns: a timestamp (`Sygnatura czasowa`, format `M/D/YYYY HH:MM:SS`)
followed by the 70 fields. The column order differs from the page order:

1. Page 1 fields (17)
2. MFIS items 1-21 (21)
3. Health fields (4)
4. Athens Insomnia Scale (8)
5. CES-D (20)

The file is UTF-8 with BOM and uses `;` as the separator.
