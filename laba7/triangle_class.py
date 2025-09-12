class IncorrectTriangleSides(Exception):
    pass

class Triangle:
    def __init__(self, a, b, c):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float)) and isinstance(c, (int, float))):
            raise IncorrectTriangleSides("Стороны должны быть числами")

        if a <= 0 or b <= 0 or c <= 0:
            raise IncorrectTriangleSides("Стороны должны быть положительными")

        if a + b <= c or a + c <= b or b + c <= a:
            raise IncorrectTriangleSides("Некорректные стороны — нарушено неравенство треугольника")

        self.a = a
        self.b = b
        self.c = c

    def triangle_type(self):
        if self.a == self.b == self.c:
            return "equilateral"
        elif self.a == self.b or self.a == self.c or self.b == self.c:
            return "isosceles"
        else:
            return "nonequilateral"

    def perimeter(self):
        return self.a + self.b + self.c
t = Triangle(3, 4 , 5)
print(t.triangle_type())
print(t.perimeter())