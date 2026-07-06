from fastapi import FastAPI

app = FastAPI()


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    return {"path": full_path}
