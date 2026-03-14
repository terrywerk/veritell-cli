"""Diagnostics primitives for the Veritell CLI scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Diagnostic:
    """A lightweight diagnostic record produced during a run."""

    message: str
    severity: str = "info"

