"""Проверки геометрии и зависимости движения от времени."""

import math
import unittest

from src.models.animation_model import AnimationModel


class AnimationModelTests(unittest.TestCase):
    """Проверить наблюдаемые свойства движения по окружности."""

    def assert_position(self, model, x, y):
        """Сравнить координаты с учётом погрешности вычислений."""
        actual_x, actual_y = model.position
        self.assertAlmostEqual(actual_x, x)
        self.assertAlmostEqual(actual_y, y)

    def test_initial_position_is_top(self):
        """Точка начинает движение в верхней части окружности."""
        self.assert_position(AnimationModel(), 300, 100)

    def test_positive_speed_is_clockwise(self):
        """За четверть оборота точка приходит направо."""
        model = AnimationModel()
        model.advance(math.pi / 2)
        self.assert_position(model, 500, 300)

    def test_negative_speed_is_counterclockwise(self):
        """Отрицательная скорость приводит точку налево."""
        model = AnimationModel(speed=-1)
        model.advance(math.pi / 2)
        self.assert_position(model, 100, 300)

    def test_full_revolution(self):
        """После полного оборота точка возвращается наверх."""
        model = AnimationModel(speed=2)
        model.advance(math.pi)
        self.assert_position(model, 300, 100)

    def test_radius_is_preserved(self):
        """Долгое движение не уводит точку с окружности."""
        model = AnimationModel(center_x=17, center_y=-25, radius=73)
        for _ in range(1000):
            model.advance(0.037)
            x, y = model.position
            self.assertAlmostEqual(math.hypot(x - 17, y + 25), 73)

    def test_motion_does_not_depend_on_frame_count(self):
        """Разное количество кадров за секунду даёт одинаковую позицию."""
        single = AnimationModel()
        multiple = AnimationModel()
        single.advance(1)
        for _ in range(100):
            multiple.advance(0.01)
        self.assert_position(multiple, *single.position)

    def test_zero_speed_stops_motion(self):
        """Нулевая скорость сохраняет положение при любом интервале."""
        model = AnimationModel(speed=0)
        model.advance(123)
        self.assert_position(model, 300, 100)

    def test_changing_speed_preserves_position(self):
        """Смена знака скорости не переносит точку в другое место."""
        model = AnimationModel()
        model.advance(1)
        position = model.position
        model.set_speed(-2)
        self.assert_position(model, *position)
        model.advance(0.5)
        self.assert_position(model, 300, 100)

    def test_reset_preserves_speed(self):
        """Сброс возвращает начальную позицию и сохраняет скорость."""
        model = AnimationModel(speed=-3)
        model.advance(8)
        model.reset()
        self.assert_position(model, 300, 100)
        self.assertEqual(model.speed, -3)

    def test_invalid_initial_values_are_rejected(self):
        """Нулевой радиус и бесконечные параметры недопустимы."""
        for params in ({"radius": 0}, {"radius": -1},
                       {"center_x": math.inf}, {"center_y": math.nan},
                       {"speed": math.inf}, {"radius": math.nan}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                AnimationModel(**params)

    def test_invalid_speed_is_rejected(self):
        """Скорость NaN или бесконечность не меняет модель."""
        model = AnimationModel()
        for speed in (math.inf, -math.inf, math.nan):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                model.set_speed(speed)
        self.assertEqual(model.speed, 1)

    def test_invalid_elapsed_time_is_rejected(self):
        """Отрицательный или бесконечный интервал недопустим."""
        model = AnimationModel()
        for elapsed in (-1, math.inf, math.nan):
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                model.advance(elapsed)
        self.assert_position(model, 300, 100)


if __name__ == "__main__":
    unittest.main()
