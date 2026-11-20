from config import config


def build_vlm_prompt(page_idx: int) -> str:
    """Build the VLM prompt that extracts raw text from a page image."""
    return config.prompts["vlm"].format(page_idx=page_idx + 1)


def build_text_format_prompt(page_idx: int, raw_text: str) -> str:
    """Build the text-model prompt that turns raw page text into JSON."""
    schema_key = f"page_{page_idx + 1}_json_schema"
    page_schema = config.prompts[schema_key]

    return config.prompts["text_format"].format(
        vlm_output=raw_text,
        page_json_schema=page_schema,
    )
