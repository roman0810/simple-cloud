"""Нагрузочный тест поднятого сервиса.

Пример:
    python scripts/load_test.py --url http://127.0.0.1:8000 -n 200 -c 20 --index 100000

Каждый "клиент" создаёт задачу (POST /fibonacci), затем опрашивает
GET /fibonacci/tasks/{id}, пока задача не будет готова.
"""
import argparse
import asyncio
import random
import statistics
import time

import httpx


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * p / 100))]


def report(title: str, values: list[float]) -> None:
    if not values:
        print(f"{title}: нет данных")
        return
    print(
        f"{title}: avg={statistics.mean(values) * 1000:.0f}ms "
        f"p50={percentile(values, 50) * 1000:.0f}ms "
        f"p95={percentile(values, 95) * 1000:.0f}ms "
        f"p99={percentile(values, 99) * 1000:.0f}ms "
        f"max={max(values) * 1000:.0f}ms"
    )


async def one_request(client, args, stats):
    index = random.randint(args.min_index, args.index)
    start = time.perf_counter()
    try:
        r = await client.post("/fibonacci", json={"index": index})
        stats["submit"].append(time.perf_counter() - start)
        if r.status_code != 202:
            stats["errors"].append(f"POST -> {r.status_code}")
            return
        task_id = r.json()["task_id"]
        deadline = start + args.timeout
        while time.perf_counter() < deadline:
            r = await client.get(f"/fibonacci/tasks/{task_id}")
            if r.status_code != 200:
                stats["errors"].append(f"GET -> {r.status_code}")
                return
            status = r.json()["status"]
            if status == "done":
                stats["total"].append(time.perf_counter() - start)
                return
            if status == "failed":
                stats["errors"].append("task failed")
                return
            await asyncio.sleep(args.poll_interval)
        stats["errors"].append("timeout")
    except httpx.HTTPError as e:
        stats["errors"].append(type(e).__name__)


async def main(args):
    stats = {"submit": [], "total": [], "errors": []}
    sem = asyncio.Semaphore(args.concurrency)
    limits = httpx.Limits(max_connections=args.concurrency)

    async with httpx.AsyncClient(base_url=args.url, timeout=30, limits=limits) as client:
        async def bounded():
            async with sem:
                await one_request(client, args, stats)

        print(f"{args.requests} задач, параллельность {args.concurrency}, "
              f"index {args.min_index}..{args.index}, цель {args.url}")
        start = time.perf_counter()
        await asyncio.gather(*(bounded() for _ in range(args.requests)))
        elapsed = time.perf_counter() - start

    ok = len(stats["total"])
    print(f"\nВремя: {elapsed:.2f}s, успешно: {ok}/{args.requests}, "
          f"ошибок: {len(stats['errors'])}, пропускная способность: {ok / elapsed:.1f} задач/с")
    report("Создание задачи  ", stats["submit"])
    report("Задача до ответа ", stats["total"])
    for err in sorted(set(stats["errors"])):
        print(f"  ошибка '{err}': {stats['errors'].count(err)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("-n", "--requests", type=int, default=100, help="сколько задач создать")
    p.add_argument("-c", "--concurrency", type=int, default=10, help="сколько клиентов одновременно")
    p.add_argument("--index", type=int, default=50000, help="максимальный индекс (сервис ограничивает 100000)")
    p.add_argument("--min-index", type=int, default=0)
    p.add_argument("--poll-interval", type=float, default=0.1, help="период опроса результата, сек")
    p.add_argument("--timeout", type=float, default=120, help="сколько ждать одну задачу, сек")
    asyncio.run(main(p.parse_args()))
