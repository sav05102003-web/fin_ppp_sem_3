"""Интеграционные проверки настоящего окна Tkinter."""

import tkinter as tk
import unittest
from unittest.mock import patch

from src.app import App


class AppTests(unittest.TestCase):
    """Проверить геометрию окна, клавиатуру и таймер анимации."""

    def setUp(self):
        """Создать настоящее окно или пропустить GUI без дисплея."""
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk недоступен: {exc}")
        self.clock = patch("src.app.time.perf_counter", return_value=100.0)
        self.now = self.clock.start()
        self.app = App(self.root)
        self.root.update()
        self.root.focus_force()
        self.root.update()

    def tearDown(self):
        """Закрыть окно и восстановить реальные часы."""
        if hasattr(self, "app"):
            self.app.close()
        if hasattr(self, "clock"):
            self.clock.stop()

    def press(self, key):
        """Отправить событие клавиши настоящему окну."""
        self.root.event_generate(f"<KeyPress-{key}>")
        self.root.update()

    def test_canvas_fills_exact_window(self):
        """Клиентская область и Canvas равны 600×600 без рамки."""
        self.assertEqual(self.root.winfo_width(), 600)
        self.assertEqual(self.root.winfo_height(), 600)
        self.assertEqual(self.app.canvas.winfo_width(), 600)
        self.assertEqual(self.app.canvas.winfo_height(), 600)
        self.assertEqual(self.app.canvas.winfo_x(), 0)
        self.assertEqual(self.app.canvas.winfo_y(), 0)
        self.assertEqual(self.root.resizable(), (0, 0))
        self.assertEqual(self.app.canvas.coords(self.app.renderer.orbit_id),
                         [100, 100, 500, 500])

    def test_timer_moves_existing_point(self):
        """Кадр меняет координаты, сохраняя два объекта Canvas."""
        before = self.app.canvas.coords(self.app.renderer.point_id)
        self.now.return_value = 100.5
        # Выполняем именно callback, зарегистрированный в таймере Tk.
        callback = self.root.tk.call("after", "info", self.app._after_id)[0]
        self.root.tk.call("after", "cancel", self.app._after_id)
        self.root.tk.call(callback)
        self.assertNotEqual(
            before, self.app.canvas.coords(self.app.renderer.point_id),
        )
        self.assertEqual(len(self.app.canvas.find_all()), 2)
        self.assertIsNotNone(self.app._after_id)

    def test_pause_does_not_accumulate_time(self):
        """После паузы движение продолжается без скачка."""
        self.press("space")
        self.assertTrue(self.app.paused)
        position = self.app.model.position
        self.now.return_value = 200.0
        self.press("space")
        self.assertFalse(self.app.paused)
        self.assertEqual(self.app.model.position, position)

    def test_keyboard_controls_speed_and_direction(self):
        """Стрелки регулируют скорость и направление."""
        self.press("Up")
        self.assertEqual(self.app.model.speed, 1.25)
        self.press("Left")
        self.assertEqual(self.app.model.speed, -1.25)
        self.press("Down")
        self.assertEqual(self.app.model.speed, -1)
        self.press("Right")
        self.assertEqual(self.app.model.speed, 1)

    def test_zero_speed_and_restart(self):
        """Замедление останавливается на нуле, стрелка запускает точку."""
        for _ in range(6):
            self.press("Down")
        self.assertEqual(self.app.model.speed, 0)
        self.press("Left")
        self.assertEqual(self.app.model.speed, -0.25)

    def test_reset_preserves_pause(self):
        """Сброс возвращает точку наверх и сохраняет паузу."""
        self.now.return_value = 101.0
        self.press("space")
        self.app.reset()
        self.assertTrue(self.app.paused)
        x, y = self.app.model.position
        self.assertAlmostEqual(x, 300)
        self.assertAlmostEqual(y, 100)

    def test_escape_cancels_timer(self):
        """Esc завершает приложение и удаляет отложенный кадр."""
        self.press("Escape")
        self.assertTrue(self.app._closed)
        self.assertIsNone(self.app._after_id)


if __name__ == "__main__":
    unittest.main()
