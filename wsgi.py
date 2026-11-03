"""WSGI-точка входа для PythonAnywhere.

В WSGI-файле PythonAnywhere достаточно добавить каталог проекта в sys.path
и импортировать application отсюда:

    from wsgi import application
"""

from app import app as application

__all__ = ["application"]
