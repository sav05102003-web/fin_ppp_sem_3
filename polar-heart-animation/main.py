"""Запустить приложение «Сердце в полярных координатах»."""

from src.app import App


def main() -> None:
    """Создать окно и запустить цикл событий tkinter."""
    App().run()


if __name__ == "__main__":
    main()
