"""Configuration loading for Property Scout.

A single ``config.yaml`` at the project root drives everything. Missing keys
fall back to documented defaults so a partial config still runs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


DEFAULTS: Dict[str, Any] = {
    "contact_email": "ops@example.com",
    "default_max_rent": 12000,
    "default_min_size_sqm": 25,
    "max_listing_age_days": 60,
    "exclude_inferred_age_over_limit": True,
    "include_unknown_age_in_separate_section": True,
    "recheck_previously_exported_listings": True,
    "request_delay_seconds": 2,
    "cache_ttl_hours": 24,
    "database_path": "property_scout.db",
    "cache_dir": ".cache",
    "export_dir": "exports",
    "log_dir": "logs",
    "sources": {},
    "saved_areas": [],
}


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass
class Config:
    contact_email: str
    default_max_rent: int
    default_min_size_sqm: int
    max_listing_age_days: int
    exclude_inferred_age_over_limit: bool
    include_unknown_age_in_separate_section: bool
    recheck_previously_exported_listings: bool
    request_delay_seconds: float
    cache_ttl_hours: int
    database_path: str
    cache_dir: str
    export_dir: str
    log_dir: str
    sources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    saved_areas: List[str] = field(default_factory=list)
    root: Path = field(default_factory=_project_root)

    # --- absolute-path helpers -------------------------------------------
    def _abs(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else (self.root / p)

    @property
    def db_path(self) -> Path:
        return self._abs(self.database_path)

    @property
    def cache_path(self) -> Path:
        p = self._abs(self.cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def export_path(self) -> Path:
        p = self._abs(self.export_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def log_path(self) -> Path:
        p = self._abs(self.log_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def user_agent(self) -> str:
        """Descriptive, honest UA identifying the tool + a contact address."""
        return (
            "PropertyScout/1.0 (internal rental-sourcing tool; "
            f"+{self.contact_email})"
        )

    def enabled_sources(self) -> List[str]:
        return [name for name, cfg in self.sources.items() if cfg and cfg.get("enabled", True)]


def load_config(path: str | os.PathLike | None = None) -> Config:
    """Load ``config.yaml`` (or a given path), applying defaults for gaps."""
    if path is None:
        path = _project_root() / "config.yaml"
    path = Path(path)

    data: Dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    merged = {**DEFAULTS, **data}
    known = set(Config.__dataclass_fields__.keys()) - {"root"}
    kwargs = {k: merged[k] for k in known if k in merged}
    cfg = Config(**kwargs)
    cfg.root = _project_root()
    return cfg
