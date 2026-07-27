"""Adapter registry.

New agencies are added by writing an adapter class and registering it here (or
its module) - core pipeline code never changes. Enable/disable per source in
config.yaml under ``sources:``.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Type

from ..config import Config
from .base import BaseAdapter, PoliteClient
from .property24 import Property24Adapter
from .generic import (
    PrivatePropertyAdapter,
    GumtreeAdapter,
    PamGoldingAdapter,
    Century21Adapter,
    SeeffAdapter,
    RemaxAdapter,
    RawsonAdapter,
)

# Registry keyed by the config/source name. Order defines run priority.
REGISTRY: Dict[str, Type[BaseAdapter]] = {
    "property24": Property24Adapter,
    "private_property": PrivatePropertyAdapter,
    "gumtree": GumtreeAdapter,
    "pamgolding": PamGoldingAdapter,
    "century21": Century21Adapter,
    "seeff": SeeffAdapter,
    "remax": RemaxAdapter,
    "rawson": RawsonAdapter,
}


def build_adapters(
    config: Config,
    only: Optional[List[str]] = None,
    client: Optional[PoliteClient] = None,
) -> List[BaseAdapter]:
    """Instantiate enabled adapters in priority order.

    ``only`` restricts to a subset of source names (used by the smoke test / CLI).
    A shared :class:`PoliteClient` keeps one rate-limit clock per domain across
    all adapters.
    """
    client = client or PoliteClient(config)
    if only:
        # An explicit subset (CLI --sources / smoke / demo) is authoritative and
        # may name sources not listed in config.
        enabled = [n for n in only if n in REGISTRY]
    else:
        enabled = config.enabled_sources() or list(REGISTRY.keys())

    adapters: List[BaseAdapter] = []
    seen = set()
    # Preserve registry priority order, then append any extras from `only`.
    for name in list(REGISTRY.keys()):
        if name in enabled and name not in seen:
            adapters.append(REGISTRY[name](config, client=client))
            seen.add(name)
    return adapters


def register(name: str, adapter_cls: Type[BaseAdapter]) -> None:
    """Public hook so plugins can add an adapter without editing this file."""
    REGISTRY[name] = adapter_cls
