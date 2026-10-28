# Учебное виртуальное окружение

Каталог создан командой `python -m venv --without-pip venv` на Windows
с Python 3.12.14. В соответствии с методичкой сам каталог `venv/`
не исключён из Git: сохранены конфигурация, интерпретаторы и скрипты активации.

Установленные библиотеки из `site-packages/`, кеши и личные данные
не версионируются. Их точные версии перечислены в `requirements-lock.txt`.
Зависимости установлены в это окружение и использованы при проверках.

Окружения venv зависят от пути и версии базового Python. После клонирования
обязательно пересоздайте окружение и установите библиотеки:

```powershell
python -m venv --clear venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

На macOS/Linux используйте `python3 -m venv --clear venv`, затем
`./venv/bin/python -m pip install -r requirements.txt`.
