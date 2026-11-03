import logging
import math
from itertools import zip_longest

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from common_calc.base import receiver
from common_calc.errors import CalculationError

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # 1 МБ более чем достаточно
app.logger.setLevel(logging.INFO)

HTTP_ERRORS = {
    400: (
        "Некорректный запрос",
        "Сервер не смог обработать запрос. Вернитесь назад и проверьте данные.",
    ),
    403: (
        "Доступ запрещён",
        "У вас нет доступа к этой странице.",
    ),
    404: (
        "Страница не найдена",
        "Похоже, такой страницы не существует. Вернитесь к калькулятору и попробуйте снова.",
    ),
    405: (
        "Метод не поддерживается",
        "Этот адрес не принимает такой тип запроса.",
    ),
    413: (
        "Слишком большой запрос",
        "Данных слишком много. Уменьшите количество участников и попробуйте снова.",
    ),
    500: (
        "Что-то пошло не так",
        "Внутренняя ошибка сервера. Мы уже записали её в лог — попробуйте ещё раз.",
    ),
}


def format_money(value):
    """Форматирует число как сумму в рублях: 1 234,50 ₽."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"

    formatted = f"{number:,.2f}".replace(",", "\u00a0").replace(".", ",")
    if formatted.endswith(",00"):
        formatted = formatted[:-3]
    return f"{formatted}\u00a0₽"


app.add_template_filter(format_money, "rub")


def submitted_rows(form):
    """Возвращает введённые строки, чтобы не терять данные при ошибке."""
    names = form.getlist("name")
    sums = form.getlist("sum")
    rows = [
        {"name": name, "sum": amount}
        for name, amount in zip_longest(names, sums, fillvalue="")
    ]
    while len(rows) < 2:
        rows.append({"name": "", "sum": ""})
    return rows


def error_page(status_code, title, message):
    return (
        render_template(
            "error.html",
            status_code=status_code,
            error_title=title,
            error_message=message,
        ),
        status_code,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", rows=submitted_rows(request.form))

    try:
        participants, amount, average, debts, overpays, transactions = receiver(
            request.form
        )
    except CalculationError as error:
        app.logger.info("Ошибка валидации формы: %s", error)
        return (
            render_template(
                "index.html",
                rows=submitted_rows(request.form),
                form_error=error.message,
                error_field=error.field,
            ),
            400,
        )

    return render_template(
        "result.html",
        participants=participants,
        total=amount,
        average=average,
        debts=debts,
        overpays=overpays,
        transactions=transactions,
    )


@app.errorhandler(HTTPException)
def handle_http_error(error):
    title, message = HTTP_ERRORS.get(
        error.code,
        (
            "Ошибка",
            "Не удалось обработать запрос. Попробуйте вернуться на главную страницу.",
        ),
    )
    if error.code and error.code >= 500:
        app.logger.error("HTTP %s: %s", error.code, error.description)
    return error_page(error.code or 500, title, message)


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return handle_http_error(error)

    app.logger.exception("Необработанная ошибка при обработке запроса")
    title, message = HTTP_ERRORS[500]
    return error_page(500, title, message)


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


if __name__ == "__main__":
    app.run()
