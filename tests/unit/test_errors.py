"""Jerarquía de las excepciones de dominio (AGENTS.md §8)."""

from __future__ import annotations

import pytest

from dcf_app.errors import DCFError, ExtractionError, ValidationError, ValuationError


def test_base_error_is_an_exception() -> None:
    assert issubclass(DCFError, Exception)


@pytest.mark.parametrize("error_type", [ExtractionError, ValidationError, ValuationError])
def test_domain_errors_inherit_from_base(error_type: type[DCFError]) -> None:
    assert issubclass(error_type, DCFError)


def test_message_is_exposed_verbatim() -> None:
    message = "El balance no cuadra: activo 1.000,00 vs. pasivo + patrimonio 999,50"
    assert str(ValuationError(message)) == message
