# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .core.config import settings
from .core.database import init_db
from pathlib import Path

# 确保必要的目录存在
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
    yield
    # 关闭时的清理工作

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（必须在静态文件mount之前）
from .api import tasks, upload, config, translation

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.VERSION}

app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(translation.router, prefix="/api", tags=["translation"])

# 静态文件服务（生产环境）
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    # 挂载静态资源目录（assets等）
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    if (static_dir / "vite.svg").exists():
        app.mount("/vite.svg", StaticFiles(directory=str(static_dir)), name="vite-svg")

# SPA fallback - 对于所有非API路由，返回index.html
@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    """SPA fallback: 返回index.html让Vue Router处理路由"""
    static_dir = Path(__file__).parent.parent / "static"
    index_file = static_dir / "index.html"

    # 如果是API请求但不存在的路径，返回404
    if full_path.startswith("api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    # 对于其他所有路径，返回index.html
    if index_file.exists():
        return FileResponse(index_file)
    return {"detail": "Not Found"}
