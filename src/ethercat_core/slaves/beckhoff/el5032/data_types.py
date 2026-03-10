"""Beckhoff EL5032 command/status data model placeholders."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class El5032Command:
    """Placeholder command model for Beckhoff EL5032."""


@dataclass(slots=True)
class El5032Status:
    """Placeholder status model for Beckhoff EL5032."""

