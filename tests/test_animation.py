"""Проверить течение времени, изменение угла и управление анимацией."""

from math import nan, pi, tau
import unittest

from src.models.animation import AnimationModel


class AnimationTests(unittest.TestCase):
    """Проверить состояние анимации без запуска окна."""

    def test_angle_increases(self) -> None:
        """Продвинуть контур после положительного интервала времени."""
        model = AnimationModel()
        model.advance(0.1)
        self.assertGreater(model.angle, 0)
        self.assertLess(model.progress, 1)

    def test_angular_increment_varies_along_contour(self) -> None:
        """Получить разные приращения за равные временные интервалы."""
        first = AnimationModel(angle=0)
        second = AnimationModel(angle=pi / 4)
        first.advance(1 / 240)
        second.advance(1 / 240)
        self.assertGreater(first.last_step, second.last_step)

    def test_pause_freezes_all_progress(self) -> None:
        """Не менять состояние во время паузы."""
        model = AnimationModel()
        model.advance(0.4)
        model.toggle_pause()
        snapshot = (model.angle, model.hold, model.cycles)
        model.advance(5)
        self.assertEqual(snapshot, (model.angle, model.hold, model.cycles))
        model.toggle_pause()
        model.advance(0.1)
        self.assertGreater(model.angle, snapshot[0])

    def test_completed_contour_is_held_then_restarts(self) -> None:
        """Показать готовый контур перед новым проходом."""
        model = AnimationModel(angle=tau - 0.001)
        model.advance(0.01)
        self.assertEqual(model.angle, tau)
        self.assertGreater(model.hold, 0)
        model.advance(0.9)
        self.assertEqual(model.cycles, 1)
        self.assertLess(model.angle, 0.3)

    def test_speed_affects_progress(self) -> None:
        """При большей скорости быстрее двигаться вдоль контура."""
        slow = AnimationModel(speed=0.25)
        fast = AnimationModel(speed=3)
        slow.advance(0.5)
        fast.advance(0.5)
        self.assertGreater(fast.angle, slow.angle)

    def test_small_and_large_frame_intervals_agree(self) -> None:
        """Не привязывать скорость к частоте кадров."""
        first, second = AnimationModel(), AnimationModel()
        first.advance(1.0)
        for _ in range(60):
            second.advance(1 / 60)
        self.assertAlmostEqual(first.angle, second.angle, places=7)

    def test_reset_preserves_settings(self) -> None:
        """Сбросить проход, сохранив выбранную скорость и паузу."""
        model = AnimationModel(speed=2, angle=2, paused=True, cycles=4)
        model.reset()
        self.assertEqual((model.angle, model.cycles, model.hold), (0, 0, 0))
        self.assertEqual(model.speed, 2)
        self.assertTrue(model.paused)

    def test_invalid_inputs_are_rejected(self) -> None:
        """Отклонить отрицательное время и недопустимую скорость."""
        model = AnimationModel()
        for elapsed in (-1, nan):
            with self.assertRaises(ValueError):
                model.advance(elapsed)
        for speed in (0, 4, nan):
            with self.assertRaises(ValueError):
                model.set_speed(speed)


if __name__ == "__main__":
    unittest.main()
