import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.auth import router as auth_router
from app.db import init_db
from app.tasks import create_task, get_task

MAX_INDEX = 100_000

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cloudbox")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # при старте создаём таблицы в БД
    yield


app = FastAPI(title="CloudBox", lifespan=lifespan)
app.include_router(auth_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}


class FibonacciRequest(BaseModel):
    index: int


@app.post("/fibonacci", status_code=202)
def create_fibonacci_task(body: FibonacciRequest):
    logger.info("Запрос на вычисление fibonacci(%s)", body.index)
    if body.index < 0:
        logger.warning("Некорректный index=%s", body.index)
        raise HTTPException(status_code=400, detail="index must be >= 0")
    if body.index > MAX_INDEX:
        raise HTTPException(status_code=400, detail=f"index must be <= {MAX_INDEX}")
    return {"task_id": create_task(body.index)}


@app.get("/fibonacci/tasks/{task_id}")
def get_fibonacci_result(task_id: str):
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    result = {"task_id": task_id, "status": task["status"], "index": int(task["index"])}
    if task["status"] == "done":
        result["value"] = task["value"]  # строкой: число может не влезть в JS number
        result["time"] = float(task["time"])
    elif task["status"] == "failed":
        result["error"] = task.get("error")
    return result


# Отдаём index.html при заходе на "/" и раздаём остальные статические файлы
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")