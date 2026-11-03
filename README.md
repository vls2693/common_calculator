# Общий калькулятор

Веб-калькулятор для честного разделения общих расходов. Участники указывают, сколько каждый уже потратил, а приложение считает средний расход и минимальный набор переводов между ними.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Приложение будет доступно на `http://127.0.0.1:5000`.

## Деплой на PythonAnywhere

Сайт: **https://vls2693.pythonanywhere.com**

Автодеплой работает так:

1. Push в `main` запускает GitHub Actions.
2. Сначала выполняются тесты.
3. Если тесты прошли, workflow через официальный PythonAnywhere API создаёт временную Bash-консоль на сервере.
4. Консоль делает `git fetch` + `git reset --hard origin/main`. Если `requirements.txt` изменился, зависимости обновляются.
5. Веб-приложение перезагружается через API, временная консоль удаляется.

У PythonAnywhere нет GitHub-интеграции как у Heroku, а на бесплатном плане нет SSH, поэтому используется API-токен. Токен хранится в GitHub Secrets и его можно отозвать в любой момент.

### Одноразовая настройка

1. **Создайте API-токен.** PythonAnywhere → **Account** → **API Token** → **Generate**. Скопируйте токен.
2. **Добавьте токен в GitHub.** Репозиторий → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Имя: `PYTHONANYWHERE_API_TOKEN`.
3. **Проверьте пути.** На PythonAnywhere откройте **Web** и запомните:
   - **Source code** — каталог с кодом;
   - **Virtualenv** — путь к виртуальному окружению.

   Значения по умолчанию в workflow: `/home/vls2693/common_calculator` и `/home/vls2693/.virtualenvs/common_calc`. Если у вас другие пути, создайте переменные репозитория (**Settings → Secrets and variables → Actions → Variables**): `PA_PROJECT_DIR` и `PA_VENV`. Дополнительно можно задать `PA_DOMAIN` и `PA_USERNAME`.
4. **Подготовьте git-репозиторий на сервере.** Откройте Bash-консоль на PythonAnywhere и выполните (подставьте путь из **Source code**):

   ```bash
   cd /home/vls2693/common_calculator
   git init -q
   git remote add origin https://github.com/vls2693/common_calculator.git 2>/dev/null || \
     git remote set-url origin https://github.com/vls2693/common_calculator.git
   git fetch --depth=1 origin main
   git checkout -f -B main FETCH_HEAD
   ```

   Команда `git checkout -f` заменит файлы приложения в этом каталоге версией из GitHub.
5. **Установите зависимости** в окружение из вкладки **Web**:

   ```bash
   /home/vls2693/.virtualenvs/common_calc/bin/pip install -r requirements.txt
   ```

   Если виртуального окружения нет, создайте его. Версия Python в окружении должна совпадать с версией на вкладке **Web**:

   ```bash
   python3 -m venv /home/vls2693/.virtualenvs/common_calc
   /home/vls2693/.virtualenvs/common_calc/bin/pip install --upgrade pip
   /home/vls2693/.virtualenvs/common_calc/bin/pip install -r requirements.txt
   ```

   После этого укажите этот путь в **Web → Virtualenv** и в переменной `PA_VENV`.
6. **Настройте WSGI-файл.** На вкладке **Web** откройте ссылку **WSGI configuration file** и замените содержимое на:

   ```python
   import sys

   path = "/home/vls2693/common_calculator"
   if path not in sys.path:
       sys.path.insert(0, path)

   from wsgi import application
   ```

   Сохраните файл и нажмите **Reload**.
7. **Проверьте сайт** по адресу https://vls2693.pythonanywhere.com. После этого каждый push в `main` будет деплоиться автоматически.

### Ручной запуск деплоя

GitHub → **Actions** → **CI** → **Run workflow**. Деплой выполнится только для ветки `main` и только после успешных тестов.

### Ограничения бесплатного плана

- 100 CPU-секунд в день. Поэтому зависимости переустанавливаются только при изменении `requirements.txt`.
- Веб-приложение нужно периодически продлевать на вкладке **Web**.
- SSH недоступен, поэтому используется API-токен.

## Возможности

- Добавление и удаление участников прямо в форме.
- Живой подсчёт общей суммы.
- Поддержка дробных сумм (точка или запятая) и сумм с пробелами.
- Поле суммы принимает только цифры и один десятичный разделитель — буквы и лишние символы отфильтровываются сразу при вводе и вставке.
- Адаптивный интерфейс для телефонов, планшетов и десктопа.
- Автоматическая тёмная тема по системным настройкам.
- Печать результата.
- Понятные ошибки валидации без потери введённых данных.
- Обработка ошибок 400, 403, 404, 405, 413 и 500.

## Правила валидации

- Участник должен быть хотя бы один.
- Имена не должны повторяться.
- Сумма должна быть числом от 0 до 1 000 000 000.
- Максимум 100 участников на сервере (30 при добавлении через интерфейс).
- Суммы округляются до копеек.

## Тесты

```bash
python -m unittest discover -s tests -v
```
