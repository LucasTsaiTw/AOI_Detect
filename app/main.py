import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from sqlalchemy.future import select

# 引入 API 路由 (確認你的路徑在 app/api 裡面)
from app.api import auth, inference

# 引入資料庫與模型
from app.database import AsyncSessionLocal, Base, engine

# 引入密碼雜湊模組 (確認你的路徑在 app/core/security.py)
from app.services.security import get_password_hash
from app.user import DBUser


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 系統啟動時：自動建立 SQLite 資料表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. 系統啟動時：檢查並寫入預設 admin 帳號
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DBUser).where(DBUser.username == "admin"))
        if not result.scalars().first():
            default_admin = DBUser(
                username="admin",
                hashed_password=get_password_hash("1234"),
                role="admin",
            )
            db.add(default_admin)
            await db.commit()
            print("\n=========================================")
            print("✅ 預設管理員帳號已建立：admin / 1234")
            print("=========================================\n")

    yield


# 初始化 FastAPI，並掛載 lifespan
app = FastAPI(title="Vision AOI API", lifespan=lifespan)

# ==========================================
# 註冊後端 API 路由
# ==========================================
# 1. 身分驗證與帳號管理 API
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

# 2. AOI 推論與抽樣 API
app.include_router(inference.router, prefix="/api/inference", tags=["Inference"])


# ==========================================
# 渲染前端網頁
# ==========================================
@app.get("/")
async def serve_frontend():
    # 自動抓取目前的專案根目錄 (根據 main.py 的位置往上推一層)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    file_path = os.path.join(base_dir, "app", "static", "index.html")

    # 防呆機制：如果還是找不到檔案，直接把路徑印在網頁上給你看
    if not os.path.exists(file_path):
        return {"detail": f"找不到網頁檔案！系統目前尋找的絕對路徑是：{file_path}"}

    return FileResponse(file_path)
