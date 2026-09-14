"""Unit tests for the wine cellar blueprint: pure functions and model logic,
tested in isolation from HTTP routing and without touching the database."""

from datetime import date

import pytest

from app.blueprints.wine_cellar.models import Bottle
from app.blueprints.wine_cellar.routes import (
    _bottle_from_form,
    _parse_date,
    _parse_decimal,
    _parse_int,
)


# ---------------------------------------------------------------------------
# Bottle.drink_status()
# ---------------------------------------------------------------------------

def test_drink_status_none_when_window_not_set():
    bottle = Bottle(name="Test", drink_window_start=None, drink_window_end=None)
    assert bottle.drink_status() is None


def test_drink_status_none_when_only_start_set():
    bottle = Bottle(name="Test", drink_window_start=2020, drink_window_end=None)
    assert bottle.drink_status() is None


def test_drink_status_cellar_when_before_window():
    current_year = date.today().year
    bottle = Bottle(
        name="Test", drink_window_start=current_year + 1, drink_window_end=current_year + 5
    )
    assert bottle.drink_status() == "cellar"


def test_drink_status_ready_when_within_window():
    current_year = date.today().year
    bottle = Bottle(
        name="Test", drink_window_start=current_year - 1, drink_window_end=current_year + 1
    )
    assert bottle.drink_status() == "ready"


def test_drink_status_ready_on_boundary_years():
    current_year = date.today().year
    bottle = Bottle(
        name="Test", drink_window_start=current_year, drink_window_end=current_year
    )
    assert bottle.drink_status() == "ready"


def test_drink_status_past_when_after_window():
    current_year = date.today().year
    bottle = Bottle(
        name="Test", drink_window_start=current_year - 5, drink_window_end=current_year - 1
    )
    assert bottle.drink_status() == "past"


# ---------------------------------------------------------------------------
# _parse_int / _parse_decimal / _parse_date
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, "", "   "])
def test_parse_int_returns_none_for_blank(value):
    assert _parse_int(value) is None


def test_parse_int_parses_valid_integer_with_whitespace():
    assert _parse_int("  42 ") == 42


@pytest.mark.parametrize("value", [None, "", "  "])
def test_parse_decimal_returns_none_for_blank(value):
    assert _parse_decimal(value) is None


def test_parse_decimal_returns_stripped_string():
    assert _parse_decimal("  45.00 ") == "45.00"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_parse_date_returns_none_for_blank(value):
    assert _parse_date(value) is None


def test_parse_date_parses_iso_format():
    assert _parse_date("2021-05-01") == date(2021, 5, 1)


def test_parse_date_raises_for_invalid_format():
    with pytest.raises(ValueError):
        _parse_date("05/01/2021")


# ---------------------------------------------------------------------------
# _bottle_from_form
# ---------------------------------------------------------------------------

def test_bottle_from_form_requires_name():
    errors = []
    data = _bottle_from_form({}, errors)
    assert "Name is required." in errors
    assert data["name"] == ""


def test_bottle_from_form_defaults_quantity_to_one():
    errors = []
    data = _bottle_from_form({"name": "Test Wine"}, errors)
    assert not errors
    assert data["quantity"] == 1


def test_bottle_from_form_rejects_negative_quantity():
    errors = []
    data = _bottle_from_form({"name": "Test Wine", "quantity": "-1"}, errors)
    assert "Quantity must be a non-negative whole number." in errors
    assert data["quantity"] == 1


def test_bottle_from_form_rejects_non_numeric_quantity():
    errors = []
    data = _bottle_from_form({"name": "Test Wine", "quantity": "abc"}, errors)
    assert "Quantity must be a non-negative whole number." in errors


def test_bottle_from_form_accepts_zero_quantity():
    errors = []
    data = _bottle_from_form({"name": "Test Wine", "quantity": "0"}, errors)
    assert not errors
    assert data["quantity"] == 0


def test_bottle_from_form_rejects_non_numeric_vintage():
    errors = []
    data = _bottle_from_form({"name": "Test Wine", "vintage": "abc"}, errors)
    assert "Vintage must be a whole number." in errors
    assert data["vintage"] is None


def test_bottle_from_form_rejects_inverted_drink_window():
    errors = []
    data = _bottle_from_form(
        {"name": "Test Wine", "drink_window_start": "2030", "drink_window_end": "2020"},
        errors,
    )
    assert "Drink window start must be before or equal to the end year." in errors


def test_bottle_from_form_accepts_equal_drink_window_bounds():
    errors = []
    data = _bottle_from_form(
        {"name": "Test Wine", "drink_window_start": "2025", "drink_window_end": "2025"},
        errors,
    )
    assert not errors
    assert data["drink_window_start"] == 2025
    assert data["drink_window_end"] == 2025


def test_bottle_from_form_rejects_non_numeric_purchase_price():
    errors = []
    data = _bottle_from_form({"name": "Test Wine", "purchase_price": "free"}, errors)
    assert "Purchase price must be a number." in errors


def test_bottle_from_form_rejects_invalid_purchase_date():
    errors = []
    data = _bottle_from_form({"name": "Test Wine", "purchase_date": "not-a-date"}, errors)
    assert "Purchase date must be a valid date." in errors


def test_bottle_from_form_strips_whitespace_and_blanks_become_none():
    errors = []
    data = _bottle_from_form(
        {"name": "  Test Wine  ", "producer": "   ", "region": "  Piedmont  "},
        errors,
    )
    assert not errors
    assert data["name"] == "Test Wine"
    assert data["producer"] is None
    assert data["region"] == "Piedmont"
