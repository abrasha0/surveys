from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    app_password: str = "a"
    ollama_url: str = "http://localhost:11434"
    model_name: str = "deepseek-ocr"
    results_csv: str = "wyniki.csv"
    cache_file: str = "logs/cache_results.json"
    max_retries: int = 3
    timeout_sec: int = 120

    model_config = {"env_prefix": "ANKIETER_"}


config = AppConfig()
