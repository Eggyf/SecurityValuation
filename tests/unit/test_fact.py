"""Tests de :mod:`dcf_app.models.fact`."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError as PydanticValidationError

from dcf_app.models.fact import Confidence, Fact, Scale, SourceKind, SourceRef


def _source(
    kind: SourceKind = SourceKind.IXBRL,
    concept: str | None = "us-gaap:Revenues",
    location: str | None = None,
) -> SourceRef:
    return SourceRef(kind=kind, concept=concept, location=location)


def _fact(
    value: float | None = 100.0,
    unit: str = "USD",
    scale: Scale = Scale.MILLIONS,
    source: SourceRef | None = None,
) -> Fact:
    return Fact(
        value=value,
        unit=unit,
        scale=scale,
        period_end=date(2024, 12, 31),
        source=source if source is not None else _source(),
    )


def test_scale_exponents() -> None:
    assert Scale.UNITS.exponent == 0
    assert Scale.THOUSANDS.exponent == 3
    assert Scale.MILLIONS.exponent == 6
    assert Scale.BILLIONS.exponent == 9


def test_scale_from_exponent_round_trip() -> None:
    for scale in Scale:
        assert Scale.from_exponent(scale.exponent) is scale


def test_scale_from_exponent_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="no soportado"):
        Scale.from_exponent(4)


def test_to_scale_thousands_to_millions() -> None:
    # 1.500 miles = 1,5 millones.
    fact = _fact(value=1500.0, scale=Scale.THOUSANDS)
    assert fact.to_scale(Scale.MILLIONS) == pytest.approx(1.5)


def test_to_scale_millions_to_units() -> None:
    # 2,5 millones = 2.500.000 unidades.
    fact = _fact(value=2.5)
    assert fact.to_scale(Scale.UNITS) == pytest.approx(2_500_000.0)


def test_to_scale_same_scale_is_identity() -> None:
    fact = _fact(value=123.45)
    assert fact.to_scale(Scale.MILLIONS) == pytest.approx(123.45)


def test_to_scale_with_missing_value_returns_none() -> None:
    assert _fact(value=None).to_scale(Scale.MILLIONS) is None


def test_confidence_derived_from_source_kind() -> None:
    assert _fact().confidence is Confidence.HIGH
    extension = _fact(source=_source(SourceKind.IXBRL_EXTENSION, concept="company:Metrica"))
    assert extension.confidence is Confidence.MEDIUM
    text = _fact(source=_source(SourceKind.TEXT_FALLBACK, concept=None, location="Item 8, p. 57"))
    assert text.confidence is Confidence.LOW


def test_ixbrl_source_without_concept_is_rejected() -> None:
    # Trazabilidad (AGENTS.md §9): una cifra sin fuente debe romper el modelo.
    with pytest.raises(PydanticValidationError):
        _source(concept=None)


def test_text_fallback_without_location_is_rejected() -> None:
    with pytest.raises(PydanticValidationError):
        SourceRef(kind=SourceKind.TEXT_FALLBACK)


def test_user_input_source_needs_nothing_else() -> None:
    source = SourceRef(kind=SourceKind.USER_INPUT)
    assert source.describe() == "Introducido por el usuario"


def test_describe_includes_concept() -> None:
    assert "us-gaap:Revenues" in _source().describe()


def test_period_must_be_ordered() -> None:
    with pytest.raises(PydanticValidationError):
        Fact(
            value=1.0,
            unit="USD",
            scale=Scale.MILLIONS,
            period_start=date(2024, 12, 31),
            period_end=date(2024, 1, 1),
            source=_source(),
        )


def test_json_round_trip() -> None:
    fact = _fact(value=1000.0)
    rebuilt = Fact.model_validate_json(fact.model_dump_json())
    assert rebuilt.model_dump() == fact.model_dump()
