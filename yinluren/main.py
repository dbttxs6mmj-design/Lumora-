from dotenv import load_dotenv
load_dotenv(override=True)  # .env 為唯一真實來源，覆蓋系統殘留之舊環境變數（避免用到失效金鑰）

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from yinluren.api.routes import router
from yinluren.db import init_db, purge_delivery_demo_profiles

app = FastAPI(title="Lumora", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 只註冊一次，不要再加 prefix
app.include_router(router)


@app.on_event("startup")
def on_startup():
    init_db()
    purge_delivery_demo_profiles()


# ─── 同源直供前端（部署用：一個網址同時給 UI + API）───
from pathlib import Path as _Path
from fastapi.responses import FileResponse as _FileResponse, JSONResponse as _JSONResponse

_FRONTEND_DIR = _Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.is_dir():

    @app.get("/", include_in_schema=False)
    def _serve_index():
        return _FileResponse(str(_FRONTEND_DIR / "index.html"))

    @app.get("/{asset_path:path}", include_in_schema=False)
    def _serve_spa(asset_path: str):
        if asset_path.startswith("api/"):
            return _JSONResponse({"detail": "Not Found"}, status_code=404)
        target = (_FRONTEND_DIR / asset_path).resolve()
        if _FRONTEND_DIR in target.parents and target.is_file():
            return _FileResponse(str(target))
        return _FileResponse(str(_FRONTEND_DIR / "index.html"))
