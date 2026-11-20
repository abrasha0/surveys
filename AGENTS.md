# ogólne wytyczne dot. kodu i flow pracy

1. trzymasz się wytycznych z README.md i dokumentacji w ./docs (architecture.md, survey-structure.md)

2. kiedy mówię o rozpoczęciu pracy nad kolejną fazą mam na myśli takie flow:

- przeanalizuj aktualny stan codebase
- przeanalizuj wytyczne i plan pod fazę X
- przejdź w tryb /plan i przygotuj plan implementacji fazy X
- poczekaj na moje zapoznanie się z planem, po mojej jasnej akceptacji implementujesz zgodnie z planem
- jeżeli w trakcie implementacji zaszły zmiany względem pierwotnych założeń trzeba uzupełnić je zgodnie z realizacją (jasno wskazujesz co się dzieje)
- po zakończonej implementacji nie testujesz i nie uruchamiasz niczego samemu: mowisz ze skonczyles i ja sam to testuje (jeżeli coś wymaga odpalenia skryptu, jakiegoś kroku wcześniej to jasno o nim informujesz na zakończeniu)

3. kiedy coś jest poprawiane abstrachując od implementacji wytycznych step-by-step - jeżeli w trakcie implementacji zaszły zmiany względem pierwotnych założeń trzeba uzupełnić je zgodnie z realizacją (jasno wskazujesz co się dzieje)

4. po zakończonym zestawie kroków implementacyjnych chcemy uzupełnić readme - zależnie od tego co zostało zrealizowane. nie chcemy wspominać o każdym poprawionym błędzie. to ma być bardziej know-how dot. aplikacji: sekcja co to jest i po co to jest, sekcja z wypisanymi funkcjonalnościami, sekcja how-to-start-it. więc jeżeli coś zmieni się na tych płaszczyznach, zostanie uzupełnione, zaimplementowane, usunięte - readme powinno to uwzględniać.

5. kiedy mowie cos w stylu "zapisz zmiany w repozytorium/wrzuć do gita/zapisujemy zmiany/checkpoint" masz przygotować pełne flow wrzucenia czytelnego commita do repozytorium
   wytyczne przygotowania zmian do wbicia:

- przeglądasz i analizujesz zmiany (muszą nadawać się do wbicia i coś znaczyć)
- tworzysz commit z message z prefiksem feat|fix|refactor|docs|chore: message in english
- message ma być krótki, zwięzły i konkretnie mówić co zostało zrobione w ramach tego commita
- przedstawiasz mi to do akceptacji i ewentualnego wprowadzenia zmian/przeiterowania
- jak jasno zaakceptuję zmiany to robisz git push

6. kiedy rozwiązujemy konkretne issue masz przygotować kompletne flow jego poprawy

- odczytanie opisu błędu (issue albo mój opis)
- analiza błędu
- analiza kodu, który realizuje tę część funkcjonalności
- wskazanie kodu/logiki, która odpowiada za ten błąd
- przygotowanie szczegółowego planu poprawy
- czekasz na moją akceptację/wskazówki dot. planu
- po mojej akceptacji realizujesz poprawkę zgodnie z planem
- dajesz mi przestrzeń do testowania

7. ogólnie w trakcie implementacji i wprowadzania poprawek starasz się trzymać najnowszych standardów react+vite+fastAPI

# ważne informacje

stack: backend FastAPI (`src/backend`), frontend React + Vite + TypeScript (`src/frontend`), modele AI przez Ollamę. konfiguracja w `config.yaml` w katalogu głównym (kopia jednego z profili z `configs/`, `app.password` musi być ustawione).

środowisko przygotowuje `.\scripts\full_setup.ps1` (Windows) albo `scripts/full_setup.sh` (macOS, Linux), całość w trybie deweloperskim uruchamia `.\scripts\run_dev.ps1` albo `scripts/run_dev.sh`. skrypty `.ps1` i `.sh` robią te same kroki, więc zmiana w jednym wymaga takiej samej zmiany w drugim.

jeżeli musisz przetestować kawałek kodu backendu to musisz korzystać z wirtualnego środowiska:

```ps1
.venv\Scripts\Activate.ps1
cd src\backend
python -m uvicorn main:app --reload --port 8000
```

na macOS i Linuksie:

```bash
source .venv/bin/activate
cd src/backend
python -m uvicorn main:app --reload --port 8000
```

jeżeli musisz sprawdzić zmiany we frontendzie, używasz lintu i builda:

```ps1
cd src\frontend
npm run lint
npm run build
```

jeżeli musisz testować modele ollama rób to z poziomu katalogu root aplikacji
