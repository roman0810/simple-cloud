from fastapi import FastAPI, HTTPException

app = FastAPI(title="CloudBox")

def fibonacci(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

@app.get("/fibonacci/{index}")
def get_fibonacci(index: int):
    if index < 0:
        raise HTTPException(status_code=400, detail="index must be >= 0")
    return {"index": index, "value": fibonacci(index)}