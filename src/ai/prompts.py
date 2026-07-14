from config import config


def build_vlm_prompt(page_idx: int) -> str:
    """Prompt dla modelu wizyjnego (VLM) — ekstrakcja surowego tekstu z obrazu."""
    return config.prompts["vlm"].format(page_idx=page_idx + 1)


def build_text_format_prompt(page_idx: int, raw_text: str) -> str:
    """Prompt dla modelu tekstowego — formatowanie surowego tekstu do JSON."""
    schema_key = f"page_{page_idx + 1}_json_schema"
    page_schema = config.prompts[schema_key]

    return config.prompts["text_format"].format(
        vlm_output=raw_text,
        page_json_schema=page_schema,
    )
