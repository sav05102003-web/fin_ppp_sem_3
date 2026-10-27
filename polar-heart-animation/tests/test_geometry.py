"""Проверить полярные формулы и замыкание контуров."""

from math import inf, isfinite, pi, tau
import unittest

from src.models.figures import FIGURES, limacon_radius, rose_radius
from src.models.heart import (
    heart_radius, polar_to_cartesian, sample_curve,
)


class GeometryTests(unittest.TestCase):
    """Проверить свойства фигур независимо от графического интерфейса."""

    def test_polar_conversion_on_axes(self) -> None:
        """Сохранить длину радиуса и направление осей."""
        x, y = polar_to_cartesian(3.0, pi / 2)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 3.0)

    def test_heart_is_symmetric_about_vertical_axis(self) -> None:
        """Обеспечить равные радиусы слева и справа от вертикальной оси."""
        for index in range(80):
            angle = tau * index / 80
            self.assertAlmostEqual(
                heart_radius(angle), heart_radius(pi - angle), places=6,
            )

    def test_heart_cusp_and_tip(self) -> None:
        """Расположить выемку сверху и острие снизу."""
        self.assertAlmostEqual(heart_radius(pi / 2), 0.0, places=6)
        self.assertAlmostEqual(heart_radius(-pi / 2), 4.0, places=6)

    def test_all_contours_are_finite_closed_and_nonempty(self) -> None:
        """Проверить все фигуры из каталога одним алгоритмом."""
        for figure in FIGURES:
            with self.subTest(figure=figure.name):
                points = sample_curve(figure.radius)
                self.assertEqual(len(points), 1001)
                self.assertEqual(points[0], points[-1])
                self.assertTrue(all(isfinite(v) for p in points for v in p))
                self.assertGreater(max(x for x, _ in points), 1.0)

    def test_rose_has_four_petals(self) -> None:
        """Попасть в четыре крайние точки лепестков."""
        points = sample_curve(rose_radius)
        for expected in ((2.4, 0), (-2.4, 0), (0, 2.4), (0, -2.4)):
            self.assertTrue(any(
                abs(x - expected[0]) < 1e-8
                and abs(y - expected[1]) < 1e-8
                for x, y in points
            ))

    def test_negative_radius_is_supported(self) -> None:
        """Отразить отрицательный радиус через начало координат."""
        self.assertLess(rose_radius(pi / 2), 0)
        x, y = polar_to_cartesian(-2.4, pi / 2)
        self.assertAlmostEqual(x, 0)
        self.assertAlmostEqual(y, -2.4)

    def test_limacon_extreme_radii(self) -> None:
        """Проверить характерные размеры лимакона."""
        self.assertAlmostEqual(limacon_radius(0), 3.2)
        self.assertAlmostEqual(limacon_radius(pi), 0.8)

    def test_another_formula_needs_no_renderer_changes(self) -> None:
        """Построить окружность, передав только полярную функцию."""
        for x, y in sample_curve(lambda _angle: 2):
            self.assertAlmostEqual(x * x + y * y, 4)

    def test_invalid_curve_data_is_rejected(self) -> None:
        """Не передавать некорректные координаты на холст."""
        with self.assertRaises(ValueError):
            sample_curve(heart_radius, samples=4)
        with self.assertRaises(ValueError):
            sample_curve(lambda _angle: inf)


if __name__ == "__main__":
    unittest.main()
