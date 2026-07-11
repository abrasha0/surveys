from domain.field_specs import PAGE_MAP

def build_system_prompt(page_idx: int) -> str:
    fields = PAGE_MAP.get(page_idx, [])
    lines = [f"=== Strona {page_idx+1} ==="]

    # Dodajemy krótki opis strony (opcjonalnie, dla lepszego kontekstu)
    if page_idx == 0:
        lines.append("Otrzymasz zdjęcie pierwszej strony ankiety – dane demograficzne, praca, styl życia.")
    elif page_idx == 1:
        lines.append("Otrzymasz zdjęcie drugiej strony – skala CES-D (odczucia w minionym tygodniu).")
    elif page_idx == 2:
        lines.append("Otrzymasz zdjęcie trzeciej strony – Ateńska skala bezsenności.")
    elif page_idx == 3:
        lines.append("Otrzymasz zdjęcie czwartej strony – MFIS (część 1, pozycje 1-15).")
    elif page_idx == 4:
        lines.append("Otrzymasz zdjęcie piątej strony – MFIS (część 2, pozycje 16-21) oraz pytania o zdrowie.")

    lines.append("Zwróć WYŁĄCZNIE JSON z następującymi polami:")
    for f in fields:
        if f.kind == "select":
            lines.append(f"  - {f.name}: jedna z wartości: {', '.join(f.choices)}")
        elif f.kind == "text":
            lines.append(f"  - {f.name}: tekst")
        elif f.kind == "number":
            lines.append(f"  - {f.name}: liczba (np. 23)")
    lines.append("  - needs_review: dict[str, bool] — true jeśli nie jesteś pewien odczytu")
    lines.append("Odpowiedz wyłącznie w formacie JSON.")
    return "\n".join(lines)