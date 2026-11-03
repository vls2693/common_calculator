(function () {
    "use strict";

    var form = document.getElementById("expense-form");
    if (!form) {
        return;
    }

    var people = document.getElementById("people");
    var template = document.getElementById("person-template");
    var addButton = document.getElementById("add-row");
    var resetButton = document.getElementById("reset-form");
    var totalElement = document.getElementById("total-amount");
    var countElement = document.getElementById("people-count");
    var errorBox = document.getElementById("form-error");
    var submitButton = form.querySelector('button[type="submit"]');
    var submitLabel = submitButton.querySelector(".btn-label");

    var MIN_PEOPLE = 2;
    var MAX_PEOPLE = 30;
    var MAX_AMOUNT = 1000000000;
    var MAX_DECIMALS = 2;

    var moneyFormatter = new Intl.NumberFormat("ru-RU", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    function rows() {
        return Array.prototype.slice.call(people.querySelectorAll(".person-row"));
    }

    function formatMoney(value) {
        var formatted = moneyFormatter.format(value).replace(",00", "");
        return formatted + "\u00a0₽";
    }

    function sanitizeAmount(rawValue) {
        var cleaned = rawValue.replace(/[^\d.,]/g, "");
        var result = "";
        var hasSeparator = false;
        var decimals = 0;

        for (var i = 0; i < cleaned.length; i += 1) {
            var character = cleaned.charAt(i);

            if (character === "," || character === ".") {
                if (!hasSeparator) {
                    hasSeparator = true;
                    result += character;
                }
                continue;
            }

            if (hasSeparator && decimals >= MAX_DECIMALS) {
                continue;
            }
            if (hasSeparator) {
                decimals += 1;
            }
            result += character;
        }

        if (result.charAt(0) === "," || result.charAt(0) === ".") {
            result = "0" + result;
        }
        return result;
    }

    function filterAmountInput(input) {
        var rawValue = input.value;
        var caret = typeof input.selectionStart === "number"
            ? input.selectionStart
            : rawValue.length;
        var caretValue = sanitizeAmount(rawValue.slice(0, caret));
        var sanitized = sanitizeAmount(rawValue);

        if (sanitized !== rawValue) {
            input.value = sanitized;
            var position = Math.min(caretValue.length, sanitized.length);
            input.setSelectionRange(position, position);
        }
        return sanitized;
    }

    function normalizeAmountInput(input) {
        filterAmountInput(input);
        var normalized = input.value.replace(/[.,]$/, "");
        if (normalized !== input.value) {
            input.value = normalized;
        }
        return normalized;
    }

    function parseAmount(rawValue) {
        var normalized = rawValue
            .replace(/\s|\u00a0/g, "")
            .replace(",", ".");
        if (!normalized) {
            return NaN;
        }
        var value = Number(normalized);
        return Number.isFinite(value) ? value : NaN;
    }

    function hideError() {
        if (errorBox) {
            errorBox.hidden = true;
            errorBox.textContent = "";
        }
    }

    function showError(message) {
        if (errorBox) {
            errorBox.textContent = message;
            errorBox.hidden = false;
        }
    }

    function updateSummary() {
        var currentRows = rows();
        var total = currentRows.reduce(function (sum, row) {
            var input = row.querySelector('input[name="sum"]');
            var value = parseAmount(input.value);
            return sum + (Number.isFinite(value) && value > 0 ? value : 0);
        }, 0);

        countElement.textContent = String(currentRows.length);
        totalElement.textContent = formatMoney(Math.round(total * 100) / 100);

        addButton.disabled = currentRows.length >= MAX_PEOPLE;

        var removeButtons = people.querySelectorAll(".remove-row");
        Array.prototype.forEach.call(removeButtons, function (button, index) {
            button.disabled = currentRows.length <= MIN_PEOPLE;
            button.setAttribute(
                "aria-label",
                "Удалить участника " + (index + 1)
            );
            button.setAttribute(
                "title",
                currentRows.length <= MIN_PEOPLE
                    ? "Должно остаться хотя бы два участника"
                    : "Удалить участника " + (index + 1)
            );
        });
    }

    function refreshRows() {
        rows().forEach(function (row, index) {
            var nameInput = row.querySelector('input[name="name"]');
            var sumInput = row.querySelector('input[name="sum"]');
            var nameLabel = row.querySelector(".field-name label");
            var sumLabel = row.querySelector(".field-amount label");
            var position = index + 1;

            nameInput.id = "name-" + position;
            sumInput.id = "sum-" + position;
            nameLabel.htmlFor = nameInput.id;
            sumLabel.htmlFor = sumInput.id;
        });

        updateSummary();
    }

    function addRow() {
        if (rows().length >= MAX_PEOPLE) {
            return null;
        }

        var fragment = template.content.cloneNode(true);
        var row = fragment.querySelector(".person-row");
        people.appendChild(fragment);
        refreshRows();
        row.classList.add("is-new");
        window.setTimeout(function () {
            row.classList.remove("is-new");
        }, 320);
        return row;
    }

    addButton.addEventListener("click", function () {
        var row = addRow();
        if (row) {
            row.querySelector('input[name="name"]').focus();
        }
    });

    people.addEventListener("click", function (event) {
        var button = event.target.closest(".remove-row");
        if (!button || rows().length <= MIN_PEOPLE) {
            return;
        }
        button.closest(".person-row").remove();
        refreshRows();
    });

    people.addEventListener("beforeinput", function (event) {
        if (!event.target.matches('input[name="sum"]')) {
            return;
        }
        if (
            event.inputType === "insertText" &&
            event.data &&
            /[^\d.,]/.test(event.data)
        ) {
            event.preventDefault();
        }
    });

    people.addEventListener("input", function (event) {
        if (!event.target.matches("input")) {
            return;
        }
        if (event.target.matches('input[name="sum"]')) {
            filterAmountInput(event.target);
        }
        event.target.setCustomValidity("");
        hideError();
        updateSummary();
    });

    people.addEventListener("focusout", function (event) {
        if (!event.target.matches('input[name="sum"]')) {
            return;
        }
        normalizeAmountInput(event.target);
        updateSummary();
    });

    form.addEventListener("submit", function (event) {
        var currentRows = rows();
        var firstInvalid = null;
        var names = Object.create(null);

        currentRows.forEach(function (row) {
            var nameInput = row.querySelector('input[name="name"]');
            var sumInput = row.querySelector('input[name="sum"]');
            var name = nameInput.value.trim();
            var key = name.toLocaleLowerCase();

            nameInput.value = name;
            nameInput.setCustomValidity("");
            sumInput.setCustomValidity("");
            normalizeAmountInput(sumInput);

            var value = parseAmount(sumInput.value);

            if (!name) {
                nameInput.setCustomValidity("Укажите имя участника.");
                firstInvalid = firstInvalid || nameInput;
            } else if (names[key]) {
                nameInput.setCustomValidity("Имена не должны повторяться.");
                names[key].setCustomValidity("Имена не должны повторяться.");
                firstInvalid = firstInvalid || nameInput;
            } else {
                names[key] = nameInput;
            }

            if (!sumInput.value.trim()) {
                sumInput.setCustomValidity("Укажите сумму расходов.");
                firstInvalid = firstInvalid || sumInput;
            } else if (!Number.isFinite(value)) {
                sumInput.setCustomValidity(
                    "Введите число, например 1500 или 1500,50."
                );
                firstInvalid = firstInvalid || sumInput;
            } else if (value < 0) {
                sumInput.setCustomValidity("Сумма не может быть отрицательной.");
                firstInvalid = firstInvalid || sumInput;
            } else if (value > MAX_AMOUNT) {
                sumInput.setCustomValidity("Слишком большая сумма.");
                firstInvalid = firstInvalid || sumInput;
            }
        });

        if (firstInvalid) {
            event.preventDefault();
            showError("Проверьте выделенные поля и попробуйте снова.");
            firstInvalid.reportValidity();
            firstInvalid.focus();
            return;
        }

        hideError();
        submitButton.disabled = true;
        submitLabel.textContent = "Считаем…";
    });

    resetButton.addEventListener("click", function () {
        var firstRow = rows()[0];
        firstRow.querySelectorAll("input").forEach(function (input) {
            input.value = "";
            input.setCustomValidity("");
        });

        while (rows().length > 1) {
            rows()[rows().length - 1].remove();
        }

        while (rows().length < MIN_PEOPLE) {
            addRow();
        }

        refreshRows();
        hideError();
        rows()[0].querySelector('input[name="name"]').focus();
    });

    window.addEventListener("pageshow", function () {
        submitButton.disabled = false;
        submitLabel.textContent = "Рассчитать";
    });

    var serverError = document.querySelector(".alert[data-error-field]");
    if (serverError) {
        var fieldId = serverError.getAttribute("data-error-field");
        var field = fieldId ? document.getElementById(fieldId) : null;
        if (field) {
            var row = field.closest(".person-row");
            if (row) {
                row.classList.add("has-error");
            }
            field.focus();
            if (typeof field.select === "function") {
                field.select();
            }
        } else {
            serverError.focus();
        }
    }

    refreshRows();
})();
