import gc
import os
import shutil

from anomalib.data import Folder
from anomalib.deploy import ExportType
from anomalib.engine import Engine
from anomalib.models import Patchcore

# 設定路徑與要訓練的類別
DATASET_ROOT = "/Code/dataset"
OUTPUT_ROOT = "/Code/weights"
CATEGORIES = ["bottle", "transistor", "wood", "capsule", "metal_nut"]

for category in CATEGORIES:
    # 檢查訓練路徑是否存在，不存在就跳過
    train_path = os.path.join(DATASET_ROOT, f"{category}/train/good")
    if not os.path.exists(train_path):
        print(f"Skipping {category}: Path not found.")
        continue

    datamodule = Folder(
        name=category,
        root=DATASET_ROOT,
        normal_dir=f"{category}/train/good",
        image_size=(224, 224),
    )

    # 採樣率 0.01 ：從特徵空間中抽取 1% 的特徵來建立記憶庫
    model = Patchcore(backbone="resnet18", coreset_sampling_ratio=0.01)
    category_dir = os.path.join(OUTPUT_ROOT, category)

    engine = Engine(
        default_root_dir=os.path.join(category_dir, "temp"),
        accelerator="cpu",
        devices=1,
    )

    print(f" Training: {category}")
    engine.fit(datamodule=datamodule, model=model)
    engine.export(model=model, export_type=ExportType.TORCH, export_root=category_dir)

    # 權重檔重新命名為 [種類]_model.pt
    source_pt = os.path.join(category_dir, "weights", "torch", "model.pt")
    target_pt = os.path.join(category_dir, f"{category}_model.pt")

    if os.path.exists(source_pt):
        os.rename(source_pt, target_pt)
        print(f"Saved: {target_pt}")

    # 清空 Anomalib 產生的深層暫存資料夾
    for folder in ["weights", "temp"]:
        path = os.path.join(category_dir, folder)
        if os.path.exists(path):
            shutil.rmtree(path)

    # 回收記憶體，避免跑下一個類別時 OOM
    del model, engine, datamodule
    gc.collect()

print("\ndone.")
