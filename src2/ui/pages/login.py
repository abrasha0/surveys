import streamlit as st
from state.state_manager import StateManager

def render():
    st.title("AnkieterAI")
    st.markdown("Zautomatyzowany system wprowadzania ankiet papierowych")
    password = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        sm = StateManager()
        if sm.set_authenticated(password):
            st.rerun()
        else:
            st.error("Nieprawidłowe hasło")