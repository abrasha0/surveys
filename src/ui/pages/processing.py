import asyncio
import streamlit as st
from state.state_manager import StateManager
from ai.client import AIClient, ProcessingStatus
from data_handler import save_cache
from ui.styles import inject_global_css

def render():
    inject_global_css()
    sm = StateManager()
    surveys = sm.get_surveys()
    if not surveys:
        st.error("Brak ankiet do przetworzenia")
        return

    progress_placeholder = st.empty()
    history_placeholder = st.empty()
    history = []  # przechowuje ostatnie komunikaty

    def update_progress(status: ProcessingStatus):
        pct = status.survey_idx / max(status.total_surveys, 1)
        with progress_placeholder.container():
            st.progress(pct, text=f"Ankieta {status.survey_idx+1} z {status.total_surveys}")

            if status.status == "survey_start":
                st.info(status.message)

            elif status.status == "vlm_extracting":
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;min-height:24px;font-size:0.9rem">'
                    f'<span class="mini-spinner"></span>'
                    f'<span>👁 {status.message}</span></div>',
                    unsafe_allow_html=True,
                )

            elif status.status == "vlm_retrying":
                st.warning(f"🔄 {status.message}")

            elif status.status == "text_formatting":
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;min-height:24px;font-size:0.9rem">'
                    f'<span class="mini-spinner" style="border-top-color:#1E88E5;"></span>'
                    f'<span>📝 {status.message}</span></div>',
                    unsafe_allow_html=True,
                )

            elif status.status == "text_retrying":
                st.warning(f"🔄 {status.message}")

            elif status.status == "fallback_activated":
                st.error(f"⚠️ {status.message}")

            elif status.status == "page_error":
                st.error(status.message)

            elif status.status == "survey_done":
                extra = status.extra or {}
                elapsed = extra.get("elapsed_s", "")
                pages = extra.get("pages", "")
                msg = status.message
                if elapsed:
                    msg += f" ({elapsed}s, {pages} stron)"
                st.success(msg)

            elif status.status == "batch_done":
                st.success(status.message)

        # Dodaj do historii tylko jeśli nowy i nie jest ostatnim
        if status.message not in history[-8:]:
            history.append(status.message)
        with history_placeholder.container():
            st.caption("Ostatnie kroki:")
            for line in history[-8:]:
                st.text(line)

    async def run_batch():
        client = AIClient()
        try:
            groups = [s.files for s in surveys]
            await client.analyze_batch(
                groups,
                progress_callback=update_progress,
                survey_done_callback=lambda idx, res: sm.set_ai_result(idx, res),
            )
            save_cache(sm.get_ai_results())
            sm.set_processing(False)
            st.rerun()
        except Exception as e:
            st.error(f"Błąd przetwarzania: {e}")
            sm.set_processing(False)
        finally:
            await client.close()

    asyncio.run(run_batch())