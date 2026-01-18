from langchain_core.prompts import PromptTemplate

SQL_GENERATION_TEMPLATE = """You are a PostgreSQL expert. Generate syntactically correct SQL queries to answer questions about the delivery_data table.

Table Schema:
{table_info}

CRITICAL DATE/TIME PARSING RULES:
1. Month names → Use EXTRACT(MONTH FROM "Delivery_Date") = <number>
   - January = 1, February = 2, March = 3, April = 4, May = 5, June = 6
   - July = 7, August = 8, September = 9, October = 10, November = 11, December = 12

2. Time periods:
   - "yesterday" → WHERE "Delivery_Date" = CURRENT_DATE - INTERVAL '1 day'
   - "today" → WHERE "Delivery_Date" = CURRENT_DATE  
   - "last week" → WHERE "Delivery_Date" >= CURRENT_DATE - INTERVAL '7 days'
   - "this month" → WHERE "Delivery_Date" >= DATE_TRUNC('month', CURRENT_DATE)
   - "last month" → WHERE "Delivery_Date" >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND "Delivery_Date" < DATE_TRUNC('month', CURRENT_DATE)

3. Specific month + year:
   - "December 2025" → WHERE EXTRACT(YEAR FROM "Delivery_Date") = 2025 AND EXTRACT(MONTH FROM "Delivery_Date") = 12
   - "Q1 2025" → WHERE EXTRACT(YEAR FROM "Delivery_Date") = 2025 AND EXTRACT(MONTH FROM "Delivery_Date") IN (1,2,3)

FORECAST / PREDICTIVE TABLE RULES:
1. **AIL_Monthly_Total_Final_Territory**: Use for territory, region, or area forecasts.
   - Columns: Date, intTerritory, numDeliveryQtyMT, Region, Area, Territory
2. **AIL_Monthly_Total_Forecast**: Use for overall/global forecasts.
   - Columns: Date, numDeliveryQtyMT
3. **AIL_Monthly_Total_Item**: Use for product/item-level forecasts.
   - Columns: Date, Item_Name, numDeliveryQtyMT

QUERY OPTIMIZATION RULES:
- **CRITICAL**: Customer names in DB often have trailing spaces or slight variations. 
   - ALWAYS use `ILIKE` with wildcards for customer names.
   - Example: `WHERE "Customer_Name" ILIKE '%Jahan Trading - Mirpur%'`
   - DO NOT use `=` for customer names unless you are 100% sure.
- **TABLE SELECTION**: 
   - For HISTORICAL delivery data: Use `delivery_data`.
   - For FORECASTS/PREDICTIONS: Use one of the 3 `AIL_...` tables above based on granularity (Territory, Global, or Item).
- Always use aggregate functions (SUM, COUNT, AVG) when asked for totals
- Use double quotes for column/table names: "Delivery_Date", "Customer_Name"
- Include ALL filters mentioned in the question (year AND month, not just year!)
- Only generate SELECT queries, no INSERT/UPDATE/DELETE
- Do NOT add LIMIT clause for aggregate queries (SUM, COUNT, AVG)

EXAMPLES:

Question: "What is yesterday's total delivery?"
SELECT SUM("Delivery_Qty") FROM delivery_data WHERE "Delivery_Date" = CURRENT_DATE - INTERVAL '1 day';

Question: "Show deliveries for M/S ABC Corp in December 2025"
SELECT * FROM delivery_data WHERE "Customer_Name" = 'M/S ABC Corp' AND EXTRACT(YEAR FROM "Delivery_Date") = 2025 AND EXTRACT(MONTH FROM "Delivery_Date") = 12;

Question: "Total sales in Q1 2025"
SELECT SUM("Delivery_Value") FROM delivery_data WHERE EXTRACT(YEAR FROM "Delivery_Date") = 2025 AND EXTRACT(MONTH FROM "Delivery_Date") IN (1,2,3);

Question: "How many orders did customer XYZ place last month?"
SELECT COUNT(*) FROM delivery_data WHERE "Customer_Name" = 'XYZ' AND "Delivery_Date" >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND "Delivery_Date" < DATE_TRUNC('month', CURRENT_DATE);

Now answer this question:
Question: {input}

Note: You may default to LIMIT {top_k} if specific limit is not provided, but do not use LIMIT for aggregate queries.

SQLQuery:"""

sql_prompt = PromptTemplate(
    input_variables=["input", "top_k", "table_info"],
    template=SQL_GENERATION_TEMPLATE
)
