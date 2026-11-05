import logging
import time

import redis

from app.tasks import work_once

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")


def main() -> None:
    logger.info("Воркер запущен")
    while True:
        try:
            work_once()
        except redis.RedisError as e:
            logger.error("Ошибка redis: %s, повтор через 1с", e)
            time.sleep(1)


if __name__ == "__main__":
    main()
