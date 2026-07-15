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

    hideElements(document);
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
    st.html(
        """
        <style id="verification-fullheight">
            [data-testid="stMain"] {
                height: 100vh !important;
                overflow: hidden !important;
            }

            [data-testid="stMainBlockContainer"] {
                display: flex !important;
                flex-direction: column !important;
                height: 100vh !important;
                padding-top: 0.5rem !important;
                padding-bottom: 0.5rem !important;
                overflow: hidden !important;
            }

            [data-testid="stMainBlockContainer"]
                [data-testid="stVerticalBlock"]:has([data-testid="stHorizontalBlock"]:has(.verify-col-image)) {
                display: flex !important;
                flex-direction: column !important;
                flex: 1 1 auto !important;
                min-height: 0 !important;
            }

            [data-testid="stMainBlockContainer"]
                [data-testid="stLayoutWrapper"]:has([data-testid="stHorizontalBlock"]:has(.verify-col-image)) {
                display: flex !important;
                flex-direction: column !important;
                flex: 1 1 auto !important;
                min-height: 0 !important;
            }

            [data-testid="stHorizontalBlock"]:has(.verify-col-image) {
                flex: 1 1 0% !important;
                min-height: 0 !important;
            }

            [data-testid="stHorizontalBlock"]:has(.verify-col-image)
                [data-testid="stColumn"]:has(.verify-col-image),
            [data-testid="stHorizontalBlock"]:has(.verify-col-image)
                [data-testid="stColumn"]:has(.verify-col-image) * {
                height: 100% !important;
                min-height: 0 !important;
            }

            .verify-col-image {
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                overflow: hidden !important;
            }

            .verify-col-image img {
                max-width: 100% !important;
                max-height: 100% !important;
                object-fit: contain !important;
            }
        </style>
        """,
    )

def _inject_image_scaling_js():
    """Wymusza layout obrazka przez inline !important na realnych węzłach DOM —
    omija niewidzialny dla nas CSS-in-JS Streamlita (Emotion), zamiast z nim
    konkurować przez zewnętrzny <style>."""
    st.components.v1.html(
        """
        <script>
        (function() {
            function force(el, styles) {
                if (!el) return;
                for (var prop in styles) {
                    el.style.setProperty(prop, styles[prop], 'important');
                }
            }

            function applyFix() {
                var doc = window.parent.document;
                var img = doc.querySelector('.verify-col-image');
                if (!img) return;

                var stColumn = img.closest('[data-testid="stColumn"]');
                var stHorizontalBlock = stColumn ? stColumn.closest('[data-testid="stHorizontalBlock"]') : null;
                var stLayoutWrapper = stHorizontalBlock ? stHorizontalBlock.parentElement : null;
                var rootVerticalBlock = stLayoutWrapper ? stLayoutWrapper.parentElement : null;
                var mainBlockContainer = doc.querySelector('[data-testid="stMainBlockContainer"]');
                var stMain = doc.querySelector('[data-testid="stMain"]');

                force(stMain, { height: '100vh', overflow: 'hidden' });
                force(mainBlockContainer, {
                    display: 'flex', 'flex-direction': 'column', height: '100vh', overflow: 'hidden'
                });
                force(rootVerticalBlock, {
                    display: 'flex', 'flex-direction': 'column', flex: '1 1 auto', 'min-height': '0'
                });
                force(stLayoutWrapper, {
                    display: 'flex', 'flex-direction': 'column', flex: '1 1 auto', 'min-height': '0'
                });
                force(stHorizontalBlock, { flex: '1 1 0%', 'min-height': '0' });
                force(stColumn, { height: '100%', 'min-height': '0' });

                if (stColumn) {
                    stColumn.querySelectorAll('*').forEach(function(el) {
                        force(el, { height: '100%' });
                    });
                }
            }

            var resizeTimer;
            window.addEventListener('resize', function() {
                clearTimeout(resizeTimer);
                resizeTimer = setTimeout(applyFix, 150);
            });

            var observer = new MutationObserver(function() {
                applyFix();
            });
            observer.observe(window.parent.document.body, { childList: true, subtree: true });

            applyFix();
            setTimeout(applyFix, 300);
        })();
        </script>
        """,
        height=0,
    )