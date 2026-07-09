# AnkieterAI

Automatyczny system wprowadzania ankiet papierowych do formy cyfrowej z wykorzystaniem lokalnego modelu wizyjno-językowego (VLM).

## Funkcjonalności

- Logowanie hasłem do aplikacji
- Upload zdjęć ankiet (jpg/png/webp)
- Automatyczna analiza obrazów przez VLM (Ollama + llava-llama3)
- Batch processing z progress barem i cache'owaniem wyników
- Weryfikacja i korekta odczytanych danych w interfejsie side-by-side
- Podgląd zdjęć z zoomem (zakładki dla każdej strony)
- Formularz z dynamicznym zaznaczaniem pól o niskiej pewności odczytu
- Skrót klawiszowy Spacja do szybkiego zatwierdzania
- Eksport wyników do CSV (UTF-8 BOM, gotowy do Excela)
- Zapis do cache (wznawianie sesji po przerwie)

## Uruchomienie

1. Przygotowanie środowiska:
   ```powershell
   .\scripts\setup_env.ps1
   ```

2. Uruchomienie Ollamy:
   ```powershell
   .\scripts\setup_ollama.ps1
   ```

3. Start aplikacji:
   ```powershell
   .venv\Scripts\Activate.ps1
   streamlit run src/main.py
   ```

Aplikacja dostępna pod `http://localhost:8501`. Domyślne hasło: `ankieter2026`.