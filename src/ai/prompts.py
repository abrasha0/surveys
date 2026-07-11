from domain.field_specs import PAGE_MAP, PAGE_DESCRIPTIONS


def build_system_prompt(page_idx: int) -> str:
    fields = PAGE_MAP.get(page_idx, [])
    lines = [f"=== Strona {page_idx+1} ==="]

    description = PAGE_DESCRIPTIONS.get(page_idx, "")
    if description:
        lines.append(description)

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
