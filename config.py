"""Centralized configuration settings for local Ollama server, models, workspace, and database paths."""

import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Local Ollama Server Settings
    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    primary_model: str = Field(
        default_factory=lambda: os.getenv("PRIMARY_MODEL", "qwen2.5-coder:14b")
    )
    fallback_models: List[str] = Field(
        default_factory=lambda: ["qwen2.5-coder:7b", "gemma2"]
    )
    temperature: float = Field(default=0.2)
    timeout_seconds: float = Field(default=60.0)

    # Workspace Settings
    workspace_path: Path = Field(
        default_factory=lambda: Path(
            os.getenv("WORKSPACE_PATH", r"d:\learning\school_projects\my_neo-agent")
        ).resolve()
    )

    # Database & Storage Settings
    data_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv("DATA_DIR", r"d:\learning\school_projects\my_neo-agent\data")
        ).resolve()
    )
    checkpoint_db_path: Path = Field(
        default_factory=lambda: Path(
            os.getenv(
                "CHECKPOINT_DB_PATH",
                r"d:\learning\school_projects\my_neo-agent\data\checkpoints.db",
            )
        ).resolve()
    )
    chat_history_db_path: Path = Field(
        default_factory=lambda: Path(
            os.getenv(
                "CHAT_HISTORY_DB_PATH",
                r"d:\learning\school_projects\my_neo-agent\data\chat_history.db",
            )
        ).resolve()
    )

    # Self-Correction & Agent Control Settings
    max_retries: int = Field(default=3)
    require_permission_tools: List[str] = Field(
        default_factory=lambda: [
            "execute_command",
            "run_command",
            "write_to_file",
            "delete_file",
            "modify_file",
        ]
    )

    def ensure_directories(self) -> None:
        """Ensure all required workspace and data directories exist."""
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.chat_history_db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def model_chain(self) -> List[str]:
        """Returns ordered list of models starting with primary followed by fallbacks."""
        chain = [self.primary_model]
        for model in self.fallback_models:
            if model not in chain:
                chain.append(model)
        return chain


# Global configuration instance
settings = Settings()
settings.ensure_directories()
