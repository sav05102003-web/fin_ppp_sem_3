"""Проверки времени и состояний анимации."""

import unittest

from src.models.animation import AnimationModel


class AnimationTests(unittest.TestCase):
    """Проверять реальные свойства анимации независимо от Tkinter."""

    def test_pass_takes_twelve_seconds(self):
        """Полный проход при 1× должен занять заданную длительность."""
        model = AnimationModel()
        model.advance(6)
        self.assertAlmostEqual(model.progress, 0.5)
        model.advance(6)
        self.assertTrue(model.completed)

    def test_same_result_for_different_frame_rates(self):
        """Разная частота кадров не должна менять скорость рисования."""
        for fps in (24, 30, 60, 144):
            model = AnimationModel()
            for _ in range(fps * 3):
                model.advance(1 / fps)
            self.assertAlmostEqual(model.progress, 0.25)

    def test_pause_freezes_progress(self):
        """Пауза не должна копить пропущенное время."""
        model = AnimationModel()
        model.advance(3)
        model.paused = True
        model.advance(20)
        self.assertEqual(model.progress, 0.25)
        model.paused = False
        model.advance(3)
        self.assertEqual(model.progress, 0.5)

    def test_speed_change_does_not_reset_progress(self):
        """Новая скорость должна влиять только на последующие кадры."""
        model = AnimationModel()
        model.advance(3)
        model.speed = 2
        self.assertEqual(model.progress, 0.25)
        model.advance(3)
        self.assertEqual(model.progress, 0.75)

    def test_restart_preserves_speed_and_pause(self):
        """Сброс должен сохранять выбранные параметры."""
        model = AnimationModel()
        model.speed = 2
        model.paused = True
        model.show_all()
        model.restart()
        self.assertEqual(model.progress, 0)
        self.assertEqual(model.speed, 2)
        self.assertTrue(model.paused)

    def test_progress_cannot_exceed_one(self):
        """Линия должна останавливаться в своей конечной точке."""
        model = AnimationModel()
        model.advance(100)
        model.advance(100)
        self.assertEqual(model.progress, 1)

    def test_invalid_time_and_speed(self):
        """Нечисловая/неограниченная скорость не должна ломать анимацию."""
        model = AnimationModel()
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                model.advance(value)
        for value in (0, -1, 5, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                model.speed = value
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                AnimationModel(value)


if __name__ == "__main__":
    unittest.main()
