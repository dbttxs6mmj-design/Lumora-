from dotenv import load_dotenv
load_dotenv(override=True)

import os
import time
import threading
from collections import defaultdict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse as _JSONResponse

from yinluren.api.routes import router
from yinluren.db import init_db, purge_delivery_demo_profiles

app = FastAPI(title="Lumora", version="0.1.0")

# ─── CORS（修正：allow_credentials 不可與 allow_origins=["*"] 並用）───
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
_allowed_origins: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,   # ← 修正：不使用 cookie-based auth，credentials 設 False
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# ─── 資安標頭 Middleware ───
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # HSTS（僅 HTTPS 生效）
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    # CSP：只允許同源資源 + Fonts CDN（Google Fonts）
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "   # SPA inline script 需要
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' https://api.perplexity.ai https://api.openai.com "
        "https://api.anthropic.com https://generativelanguage.googleapis.com; "
        "frame-ancestors 'none';"
    )
    return response

# ─── 簡易 Rate Limiter（無外部依賴）───
_rate_store: dict = defaultdict(list)
_rate_lock = threading.Lock()

def _check_rate(key: str, limit: int, window_sec: int) -> bool:
    """回傳 True 表示允許，False 表示超速。"""
    now = time.time()
    with _rate_lock:
        timestamps = _rate_store[key]
        # 清掉過期記錄
        _rate_store[key] = [t for t in timestamps if now - t < window_sec]
        if len(_rate_store[key]) >= limit:
            return False
        _rate_store[key].append(now)
        return True

def rate_limit(request: Request, limit: int = 30, window_sec: int = 60):
    """
    每 IP 在 window_sec 秒內最多 limit 次請求。
    超速回 429，讓 routes.py 的 Depends 注入使用。
    """
    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    key = f"{ip}:{path}"
    if not _check_rate(key, limit, window_sec):
        raise _JSONResponse(  # type: ignore[misc]
            content={"detail": "請求過於頻繁，請稍後再試。"},
            status_code=429,
        )

# ─── 路由 ───
app.include_router(router)


@app.on_event("startup")
def on_startup():
    init_db()
    purge_delivery_demo_profiles()


# ─── 同源直供前端（部署用）───
from pathlib import Path as _Path
from fastapi.responses import FileResponse as _FileResponse

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
