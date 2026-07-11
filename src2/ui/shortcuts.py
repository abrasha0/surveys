import streamlit as st

def inject_space_shortcut():
    st.components.v1.html(
        """
        <script>
        document.addEventListener('keydown', function(e) {
            if (e.key === ' ' && e.target === document.body) {
                e.preventDefault();
                var btn = document.querySelector('button[data-testid="baseButton-primary"]');
                if (btn) btn.click();
            }
        });
        </script>
        """,
        height=0,
    )