"""Проверить связь окна, отрисовки и элементов управления."""

import tkinter as tk
import unittest

from src.app import App
from src.models.figures import FIGURES


class AppTests(unittest.TestCase):
    """Проверить реальное окно tkinter при наличии графической среды."""

    def setUp(self) -> None:
        """Создать окно или пропустить GUI-проверки без дисплея."""
        try:
            self.app = App()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.app.root.update()

    def tearDown(self) -> None:
        """Освободить ресурсы созданного окна."""
        if hasattr(self, "app"):
            self.app.close()

    def test_switch_figures_and_resize(self) -> None:
        """Сохранить контур внутри холста после выбора фигуры и ресайза."""
        self.app.root.geometry("800x650")
        self.app.root.update()
        for figure in FIGURES:
            with self.subTest(figure=figure.name):
                self.app.controls.figure.set(figure.name)
                self.app.change_figure()
                self.app.root.update()
                self.assertEqual(self.app.heading.get(), figure.name)
                width = self.app.canvas.winfo_width()
                height = self.app.canvas.winfo_height()
                for x, y in self.app.renderer.screen_points:
                    self.assertTrue(0 <= x <= width)
                    self.assertTrue(0 <= y <= height)
                self.assertEqual(len(self.app.canvas.find_all()), 5)

    def test_full_contour_and_reset(self) -> None:
        """Вернуть анимацию после просмотра полного контура."""
        self.app.controls.mode.set(True)
        self.app.change_mode()
        self.assertIn("disabled", self.app.controls.pause_button.state())
        self.app.reset()
        self.assertFalse(self.app.controls.mode.get())
        self.assertNotIn("disabled", self.app.controls.pause_button.state())

    def test_space_on_focused_button_toggles_once(self) -> None:
        """Обработать пробел один раз даже при фокусе на кнопке паузы."""
        button = self.app.controls.pause_button
        button.focus_force()
        self.app.root.update()
        button.event_generate("<KeyPress-space>")
        button.event_generate("<KeyRelease-space>")
        self.app.root.update()
        self.assertTrue(self.app.model.paused)

    def test_speed_control_updates_model(self) -> None:
        """Передать скорость из интерфейса в модель."""
        self.app.change_speed("2.5")
        self.assertEqual(self.app.model.speed, 2.5)


if __name__ == "__main__":
    unittest.main()
