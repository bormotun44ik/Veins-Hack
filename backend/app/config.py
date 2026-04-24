from pathlib import Path

from pydantic_settings import BaseSettings

# Repo root = 2 levels up from backend/app/config.py
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    database_path: str = str(REPO_ROOT / "db" / "veins.db")
    data_dir: str = str(REPO_ROOT / "data")
    github_token: str = ""
    github_repo: str = "bormotun44ik/veeins-test"
    shadoclaw_base_url: str = "http://127.0.0.1:8317/v1"
    shadoclaw_api_key: str = "sk-dummy"
    use_fake_github: bool = False
    log_level: str = "INFO"
    groq_api_key_1: str = ""
    groq_api_key_2: str = ""
    groq_api_key_3: str = ""
    groq_api_key_4: str = ""
    groq_api_key_5: str = ""

    @property
    def groq_keys(self) -> list[str]:
        return [k for k in [self.groq_api_key_1, self.groq_api_key_2, self.groq_api_key_3,
                             self.groq_api_key_4, self.groq_api_key_5] if k]

    def groq_client(self):
        import itertools
        from groq import Groq
        keys = self.groq_keys
        if not keys:
            raise RuntimeError("No Groq API keys configured")
        if not hasattr(self, '_groq_cycle'):
            self._groq_cycle = itertools.cycle(keys)
        return Groq(api_key=next(self._groq_cycle))

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
