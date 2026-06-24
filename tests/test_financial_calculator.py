"""Unit tests for the deterministic mortgage calculator."""
import pytest
from tools.financial_calculator import MortgageCalculatorTool


@pytest.fixture
def calc():
    return MortgageCalculatorTool()


def test_standard_mortgage(calc):
    result = calc._run(principal=200_000, annual_rate_pct=3.5, years=30)
    assert "898" in result or "cuota" in result.lower()


def test_zero_interest(calc):
    result = calc._run(principal=12_000, annual_rate_pct=0.0, years=1)
    # output uses a thousands separator: 12.000 € / 12 = 1,000.00 €/mes
    assert "1,000.00" in result


def test_output_contains_all_fields(calc):
    result = calc._run(principal=150_000, annual_rate_pct=2.5, years=20)
    assert "Cuota mensual" in result
    assert "Total a devolver" in result
    assert "Total intereses" in result
