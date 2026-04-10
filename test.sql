-- ============================================================================
-- 🎓 Vision AOI 系統 - SQL 實戰練功房
-- 💡 說明：在 VS Code 將你想執行的那「一整段 SQL」反白選取後，按右鍵選擇執行
-- ============================================================================

-- 🟢【Level 1：基礎查詢與過濾 (SELECT, WHERE, ORDER BY, LIMIT)】

-- 1. 查詢系統內所有的帳號與權限 (不顯示密碼)
SELECT id, username, role, is_active 
FROM users;

-- 2. 撈出最新抽樣的 10 筆檢測紀錄，依時間由新到舊排序
SELECT image_name, category, score, created_at 
FROM inference_records 
ORDER BY created_at DESC 
LIMIT 10;

-- 3. 找出 影像辨識模型 極度有把握的瑕疵品 (異常分數大於 95 分)，並由高排到低
SELECT image_name, category, score, pred_label
FROM inference_records 
WHERE score > 95 AND pred_label NOT LIKE '%正常%'
ORDER BY score DESC;

-- ============================================================================

-- 🟡【Level 2：統計與群組化 (COUNT, AVG, GROUP BY, HAVING)】

-- 4. 統計系統內每種「權限角色」各有幾個帳號？
SELECT role AS 權限角色, COUNT(*) AS 帳號數量
FROM users
GROUP BY role;

-- 5. 【產品超常用】統計每種「產品類別」的抽樣總數、平均分數、平均運算時間
SELECT 
    category AS 產品類別, 
    COUNT(*) AS 抽樣總數, 
    ROUND(AVG(score), 2) AS 平均異常分數,
    ROUND(AVG(inference_time_ms), 1) AS 平均運算耗時_毫秒
FROM inference_records
GROUP BY category
ORDER BY 抽樣總數 DESC;

-- 6. 找出「被抽樣超過 5 次以上」的產品類別 (使用 HAVING 過濾群組結果)
SELECT category, COUNT(*) AS count
FROM inference_records
GROUP BY category
HAVING count > 5;

-- ============================================================================

-- 🟠【Level 3：多表關聯 (INNER JOIN, LEFT JOIN, COALESCE)】

-- 7. 查詢「已經被主管覆判過」的紀錄 (兩張表都有的資料才顯示)
SELECT 
    i.image_name AS 影像檔名,
    i.score AS 影像辨識模型分數,
    r.manager_username AS 審核主管,
    r.review_status AS 判定結果,
    r.comments AS 備註
FROM inference_records i
INNER JOIN defect_reviews r ON i.id = r.record_id;

-- 8. 查詢「所有」影像辨識模型 判斷為 NG 的紀錄，並顯示主管審核狀態 (沒有審核的補上'未審核')
SELECT 
    i.image_name AS 影像檔名,
    i.pred_label AS 影像辨識模型判定,
    COALESCE(r.review_status, '尚未審核') AS 目前狀態
FROM inference_records i
LEFT JOIN defect_reviews r ON i.id = r.record_id
WHERE i.pred_label NOT LIKE '%正常%';

-- ============================================================================

-- 🔴【Level 4：進階實戰 - 找碴與日報表 (CTE 暫存表, 日期函數)】

-- 9. 【找出過殺 (Overkill)】：標準答案是正常，但 影像辨識模型 卻判斷 NG
-- 使用 WITH (CTE) 建立一個暫時的查詢表，讓語法更乾淨
WITH OverkillRecords AS (
    SELECT 
        image_name, category, ground_truth, pred_label, score
    FROM inference_records
    WHERE ground_truth LIKE '%正常%' 
      AND pred_label NOT LIKE '%正常%'
)
SELECT * FROM OverkillRecords ORDER BY score DESC;

-- 10. 【產品每日報表】：統計「每天」的總抽樣數與抓到的瑕疵數
SELECT 
    DATE(created_at) AS 檢測日期,
    COUNT(*) AS 總抽檢數量,
    SUM(CASE WHEN pred_label NOT LIKE '%正常%' THEN 1 ELSE 0 END) AS 影像辨識模型判定異常數,
    ROUND(AVG(score), 2) AS 單日平均分數
FROM inference_records
GROUP BY DATE(created_at)
ORDER BY 檢測日期 DESC;
