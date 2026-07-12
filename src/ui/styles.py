import streamlit as st

_CSS_INJECTED = False

def _hide_toolbar_js():
    st.components.v1.html(
        """
<script>
(function() {
    var SELECTORS = [
        '[data-testid="stAppToolbar"]',
        '[data-testid="stToolbar"]',
        '[data-testid="stHeader"]',
        '.stAppHeader',
        '[data-testid="stDecoration"]',
        '[data-testid="stStatusWidget"]',
        '#MainMenu',
    ];

    function hideElements(root) {
        SELECTORS.forEach(function(sel) {
            root.querySelectorAll(sel).forEach(function(el) {
                el.remove();
            });
        });
    }

    function patchContainerLayout(root) {
        root.querySelectorAll(
            '[data-testid="stAppViewBlockContainer"], .block-container'
        ).forEach(function(el) {
            el.style.padding = '0';
            el.style.maxWidth = '100%';
            el.style.width = '100%';
        });
    }

    hideElements(document);
    patchContainerLayout(document);

    var observer = new MutationObserver(function(mutations) {
        for (var i = 0; i < mutations.length; i++) {
            var m = mutations[i];
            if (m.type === 'childList') {
                for (var j = 0; j < m.addedNodes.length; j++) {
                    var node = m.addedNodes[j];
                    if (node.nodeType !== 1) continue;
                    hideElements(node);
                    patchContainerLayout(node);
                }
            }
            if (m.type === 'attributes' && m.attributeName === 'style') {
                var el = m.target;
                if (el.matches('[data-testid="stAppViewBlockContainer"], .block-container')) {
                    el.style.padding = '0';
                    el.style.maxWidth = '100%';
                    el.style.width = '100%';
                }
            }
        }
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['style']
    });
})();
</script>
""",
        height=0,
    )


def inject_global_css():
    global _CSS_INJECTED
    if _CSS_INJECTED:
        return
    _hide_toolbar_js()
    st.markdown(
        """
<style>
    /* Ukryj pusty header Streamlit */
    header[data-testid="stHeader"],
    header.stAppHeader {
        display: none !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
    }

    /* Rozciągnięcie na całą szerokość */
    .stMainBlockContainer,
    [data-testid="stMainBlockContainer"],
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        width: 100% !important;
    }
    .stApp {
        overflow: hidden;
    }

    /* Spinner */
    .mini-spinner {
        display: inline-block;
        width: 14px;
        height: 14px;
        border: 2.5px solid rgba(49, 51, 63, 0.12);
        border-top-color: #ff4b4b;
        border-radius: 50%;
        animation: mini-spin 0.7s linear infinite;
        flex-shrink: 0;
    }
    @keyframes mini-spin {
        to { transform: rotate(360deg); }
    }

    /* Kropka błędu */
    .field-err-dot {
        width: 6px;
        height: 6px;
        background: #ff4b4b;
        border-radius: 50%;
        margin-top: 22px;
        margin-left: 2px;
        flex-shrink: 0;
    }

    /* Obrazek w kolumnie */
    .verify-col-image {
        height: calc(100vh - 150px);
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }
    .verify-col-image img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }

    /* Pola formularza */
    .stSelectbox, .stTextInput, .stNumberInput {
        margin-bottom: 0.2rem !important;
    }
    label {
        font-size: 0.8rem !important;
        margin-bottom: 0 !important;
    }

    /* Header z progressbarem */
    .header-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }
    .header-label {
        font-size: 0.85rem;
        white-space: nowrap;
    }
    .header-progress {
        flex: 0 1 200px;
        height: 6px;
        background: #e0e0e0;
        border-radius: 3px;
        overflow: hidden;
    }
    .header-progress-fill {
        height: 100%;
        background: #1E88E5;
        border-radius: 3px;
    }
</style>
""",
        unsafe_allow_html=True,
    )
    _CSS_INJECTED = True

def inject_verification_css():
    pass