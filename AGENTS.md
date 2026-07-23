# ogólne wytyczne dot. kodu i flow pracy

1. trzymasz się planu i wytycznych zdefiniowanych w ./docs

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
- tworzysz commit z message z prefiksem chore|fix|feat|refactor: message in english
- message ma być krótki, zwięzły i konkretnie mówić co zostało zrobione w ramach tego commita
- przedstawiasz mi to do akceptacji i ewentualnego wprowadzenia zmian/przeiterowania
- jak jasno zaakceptuję zmiany to robisz git push

6. kiedy rozwiązujemy konkretne issue masz przygotować kompletne flow jego poprawy

- odczytanie błędu z ./docs/known-issues.md
- analiza błędu
- analiza kodu, który realizuje tę część funkcjonalności
- wskazanie kodu/logiki, która odpowiada za ten błąd
- przygotowanie szczegółowego planu poprawy
- czekasz na moją akceptację/wskazówki dot. planu
- po mojej akceptacji realizujesz poprawkę zgodnie z planem
- dajesz mi przestrzeń do testowania
- NIE zmieniasz niczego w known-issues.md, chyba że jasno i bezpośrednio o to poproszę

7. ogólnie w trakcie implementacji i wprowadzania poprawek starasz się trzymać najnowszych standardów react+vite+fastAPI

# ważne informacje

jeżeli musisz przetestować kawałek kodu to musisz korzystać z wirtualnego środowiska:

```ps1
.venv\Scripts\Activate.ps1
streamlit run src/app.py
```

jeżeli musisz testować modele ollama rób to z poziomu katalogu root aplikacji
