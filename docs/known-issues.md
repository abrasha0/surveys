# Known Issues — AnkieterAI

## Legenda

| Ikona        | Znaczenie                           |
| ------------ | ----------------------------------- |
| ✅ Done      | Zrealizowane, commit potwierdzający |
| 🔄 W trakcie | W realizacji lub częściowo zrobione |
| ❌ Otwarte   | Do zrobienia                        |

template

```markdown
| | | ❌ Otwarte | | |
```

---

| #   | Opis                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Status       | Priorytet | Commit / Uwagi                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ | --------- | ----------------------------------------------------------------------------------------------------- |
| 1   | **Próg re-OCR** jeżeli realnie przeczytano tylko X % odpowiedzi to trzeba dać jeszcze raz to samo zdjęcie do VLM                                                                                                                                                                                                                                                                                                                                                                                                   | ❌ Otwarte   | niski     |                                                                                                       |
| 2   | **lepsze ustrukturyzowanie aplikacji** w katalogu root powinny być główne katalogi: _docs_ - cała dokumentacja, _src_ - jedyne źródło kodu z podkatalogami _backend_ i _frontend_, _scripts_ - z kompletem skryptów do setupu i uruchomienia aplikacji, _working_vault_ - ze wszystkimi plikami związanymi z runtime: _dist_, _surveys_data_ (miejsce na zdjęcia ankiet do procesowania z plikiem _.processed.json_ ze spisem i statusami każdego zdjęcia), _logs_ (jedyne miejsce na logi z całej aplikacji) itd. | ✅ Done      | wysoki    | d91da6d refactor: restructure project directories — backend, frontend, working_vault                   |
| 3   | **szczegółowe przeanalizowanie flow aplikacji** - aktualnie od razu po zalogowaniu się do aplikacji widzę ekran completed, nowa sesja niczym nie skutkuje, a /api/surveys zwraca 200 i takie response [...]                                                                                                                                                                                                                                                                                                    | ✅ Done      | krytyczny | 4df504f feat: cutover to FastAPI+React, cleanup Streamlit code and tests (stage 10)                  |
| 4   | **automatyczne kopiowanie dist** albo używanie tego gotowego z katalogu src/frontend/dist, żeby nie musieć go kopiować ręcznie po każdej zmianie przed run_dev.ps1; to musi zostać zautomatyzowane                                                                                                                                                                                                                                                                                                                 | ✅ Done      |           | d91da6d — full_setup.ps1 kopiuje do working_vault/dist/, run_dev.ps1 używa Vite dev servera z proxy  |
