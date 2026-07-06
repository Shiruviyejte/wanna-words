from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    app_name: str = "wanna-thesaurus"
    api_prefix: str = "/wanna"
    database_url: str = "postgresql+asyncpg://postgres:123456@localhost:5432/wanna-word"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    cors_origin_regex: str = r"^https?://((localhost|127\.0\.0\.1)|(\d{1,3}\.){3}\d{1,3})(:\d+)?$"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    chat_mock_mode: bool = False
    app_secret_key: str = "change-this-secret-key-for-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    file_manager_root: str = "word"
    file_manager_text_max_size: int = 2 * 1024 * 1024
    whitelist_paths: list[str] = [
        "/api/v1/wordbooks/tree",
        "/api/v1/words/by-book",
        "/api/v1/article-books/tree",
        "/api/v1/articles/by-book",
        "/api/v1/users/password",
        "/api/v1/users/profile",
        "/api/v1/auth/me",
    ]
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
settings = Settings()
