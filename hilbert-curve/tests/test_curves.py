"""Геометрические свойства рекурсивных кривых."""

import unittest

from src.models.curves import CURVES, hilbert_points, peano_points
from src.renderers.curve_renderer import fit_points, gradient_color


class CurveTests(unittest.TestCase):
    """Проверять заполнение сетки, непрерывность и масштабирование."""

    def test_hilbert_first_order(self):
        """Первый порядок должен иметь узнаваемый П-образный обход."""
        self.assertEqual(hilbert_points(1), ((0, 0), (0, 1), (1, 1), (1, 0)))

    def test_all_grids_are_filled_exactly_once(self):
        """Каждая клетка квадратной сетки должна посещаться ровно один раз."""
        for name, spec in CURVES.items():
            for order in range(1, spec.max_order + 1):
                with self.subTest(curve=name, order=order):
                    size = spec.base ** order
                    points = spec.builder(order)
                    self.assertEqual(len(points), size * size)
                    self.assertEqual(
                        set(points),
                        {(x, y) for x in range(size) for y in range(size)},
                    )

    def test_consecutive_points_share_an_edge(self):
        """У ломаной не должно быть разрывов или диагональных скачков."""
        for name, spec in CURVES.items():
            for order in range(1, spec.max_order + 1):
                with self.subTest(curve=name, order=order):
                    points = spec.builder(order)
                    self.assertTrue(all(
                        abs(x - nx) + abs(y - ny) == 1
                        for (x, y), (nx, ny) in zip(points, points[1:])
                    ))

    def test_hilbert_endpoints(self):
        """Концы Гильберта находятся в соседних нижних углах квадрата."""
        for order in range(1, 8):
            points = hilbert_points(order)
            self.assertEqual(points[0], (0, 0))
            self.assertEqual(points[-1], (2 ** order - 1, 0))

    def test_peano_endpoints(self):
        """Концы Пеано находятся в противоположных углах квадрата."""
        for order in range(1, 5):
            points = peano_points(order)
            self.assertEqual(points[0], (0, 0))
            self.assertEqual(points[-1], (3 ** order - 1, 3 ** order - 1))

    def test_invalid_orders(self):
        """Ограничивать память и не принимать дробную глубину рекурсии."""
        for builder, maximum in ((hilbert_points, 7), (peano_points, 4)):
            for value in (0, -1, maximum + 1, 1.5, True, "3"):
                with self.subTest(builder=builder.__name__, value=value):
                    with self.assertRaises(ValueError):
                        builder(value)

    def test_fit_preserves_square_in_wide_and_tall_windows(self):
        """Изменение пропорций окна не должно растягивать сетку."""
        for width, height in ((1100, 600), (500, 900), (200, 200)):
            points = fit_points(hilbert_points(3), width, height)
            xs, ys = zip(*points)
            self.assertAlmostEqual(max(xs) - min(xs), max(ys) - min(ys))
            self.assertAlmostEqual(min(xs) + max(xs), width)
            self.assertAlmostEqual(min(ys) + max(ys), height)
            self.assertTrue(all(0 <= x <= width and 0 <= y <= height
                                for x, y in points))

    def test_gradient_is_smooth(self):
        """Соседние позиции должны давать близкие корректные RGB-цвета."""
        colors = [gradient_color(i / 191) for i in range(192)]
        self.assertEqual(len(set(colors)), 192)
        for first, second in zip(colors, colors[1:]):
            a = [int(first[i:i + 2], 16) for i in (1, 3, 5)]
            b = [int(second[i:i + 2], 16) for i in (1, 3, 5)]
            self.assertLessEqual(max(abs(x - y) for x, y in zip(a, b)), 4)


if __name__ == "__main__":
    unittest.main()
