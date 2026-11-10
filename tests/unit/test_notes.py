"""Tests de :mod:`dcf_app.models.notes`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from dcf_app.models.notes import NonRecurringItem, SupplementaryNotes


def test_defaults_are_empty_and_none() -> None:
    notes = SupplementaryNotes()
    assert notes.dilutive_securities.options_outstanding is None
    assert notes.effective_tax_rates.effective is None
    assert notes.effective_tax_rates.statutory is None
    assert notes.non_recurring_items == []
    assert notes.debt_maturities == []
    assert notes.weighted_avg_interest_rate is None


def test_non_recurring_item_requires_description() -> None:
    with pytest.raises(PydanticValidationError):
        NonRecurringItem(description="")


def test_non_recurring_item_round_trip() -> None:
    item = NonRecurringItem(description="Reestructuración de plantas, 2023", affects_ebit=True)
    rebuilt = NonRecurringItem.model_validate_json(item.model_dump_json())
    assert rebuilt == item
