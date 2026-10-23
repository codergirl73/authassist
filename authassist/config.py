"""Environment and YAML config loading."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is not None:
        value = value.split("#")[0].strip() or default
    return value


def env_bool(name: str, default: bool = False) -> bool:
    return (env(name, str(default)) or "").lower() in {"1", "true", "yes", "on"}


NEBIUS_BASE_URL = env("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
DEMO_MODE = env_bool("DEMO_MODE", True)
APP_ENV = env("APP_ENV", "dev")
CACHE_DIR = ROOT / (env("CACHE_DIR", ".cache") or ".cache")
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"


def nebius_api_key() -> str:
    key = env("NEBIUS_API_KEY")
    if not key:
        raise RuntimeError("NEBIUS_API_KEY is not set (see .env.example)")
    return key


def tavily_api_key() -> str:
    key = env("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set (see .env.example)")
    return key


@lru_cache
def models_config() -> dict:
    return yaml.safe_load((CONFIG_DIR / "models.yaml").read_text())


@lru_cache
def procedure_config(name: str = "lumbar_mri") -> dict:
    return yaml.safe_load((CONFIG_DIR / "procedures" / f"{name}.yaml").read_text())
