"""Главное окно приложения."""

import tkinter as tk


class App:
    """Создать окно для визуализации полярного сердца."""

    def __init__(self) -> None:
        """Подготовить окно и холст."""
        self.root = tk.Tk()
        self.root.title("Сердце в полярных координатах")
        self.root.geometry("1000x760")
        self.canvas = tk.Canvas(self.root, background="#10131e")
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def run(self) -> None:
        """Запустить главный цикл обработки событий."""
        self.root.mainloop()
