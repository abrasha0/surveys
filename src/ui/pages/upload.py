import streamlit as st
from ingestion.file_grouping import group_files_by_survey
from domain.schemas import SurveyGroup
from config import config

def render():
    st.title("Wgrywanie ankiet")
    files = st.file_uploader(
        "Wybierz zdjęcia (jpg/png/webp)",
        accept_multiple_files=True,
        type=config.app["accepted_file_types"],
    )
    if not files:
        return None, False

    # Grupowanie – zwraca listę grup (każda to lista ścieżek) oraz ostrzeżenia
    raw_groups, warnings = group_files_by_survey(files)
    
    # Konwersja na SurveyGroup
    groups = [SurveyGroup(id=i, files=group) for i, group in enumerate(raw_groups)]

    st.subheader("Podgląd grupowania")
    for g in groups:
        names = [p.name for p in g.files]
        st.write(f"**Grupa {g.id+1}** ({len(g.files)} plików): {', '.join(names)}")
    if warnings:
        for w in warnings:
            st.warning(w)

    start_clicked = st.button("Rozpocznij analizę", type="primary")
    if start_clicked:
        return groups, True
    return None, False