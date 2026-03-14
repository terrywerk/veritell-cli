"""Compatibility shim for the canonical Veritell test case model."""

from __future__ import annotations

from .models import VeritellTestCase


class TestCase(VeritellTestCase):
    """Backward-compatible import path for the canonical test case model."""

    __test__ = False

