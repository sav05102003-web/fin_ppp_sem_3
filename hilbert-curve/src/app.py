"""Окно приложения и связь математической модели с Canvas."""

import time
import tkinter as tk
from tkinter import ttk

from src.models.animation import AnimationModel
from src.models.curves import CURVES
from src.renderers.curve_renderer import CurveRenderer
from src.widgets.controls import Controls


class App:
    """Управлять выбором кривой, анимацией и событиями окна."""

    def __init__(self, root=None):
        """Создать окно с кривой Гильберта третьего порядка."""
        self.root = root if root is not None else tk.Tk()
        self.root.title("Кривая Гильберта — сложная анимация")
        self.root.geometry("1120x820")
        self.root.minsize(990, 650)
        self.root.configure(bg="#f4f6fa")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        self.animation = AnimationModel()
        self._timer = None
        self._resize_timer = None
        self._closed = False
        self._previous_time = time.perf_counter()
        self._setup_style()
        header = ttk.Frame(self.root, padding=(24, 20, 24, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Кривые, заполняющие плоскость",
                  style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Рекурсия · цвет · движение",
                  style="Subtle.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(header, text="ЛАБОРАТОРНАЯ 2",
                  style="Subtle.TLabel").grid(row=0, column=1, sticky="e")
        self.controls = Controls(
            self.root, self.select_curve, self.select_curve, self.set_speed,
            self.toggle_pause, self.restart, self.show_all,
        )
        self.controls.grid(row=1, column=0, sticky="ew")
        self.canvas = tk.Canvas(
            self.root, bg="#101828", highlightthickness=0,
            width=1072, height=560,
        )
        self.canvas.grid(row=2, column=0, sticky="nsew", padx=24)
        self.renderer = CurveRenderer(self.canvas)
        footer = ttk.Frame(self.root, padding=(24, 12, 24, 8))
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.details = tk.StringVar()
        self.status = tk.StringVar()
        ttk.Label(footer, textvariable=self.details).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(footer, textvariable=self.status).grid(
            row=0, column=1, sticky="e"
        )
        self.progress = ttk.Progressbar(
            footer, maximum=1.0, mode="determinate"
        )
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(
            footer,
            text="Пробел — пауза   ·   R — сначала   ·   Enter — целиком"
                 "   ·   ↑ / ↓ — порядок   ·   Esc — выход",
            style="Subtle.TLabel",
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        self.canvas.bind("<Configure>", self._on_resize)
        self.root.bind("<space>", self._on_space)
        self.root.bind("<KeyPress>", self._on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.select_curve()
        self._timer = self.root.after(16, self._tick)

    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#f4f6fa")
        style.configure("TLabel", background="#f4f6fa", foreground="#162239")
        style.configure("Title.TLabel", font=("Segoe UI", 21, "bold"))
        style.configure("Subtle.TLabel", foreground="#657188")
        style.configure("TButton", padding=(10, 7))
        style.configure("TProgressbar", background="#17b6a0",
                        troughcolor="#e0e6ef", thickness=5)

    def select_curve(self):
        """Построить выбранную кривую, сохранив скорость и паузу."""
        spec = CURVES[self.controls.curve.get()]
        self.controls.set_order_limit(spec.max_order)
        order = self.controls.order.get()
        self.points = spec.builder(order)
        self.animation.restart()
        self._previous_time = time.perf_counter()
        grid_size = spec.base ** order
        self.details.set(
            f"{spec.name} · порядок {order} · сетка {grid_size}×{grid_size}"
            f" · {len(self.points):,} точек".replace(",", " ")
        )
        self._rebuild_renderer()
        self._refresh()

    def set_speed(self, value):
        """Изменить скорость, сохранив текущую позицию рисунка."""
        self.animation.speed = value

    def toggle_pause(self):
        """Приостановить/продолжить незавершённый проход."""
        if not self.animation.completed:
            self.animation.paused = not self.animation.paused
            self._previous_time = time.perf_counter()
            self._refresh()

    def restart(self):
        """Стереть линию и начать проход заново с сохранением паузы."""
        self.animation.restart()
        self._previous_time = time.perf_counter()
        self._refresh()

    def show_all(self):
        """Немедленно показать полную цветную кривую."""
        self.animation.show_all()
        self._refresh()

    def _refresh(self):
        self.renderer.draw(self.animation.progress)
        self.progress["value"] = self.animation.progress
        self.controls.set_animation_state(
            self.animation.paused, self.animation.completed
        )
        if self.animation.completed:
            state = "Готово"
        elif self.animation.paused:
            state = "Пауза"
        else:
            state = "Рисование"
        self.status.set(f"{state} · {self.animation.progress:.0%}")

    def _tick(self):
        if self._closed:
            return
        now = time.perf_counter()
        # Долгое перемещение окна не должно перескочить весь рисунок.
        elapsed = min(max(0.0, now - self._previous_time), 0.1)
        self._previous_time = now
        self.animation.advance(elapsed)
        self._refresh()
        self._timer = self.root.after(16, self._tick)

    def _on_resize(self, event):
        if self._resize_timer is not None:
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(60, self._rebuild_renderer)

    def _rebuild_renderer(self):
        self._resize_timer = None
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        self.renderer.rebuild(self.points, width, height)
        self.renderer.draw(self.animation.progress)

    def _on_space(self, event):
        self.toggle_pause()
        return "break"

    def _on_key(self, event):
        if event.keysym == "Escape":
            self.close()
        elif event.keysym in ("Return", "KP_Enter"):
            self.show_all()
        elif (event.keysym.lower() in ("r", "cyrillic_ka")
              or event.char in ("к", "К")):
            self.restart()
        elif event.keysym in ("Up", "Down"):
            if event.widget in (self.controls.curve_box,
                                self.controls.order_box):
                return None
            delta = 1 if event.keysym == "Up" else -1
            maximum = CURVES[self.controls.curve.get()].max_order
            self.controls.order.set(
                min(maximum, max(1, self.controls.order.get() + delta))
            )
            self.select_curve()
        else:
            return None
        return "break"

    def run(self):
        """Запустить обработку событий Tkinter."""
        self.root.mainloop()

    def close(self):
        """Отменить таймеры и закрыть окно приложения."""
        if self._closed:
            return
        self._closed = True
        for timer in (self._timer, self._resize_timer):
            if timer is not None:
                self.root.after_cancel(timer)
        self.root.destroy()
