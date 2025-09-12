import unittest
from triangle_func import get_triangle_type, IncorrectTriangleSides

class TestTriangleType(unittest.TestCase):
    def test_equilateral(self):
        self.assertEqual(get_triangle_type(3, 3, 3), "equilateral")

    def test_isosceles(self):
        self.assertEqual(get_triangle_type(5, 5, 3), "isosceles")

    def test_nonequilateral(self):
        self.assertEqual(get_triangle_type(4, 5, 6), "nonequilateral")

    def test_float_equilateral(self):
        self.assertEqual(get_triangle_type(2.5, 2.5, 2.5), "equilateral")


    def test_zero_side(self):
        with self.assertRaises(IncorrectTriangleSides):
            get_triangle_type(0, 4, 5)

    def test_negative_side(self):
        with self.assertRaises(IncorrectTriangleSides):
            get_triangle_type(-2, 3, 3)

    def test_triangle_inequality(self):
        with self.assertRaises(IncorrectTriangleSides):
            get_triangle_type(1, 2, 3)

    def test_big_side_breaks_inequality(self):
        with self.assertRaises(IncorrectTriangleSides):
            get_triangle_type(10, 1, 1)

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            get_triangle_type("a", 2, 3)

if __name__ == '__main__':
    unittest.main()