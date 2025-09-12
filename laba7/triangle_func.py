class IncorrectTriangleSides(Exception):
    pass

def get_triangle_type(a, b, c):
    if a <= 0 or b <= 0 or c <= 0:
        raise IncorrectTriangleSides("Стороны должны быть положительными числами")
    if a + b <= c or a + c <= b or b + c <= a:
        raise IncorrectTriangleSides("Нарушено неравенство треугольника")

    if a == b == c:
        return "equilateral"
    elif a == b or b == c or a == c:
        return "isosceles"
    else:
        return "nonequilateral"

print(get_triangle_type(5, 3, 3))