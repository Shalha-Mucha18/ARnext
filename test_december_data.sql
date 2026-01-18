-- Test queries to check if December 2025 data exists in the forecast tables

-- 1. Check Global/Total Forecast table for December 2025
SELECT 
    "Type",
    TO_CHAR("Date", 'YYYY-MM') AS month,
    SUM("numDeliveryQtyMT") AS total_qty,
    COUNT(*) as record_count
FROM "AIL_Monthly_Total_Forecast"
WHERE TO_CHAR("Date", 'YYYY-MM') = '2025-12'
GROUP BY "Type", month
ORDER BY "Type";

-- 2. Check what months are available as Historical
SELECT 
    TO_CHAR("Date", 'YYYY-MM') AS month,
    SUM("numDeliveryQtyMT") AS total_qty
FROM "AIL_Monthly_Total_Forecast"
WHERE "Type" = 'Historical'
AND "Date" >= '2025-01-01'
GROUP BY month
ORDER BY month DESC;

-- 3. Check Item Forecast table for December 2025
SELECT 
    "Type",
    TO_CHAR("Date", 'YYYY-MM') AS month,
    COUNT(DISTINCT "Item_Name") as item_count,
    SUM("numDeliveryQtyMT") AS total_qty
FROM "AIL_Monthly_Total_Item"
WHERE TO_CHAR("Date", 'YYYY-MM') = '2025-12'
GROUP BY "Type", month
ORDER BY "Type";

-- 4. Check Territory Forecast table for December 2025
SELECT 
    "Type",
    TO_CHAR("Date", 'YYYY-MM') AS month,
    COUNT(DISTINCT "Territory") as territory_count,
    SUM("numDeliveryQtyMT") AS total_qty
FROM "AIL_Monthly_Total_Final_Territory"
WHERE TO_CHAR("Date", 'YYYY-MM') = '2025-12'
GROUP BY "Type", month
ORDER BY "Type";

-- 5. Check the date range of Historical data
SELECT 
    MIN(TO_CHAR("Date", 'YYYY-MM')) as earliest_month,
    MAX(TO_CHAR("Date", 'YYYY-MM')) as latest_month,
    COUNT(DISTINCT TO_CHAR("Date", 'YYYY-MM')) as month_count
FROM "AIL_Monthly_Total_Forecast"
WHERE "Type" = 'Historical';
