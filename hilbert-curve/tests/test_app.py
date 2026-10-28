"""Интеграционные проверки настоящего окна Tkinter."""

from types import SimpleNamespace
import tkinter as tk
import unittest

from src.app import App


class AppTests(unittest.TestCase):
    """Проверять связь кнопок, событий и Canvas с моделью."""

    @classmethod
    def setUpClass(cls):
        """Пропустить GUI-проверки при отсутствии графической среды."""
        try:
            root = tk.Tk()
            root.withdraw()
            root.destroy()
        except tk.TclError as error:
            raise unittest.SkipTest(f"Tkinter недоступен: {error}") from error

    def setUp(self):
        """Создать настоящее окно и обработать начальную раскладку."""
        self.app = App()
        self.app.root.update()
        self.app._rebuild_renderer()

    def tearDown(self):
        """Завершить окно вместе с таймерами."""
        self.app.close()

    def test_initial_curve_and_visible_controls(self):
        """Начинать с небольшого порядка и размещать кнопки внутри окна."""
        self.assertEqual(self.app.controls.curve.get(), "Кривая Гильберта")
        self.assertEqual(self.app.controls.order.get(), 3)
        self.assertEqual(len(self.app.points), 64)
        self.assertLessEqual(
            self.app.controls.winfo_reqwidth(), self.app.root.winfo_width()
        )

    def test_pause_button_and_restart(self):
        """Кнопка должна менять состояние; сброс сохраняет паузу."""
        self.app.controls.pause_button.invoke()
        self.assertTrue(self.app.animation.paused)
        self.app.animation.progress = 0.5
        self.app.restart()
        self.assertEqual(self.app.animation.progress, 0)
        self.assertTrue(self.app.animation.paused)
        self.assertEqual(
            self.app.controls.pause_button.cget("text"), "Продолжить"
        )

    def test_switching_curve_clamps_order(self):
        """Выбор Пеано после Гильберта-7 должен ограничить порядок до 4."""
        self.app.controls.order.set(7)
        self.app.select_curve()
        self.app.controls.curve.set("Кривая Пеано")
        self.app.select_curve()
        self.assertEqual(self.app.controls.order.get(), 4)
        self.assertEqual(len(self.app.points), 6561)
        self.assertEqual(self.app.animation.progress, 0)

    def test_real_timer_draws_next_frame(self):
        """Запланированный after должен продвигать модель без ручного шага."""
        before = self.app.animation.progress
        self.app.root.after(80, self.app.root.quit)
        self.app.root.mainloop()
        self.assertGreater(self.app.animation.progress, before)

    def test_rendered_endpoint_and_reset(self):
        """После завершения кончик должен совпасть с последней вершиной."""
        self.app.show_all()
        box = self.app.canvas.coords(self.app.renderer._tip)
        endpoint = self.app.renderer.screen_points[-1]
        self.assertAlmostEqual((box[0] + box[2]) / 2, endpoint[0])
        self.assertAlmostEqual((box[1] + box[3]) / 2, endpoint[1])
        self.assertEqual(
            str(self.app.controls.pause_button.cget("state")), "disabled"
        )
        self.app.restart()
        self.assertTrue(all(
            self.app.canvas.itemcget(item, "state") == "hidden"
            for _, _, item, _ in self.app.renderer._buckets
        ))

    def test_canvas_item_count_stays_bounded(self):
        """Число объектов не должно расти вместе с числом кадров."""
        self.app.controls.order.set(7)
        self.app.select_curve()
        count = len(self.app.canvas.find_all())
        for step in range(101):
            self.app.renderer.draw(step / 100)
        self.assertEqual(len(self.app.canvas.find_all()), count)
        self.assertLessEqual(count, 195)

    def test_resize_keeps_progress_and_square(self):
        """Перестройка окна должна сохранять позицию и пропорции."""
        self.app.animation.paused = True
        self.app.animation.progress = 0.45
        self.app.root.geometry("1040x690")
        self.app.root.update()
        self.app._rebuild_renderer()
        xs, ys = zip(*self.app.renderer.screen_points)
        self.assertAlmostEqual(max(xs) - min(xs), max(ys) - min(ys))
        self.assertEqual(self.app.animation.progress, 0.45)
        self.assertLessEqual(
            self.app.controls.winfo_reqwidth(), self.app.root.winfo_width()
        )

    def test_keyboard_shortcuts_and_focus_navigation(self):
        """Стрелки меняют порядок; Tab остаётся доступным для фокуса."""
        event = SimpleNamespace(keysym="Up", char="", widget=self.app.canvas)
        self.app._on_key(event)
        self.assertEqual(self.app.controls.order.get(), 4)
        event.keysym = "Down"
        self.app._on_key(event)
        self.assertEqual(self.app.controls.order.get(), 3)
        event.keysym = "Tab"
        self.assertIsNone(self.app._on_key(event))
        event.keysym, event.char = "r", "r"
        self.app.show_all()
        self.app._on_key(event)
        self.assertEqual(self.app.animation.progress, 0)
        self.assertEqual(self.app._on_space(event), "break")
        self.assertTrue(self.app.animation.paused)

    def test_space_with_button_focus_toggles_only_once(self):
        """Пробел на кнопке не должен дважды переключать паузу."""
        button = self.app.controls.pause_button
        button.focus_force()
        self.app.root.update()
        button.event_generate("<KeyPress-space>")
        button.event_generate("<KeyRelease-space>")
        self.app.root.update()
        self.assertTrue(self.app.animation.paused)


if __name__ == "__main__":
    unittest.main()
