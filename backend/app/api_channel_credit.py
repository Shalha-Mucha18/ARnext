@router.get("/v1/credit-sales-ratio-by-channel")
def get_credit_sales_ratio_by_channel(unit_id: str = None, month: str = None):
    """Get credit vs cash sales ratio breakdown by channel based on credit_facility_type."""
    from db.engine import db
    
    try:
        unit_filter = f" AND \"unit_id\" = '{unit_id}'" if unit_id else ""

        # If no month specified, get the latest available month
        if not month:
            latest_month_query = f'''
            SELECT TO_CHAR("delivery_date", 'YYYY-MM') as month
            FROM tbldeliveryinfo
            WHERE "delivery_date" IS NOT NULL {unit_filter}
            ORDER BY "delivery_date" DESC
            LIMIT 1
            '''
            try:
                db_result = db.run(latest_month_query)
                if not db_result or db_result.strip() == '':
                    latest_result = []
                else:
                    latest_result = eval(db_result)
            except (SyntaxError, ValueError) as e:
                print(f"Error parsing channel credit latest month: {e}")
                latest_result = []
            month = latest_result[0][0] if latest_result else "2025-12"
        
        # Parse year and month
        year, month_num = month.split('-')

        # Query sales by channel and payment type using credit_facility_type
        query = f'''
        WITH base AS (
            SELECT
                "channel_name",
                CASE
                    WHEN "credit_facility_type" ILIKE 'cash' THEN 'Cash'
                    WHEN "credit_facility_type" ILIKE 'both' THEN 'Both'
                    WHEN "credit_facility_type" ILIKE 'credit' THEN 'Credit'
                    ELSE 'Other'
                END AS pay_type,
                "delivery_invoice_amount"
            FROM tbldeliveryinfo
            WHERE "delivery_date" IS NOT NULL
              AND "channel_name" IS NOT NULL
              AND "delivery_invoice_amount" IS NOT NULL
              AND EXTRACT(YEAR FROM "delivery_date") = {year}
              AND EXTRACT(MONTH FROM "delivery_date") = {month_num}
            {unit_filter}
        ),
        agg AS (
            SELECT
                pay_type,
                "channel_name",
                SUM("delivery_invoice_amount") AS channel_sales
            FROM base
            GROUP BY pay_type, "channel_name"
        )
        SELECT
            pay_type,
            "channel_name",
            ROUND(CAST(channel_sales AS NUMERIC), 2) AS channel_sales,
            ROUND(
                channel_sales * 100.0 / SUM(channel_sales) OVER (PARTITION BY pay_type),
                2
            ) AS channel_pct_within_pay_type
        FROM agg
        ORDER BY pay_type, channel_pct_within_pay_type DESC
        '''
        
        try:
            db_result = db.run(query)
            if not db_result or db_result.strip() == '':
                result = []
            else:
                result = eval(db_result)
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing database result: {e}")
            print(f"DB Result: {db_result[:200] if db_result else 'None'}")
            result = []
        
        # Organize results by payment type
        by_payment_type = {
            "Credit": [],
            "Cash": [],
            "Both": [],
            "Other": []
        }
        
        for row in result:
            pay_type = row[0]
            channel_name = row[1]
            channel_sales = float(row[2]) if row[2] is not None else 0.0
            channel_pct = float(row[3]) if row[3] is not None else 0.0
            
            by_payment_type[pay_type].append({
                "channel_name": channel_name,
                "revenue": channel_sales,
                "percentage_within_type": round(channel_pct, 2)
            })
        
        # Calculate totals
        total_credit = sum(ch["revenue"] for ch in by_payment_type["Credit"])
        total_cash = sum(ch["revenue"] for ch in by_payment_type["Cash"])
        total_both = sum(ch["revenue"] for ch in by_payment_type["Both"])
        total_other = sum(ch["revenue"] for ch in by_payment_type["Other"])
        total_revenue = total_credit + total_cash + total_both + total_other
        
        return {
            "month": month,
            "by_payment_type": by_payment_type,
            "totals": {
                "credit": total_credit,
                "cash": total_cash,
                "both": total_both,
                "other": total_other,
                "total": total_revenue
            },
            "message": "No data available for the selected month" if not result else None
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

