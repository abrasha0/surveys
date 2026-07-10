# Known Issues — AnkieterAI

## Legenda

| Ikona        | Znaczenie                           |
| ------------ | ----------------------------------- |
| ✅ Done      | Zrealizowane, commit potwierdzający |
| 🔄 W trakcie | W realizacji lub częściowo zrobione |
| ❌ Otwarte   | Do zrobienia                        |

---

## Lista

| #   | Opis                                                                                                                                                    | Status     | Priorytet | Commit / Uwagi                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------- | ----------------------------------------------------------------------------- |
| 1   | Zmiana zakładki na lewym panelu (zdjęcia) powinna skutkować zmianą zakładki na analogiczną na prawym panelu                                             | ✅ Done    | wysoki    | `b983001` — pojedyncza grupa tabów                                            |
| 2   | Bardziej szczegółowe informowanie użytkownika co się dzieje w trakcie procesowania zdjęć                                                                | ✅ Done    | średni    | `0807eed` — progress callback w UI                                            |
| 3   | Dodanie logów debugowania: info co wpadło do modelu (zdjęcie + prompt), stan modelu, zużycie zasobów, output modelu                                     | ✅ Done    | wysoki    | `0807eed`                                                                     |
| 3.1 | Uzupełnienie logowania — dokładniejsze dane o surowych odpowiedziach modelu, timestampowanie, context requestu                                          | ❌ Otwarte | średni    | Wymaga rozszerzenia `logger.py` o wpisy per-request                           |
| 4   | Logowanie informacji z pkt 3 do pliku                                                                                                                   | ✅ Done    | wysoki    | `a6db2ea` — `logger.py` z handlerem plikowym (`logs/ankieter.log`)            |
| 5   | Usunięcie domyślnych wartości na formularzach — jeżeli model nic nie zwrócił, pole ma być puste                                                         | ✅ Done    | wysoki    | `_normalize_value()` zwraca `None` zamiast `choices[0]`, pola modelu `Optional` |
| 6   | Zaznaczanie w UI pustych/źle wypełnionych pól; oznaczenie znika po interakcji użytkownika z polem                                                       | ✅ Done    | wysoki    | Czerwona kropka w `_render_single_field()`, `on_change` resetuje stan touched  |
| 7   | Strona 1 na podglądzie: zamiast sekcji A,B,C — pola ponumerowane 1-14, ułożone w 2 kolumny jak na papierze                                              | ✅ Done    | wysoki    | `72aac8e` — layout kolumnowy 1:7 / 8:14                                       |
| 8   | Lepsze komunikaty błędów przy `JSONDecodeError` — chcemy wiedzieć co się wyłożyło i dlaczego (treść odpowiedzi, status HTTP, fragment surowego outputu) | ❌ Otwarte | średni    | Do implementacji w `ai_client.py` — rozszerzenie loggingu błędów              |
| 9   | Monitorowanie issues z poziomu repozytorium — śledzenie czy dany problem został rozwiązany                                                              | ❌ Otwarte | niski     | Wymaga procesu: tagi w commitach + sekcja w README lub dedykowany plik        |
| 10  | Progress bar: najpierw ma pokazywać stan przeprocesowania, a po kliknięciu "Rozpocznij analizę" resetować się i pokazywać aktualny progress batcha      | ❌ Otwarte | średni    | Do implementacji w `ui_components.py` / `main.py` — reset stanu progress bara |
