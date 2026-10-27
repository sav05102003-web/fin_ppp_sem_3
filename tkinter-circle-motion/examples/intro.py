"""Пример 1 из методички: зелёный шарик движется вправо."""

import tkinter as tk


def main() -> None:
    """Запустить пример с Canvas размером 300×200."""
    root = tk.Tk()
    root.title("Пример 1 — знакомство с tkinter")
    canvas = tk.Canvas(root, width=300, height=200, bg="white")
    canvas.pack()
    ball = canvas.create_oval(0, 100, 40, 140, fill="green")

    def motion() -> None:
        """Сдвинуть шарик и назначить следующий кадр до правой границы."""
        canvas.move(ball, 1, 0)
        if canvas.coords(ball)[2] < 300:
            root.after(10, motion)

    motion()
    root.mainloop()


if __name__ == "__main__":
    main()
