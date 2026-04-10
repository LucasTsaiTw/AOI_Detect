import sqlite3

from passlib.context import CryptContext

# 初始化密碼雜湊設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DB_PATH = "aoi_records.db"


def get_db_connection():
    """建立並回傳資料庫連線"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 資料格式轉換為 dict 物件
    return conn


def init_db():
    """初始化資料庫結構與預設資料"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 建立系統使用者資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 主鍵，自動遞增
            username TEXT UNIQUE NOT NULL,      -- 使用者帳號，必填且不能重複
            hashed_password TEXT NOT NULL,    -- 儲存密碼雜湊後的值
            role TEXT DEFAULT 'operator',   -- 使用者角色，預設為 'operator'，可為 'admin' 或 'manager'
            is_active INTEGER DEFAULT 1 -- 帳號是否啟用，1 表示啟用，0 表示停用
        )
    """)

    # 執行資料筆數檢查，確認 users 資料表是否已存在紀錄
    cursor.execute("SELECT COUNT(*) FROM users")

    # 若回傳計數為 0，代表系統為初次啟動，執行預設帳號初始化
    if cursor.fetchone()[0] == 0:
        # 針對預設帳號執行密碼雜湊運算
        admin_pw = pwd_context.hash("admin123")
        mgr_pw = pwd_context.hash("mgr123")
        op_pw = pwd_context.hash("op123")

        # 批次寫入預設帳號資料，並使用?防止SQL程式碼注入攻擊
        cursor.execute(
            "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?), (?, ?, ?), (?, ?, ?)",
            (
                "it_admin",
                admin_pw,
                "admin",
                "factory_mgr",
                mgr_pw,
                "manager",
                "operator_1",
                op_pw,
                "operator",
            ),
        )
        print("System log: Default user accounts created.")

    # 建立系統testing後的紀錄資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inference_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 主鍵
            category TEXT NOT NULL, -- 產品類別
            file_path TEXT NOT NULL, -- 圖片檔案路徑
            image_name TEXT NOT NULL, -- 圖片檔名
            pred_label TEXT NOT NULL, -- 預測結果
            score REAL NOT NULL, -- 預測分數
            operator TEXT DEFAULT 'system', -- 操作者
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 建立時間
        )
    """)

    # 建立瑕疵覆判資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defect_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,            -- 主鍵
            record_id INTEGER NOT NULL UNIQUE,               -- 對應 inference_records 的 id，且一筆紀錄只能有一筆覆判紀錄
            manager_username TEXT NOT NULL,                  -- 覆判管理員帳號
            review_status TEXT DEFAULT 'pending',            -- 覆判狀態 (pending, confirmed, rejected)
            comments TEXT,                                   -- 覆判意見               
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 覆判時間
            FOREIGN KEY (record_id) REFERENCES inference_records(id) -- 設定外鍵約束，確保 record_id 必須對應到 inference_records 表中的 id
        )
    """)

    # 建立管理員專用報表視圖
    cursor.execute("DROP VIEW IF EXISTS vw_manager_defect_dashboard")
    cursor.execute("""
        CREATE VIEW vw_manager_defect_dashboard AS
        SELECT 
            i.id AS record_id, 
            i.category,
            i.file_path,  
            i.image_name,
            i.pred_label,
            i.score,
            i.created_at AS detect_time,
            COALESCE(r.review_status, 'pending') AS review_status,
            r.manager_username,
            r.comments
        FROM inference_records i
        LEFT JOIN defect_reviews r ON i.id = r.record_id
        WHERE 
            i.pred_label != 'good' AND i.pred_label NOT LIKE '%正常%'
    """)

    # 建立產品類別字典表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 主鍵
            category_code TEXT UNIQUE NOT NULL,   -- 產品類別代碼 (如 bottle, cable 等)，必填且唯一
            display_name TEXT NOT NULL,           -- 產品類別顯示名稱 (如 Bottle (瓶子))，必填
            is_active INTEGER DEFAULT 1           -- 是否啟用該類別，1 表示啟用，0 表示停用
        )
    """)

    # 寫入預設產品類別 (僅於資料表為空時執行)
    cursor.execute("SELECT COUNT(*) FROM product_categories")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ("bottle", "Bottle (瓶子)"),
            ("cable", "Cable (電纜)"),
            ("capsule", "Capsule (膠囊)"),
            ("carpet", "Carpet (地毯)"),
            ("grid", "Grid (網格)"),
            ("hazelnut", "Hazelnut (榛果)"),
            ("leather", "Leather (皮革)"),
            ("metal_nut", "Metal Nut (金屬螺帽)"),
            ("pill", "Pill (藥丸)"),
            ("screw", "Screw (螺絲)"),
            ("tile", "Tile (磁磚)"),
            ("toothbrush", "Toothbrush (牙刷)"),
            ("transistor", "Transistor (電晶體)"),
            ("wood", "Wood (木材)"),
            ("zipper", "Zipper (拉鍊)"),
        ]
        cursor.executemany(
            "INSERT INTO product_categories (category_code, display_name) VALUES (?, ?)",
            default_categories,
        )
        print("System log: Default product categories created.")

    conn.commit()
    conn.close()


def insert_inference_record(
    category, file_path, image_name, pred_label, score, operator="system"
):
    """新增一筆 影像辨識模型 推論紀錄至資料庫"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO inference_records 
        (category, file_path, image_name, pred_label, score, operator)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (category, file_path, image_name, pred_label, score, operator),
    )
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def submit_defect_review(record_id, manager_username, review_status, comments=""):
    """寫入或更新瑕疵覆判紀錄 (使用 UPSERT 邏輯)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO defect_reviews (record_id, manager_username, review_status, comments)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(record_id) DO UPDATE SET 
            manager_username = excluded.manager_username,
            review_status = excluded.review_status,
            comments = excluded.comments,
            reviewed_at = CURRENT_TIMESTAMP
        """,
        (record_id, manager_username, review_status, comments),
    )
    conn.commit()
    conn.close()
