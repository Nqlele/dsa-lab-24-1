import pytest
from triangle_class import Triangle, IncorrectTriangleSides


def test_equilateral():
    t = Triangle(3, 3, 3)
    assert t.triangle_type() == "equilateral"
    assert t.perimeter() == 9

def test_isosceles():
    t1 = Triangle(3, 3, 4)
    t2 = Triangle(4, 3, 3)
    t3 = Triangle(4, 3, 4)
    assert t1.triangle_type() == "isosceles"
    assert t2.triangle_type() == "isosceles"
    assert t3.triangle_type() == "isosceles"
    assert t1.perimeter() == 10

def test_nonequilateral():
    t = Triangle(3, 4, 5)
    assert t.triangle_type() == "nonequilateral"
    assert t.perimeter() == 12


def test_incorrect_types():
    with pytest.raises(IncorrectTriangleSides):
        Triangle("3", 4, 5)

def test_negative_sides():
    with pytest.raises(IncorrectTriangleSides):
        Triangle(-3, 4, 5)

def test_zero_sides():
    with pytest.raises(IncorrectTriangleSides):
        Triangle(0, 4, 5)

def test_invalid_triangle():
    with pytest.raises(IncorrectTriangleSides):
        Triangle(1, 1, 10)

def test_float_sides():
    t = Triangle(2.5, 2.5, 2.5)
    assert t.triangle_type() == "equilateral"
    assert t.perimeter() == 7.5