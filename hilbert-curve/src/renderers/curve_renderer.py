"""Цветная ломаная с ограниченным числом объектов Canvas."""

import colorsys
import math


def gradient_color(position: float) -> str:
    """Вернуть цвет плавного перехода от бирюзового к розовому."""
    position = max(0.0, min(1.0, position))
    rgb = colorsys.hsv_to_rgb(0.48 + 0.44 * position, 0.62, 0.98)
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in rgb)


def fit_points(points, width, height, padding=48):
    """Вписать квадратную сетку в Canvas с одинаковым масштабом по осям."""
    maximum = max(max(x, y) for x, y in points)
    side = max(1.0, min(width, height) - 2 * padding)
    scale = side / max(1, maximum)
    left, bottom = (width - side) / 2, (height + side) / 2
    return tuple((left + x * scale, bottom - y * scale) for x, y in points)


class CurveRenderer:
    """Разбить линию на цветовые участки и обновлять только видимую часть."""

    def __init__(self, canvas):
        """Связать отрисовку с заданным Canvas."""
        self.canvas = canvas
        self.points = ()
        self.screen_points = ()
        self._buckets = []
        self._last_amount = -1.0
        self._tip = None
        self._start = None
        self._guide = None

    def rebuild(self, points, width, height):
        """Пересоздать масштаб и цветовые участки при изменении рисунка."""
        self.points = points
        self.screen_points = fit_points(points, width, height)
        self.canvas.delete("curve")
        self._buckets.clear()
        self._last_amount = -1.0
        segments = len(points) - 1
        count = min(192, segments)
        gap = math.dist(self.screen_points[0], self.screen_points[1])
        stroke = max(1.0, min(5.0, gap * 0.36))
        xs, ys = zip(*self.screen_points)
        self._guide = self.canvas.create_rectangle(
            min(xs), min(ys), max(xs), max(ys),
            outline="#253149", dash=(3, 7), tags="curve",
        )
        for index in range(count):
            start = index * segments // count
            end = (index + 1) * segments // count
            x, y = self.screen_points[start]
            item = self.canvas.create_line(
                x, y, x, y, fill=gradient_color(index / max(1, count - 1)),
                width=stroke, capstyle="round", joinstyle="round",
                state="hidden", tags="curve",
            )
            full_coords = [
                value
                for point in self.screen_points[start:end + 1]
                for value in point
            ]
            self._buckets.append((start, end, item, full_coords))
        x, y = self.screen_points[0]
        self._start = self.canvas.create_oval(
            x - 3, y - 3, x + 3, y + 3,
            fill=gradient_color(0), outline="", tags="curve",
        )
        self._tip = self.canvas.create_oval(
            x - 5, y - 5, x + 5, y + 5,
            fill="#ffffff", outline="#111a2c", width=2, tags="curve",
        )

    def draw(self, progress):
        """Показать progress долей кривой и интерполированный кончик линии."""
        if not self.screen_points:
            return
        segments = len(self.screen_points) - 1
        amount = max(0.0, min(1.0, progress)) * segments
        if amount == self._last_amount:
            return
        backwards = amount < self._last_amount
        for start, end, item, full_coords in self._buckets:
            if amount <= start:
                if backwards:
                    self.canvas.itemconfigure(item, state="hidden")
            elif amount >= end:
                if backwards or self._last_amount < end:
                    self.canvas.coords(item, *full_coords)
                    self.canvas.itemconfigure(item, state="normal")
            else:
                whole = int(amount)
                coords = [
                    value
                    for point in self.screen_points[start:whole + 1]
                    for value in point
                ]
                coords.extend(self._point_at(amount))
                self.canvas.coords(item, *coords)
                self.canvas.itemconfigure(item, state="normal")
        x, y = self._point_at(amount)
        self.canvas.coords(self._tip, x - 5, y - 5, x + 5, y + 5)
        self.canvas.itemconfigure(self._tip, fill=gradient_color(progress))
        self._last_amount = amount

    def _point_at(self, amount):
        whole = min(int(amount), len(self.screen_points) - 1)
        x, y = self.screen_points[whole]
        if whole == len(self.screen_points) - 1:
            return x, y
        nx, ny = self.screen_points[whole + 1]
        part = amount - whole
        return x + (nx - x) * part, y + (ny - y) * part
