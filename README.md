# Учебный репозиторий по WEB-у

Простое приложение на FastAPI: веб-страница в браузере дёргает API-ручку `/fibonacci`, которая считает число Фибоначчи.

## Начало работы

1. Создать и активировать виртуальное окружение:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Установить зависимости:

   ```bash
   pip install -r requirements.txt
   ```

## Запуск сервиса

Активируйте окружение и запустите сервер:

```bash
source venv/bin/activate
uvicorn app.main:app --port 8000 --reload
```

Затем откройте в браузере [http://127.0.0.1:8000](http://127.0.0.1:8000)

Чтобы сервис был доступен по сети, запустите с `--host 0.0.0.0`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Обратите внимание, что порт `обязан` быть свободен. Если кто-то другой занял порт 8000, то воспользуйтесь другим, например 8001.

## Запуск через Docker Compose

Поднимает web, postgres, redis и воркеров:

```bash
# сборка и запуск в фоне (по умолчанию 2 воркера)
docker compose up -d --build

# запуск с 4 воркерами
docker compose up -d --build --scale worker=4

# логи воркеров и остановка
docker compose logs -f worker
docker compose down
```

После запуска сервис доступен на http://127.0.0.1:8000.

## Проверка API напрямую

Вычисление асинхронное: задачи хранятся в redis и обрабатываются воркерами.

```bash
# 1. создать задачу -> {"task_id": "<uuid>"}
curl -X POST http://127.0.0.1:8000/fibonacci -H 'Content-Type: application/json' -d '{"index": 10}'
# 2. получить результат по uuid -> {"status": "pending|running|done|failed", "value": "55", ...}
curl http://127.0.0.1:8000/fibonacci/tasks/<uuid>
```

Число воркеров задаётся в `docker-compose.yml` (`deploy.replicas`) или флагом: `docker compose up --scale worker=4`.

## Health-check

Сервис отдаёт служебную ручку `/health`, чтобы можно было быстро проверить, что он жив (пригодится для Docker healthcheck, k8s probes, мониторинга):

```bash
curl http://127.0.0.1:8000/health
# {"status": "ok"}
```

## Нагрузочный тест

Для поднятого сервиса (`docker compose up`). Нужен `httpx` (`pip install -r requirements.txt`):

```bash
python scripts/load_test.py --url http://127.0.0.1:8000 -n 200 -c 20 --index 100000
```

Скрипт создаёт задачи, дожидается результатов и печатает пропускную способность и задержки (avg/p50/p95/p99). Сравните результаты при разном числе воркеров: `docker compose up --scale worker=1` и `--scale worker=4`. Параметры: `python scripts/load_test.py --help`.

## Логирование

Сервис логирует входящие запросы к `/fibonacci` и предупреждения о некорректных значениях `index` через стандартный модуль `logging`. Логи выводятся в консоль вместе с логами uvicorn — отдельной настройки не требуется.

## Тесты

Проект покрыт тестами на `pytest` (см. `tests/test_main.py`): проверяются обычный случай, граничный случай (`index = 0`), ошибка валидации (`index < 0`), отдача главной страницы и health-check.

```bash
source venv/bin/activate
pytest -v
```
