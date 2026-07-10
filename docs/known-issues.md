1. zmiana zakładki na lewym panelu (zdjęcia) powinna skutkować zmianą zakładki na analogiczną na prawym panelu
2. bardziej szczegółowe informowanie użytkownika co się dzieje w trakcie procesowania zdjęć - OK
3. A.D. 2 dodanie logów do debugowania: info co wpadło do modelu (które zdjęcie z którym promptem), czy model działa, jego bieżące zużycie zasobów, co model wypluł - OK
4. A.D. 3 logowanie tych informacji też do pliku - OK
5. usunięcie domyślnych wartości na formularzach, jeżeli model nic nie zwrócił to ma być po prostu puste pole, bez uzupełniania danych
6. zaznaczanie użytkownikowi w ui pustych/źle wypełnionych/niewypełnionych pól -> po jego interakcji oznaczenie konkretnego pola znika
7. zamiast sekcji A,B,C na podglądzie danych dla Strona 1 powinny być one analogicznie ponumerowane i ułożone jak na zdjęciu: kolumna 1: 1 (plec) - 7 (uczelnia); kolumna 2: 8 (czy pracujesz zawodowo w trakcie studiów) - 14 (czy pijesz napoje zawierające kofeinę)
8. mamy log 'Attempt 1/3 for page 1 failed after 6.78s: JSONDecodeError: Expecting value: line 1 column 1 (char 0)' - chcemy się lepiej dowiedzieć co się wyłożyło i dlaczego
9. monitorowanie issues z poziomu repozytorium i tego, czy zostały rozwiązane
10. najpierw progress bar powinien przedstawiać stan przeprocesowania, a kiedy użytkownik zaczyna procesować to powinien się resetować i przedstawiać jego progress
