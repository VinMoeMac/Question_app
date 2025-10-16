"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the application."""

    csv_path: Path
    default_page_size: int = 100
    max_page_size: int = 500
    app_title: str = "BLISS: Internet-scale Questions Dataset"

    @property
    def csv_display_name(self) -> str:
        """Return a shortened path that is safe to display in the UI."""

        try:
            return self.csv_path.name
        except Exception:
            return str(self.csv_path)


def _parse_int(env_name: str, default: int) -> int:
    """Parse an integer from the environment with a sane fallback."""

    raw_value = os.getenv(env_name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Environment variable {env_name} must be an integer") from exc

    return value


def _load_settings() -> Settings:
    csv_env = os.getenv("CSV_PATH", "data/sample_questions.csv")
    csv_path = Path(csv_env).expanduser().resolve()

    if not csv_path.exists():
        raise FileNotFoundError(
            "CSV file not found. Set the CSV_PATH environment variable to a valid file."
        )

    default_page_size = _parse_int("DEFAULT_PAGE_SIZE", 100)
    max_page_size = _parse_int("MAX_PAGE_SIZE", 500)

    if default_page_size < 1:
        default_page_size = 1
    if max_page_size < 1:
        max_page_size = 1
    if default_page_size > max_page_size:
        default_page_size = max_page_size

    return Settings(
        csv_path=csv_path,
        default_page_size=default_page_size,
        max_page_size=max_page_size,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return _load_settings()
