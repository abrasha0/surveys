import streamlit as st
from pathlib import Path
from data_handler import export_csv_path
from state.state_manager import StateManager
from config import config

def render():
    st.balloons()
    st.success("Wszystkie ankiety przetworzone!")

    csv_path = Path(export_csv_path())
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            csv_content = f.read()
        st.download_button(
            "Pobierz CSV",
            data=csv_content,
            file_name=config.app["csv_results"],
            mime="text/csv",
        )
    if st.button("Nowa sesja"):
        StateManager.clear_session()
        st.rerun()