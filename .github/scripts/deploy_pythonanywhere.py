#!/usr/bin/env python3
"""Деплой приложения на PythonAnywhere через официальный API.

Запускается из GitHub Actions после успешных тестов. Скрипт создаёт
временную Bash-консоль на PythonAnywhere, обновляет код до текущей
версии ветки main, при изменении requirements.txt ставит зависимости
и перезагружает веб-приложение.

Обязательные переменные окружения:
    PYTHONANYWHERE_API_TOKEN — токен из Account → API Token.

Необязательные переменные окружения (значения по умолчанию рассчитаны
на аккаунт vls2693):
    PA_USERNAME    — имя пользователя PythonAnywhere;
    PA_DOMAIN      — домен веб-приложения;
    PA_PROJECT_DIR — каталог с кодом на сервере;
    PA_VENV        — путь к virtualenv на сервере;
    PA_HOST        — www.pythonanywhere.com (US) или eu.pythonanywhere.com (EU);
    PA_REPO_URL    — URL репозитория для git fetch.

Если каталог проекта ещё не является git-репозиторием, скрипт инициализирует
его сам. Каталог должен содержать app.py — это защита от деплоя не туда.
"""

import json
import os
import shlex
import sys
import time
import urllib.error
import urllib.request

DEFAULT_USERNAME = "vls2693"
DEFAULT_DOMAIN = "vls2693.pythonanywhere.com"
DEFAULT_HOST = "www.pythonanywhere.com"
DEFAULT_REPO_URL = "https://github.com/vls2693/common_calculator.git"

POLL_INTERVAL_SECONDS = 5
CONSOLE_START_ATTEMPTS = 3
DEPLOY_TIMEOUT_SECONDS = 15 * 60
SUCCESS_MARKER = "DEPLOY_OK"
ERROR_MARKER = "DEPLOY_ERROR"


def env(name, default=""):
    return os.environ.get(name, default).strip()


def api_url(host, username, path):
    return f"https://{host}/api/v0/user/{username}/{path}"


def api_request(method, url, token, payload=None, timeout=30):
    """Выполняет запрос к API и возвращает (http_status, тело_ответа)."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Token {token}")
    request.add_header("Accept", "application/json")
    request.add_header("Accept-Encoding", "identity")
    if data is not None:
        request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            return response.status, body
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def parse_json(body, context):
    """Разбирает JSON и показывает тело ответа, если формат неожиданный."""
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        snippet = body.strip()[:500] or "<пустой ответ>"
        raise RuntimeError(
            f"{context}: API вернул не JSON ({error}). Ответ: {snippet!r}"
        ) from error


def check_token(host, username, token):
    """Проверяет токен дешёвым запросом, чтобы ошибка была понятной."""
    status, body = api_request(
        "GET", api_url(host, username, "webapps/"), token
    )
    if status >= 400:
        raise RuntimeError(
            f"PythonAnywhere API отклонил токен: HTTP {status}. "
            f"Проверьте секрет PYTHONANYWHERE_API_TOKEN. Ответ: {body[:300]!r}"
        )
    return parse_json(body, "Список веб-приложений")


def build_command(
    project_dir, venv, username, domain, host=DEFAULT_HOST, repo_url=DEFAULT_REPO_URL
):
    """Собирает shell-команду, которая выполнится в консоли на сервере."""
    quote = shlex.quote
    reload_url = api_url(host, username, f"webapps/{domain}/reload/")
    wsgi_file = f"/var/www/{domain.replace('.', '_')}_wsgi.py"
    pip = f"{venv}/bin/pip"
    remote_url = quote(repo_url)

    return "\n".join(
        [
            "set -e",
            f"trap 'echo \"{ERROR_MARKER}: command failed\"' ERR",
            f"cd {quote(project_dir)}",
            "if [ ! -d .git ]; then",
            (
                '  if [ ! -f app.py ]; then '
                f'echo "{ERROR_MARKER}: {project_dir} is not the project directory"; '
                "exit 1; fi"
            ),
            "  git init -q",
            "fi",
            (
                "git remote get-url origin > /dev/null 2>&1 "
                f"&& git remote set-url origin {remote_url} "
                f"|| git remote add origin {remote_url}"
            ),
            "OLD_REV=$(git rev-parse HEAD 2>/dev/null || true)",
            "git fetch --depth=1 origin main",
            "git reset --hard FETCH_HEAD",
            "NEW_REV=$(git rev-parse HEAD)",
            (
                'if [ -z "$OLD_REV" ] || '
                '! git diff --quiet "$OLD_REV" "$NEW_REV" -- requirements.txt; then'
            ),
            f"  if [ -x {quote(pip)} ]; then",
            f"    {quote(pip)} install --no-cache-dir -r requirements.txt",
            "  else",
            (
                f'    echo "WARNING: {pip} not found, '
                'dependencies were not updated"'
            ),
            "  fi",
            "fi",
            'if [ -n "$API_TOKEN" ]; then',
            (
                "  curl -fsS -X POST "
                f'-H "Authorization: Token $API_TOKEN" {quote(reload_url)} '
                "> /dev/null"
            ),
            "else",
            f"  touch {quote(wsgi_file)}",
            "fi",
            f'echo "{SUCCESS_MARKER} $NEW_REV"',
        ]
    )


def get_or_create_console(host, username, token, project_dir):
    """Возвращает (id консоли, создана_ли_нами).

    Сначала пытаемся переиспользовать существующую bash-консоль: на бесплатном
    плане их не больше двух, а создание новой через API не всегда возвращает
    тело ответа. Если консолей нет — создаём свою и потом удаляем.
    """
    status, body = api_request(
        "GET", api_url(host, username, "consoles/"), token
    )
    if status < 400 and body.strip():
        try:
            consoles = json.loads(body)
        except json.JSONDecodeError:
            consoles = []
        if isinstance(consoles, list):
            for console in consoles:
                if not isinstance(console, dict):
                    continue
                if console.get("executable") not in ("bash", "sh"):
                    continue
                console_id = console.get("id")
                if console_id is not None:
                    print(f"Использую существующую консоль {console_id}.")
                    return console_id, False

    status, body = api_request(
        "POST",
        api_url(host, username, "consoles/"),
        token,
        {"executable": "bash", "working_directory": project_dir},
    )
    if status >= 400:
        raise RuntimeError(
            f"Не удалось создать консоль: HTTP {status}. Ответ: {body[:300]!r}"
        )

    console_id = None
    if body.strip():
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            console_id = data.get("id")
    if console_id is None:
        # Некоторые версии API отвечают на создание пустым телом —
        # тогда id берём из списка консолей.
        status, body = api_request(
            "GET", api_url(host, username, "consoles/"), token
        )
        data = parse_json(body, "Список консолей после создания")
        if isinstance(data, list) and data:
            console_id = max(
                (c.get("id") for c in data if isinstance(c, dict)),
                key=lambda value: value if isinstance(value, int) else -1,
                default=None,
            )
    if console_id is None:
        raise RuntimeError(
            f"PythonAnywhere не вернул id консоли: {body[:300]!r}"
        )
    print(f"Создана временная консоль {console_id}.")
    return console_id, True


def send_input(host, username, token, console_id, command):
    status, body = api_request(
        "POST",
        api_url(host, username, f"consoles/{console_id}/send_input/"),
        token,
        {"input": command + "\n"},
    )
    if status >= 400:
        raise RuntimeError(
            f"Не удалось отправить команду в консоль: HTTP {status}. "
            f"Ответ: {body[:300]!r}"
        )


def latest_output(host, username, token, console_id):
    status, body = api_request(
        "GET",
        api_url(host, username, f"consoles/{console_id}/get_latest_output/"),
        token,
    )
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body
    if isinstance(data, dict):
        return str(data.get("output") or data.get("latest_output") or data)
    return str(data)


def delete_console(host, username, token, console_id):
    try:
        api_request(
            "DELETE",
            api_url(host, username, f"consoles/{console_id}/"),
            token,
        )
    except Exception as error:  # noqa: BLE001 - удаление не должно ломать деплой
        print(f"Не удалось удалить временную консоль {console_id}: {error}")


def run_deploy(
    token, username, domain, project_dir, venv, host, repo_url=DEFAULT_REPO_URL
):
    command = build_command(
        project_dir, venv, username, domain, host, repo_url
    )
    console_id = None
    console_created = False

    try:
        check_token(host, username, token)
        console_id, console_created = get_or_create_console(
            host, username, token, project_dir
        )

        for attempt in range(1, CONSOLE_START_ATTEMPTS + 1):
            try:
                send_input(host, username, token, console_id, command)
                break
            except Exception:
                if attempt == CONSOLE_START_ATTEMPTS:
                    raise
                time.sleep(3)

        deadline = time.monotonic() + DEPLOY_TIMEOUT_SECONDS
        last_output = ""

        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_SECONDS)
            output = latest_output(host, username, token, console_id)
            if output and output != last_output:
                print(output)
                last_output = output

            if SUCCESS_MARKER in output:
                print("Деплой на PythonAnywhere завершён успешно.")
                return 0

            if ERROR_MARKER in output:
                print("::error::Деплой на PythonAnywhere завершился с ошибкой.")
                return 1

        print(
            "::error::Деплой не завершился за "
            f"{DEPLOY_TIMEOUT_SECONDS // 60} минут. Последний вывод консоли:"
        )
        print(last_output)
        return 1

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        print(f"::error::PythonAnywhere API вернул {error.code}: {body}")
        return 1
    except Exception as error:  # noqa: BLE001 - показываем причину в логе Actions
        print(f"::error::Не удалось выполнить деплой: {error}")
        return 1
    finally:
        if console_id is not None and console_created:
            delete_console(host, username, token, console_id)


def main():
    username = env("PA_USERNAME", DEFAULT_USERNAME)
    domain = env("PA_DOMAIN", DEFAULT_DOMAIN)
    host = env("PA_HOST", DEFAULT_HOST)
    repo_url = env("PA_REPO_URL", DEFAULT_REPO_URL)
    project_dir = env("PA_PROJECT_DIR", f"/home/{username}/common_calculator")
    venv = env("PA_VENV", f"/home/{username}/.virtualenvs/myenv")

    if "--print-command" in sys.argv:
        print(build_command(project_dir, venv, username, domain, host, repo_url))
        return 0

    token = env("PYTHONANYWHERE_API_TOKEN")
    if not token:
        print(
            "::warning::Секрет PYTHONANYWHERE_API_TOKEN не задан — "
            "деплой пропущен."
        )
        print(
            "Добавьте токен в Settings → Secrets and variables → Actions → "
            "New repository secret."
        )
        return 0

    print(f"Деплой в {domain}: {project_dir}")
    return run_deploy(
        token, username, domain, project_dir, venv, host, repo_url
    )


if __name__ == "__main__":
    sys.exit(main())
