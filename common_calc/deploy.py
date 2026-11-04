"""Деплой приложения по защищённому HTTP-запросу.

GitHub Actions после успешных тестов вызывает ``POST /deploy`` с секретным
токеном. Приложение обновляет код из GitHub, при необходимости ставит
зависимости и перезагружает веб-приложение. Такой способ работает на
бесплатном плане PythonAnywhere, где API консолей требует консоль,
предварительно открытую в браузере.
"""

import hmac
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REPO_URL = "https://github.com/vls2693/common_calculator.git"
DEFAULT_TOKEN_FILE = "/home/vls2693/.common_calc_deploy_token"
DEFAULT_WSGI_FILE = "/var/www/vls2693_pythonanywhere_com_wsgi.py"

FETCH_TIMEOUT_SECONDS = 120
PIP_TIMEOUT_SECONDS = 600
RELOAD_DELAY_SECONDS = 2
OUTPUT_LIMIT = 2000

_deploy_lock = threading.Lock()

# В консолях PythonAnywhere git иногда отсутствует в PATH, но он есть
# в /usr/bin. Веб-приложение не должно зависеть от настроек .bashrc.
GIT = shutil.which("git") or "/usr/bin/git"


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def deploy_token():
    """Токен из переменной окружения или из файла вне репозитория."""
    token = _env("DEPLOY_TOKEN")
    if token:
        return token
    try:
        return Path(
            _env("DEPLOY_TOKEN_FILE", DEFAULT_TOKEN_FILE)
        ).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def token_matches(provided):
    expected = deploy_token()
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided, expected)


def current_revision():
    """Текущий коммит рабочей копии или пустая строка."""
    try:
        result = subprocess.run(
            [GIT, "rev-parse", "HEAD"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _reload_url():
    username = _env("PA_USERNAME", "vls2693")
    domain = _env("PA_DOMAIN", "vls2693.pythonanywhere.com")
    host = _env("PA_HOST", "www.pythonanywhere.com")
    return (
        f"https://{host}/api/v0/user/{username}/webapps/{domain}/reload/"
    )


def _reload_app():
    """Просит PythonAnywhere перезагрузить приложение.

    В веб-приложении PythonAnywhere доступна переменная API_TOKEN, поэтому
    обычно используется официальный reload-эндпоинт. Если токена нет,
    остаётся коснуться WSGI-файла — PythonAnywhere перезагрузит приложение.
    """
    api_token = os.environ.get("API_TOKEN", "").strip()
    if api_token:
        request = urllib.request.Request(
            _reload_url(),
            data=b"",
            method="POST",
            headers={"Authorization": f"Token {api_token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30):
                return
        except Exception:  # noqa: BLE001 - пробуем запасной вариант
            pass

    try:
        Path(_env("DEPLOY_WSGI_FILE", DEFAULT_WSGI_FILE)).touch()
    except OSError:
        pass


def _run(args, timeout):
    return subprocess.run(
        args,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _tail(text):
    return (text or "").strip()[-OUTPUT_LIMIT:]


def run_deploy(commit=""):
    """Обновляет код до указанного коммита и возвращает результат.

    ``commit`` — полный SHA из GitHub Actions. Если он не передан,
    разворачивается последний коммит ветки ``main``.
    """
    target = (commit or "").strip().lower()
    if target and not re.fullmatch(r"[0-9a-f]{40}", target):
        return {
            "ok": False,
            "step": "commit",
            "detail": "Ожидался полный SHA коммита из 40 hex-символов.",
        }

    if not _deploy_lock.acquire(blocking=False):
        return {
            "ok": False,
            "step": "busy",
            "detail": "Деплой уже выполняется.",
        }

    try:
        repo_url = _env("DEPLOY_REPO_URL", DEFAULT_REPO_URL)
        old_rev = current_revision()

        remote = _run([GIT, "remote", "get-url", "origin"], 15)
        if remote.returncode == 0:
            _run([GIT, "remote", "set-url", "origin", repo_url], 15)
        else:
            _run([GIT, "remote", "add", "origin", repo_url], 15)

        fetch = _run(
            [GIT, "fetch", "--depth=1", "origin", target or "main"],
            FETCH_TIMEOUT_SECONDS,
        )
        if fetch.returncode != 0:
            return {
                "ok": False,
                "step": "fetch",
                "detail": _tail(fetch.stderr),
            }

        reset = _run(
            [GIT, "reset", "--hard", "FETCH_HEAD"], FETCH_TIMEOUT_SECONDS
        )
        if reset.returncode != 0:
            return {
                "ok": False,
                "step": "reset",
                "detail": _tail(reset.stderr),
            }

        new_rev = current_revision()
        requirements_changed = True
        if old_rev:
            diff = _run(
                [
                    GIT,
                    "diff",
                    "--quiet",
                    old_rev,
                    new_rev,
                    "--",
                    "requirements.txt",
                ],
                30,
            )
            requirements_changed = diff.returncode != 0

        pip_output = ""
        if requirements_changed:
            pip = Path(_env("DEPLOY_VENV", sys.prefix)) / "bin" / "pip"
            if not pip.exists():
                return {
                    "ok": False,
                    "step": "pip",
                    "detail": f"Не найден {pip}.",
                }
            install = _run(
                [
                    str(pip),
                    "install",
                    "--no-cache-dir",
                    "-r",
                    "requirements.txt",
                ],
                PIP_TIMEOUT_SECONDS,
            )
            pip_output = _tail(install.stdout + install.stderr)
            if install.returncode != 0:
                return {
                    "ok": False,
                    "step": "pip",
                    "detail": pip_output,
                }

        threading.Timer(RELOAD_DELAY_SECONDS, _reload_app).start()
        return {
            "ok": True,
            "old": old_rev,
            "new": new_rev,
            "requirements_changed": requirements_changed,
            "pip": pip_output,
        }
    except subprocess.TimeoutExpired as error:
        return {"ok": False, "step": "timeout", "detail": str(error)}
    except Exception as error:  # noqa: BLE001 - причина уйдёт в лог Actions
        return {"ok": False, "step": "error", "detail": str(error)}
    finally:
        _deploy_lock.release()
