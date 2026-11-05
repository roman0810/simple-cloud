import json
import os
import time
import uuid

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = "fib:queue"
TASK_TTL_SECONDS = 24 * 3600

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def _key(task_id: str) -> str:
    return f"fib:task:{task_id}"


def fibonacci(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def create_task(index: int) -> str:
    """Сохраняет задачу в redis со статусом pending и кладёт её id в очередь."""
    r = get_redis()
    task_id = str(uuid.uuid4())
    r.hset(_key(task_id), mapping={"index": index, "status": "pending"})
    r.expire(_key(task_id), TASK_TTL_SECONDS)
    r.rpush(QUEUE_KEY, task_id)
    return task_id


def get_task(task_id: str) -> dict | None:
    data = get_redis().hgetall(_key(task_id))
    return data or None


def process_task(task_id: str) -> None:
    r = get_redis()
    key = _key(task_id)
    index = r.hget(key, "index")
    if index is None:
        return
    r.hset(key, "status", "running")
    try:
        start = time.time()
        value = fibonacci(int(index))
        r.hset(key, mapping={"status": "done", "value": str(value), "time": time.time() - start})
    except Exception as e:
        r.hset(key, mapping={"status": "failed", "error": str(e)})
    r.expire(key, TASK_TTL_SECONDS)


def work_once(timeout: int = 5) -> bool:
    """Ждёт задачу в очереди и обрабатывает её. Возвращает True, если задача была."""
    item = get_redis().blpop(QUEUE_KEY, timeout=timeout)
    if item is None:
        return False
    process_task(item[1])
    return True
