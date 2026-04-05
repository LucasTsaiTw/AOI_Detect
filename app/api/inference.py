from fastapi import APIRouter

# 根據你的截圖，這裡的檔名是 Backend.py 或 backend.py
from app.services.backend import get_category_images, predict_specific_image

# 建立推論模組的 API 路由器
router = APIRouter()


@router.get("/{category}/images")
async def fetch_image_list(category: str):
    """
    獲取指定類別的測試圖庫清單

    掃描後端資料集目錄，回傳該類別底下所有可用於抽樣的圖片相對路徑。
    前端將利用此清單建立隨機抽樣池 (Image Pool)。

    Args:
        category (str): 檢測類別名稱 (例如: 'cable', 'bottle')

    Returns:
        dict: 包含圖片路徑陣列的字典格式資料 (key: "images")
    """
    images = get_category_images(category)
    return {"images": images}


@router.get("/{category}/infer")
async def run_specific_inference(category: str, file_path: str):
    """
    執行單張圖片的異常檢測 (AI Inference)

    接收前端傳遞的圖片路徑，呼叫底層 Anomalib 模型進行核心推論。
    處理流程涵蓋：單例模型調用、門檻正規化運算、熱力圖生成與特徵定位框繪製。

    Args:
        category (str): 檢測類別名稱
        file_path (str): 目標圖片於資料集內的相對路徑

    Returns:
        dict: 包含真實標籤、預測標籤、異常分數、推論耗時，以及 Base64 影像編碼的完整檢測報告
    """
    result = predict_specific_image(category, file_path)
    return result
