from pydantic import SecretStr
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    app_password: str = "a"
    ollama_url: str = "http://localhost:11434"
    model_name: str = "deepseek-ocr"
    results_csv: str = "wyniki.csv"
    cache_file: str = "logs/cache_results.json"
    max_retries: int = 3
    timeout_sec: int = 120
    vlm_model: str = "deepseek-ocr"
    text_model: str = "llama3.1"
    ollama_num_parallel: int = 2
    log_file: str = "logs/ankieter.log"
    log_level: str = "DEBUG"

    # LangSmith (optional — reads LANGCHAIN_* env vars)
    langchain_tracing_v2: bool = False
    langchain_endpoint: str = ""
    langchain_api_key: SecretStr = SecretStr("")
    langchain_project: str = "ankieterai"

    model_config = {"env_prefix": "ANKIETER_"}


config = AppConfig()
