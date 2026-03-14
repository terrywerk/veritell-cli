"""Scoring primitives for the Veritell CLI scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Score:
    """A minimal score container for future evaluation logic."""

    value: float
    reason: str = ""

