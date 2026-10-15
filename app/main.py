import logging

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cloudbox")

app = FastAPI(title="CloudBox")

def fibonacci(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/fibonacci/{index}")
def get_fibonacci(index: int):
    logger.info("Запрос /fibonacci/%s", index)
    if index < 0:
        logger.warning("Некорректный index=%s", index)
        raise HTTPException(status_code=400, detail="index must be >= 0")

    start = time.time()
    value = fibonacci(index)
    seconds = time.time() - start
    
    return {"index": index, "value": value, "time": seconds}

# Отдаём index.html при заходе на "/" и раздаём остальные статические файлы
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")