import streamlit as st
from domain.field_specs import FieldSpec

def _get_index(value, choices):
    if value is None:
        return 0
    try:
        return choices.index(value)
    except ValueError:
        return 0

def render_field(field_spec: FieldSpec, prefix: str, show_errors: bool = False):
    key = f"{prefix}_{field_spec.name}"
    current_value = st.session_state.get(key, field_spec.default)

    error = False
    if field_spec.kind == "select":
        if current_value is None or current_value not in field_spec.choices:
            error = True
    elif field_spec.kind == "text":
        if current_value is None or str(current_value).strip() == "":
            error = True
    elif field_spec.kind == "number":
        if current_value is None:
            error = True

    col1, col2 = st.columns([0.04, 0.96])
    with col1:
        if show_errors and error:
            st.markdown('<div class="field-err-dot"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="opacity:0;">.</div>', unsafe_allow_html=True)

    with col2:
        if field_spec.kind == "select":
            idx = _get_index(current_value, field_spec.choices)
            st.selectbox(field_spec.label, field_spec.choices, index=idx, key=key)
        elif field_spec.kind == "text":
            st.text_input(field_spec.label, value=current_value or "", key=key)
        elif field_spec.kind == "number":
            min_val = field_spec.min or 0
            max_val = field_spec.max or 100
            st.number_input(
                field_spec.label,
                min_value=min_val,
                max_value=max_val,
                value=current_value if current_value is not None else None,
                key=key,
                placeholder="Wpisz wiek"
            )