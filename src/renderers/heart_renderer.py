"""Отрисовка полярной кривой, независимая от формулы фигуры."""

import tkinter as tk

from src.models.heart import Point, PolarCurve, sample_curve

BACKGROUND = "#10131e"


class HeartRenderer:
    """Масштабировать кривую и показывать ее на Canvas."""

    def __init__(self, canvas: tk.Canvas, curve: PolarCurve) -> None:
        """Сохранить холст и вычислить точки переданной фигуры."""
        self.canvas = canvas
        self.points = sample_curve(curve)
        self.screen_points: list[Point] = []
        self.guide = canvas.create_line(0, 0, 0, 0, fill="#302337", width=1)
        self.glow = canvas.create_line(0, 0, 0, 0, fill="#47263d", width=14)
        self.halo = canvas.create_line(0, 0, 0, 0, fill="#8c3758", width=5)
        self.line = canvas.create_line(0, 0, 0, 0, fill="#ff779a", width=2)
        self.marker = canvas.create_oval(0, 0, 0, 0, fill="#ffe1e9", outline="")
        self.resize()

    def resize(self) -> None:
        """Вписать контур в текущий размер холста с сохранением пропорций."""
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        xs, ys = zip(*self.points)
        center_x = (min(xs) + max(xs)) / 2
        center_y = (min(ys) + max(ys)) / 2
        scale = min(
            (width - 80) / (max(xs) - min(xs)),
            (height - 70) / (max(ys) - min(ys)),
        )
        # У Canvas ось Y направлена вниз, поэтому меняем знак Y.
        self.screen_points = [
            (width / 2 + (x - center_x) * scale,
             height / 2 - (y - center_y) * scale)
            for x, y in self.points
        ]
        self.canvas.coords(self.guide, *self._flatten(self.screen_points))

    def set_curve(self, curve: PolarCurve, color: str) -> None:
        """Сменить формулу и цвет, сохранив общий алгоритм отрисовки."""
        self.points = sample_curve(curve)
        self.canvas.itemconfigure(self.line, fill=color)
        self.resize()

    def draw(self, progress: float = 1.0) -> None:
        """Показать долю контура от нуля до единицы."""
        progress = min(max(progress, 0.0), 1.0)
        position = progress * (len(self.screen_points) - 1)
        index = min(int(position), len(self.screen_points) - 2)
        fraction = position - index
        first, second = self.screen_points[index:index + 2]
        tip = (first[0] + (second[0] - first[0]) * fraction,
               first[1] + (second[1] - first[1]) * fraction)
        visible = self.screen_points[:index + 1] + [tip]
        coordinates = self._flatten(visible)
        for item in (self.glow, self.halo, self.line):
            self.canvas.coords(item, *coordinates)
        x, y = tip
        self.canvas.coords(self.marker, x - 4, y - 4, x + 4, y + 4)

    @staticmethod
    def _flatten(points: list[Point]) -> list[float]:
        return [coordinate for point in points for coordinate in point]
