"""Unit tests for sample_python calculator functions."""

import pytest
from sample_python.calculator import add, divide, multiply, subtract


def test_add() -> None:
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0.5, 0.5) == 1.0


def test_subtract() -> None:
    assert subtract(5, 3) == 2
    assert subtract(1, 4) == -3
    assert subtract(2.5, 0.5) == 2.0


def test_multiply() -> None:
    assert multiply(2, 3) == 6
    assert multiply(-2, 3) == -6
    assert multiply(0, 100) == 0
    assert multiply(2.5, 2.0) == 5.0


def test_divide() -> None:
    assert divide(6, 2) == 3.0
    assert divide(5, 2) == 2.5
    assert divide(-6, 2) == -3.0


def test_divide_by_zero() -> None:
    with pytest.raises(ZeroDivisionError, match="division by zero"):
        divide(10, 0)
