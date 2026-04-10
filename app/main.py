import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, FastAPI, Form, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from pydantic import BaseModel

from app.backend.testing import get_category_images, predict_specific_image
from app.database import (
    get_db_connection,
    init_db,
    insert_inference_record,
    submit_defect_review,
)

app = FastAPI()

# 使用 bcrypt 將密碼加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==========================================
# JWT 資安防護設定
# ==========================================
SECRET_KEY = "vision_aoi_super_secret_key_2026"  # 私鑰
ALGORITHM = "HS256"  # 加密演算法
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token 有效期限：24 小時

# 宣告 OAuth2 機制，告訴 FastAPI 這是使用 Bearer Token 的 API
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 驗證 Token 是否為真、是否過期，並回傳使用者資料
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無效的憑證或憑證已過期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解碼 JWT，取得使用者名稱和角色資訊
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
    # 抓取 JWT 解碼錯誤，包含過期和無效的 Token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登入已過期，請重新登入")
    except jwt.PyJWTError:
        raise credentials_exception

    # 根據解碼後的使用者名稱從資料庫撈取完整的使用者資料，並回傳給函式使用
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    # 如果找不到使用者資料，代表憑證無效
    if user is None:
        raise credentials_exception
    return dict(user)


# 驗證是否為 IT 管理員
def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="權限不足：此操作限 IT 管理員")
    return current_user


# 驗證是否為品管主管
def require_manager(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "manager":
        raise HTTPException(status_code=403, detail="權限不足：此操作限品管主管")
    return current_user


# ==========================================

# 掛載前端檔案
if os.path.exists("app/frontend"):
    app.mount("/static", StaticFiles(directory="app/frontend"), name="static")


@app.get("/")
def serve_frontend():
    # 指向新的前端資料夾路徑
    html_path = "app/frontend/index.html"
    return (
        FileResponse(html_path)
        if os.path.exists(html_path)
        else {"error": "找不到前端網頁"}
    )


# 啟動時初始化資料庫
@app.on_event("startup")
def startup_event():
    init_db()


# ===== 產生登入帳號的 JWT 登入 API ======
@app.post("/api/auth/login")
def login(username: str = Form(...), password: str = Form(...)):
    # 從資料庫撈取使用者資料，並驗證密碼是否正確
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username.strip(),)
    ).fetchone()
    conn.close()
    # 如果找不到使用者或密碼驗證失敗，回傳錯誤訊息
    if not user or not pwd_context.verify(password.strip(), user["hashed_password"]):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    # 產生登入帳號的的 JWT
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"],
    }


# ====== 取得所有產品類別 (產線產品類別下拉選單) ======
@app.get("/api/categories")
def get_categories(
    current_user: dict = Depends(get_current_user),
):
    # 從資料庫撈取所有啟用中的產品類別，並回傳給前端顯示在下拉選單中
    conn = get_db_connection()
    categories = conn.execute(
        "SELECT category_code, display_name FROM product_categories WHERE is_active = 1 ORDER BY display_name"
    ).fetchall()
    conn.close()
    return {"categories": [dict(row) for row in categories]}


# ======backend 用的推論 API ======
@app.get("/api/inference/{product_type}/images")
def get_dataset_images_api(
    product_type: str, current_user: dict = Depends(get_current_user)
):
    # 到backend/testing.py裡的get_category_images函式撈取該產品類別底下的測試影像列表，並回傳給前端顯示在推論頁面上
    return {"images": get_category_images(product_type)}


# 推論 API：對前端傳來的特定影像進行推論，並且把推論結果存到資料庫裡，最後回傳推論結果給前端顯示
@app.get("/api/inference/{product_type}/infer")
def infer_image(
    product_type: str, file_path: str, current_user: dict = Depends(get_current_user)
):
    try:
        result_dict = predict_specific_image(product_type, file_path)
        insert_inference_record(
            category=product_type,
            file_path=result_dict.get("file_path", file_path),
            image_name=result_dict.get("image_name", "unknown"),
            pred_label=result_dict.get("pred_label", "unknown"),
            score=result_dict.get("score", 0.0),
            operator=current_user["username"],
        )
        return result_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"影像辨識模型 推論失敗: {str(e)}")


# ====== IT 管理員 API  ======
class CreateUserRequest(BaseModel):
    # 要先正確接收前端傳來的帳號、密碼和角色資訊，才能建立帳號
    username: str
    password: str
    role: str


# IT 管理員新增帳號，並且會自動建立進去資料庫，由admin.html的JS呼叫這個API來建立帳號
@app.post("/api/admin/users")
def create_new_user(
    request: CreateUserRequest, current_user: dict = Depends(require_admin)
):
    hashed_pw = pwd_context.hash(request.password)
    try:
        # 直接寫入資料庫，前端自動重新載入最新的帳號列表
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
            (request.username.strip(), hashed_pw, request.role),
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": f"帳號 [{request.username}] 建立成功！"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="帳號名稱已存在！")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立帳號失敗: {str(e)}")


# ====== 產品主管 API  ======
class CategoryRequest(BaseModel):
    # 主管新增產品類別時，前端會傳來產品類別代碼和顯示名稱
    category_code: str
    display_name: str


# 主管新增產品類別，並且會自動建立進去資料庫
@app.post("/api/manager/categories")
def create_new_category(
    request: CategoryRequest, current_user: dict = Depends(require_manager)
):
    try:
        # 直接寫入資料庫，前端自動重新載入最新的類別列表
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO product_categories (category_code, display_name) VALUES (?, ?)",
            (request.category_code.strip().lower(), request.display_name.strip()),
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": f"產品 [{request.display_name}] 建立成功！"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="此產品代碼已存在！")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立產品失敗: {str(e)}")


class ReviewRequest(BaseModel):
    record_id: int
    review_status: str
    comments: str = ""


# 主管覆判瑕疵報表，前端會傳來要覆判的紀錄ID、覆判結果和備註資訊
@app.get("/api/manager/defect-reports")
def get_defect_reports(
    current_user: dict = Depends(require_manager),
):
    # 從資料庫撈取所有的瑕疵報表資料，並回傳給前端顯示在主管儀表板的表格裡面
    conn = get_db_connection()
    reports = conn.execute(
        "SELECT * FROM vw_manager_defect_dashboard ORDER BY detect_time DESC"
    ).fetchall()
    conn.close()
    return {"reports": [dict(row) for row in reports]}


# 主管提交覆判結果，前端會呼叫這個API來把覆判結果存到資料庫裡，並且更新主管儀表板的表格內容
@app.post("/api/manager/review")
def submit_review(
    request: ReviewRequest, current_user: dict = Depends(require_manager)
):
    try:
        # 直接呼叫資料庫的函式來存覆判結果，前端自動重新載入最新的報表資料
        submit_defect_review(
            request.record_id,
            current_user["username"],
            request.review_status,
            request.comments,
        )
        return {"success": True, "message": "覆判紀錄儲存成功！"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/manager/image")
def get_record_image(
    file_path: str,
    category: Optional[str] = None,
    current_user: dict = Depends(require_manager),
):
    """提供主管查看特定路徑的瑕疵原圖"""
    normalized_path = file_path.replace("\\", "/")
    if "dataset/" in normalized_path:
        clean_path = normalized_path.split("dataset/")[-1]
    else:
        clean_path = normalized_path.lstrip("/")

    possible_paths = []
    if category:
        possible_paths.append(
            os.path.join("/code/dataset", category, "test", clean_path)
        )
        possible_paths.append(os.path.join("/code/dataset", category, clean_path))

    possible_paths.extend(
        [
            os.path.join("/code/dataset", clean_path),
            os.path.join("/code", clean_path),
            normalized_path,
        ]
    )

    for test_path in possible_paths:
        if os.path.exists(test_path):
            return FileResponse(test_path)

    print(f"\n[Image Not Found] 原始資料庫路徑: {file_path}, 類別: {category}")
    print(f"系統已經努力找過以下位置，但通通沒有: {possible_paths}\n")

    raise HTTPException(
        status_code=404, detail="找不到影像檔案！請確認圖片是否存在於 dataset 目錄中。"
    )
