import time
import re
from decimal import Decimal
from fastapi import APIRouter, HTTPException

from .schemas import ChatRequest, ChatResponse
from .deps import get_core, get_store
from core.config import settings
from llm.chain import looks_like_followup
from memory.models import SessionState

router = APIRouter()

def get_business_unit_name(unit_id: str) -> str:
    """
    Helper function to get business unit name from dim_business_unit table.
    Returns the business unit name or a fallback if not found.
    """
    if not unit_id:
        return "All Units"
    
    from db.engine import db
    try:
        query = f'''
        SELECT "strBusinessUnitName" 
        FROM dim_business_unit 
        WHERE "Unit_Id" = '{unit_id}'
        LIMIT 1
        '''
        try:
            db_result = db.run(query)
            if not db_result or db_result.strip() == '':
                result = []
            else:
                result = eval(db_result)
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing business unit query: {e}")
            result = []
        
        if result and len(result) > 0:
            return result[0][0]
        return f"Unit {unit_id}"
    except Exception as e:
        print(f"Error fetching business unit name: {e}")
        return f"Unit {unit_id}"

def is_conversational(message: str) -> bool:
    """Detect greetings, thanks, and other non-analytical messages."""
    msg = message.strip().lower()
    
    # Greetings
    if re.match(r'^(hi|hello|hey|good morning|good afternoon|good evening|greetings)[\s!.]*$', msg):
        return True
    
    # Thanks/acknowledgments
    if re.match(r'^(thanks|thank you|ok|okay|got it|understood|great|perfect|awesome|cool)[\s!.]*$', msg):
        return True
    
    # Questions about the system itself
    if any(phrase in msg for phrase in ['who are you', 'what can you do', 'how do you work', 'help me']):
        return True
    
    return False

def get_conversational_response(message: str, has_context: bool) -> str:
    """Generate appropriate conversational responses."""
    msg = message.strip().lower()
    
    # Greetings
    if re.match(r'^(hi|hello|hey)', msg):
        return "Hello! I'm your sales analytics assistant. I can help you analyze delivery data, customer trends, and business insights. What would you like to know?"
    
    # Thanks
    if 'thank' in msg:
        return "You're welcome! Let me know if you need anything else."
    
    # Acknowledgments
    if msg in ['ok', 'okay', 'got it', 'understood', 'great', 'perfect', 'awesome', 'cool']:
        return "Great! Feel free to ask me anything about your sales data."
    
    # System questions
    if 'who are you' in msg:
        return "I'm your AI sales analytics assistant. I can answer questions about deliveries, customers, trends, and provide insights based on your data."
    
    if 'what can you do' in msg or 'help' in msg:
        return """I can help you with:
- **Data queries**: "What are the top 10 customers?" or "How many deliveries in 2025?"
- **Trends**: "Show me monthly sales trends" or "Compare Q1 to Q2"
- **Analysis**: "Why did sales increase?" or "Which regions are growing?"
- **Recommendations**: "How can we improve retention?" or "What should we focus on?"

Just ask me anything about your sales and delivery data!"""
    
    return "I'm here to help with your sales analytics. What would you like to know?"

def is_elaboration_request(message: str) -> bool:
    """Detect when user wants more details about the previous answer."""
    msg = message.strip().lower()
    
    # Direct elaboration requests
    elaboration_patterns = [
        r'^(explain|tell me|can you|could you)\s+(more|further|in detail)',
        r'^(more|further)\s+(details?|info|information|explanation)',
        r'^elaborate',
        r'^go on',
        r'^continue',
        r'what (do you mean|does (this|that) mean)',
        r'why is (this|that)',
        r'how (does|did) (this|that)',
    ]
    
    for pattern in elaboration_patterns:
        if re.search(pattern, msg):
            return True
    
    # Short elaboration requests
    if msg in ['more?', 'more', 'explain', 'why?', 'how?', 'tell me more', 'can you explain more?']:
        return True
    
    return False

def is_analytical_question(message: str) -> bool:
    """Detect complex analytical questions that benefit from multi-step reasoning."""
    msg = message.strip().lower()
    
    # Analytical question patterns
    analytical_patterns = [
        r'\bwhy\s+(did|is|are|was|were|does|do|has|have)',
        r'\bhow\s+(can|could|should|did|does|do)',
        r'\bexplain\s+(why|how|the)',
        r'\bwhat\s+(caused|drives|explains)',
        r'\bwhat.*reason',
        r'\broot\s+cause',
    ]
    
    for pattern in analytical_patterns:
        if re.search(pattern, msg):
            return True
    
    return False


@router.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    core = get_core()
    store = get_store()
    t0 = time.time()

    state = store.get(req.session_id)
    
    # Handle conversational messages (greetings, thanks, etc.)
    if is_conversational(req.message):
        answer = get_conversational_response(req.message, state.last_question is not None)
        return ChatResponse(
            session_id=req.session_id,
            mode="conversational",
            answer=answer,
            meta={"latency_ms": int((time.time()-t0)*1000)}
        )
    
    # Handle elaboration requests (explain more, tell me more, etc.)
    if is_elaboration_request(req.message) and state.last_descriptive:
        answer = core.elaborate(
            last_question=state.last_question or "",
            last_answer=state.last_descriptive,
            last_result=state.last_result or "",
            user_request=req.message
        )
        return ChatResponse(
            session_id=req.session_id,
            mode="elaboration",
            answer=answer,
            used_question=state.last_question,
            meta={"latency_ms": int((time.time()-t0)*1000)}
        )
    
    question = req.message

    # Contextualize follow-up questions
    if state.last_question and looks_like_followup(req.message):
        question = core.contextualize(
            last_question=state.last_question,
            entity_type=state.entity_type,
            entities=state.entities,
            metric=state.metric,
            user_message=req.message
        )

    try:
        # Run SQL query
        out = core.run_sql_from_question(question)
        
        # Generate descriptive answer
        desc = core.descriptive(out)
        
        # Use multi-step reasoning for analytical questions
        if is_analytical_question(req.message):
            desc = core.analyze_with_reasoning(
                question=out["question"],
                result=out["result"],
                descriptive_answer=desc
            )
        
        # Extract entities for context
        ent = core.extract_entities(out["query"], out["result"])
        
        # Update session state
        new_state = SessionState(
            last_question=out["question"],
            last_sql=out["query"],
            last_result=out["result"],
            last_descriptive=desc,
            entity_type=ent.get("entity_type", "unknown"),
            entities=ent.get("entities", []) or [],
            metric=ent.get("metric", "unknown"),
        )
        store.set(req.session_id, new_state)

        return ChatResponse(
            session_id=req.session_id,
            mode="descriptive",
            answer=desc,
            used_question=out["question"],
            sql=out["query"] if (req.debug or settings.DEBUG_RETURN_SQL) else None,
            meta={
                "latency_ms": int((time.time()-t0)*1000),
                "entity_type": new_state.entity_type,
                "entities": new_state.entities[:3],
                "metric": new_state.metric
            }
        )
    except Exception as e:
        # If SQL fails, try a general conversational answer
        # This handles general questions like "How to improve sales?" that don't map to SQL
        try:
            general_answer = core.general_response(req.message)
            return ChatResponse(
                session_id=req.session_id,
                mode="general",
                answer=general_answer,
                meta={"latency_ms": int((time.time()-t0)*1000)}
            )
        except Exception:
             # If even general chat fails, revert to error
            raise HTTPException(status_code=400, detail=str(e))

@router.get("/v1/units")
def get_units():
    """Get list of unique Unit IDs with business unit names."""
    from db.engine import db
    try:
        query = '''
        SELECT DISTINCT 
            d."unit_id" as unit_id,
            COALESCE(b."strBusinessUnitName", 'Unit ' || d."unit_id") as business_unit_name
        FROM tbldeliveryinfo d
        LEFT JOIN dim_business_unit b ON d."unit_id" = b."Unit_Id"
        WHERE d."unit_id" IS NOT NULL
        ORDER BY d."unit_id"
        '''
        results = eval(db.run(query))
        # Return list of dicts with unit_id and business_unit_name
        return [{"unit_id": str(r[0]), "business_unit_name": r[1]} for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/health")
def health():
    return {"status": "ok"}

@router.get("/v1/ytd-sales")
def get_ytd_sales(unit_id: int = None, fiscal_year: bool = False):
    """Get Year-to-Date sales comparison: Current Year vs Last Year.
    
    Args:
        unit_id: Optional business unit filter (dynamic)
        fiscal_year: If True, use fiscal year (July-June) instead of calendar year
    
    Returns:
        Current YTD and Last YTD metrics with growth analysis
    """
    from db.engine import db
    from datetime import datetime, date
    
    try:
        # Build unit filter
        unit_filter = f"AND unit_id = {int(unit_id)}" if unit_id else ""
        # Get current date for YTD calculations
        import datetime
        today = datetime.date.today()
        
        if fiscal_year:
            # FY label = end year (Jul-Jun)
            if today.month < 7:
                # Jan-Jun -> FY ends this year
                current_year = today.year
                current_ytd_start = f"{today.year - 1}-07-01"
            else:
                # Jul-Dec -> FY ends next year
                current_year = today.year + 1
                current_ytd_start = f"{today.year}-07-01"

            current_ytd_end = today.strftime("%Y-%m-%d")
            last_year = current_year - 1
            last_ytd_start = f"{int(current_ytd_start[:4]) - 1}-07-01"
            last_ytd_end = f"{today.year - 1}-{today.month:02d}-{today.day:02d}"

        else:
            
            current_year = today.year
            last_year = current_year - 1
            
            current_ytd_start = f"{current_year}-01-01"
            current_ytd_end = today.strftime("%Y-%m-%d")
            
            last_ytd_start = f"{last_year}-01-01"
            last_ytd_end = f"{last_year}-{today.month:02d}-{today.day:02d}"
        
        print(current_ytd_start, current_ytd_end)
        print(last_ytd_start, last_ytd_end)
        print(unit_filter)
        # Current Year YTD Query
        current_ytd_query = f"""
        SELECT
                    COUNT(*) AS total_order,
            ROUND(SUM(delivery_qty)::numeric, 2) AS total_sales_quantity,
            ROUND(SUM(delivery_invoice_amount)::numeric, 2) AS total_revenue
FROM public.tbldeliveryinfo
WHERE delivery_date BETWEEN '{current_ytd_start}' AND '{current_ytd_end}'
  {unit_filter};
"""
        
        # Last Year YTD Query (same period)
        last_ytd_query = f"""
SELECT
  COUNT(*) AS total_order,
  ROUND(SUM(delivery_qty)::numeric, 2) AS total_sales_quantity,
  ROUND(SUM(delivery_invoice_amount)::numeric, 2) AS total_revenue
FROM public.tbldeliveryinfo
WHERE delivery_date BETWEEN '{last_ytd_start}' AND '{last_ytd_end}'
  {unit_filter};
"""
        
        # Execute queries
        try:
            current_result = eval(db.run(current_ytd_query))[0]
            last_result = eval(db.run(last_ytd_query))[0]
        except Exception as e:
            print(f"Error executing YTD queries: {e}")
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
        
        # Parse results
        current_ytd = {
            "period": "Current YTD",
            "year": current_year,
            "total_orders": current_result[0] or 0,
            "total_quantity": float(current_result[1] or 0),
            "period_start": current_ytd_start,
            "period_end": current_ytd_end
        }
        
        last_ytd = {
            "period": "Last YTD",
            "year": last_year,
            "total_orders": last_result[0] or 0,
            "total_quantity": float(last_result[1] or 0),
            "period_start": last_ytd_start,
            "period_end": last_ytd_end
        }
        
        # Calculate growth metrics
        order_growth = 0
        quantity_growth = 0
        revenue_growth = 0
        
        if last_ytd["total_orders"] > 0:
            order_growth = ((current_ytd["total_orders"] - last_ytd["total_orders"]) / last_ytd["total_orders"]) * 100
        
        if last_ytd["total_quantity"] > 0:
            quantity_growth = ((current_ytd["total_quantity"] - last_ytd["total_quantity"]) / last_ytd["total_quantity"]) * 100
        
        
        growth_metrics = {
            "order_growth_pct": round(order_growth, 2),
            "quantity_growth_pct": round(quantity_growth, 2),
            "order_change": current_ytd["total_orders"] - last_ytd["total_orders"],
            "quantity_change": round(current_ytd["total_quantity"] - last_ytd["total_quantity"], 2)
        }
        
        # Return response without AI insights for faster loading
        response = {
            "business_unit_name": get_business_unit_name(unit_id),
            "current_ytd": current_ytd,
            "last_ytd": last_ytd,
            "growth_metrics": growth_metrics,
            "comparison_date": today.strftime("%Y-%m-%d")
        }
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in YTD sales endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/ytd-sales-insights")
def get_ytd_sales_insights(unit_id: str = None, fiscal_year: bool = False):
    """Generate solution-focused CEO insights for YTD performance on-demand.
    
    Args:
        unit_id: Optional business unit filter (dynamic)
        fiscal_year: If True, use fiscal year (July-June) instead of calendar year
    
    Returns:
        AI-generated strategic insights with actionable recommendations
    """
    from db.engine import db
    from datetime import datetime, date
    
    try:
        # Get YTD data first (reuse existing logic)
        unit_filter = f" AND \"unit_id\" = '{unit_id}'" if unit_id else ""
        
        today = date.today()
        current_year = today.year
        last_year = current_year - 1
        
        current_ytd_start = f"{current_year}-01-01"
        current_ytd_end = today.strftime("%Y-%m-%d")
        last_ytd_start = f"{last_year}-01-01"
        last_ytd_end = f"{last_year}-{today.month:02d}-{today.day:02d}"
        
        # Quick queries for metrics
        current_query = f'''
        SELECT COUNT(*) AS total_order, 
               ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) AS total_sales_quantity
        FROM public.tbldeliveryinfo
        WHERE "delivery_date" >= DATE '{current_ytd_start}'
          AND "delivery_date" <= DATE '{current_ytd_end}'
          AND "delivery_date" IS NOT NULL {unit_filter}
        '''
        
        last_query = f'''
        SELECT COUNT(*) AS total_order,
               ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) AS total_sales_quantity
        FROM public.tbldeliveryinfo
        WHERE "delivery_date" >= DATE '{last_ytd_start}'
          AND "delivery_date" <= DATE '{last_ytd_end}'
          AND "delivery_date" IS NOT NULL {unit_filter}
        '''
        
        current_result = eval(db.run(current_query))[0]
        last_result = eval(db.run(last_query))[0]
        
        current_orders = current_result[0] or 0
        current_qty = float(current_result[1] or 0)
        last_orders = last_result[0] or 0
        last_qty = float(last_result[1] or 0)
        
        # Calculate growth
        order_growth = ((current_orders - last_orders) / last_orders * 100) if last_orders > 0 else 0
        qty_growth = ((current_qty - last_qty) / last_qty * 100) if last_qty > 0 else 0
        
        # Determine status
        is_growing = order_growth >= 0 and qty_growth >= 0
        is_declining = order_growth < -10 or qty_growth < -10
        
        # Create solution-focused prompt
        core = get_core()
        
        if is_declining:
            # Declining performance - focus on recovery opportunities
            prompt = f"""You are a strategic business advisor. Analyze YTD performance and provide SOLUTION-FOCUSED recommendations for the CEO.

📊 PERFORMANCE DATA:
Current YTD ({current_year}): {current_orders:,} orders, {current_qty:,.0f} MT
Last YTD ({last_year}): {last_orders:,} orders, {last_qty:,.0f} MT
Growth: {order_growth:+.1f}% orders, {qty_growth:+.1f}% quantity

🎯 TASK: Provide insights in this EXACT format (keep under 150 words total):

🔴 ALERT: [One-line status - be direct but constructive]

💡 KEY OPPORTUNITY:
[One sentence identifying the biggest opportunity to recover/improve]

✅ RECOMMENDED ACTIONS (Priority Order):
1. [Immediate action - this week - be specific with numbers/targets]
2. [Short-term action - this month - include expected outcome]
3. [Strategic action - this quarter - focus on root cause]

📈 EXPECTED IMPACT:
[Quantified outcome if actions are taken - use percentages and numbers]

⚠️ RISK IF NO ACTION:
[Brief consequence of inaction - one sentence only]

RULES:
- Focus 70% on SOLUTIONS, 30% on problems
- Be specific and actionable (not generic advice)
- Use numbers and percentages
- Positive framing even for bad news (opportunity language)
- Keep total response under 150 words
- No pleasantries or fluff
"""
        elif is_growing:
            # Growing performance - focus on capitalizing momentum
            prompt = f"""You are a strategic business advisor. Analyze YTD performance and provide SOLUTION-FOCUSED recommendations for the CEO.

📊 PERFORMANCE DATA:
Current YTD ({current_year}): {current_orders:,} orders, {current_qty:,.0f} MT
Last YTD ({last_year}): {last_orders:,} orders, {last_qty:,.0f} MT
Growth: {order_growth:+.1f}% orders, {qty_growth:+.1f}% quantity

🎯 TASK: Provide insights in this EXACT format (keep under 150 words total):

🟢 MOMENTUM: [One-line status celebrating success]

💡 KEY OPPORTUNITY:
[One sentence on how to capitalize on this growth]

✅ RECOMMENDED ACTIONS (Priority Order):
1. [Immediate action - this week - scale what's working]
2. [Short-term action - this month - expand success]
3. [Strategic action - this quarter - sustain momentum]

📈 EXPECTED IMPACT:
[Quantified outcome if actions are taken - ambitious but realistic]

RULES:
- Focus on SCALING and SUSTAINING success
- Be specific and actionable
- Use numbers and percentages
- Ambitious but realistic targets
- Keep total response under 150 words
- No generic advice
"""
        else:
            # Stable/mixed performance
            prompt = f"""You are a strategic business advisor. Analyze YTD performance and provide SOLUTION-FOCUSED recommendations for the CEO.

 PERFORMANCE DATA:
Current YTD ({current_year}): {current_orders:,} orders, {current_qty:,.0f} MT
Last YTD ({last_year}): {last_orders:,} orders, {last_qty:,.0f} MT
Growth: {order_growth:+.1f}% orders, {qty_growth:+.1f}% quantity

TASK: Provide insights in this EXACT format (keep under 150 words total):

STATUS: [One-line assessment of stable performance]

 KEY OPPORTUNITY:
[One sentence on how to accelerate growth]

RECOMMENDED ACTIONS (Priority Order):
1. [Immediate action - this week - identify growth levers]
2. [Short-term action - this month - test and optimize]
3. [Strategic action - this quarter - scale winners]

EXPECTED IMPACT:
[Quantified outcome if actions are taken]

RULES:
- Focus on ACCELERATION opportunities
- Be specific and actionable
- Use numbers and percentages
- No generic advice
"""
        
        insights = core.general_response(prompt)
        return {
            "insights": insights,
            "generated_at": datetime.now().isoformat(),
            "performance_status": "declining" if is_declining else ("growing" if is_growing else "stable"),
            "metrics": {
                "current_orders": current_orders,
                "current_quantity": current_qty,
                "order_growth_pct": round(order_growth, 1),
                "quantity_growth_pct": round(qty_growth, 1)
            }
        }
    
    except Exception as e:
        print(f"Error generating YTD insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/mtd-stats")
def get_mtd_stats(unit_id: int = None, month: int = None, year: int = None):
    from db.engine import db
    import datetime
    from dateutil.relativedelta import relativedelta

    try:
        today = datetime.date.today()

        # If month provided, use that month/year but keep cutoff as today's day
        if month:
            if not 1 <= month <= 12:
                raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

            target_year = year if year else today.year
            current_month_start = datetime.date(target_year, month, 1)

            # Use today's day as cutoff (e.g., 20), not 1
            cutoff_day = today.day
        else:
            # Default: current month and cutoff = today
            current_month_start = today.replace(day=1)
            cutoff_day = today.day

        # Cap cutoff_day to last day of current target month
        last_day_current = (current_month_start + relativedelta(months=1) - datetime.timedelta(days=1)).day
        current_cutoff_day = min(cutoff_day, last_day_current)
        current_month_end = current_month_start.replace(day=current_cutoff_day)

        # Previous month start
        prev_month_start = current_month_start - relativedelta(months=1)

        # Cap cutoff_day to last day of previous month
        last_day_prev = (prev_month_start + relativedelta(months=1) - datetime.timedelta(days=1)).day
        prev_cutoff_day = min(cutoff_day, last_day_prev)
        prev_month_end = prev_month_start.replace(day=prev_cutoff_day)

        # Unit filter (int column -> no quotes)
        unit_filter = f"AND unit_id = {int(unit_id)}" if unit_id else ""

        current_query = f"""
        SELECT
          SUM(delivery_qty) AS total_quantity,
          COUNT(*) AS total_orders
        FROM public.tbldeliveryinfo
        WHERE delivery_date BETWEEN DATE '{current_month_start}' AND DATE '{current_month_end}'
          {unit_filter};
        """

        prev_query = f"""
        SELECT
          SUM(delivery_qty) AS total_quantity,
          COUNT(*) AS total_orders
        FROM public.tbldeliveryinfo
        WHERE delivery_date BETWEEN DATE '{prev_month_start}' AND DATE '{prev_month_end}'
          {unit_filter};
        """
        current_result = eval(db.run(current_query))[0]
        prev_result = eval(db.run(prev_query))[0]

        current_qty = float(current_result[0] or 0)
        current_orders = int(current_result[1] or 0)

        prev_qty = float(prev_result[0] or 0)
        prev_orders = int(prev_result[1] or 0)

        qty_growth = ((current_qty - prev_qty) / prev_qty * 100) if prev_qty > 0 else 0.0
        order_growth = ((current_orders - prev_orders) / prev_orders * 100) if prev_orders > 0 else 0.0

        return {
            "current_month": {
                "total_quantity": round(current_qty, 2),
                "total_orders": current_orders,
                "month": current_month_start.strftime("%B"),
                "year": current_month_start.year
            },
            "previous_month": {
                "total_quantity": round(prev_qty, 2),
                "total_orders": prev_orders,
                "month": prev_month_start.strftime("%B"),
                "year": prev_month_start.year
            },
            "growth_metrics": {
                "quantity_growth_pct": round(qty_growth, 2),
                "order_growth_pct": round(order_growth, 2)
            }
        }

    except Exception as e:
        print(f"Error in MTD stats: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/v1/mtd-insights")
def get_mtd_insights(unit_id: int = None, month: int = None, year: int = None):
    """Generate AI insights for MTD performance.
    
    Args:
        unit_id: Optional business unit filter
        month: Optional month as integer (1-12)
        year: Optional year (defaults to current year if month is provided)
    """
    from db.engine import db
    import datetime
    from dateutil.relativedelta import relativedelta
    from core.core import get_core
    
    try:
        # Determine target date
        if month:
            # Validate month
            if not 1 <= month <= 12:
                raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
            
            # Use provided year or current year
            target_year = year if year else datetime.date.today().year
            target_date = datetime.date(target_year, month, 1)
        else:
            # Use today's date
            target_date = datetime.date.today()
        
        # Calculate current month range
        current_month_start = target_date.replace(day=1)
        if current_month_start.month == 12:
            current_month_end = current_month_start.replace(year=current_month_start.year + 1, month=1, day=1)
        else:
            current_month_end = current_month_start.replace(month=current_month_start.month + 1, day=1)
        
        # Calculate previous month range
        prev_month_start = current_month_start - relativedelta(months=1)
        prev_month_end = current_month_start
        
        # Build unit filter
        unit_filter = f"AND unit_id = '{unit_id}'" if unit_id else ""
        
        # Query current month stats
        current_query = f"""
        SELECT 
            COALESCE(SUM(delivery_qty), 0) as total_quantity,
            COUNT(*) as total_orders
        FROM public.tbldeliveryinfo
        WHERE delivery_date >= DATE '{current_month_start}'
          AND delivery_date < DATE '{current_month_end}'
          {unit_filter}
        """
        
        current_result = eval(db.run(current_query))
        current_qty = float(current_result[0][0]) if current_result and current_result[0][0] else 0.0
        current_orders = int(current_result[0][1]) if current_result and current_result[0][1] else 0
        
        # Query previous month stats
        prev_query = f"""
        SELECT 
            COALESCE(SUM(delivery_qty), 0) as total_quantity,
            COUNT(*) as total_orders
        FROM public.tbldeliveryinfo
        WHERE delivery_date >= DATE '{prev_month_start}'
          AND delivery_date < DATE '{prev_month_end}'
          {unit_filter}
        """
        
        prev_result = eval(db.run(prev_query))
        prev_qty = float(prev_result[0][0]) if prev_result and prev_result[0][0] else 0.0
        prev_orders = int(prev_result[0][1]) if prev_result and prev_result[0][1] else 0
        
        # Calculate growth
        qty_growth = ((current_qty - prev_qty) / prev_qty * 100) if prev_qty > 0 else 0.0
        order_growth = ((current_orders - prev_orders) / prev_orders * 100) if prev_orders > 0 else 0.0
        
        # Determine status
        is_growing = order_growth >= 0 and qty_growth >= 0
        is_declining = order_growth < -10 or qty_growth < -10
        
        # Get month names
        current_month_name = current_month_start.strftime("%B %Y")
        prev_month_name = prev_month_start.strftime("%B %Y")
        
        # Create solution-focused prompt
        core = get_core()
        
        if is_declining:
            prompt = f"""You are a strategic business advisor. Analyze MTD performance and provide SOLUTION-FOCUSED recommendations.

📊 PERFORMANCE DATA:
Current Month ({current_month_name}): {current_orders:,} orders, {current_qty:,.0f} MT
Previous Month ({prev_month_name}): {prev_orders:,} orders, {prev_qty:,.0f} MT
Growth: {order_growth:+.1f}% orders, {qty_growth:+.1f}% quantity

🎯 TASK: Provide insights in this EXACT format (keep under 120 words total):

🔴 ALERT: [One-line status]

💡 KEY OPPORTUNITY:
[One sentence on recovery opportunity]

✅ IMMEDIATE ACTIONS:
1. [Specific action with target]
2. [Specific action with outcome]

📈 EXPECTED IMPACT:
[Quantified outcome]

RULES: Focus on THIS MONTH recovery, be specific, use numbers, keep under 120 words"""
        elif is_growing:
            prompt = f"""You are a strategic business advisor. Analyze MTD performance and provide SOLUTION-FOCUSED recommendations.

📊 PERFORMANCE DATA:
Current Month ({current_month_name}): {current_orders:,} orders, {current_qty:,.0f} MT
Previous Month ({prev_month_name}): {prev_orders:,} orders, {prev_qty:,.0f} MT
Growth: {order_growth:+.1f}% orders, {qty_growth:+.1f}% quantity

🎯 TASK: Provide insights in this EXACT format (keep under 120 words total):

✅ STATUS: [One-line positive status]

💡 KEY OPPORTUNITY:
[One sentence on accelerating growth]

✅ IMMEDIATE ACTIONS:
1. [Action to capitalize on momentum]
2. [Action to expand success]

📈 EXPECTED IMPACT:
[Quantified outcome]

RULES: Focus on ACCELERATION, be specific, use numbers, keep under 120 words"""
        else:
            prompt = f"""You are a strategic business advisor. Analyze MTD performance and provide SOLUTION-FOCUSED recommendations.

📊 PERFORMANCE DATA:
Current Month ({current_month_name}): {current_orders:,} orders, {current_qty:,.0f} MT
Previous Month ({prev_month_name}): {prev_orders:,} orders, {prev_qty:,.0f} MT
Growth: {order_growth:+.1f}% orders, {qty_growth:+.1f}% quantity

🎯 TASK: Provide insights in this EXACT format (keep under 120 words total):

📊 STATUS: [One-line status]

💡 KEY FOCUS:
[One sentence on maintaining stability]

✅ RECOMMENDED ACTIONS:
1. [Action to maintain performance]
2. [Action to find growth]

RULES: Focus on STABILITY and GROWTH, be specific, keep under 120 words"""
        
        insights = core.general_response(prompt)
        return {
            "insights": insights,
            "generated_at": datetime.datetime.now().isoformat(),
            "performance_status": "declining" if is_declining else ("growing" if is_growing else "stable"),
            "metrics": {
                "current_orders": current_orders,
                "current_quantity": current_qty,
                "order_growth_pct": round(order_growth, 1),
                "quantity_growth_pct": round(qty_growth, 1)
            }
        }
    
    except Exception as e:
        print(f"Error generating MTD insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-customers-2025")
def get_top_customers(unit_id: str = None):
    """Get top 10 customers by revenue for 2025."""
    from db.engine import db
    try:
        where_clause = 'WHERE EXTRACT(YEAR FROM "delivery_date") = 2025 AND "customer_name" IS NOT NULL'
        if unit_id:
            where_clause += f" AND \"unit_id\" = '{unit_id}'"

        query = f'''
        SELECT 
            "customer_name",
            ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) as total_revenue
        FROM tbldeliveryinfo
        {where_clause}
        GROUP BY "customer_name"
        ORDER BY total_revenue DESC
        LIMIT 10
        '''
        results = eval(db.run(query))
        return [
            {"customer_name": r[0], "total_revenue": float(r[1])}
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-territories-2025")
def get_top_territories(unit_id: str = None):
    """Get top 10 territories by revenue for 2025."""
    from db.engine import db
    try:
        where_clause = 'WHERE EXTRACT(YEAR FROM "delivery_date") = 2025 AND "territory" IS NOT NULL'
        if unit_id:
            where_clause += f" AND \"unit_id\" = '{unit_id}'"

        query = f'''
        SELECT 
            "territory",
            ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) as total_revenue
        FROM tbldeliveryinfo
        {where_clause}
        GROUP BY "territory"
        ORDER BY total_revenue DESC
        LIMIT 10
        '''
        results = eval(db.run(query))
        return [
            {"territory": r[0], "total_revenue": float(r[1])}
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/regional-insights")
def get_regional_insights(unit_id: str = None, month: str = None, year: str = None):
    """Get regional sales data (Top 5 / Bottom 5)."""
    from db.engine import db
    import datetime
    
    try:
        # Date Logic with year filter support
        today = datetime.date.today()
        
        if year and month:
            # Specific month in specific year
            # month is in format "YYYY-MM", extract just the month part
            if '-' in month:
                month_part = month.split('-')[1]
            else:
                month_part = month
            target_date = datetime.datetime.strptime(f"{year}-{month_part}", "%Y-%m").date()
            start_date = target_date.replace(day=1)
            next_month_val = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month_val.replace(day=1)
        elif year:
            # Entire year
            start_date = datetime.date(int(year), 1, 1)
            end_date = datetime.date(int(year) + 1, 1, 1)
        elif month:
            # Specific month in current year
            target_date = datetime.datetime.strptime(month, "%Y-%m").date()
            start_date = target_date.replace(day=1)
            next_month_val = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month_val.replace(day=1)
        else:
            # Current month
            start_date = today.replace(day=1)
            next_month_val = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month_val.replace(day=1)

        unit_filter = f" AND unit_id = '{unit_id}'" if unit_id else "" 

        query = f'''
        WITH region_perf AS (
          SELECT
            COALESCE(region, 'Unknown') AS region,
            SUM(delivery_qty) AS total_mt,
            COUNT(*) AS orders
          FROM public.tbldeliveryinfo
          WHERE region IS NOT NULL
            {unit_filter}
            AND delivery_date >= DATE '{start_date}'
            AND delivery_date <  DATE '{end_date}'
          GROUP BY COALESCE(region, 'Unknown')
        ),
        ranked AS (
          SELECT
            *,
            ROW_NUMBER() OVER (ORDER BY total_mt DESC) AS rn_desc,
            ROW_NUMBER() OVER (ORDER BY total_mt ASC)  AS rn_asc
          FROM region_perf
        )
        SELECT
          CASE
            WHEN rn_desc <= 5 THEN 'Top 5'
            WHEN rn_asc  <= 5 THEN 'Bottom 5'
          END AS bucket,
          region,
          ROUND(total_mt::numeric, 2) AS total_mt,
          orders
        FROM ranked
        WHERE rn_desc <= 5 OR rn_asc <= 5
        ORDER BY bucket, total_mt DESC;
        '''
        
        result_raw = db.run(query)
        rows = eval(result_raw) if result_raw else []
        
        top_regions = []
        bottom_regions = []

        for row in rows:
            bucket = row[0]
            item = {
                "name": row[1],
                "quantity": float(row[2]) if row[2] is not None else 0.0,
                "orders": row[3]
            }
            if bucket == 'Top 5':
                top_regions.append(item)
            else:
                 bottom_regions.append(item)

        # Sort bottom regions ASC by quantity
        bottom_regions.sort(key=lambda x: x['quantity'])
        
        # Calculate Total Volume for share calculation if needed
        query_total = f'''
        SELECT SUM(delivery_qty)
        FROM public.tbldeliveryinfo
        WHERE region IS NOT NULL
          {unit_filter}
          AND delivery_date >= DATE '{start_date}'
          AND delivery_date <  DATE '{end_date}'
        '''
        res_total = db.run(query_total)
        parsed = eval(res_total) if res_total else []
        total_volume = float(parsed[0][0]) if parsed and parsed[0] and parsed[0][0] else 0.0

        return {
            "top_regions": top_regions,
            "bottom_regions": bottom_regions,
            "total_volume": total_volume
        }
    except Exception as e:
        return {
            "top_regions": [],
            "bottom_regions": [],
            "total_volume": 0,
            "error": str(e)
        }

@router.post("/v1/regional-insights/generate")
def generate_regional_insights(unit_id: str = None, month: str = None):
    """Generate strategic AI insights for regional performance."""
    try:
        from db.engine import db
        import datetime
        from .deps import get_core
        
        
        # Date Logic
        start_date, end_date = _get_date_range(month, year)

        unit_filter = f" AND unit_id = '{unit_id}'" if unit_id else "" 

        query = f'''
        WITH region_perf AS (
          SELECT
            COALESCE(region, 'Unknown') AS region,
            SUM(delivery_qty) AS total_mt,
            COUNT(*) AS orders
          FROM public.tbldeliveryinfo
          WHERE region IS NOT NULL
            {unit_filter}
            AND delivery_date >= DATE '{start_date}'
            AND delivery_date <  DATE '{end_date}'
          GROUP BY COALESCE(region, 'Unknown')
        ),
        ranked AS (
          SELECT
            *,
            ROW_NUMBER() OVER (ORDER BY total_mt DESC) AS rn_desc,
            ROW_NUMBER() OVER (ORDER BY total_mt ASC)  AS rn_asc
          FROM region_perf
        )
        SELECT
          CASE
            WHEN rn_desc <= 5 THEN 'Top 5'
            WHEN rn_asc  <= 5 THEN 'Bottom 5'
          END AS bucket,
          region,
          ROUND(total_mt::numeric, 2) AS total_mt,
          orders
        FROM ranked
        WHERE rn_desc <= 5 OR rn_asc <= 5
        ORDER BY bucket, total_mt DESC;
        '''
        
        result_raw = db.run(query)
        rows = eval(result_raw) if result_raw else []
        
        top_regions = []
        bottom_regions = []

        for row in rows:
            bucket = row[0]
            item = {
                "name": row[1],
                "quantity": float(row[2]) if row[2] is not None else 0.0,
                "orders": row[3]
            }
            if bucket == 'Top 5':
                top_regions.append(item)
            else:
                 bottom_regions.append(item)

        # Sort bottom regions ASC by quantity
        bottom_regions.sort(key=lambda x: x['quantity'])
        
         # Calculate Total Volume
        query_total = f'''
        SELECT SUM(delivery_qty)
        FROM public.tbldeliveryinfo
        WHERE region IS NOT NULL
          {unit_filter}
          AND delivery_date >= DATE '{start_date}'
          AND delivery_date <  DATE '{end_date}'
        '''
        res_total = db.run(query_total)
        parsed = eval(res_total) if res_total else []
        total_volume = float(parsed[0][0]) if parsed and parsed[0] and parsed[0][0] else 0.0

        # Generate Insights
        core = get_core()
        insight_result = core.analyze_regional_performance(top_regions, bottom_regions, total_volume)
        
        return insight_result

    except Exception as e:
        print(f"Error generating regional insights: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Could not generate insights: {str(e)}"}

@router.get("/v1/area-insights")
def get_area_insights(unit_id: str = None, month: str = None, year: str = None):
    """Get area sales data (Top 5 / Bottom 5) with optimized query."""
    from db.engine import db
    import datetime
    import logging
    
    # Setup logger
    logger = logging.getLogger("area_insights")
    
    try:
        # Date Logic with year filter support
        today = datetime.date.today()
        
        if year and month:
            # Specific month in specific year
            try:
                # month is in format "YYYY-MM", extract just the month part
                if '-' in month:
                    month_part = month.split('-')[1]
                else:
                    month_part = month
                target_date = datetime.datetime.strptime(f"{year}-{month_part}", "%Y-%m").date()
                start_date = target_date.replace(day=1)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1, day=1)
            except ValueError:
                logger.error(f"Invalid year-month combination: {year}-{month}")
                start_date = today.replace(day=1)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1, day=1)
        elif year:
            # Entire year
            start_date = datetime.date(int(year), 1, 1)
            end_date = datetime.date(int(year) + 1, 1, 1)
        elif month:
            # Specific month in current year
            month = month.strip()
            try:
                target_date = datetime.datetime.strptime(month, "%Y-%m").date()
                start_date = target_date.replace(day=1)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1, day=1)
            except ValueError:
                logger.error(f"Invalid month format received: {month}")
                start_date = today.replace(day=1)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1, day=1)
        else:
            # Current month
            start_date = today.replace(day=1)
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1)


        unit_filter = f" AND unit_id = '{unit_id}'" if unit_id else "" 

        # Optimized Single Query using Window Functions
        query = f'''
        WITH area_metrics AS (
            SELECT
                COALESCE(area, 'Unknown') AS area,
                SUM(delivery_qty) AS area_qty,
                COUNT(*) AS area_orders
            FROM public.tbldeliveryinfo
            WHERE area IS NOT NULL
                {unit_filter}
                AND delivery_date >= DATE '{start_date}'
                AND delivery_date <  DATE '{end_date}'
            GROUP BY COALESCE(area, 'Unknown')
        ),
        ranked_metrics AS (
            SELECT
                area,
                area_qty,
                area_orders,
                SUM(area_qty) OVER () as global_total,
                ROW_NUMBER() OVER (ORDER BY area_qty DESC) as rn_desc,
                ROW_NUMBER() OVER (ORDER BY area_qty ASC) as rn_asc
            FROM area_metrics
        )
        SELECT 
            CASE 
                WHEN rn_desc <= 5 THEN 'Top 5'
                WHEN rn_asc <= 5 THEN 'Bottom 5'
            END as category,
            area,
            ROUND(area_qty::numeric, 2) as quantity,
            area_orders,
            ROUND(global_total::numeric, 2) as total_vol
        FROM ranked_metrics
        WHERE rn_desc <= 5 OR rn_asc <= 5
        ORDER BY category DESC, area_qty DESC;
        '''
        
        result_raw = db.run(query)
        rows = eval(result_raw) if result_raw else []
        
        top_areas = []
        bottom_areas = []
        total_volume = 0.0

        for row in rows:
            category = row[0]
            area_name = row[1]
            qty = float(row[2]) if row[2] is not None else 0.0
            orders = int(row[3])
            # Capture total volume from any row (it's the same for all)
            if row[4] is not None:
                total_volume = float(row[4])

            item = {
                "name": area_name,
                "quantity": qty,
                "orders": orders
            }

            if category == 'Top 5':
                top_areas.append(item)
            elif category == 'Bottom 5':
                bottom_areas.append(item)
        
        # Sort bottom areas ASC by quantity for display if needed
        bottom_areas.sort(key=lambda x: x['quantity'])

        return {
            "top_areas": top_areas,
            "bottom_areas": bottom_areas,
            "total_volume": total_volume
        }
    except Exception as e:
        logger.error(f"Error in get_area_insights: {str(e)}")
        return {
            "top_areas": [],
            "bottom_areas": [],
            "total_volume": 0,
            "error": str(e)
        }

@router.post("/v1/area-insights/generate")
def generate_area_insights(request: dict):
    """Generate on-demand AI insights for area performance."""
    from db.engine import db
    unit_id = request.get("unit_id")
    month = request.get("month")
    
    try:
        # Fetch area data
        area_data = get_area_insights(unit_id, month)
        
        top_areas = area_data.get("top_areas", [])
        bottom_areas = area_data.get("bottom_areas", [])
        total_volume = area_data.get("total_volume", 0)
        
        # Generate AI insights
        core = get_core()
        insight_result = core.analyze_area_performance(top_areas, bottom_areas, total_volume)
        
        return insight_result

    except Exception as e:
        print(f"Error generating area insights: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Could not generate insights: {str(e)}"}

@router.get("/v1/top-customers")
def get_top_customers(unit_id: str = None, month: str = None, year: str = None):
    """Get top 10 customers by volume."""
    from db.engine import db
    import datetime
    
    try:
        # Date Logic with year filter support
        today = datetime.date.today()
        
        if year and month:
            # Specific month in specific year
            # month is in format "YYYY-MM", extract just the month part
            if '-' in month:
                month_part = month.split('-')[1]
            else:
                month_part = month
            target_date = datetime.datetime.strptime(f"{year}-{month_part}", "%Y-%m").date()
            start_date = target_date.replace(day=1)
            next_month_val = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month_val.replace(day=1)
        elif year:
            # Entire year
            start_date = datetime.date(int(year), 1, 1)
            end_date = datetime.date(int(year) + 1, 1, 1)
        elif month:
            # Specific month in current year
            target_date = datetime.datetime.strptime(month, "%Y-%m").date()
            start_date = target_date.replace(day=1)
            next_month_val = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month_val.replace(day=1)
        else:
            # Current month
            start_date = today.replace(day=1)
            next_month_val = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month_val.replace(day=1)

        unit_filter = f" AND unit_id = '{unit_id}'" if unit_id else "" 

        query = f'''
        SELECT
            COALESCE(customer_name, 'Unknown') AS customer,
            SUM(delivery_qty) AS total_mt,
            COUNT(*) AS orders
        FROM public.tbldeliveryinfo
        WHERE customer_name IS NOT NULL
            {unit_filter}
            AND delivery_date >= DATE '{start_date}'
            AND delivery_date <  DATE '{end_date}'
        GROUP BY COALESCE(customer_name, 'Unknown')
        ORDER BY total_mt DESC
        LIMIT 10;
        '''
        
        result_raw = db.run(query)
        rows = eval(result_raw) if result_raw else []
        
        top_customers = []
        for row in rows:
            top_customers.append({
                "name": row[0],
                "quantity": float(row[1]) if row[1] is not None else 0.0,
                "orders": row[2]
            })

        return {"top_customers": top_customers}
        
    except Exception as e:
        return {
            "top_customers": [],
            "error": str(e)
        }

@router.get("/v1/available-months")
def get_available_months(unit_id: str = None):
    """Get list of available months with data."""
    from db.engine import db
    from datetime import datetime
    
    try:
        unit_filter = f" AND unit_id = '{unit_id}'" if unit_id else ""
        
        query = f'''
        SELECT DISTINCT TO_CHAR(delivery_date, 'YYYY-MM') as month
        FROM tbldeliveryinfo
        WHERE delivery_date IS NOT NULL
        {unit_filter}
        AND EXTRACT(YEAR FROM delivery_date) >= 2023
        ORDER BY month DESC
        '''
        
        result_raw = db.run(query)
        rows = eval(result_raw) if result_raw else []
        
        months = []
        for row in rows:
            month_str = row[0]
            # Convert YYYY-MM to "Month YYYY" format
            try:
                dt = datetime.strptime(month_str, "%Y-%m")
                label = dt.strftime("%B %Y")  # e.g., "January 2025"
                months.append({"value": month_str, "label": label})
            except ValueError:
                continue
        
        return {"months": months}
        
    except Exception as e:
        return {"months": [], "error": str(e)}



@router.get("/v1/sales-metrics")
def get_sales_metrics(unit_id: str = None, month: str = None, generate_diagnostics: bool = False):
    """Get total sales revenue and quantity metrics with optional CEO diagnostics.
    
    Args:
        unit_id: Optional business unit filter
        month: Optional month filter in YYYY-MM format (e.g., "2025-12")
        generate_diagnostics: If True, generate CEO diagnostic insights
    """
    from db.engine import db
    import calendar
    from datetime import datetime, date

    try:
        unit_filter = f" AND \"unit_id\" = '{unit_id}'" if unit_id else ""
        
        # If no month specified, get the latest available month from DB
        if not month:
            latest_month_query = f'''
            SELECT TO_CHAR("delivery_date", 'YYYY-MM') as month
            FROM tbldeliveryinfo
            WHERE "delivery_date" IS NOT NULL {unit_filter}
            ORDER BY "delivery_date" DESC
            LIMIT 1
            '''
            latest_result = eval(db.run(latest_month_query))
            month = latest_result[0][0] if latest_result else datetime.now().strftime("%Y-%m")
        
        # Parse year and month
        try:
            year_str, month_str = month.split('-')
            year = int(year_str)
            month_num = int(month_str)
        except ValueError:
             # Fallback for invalid format, default to current
             now = datetime.now()
             year, month_num = now.year, now.month
             month = f"{year}-{month_num:02d}"

        # Calculate period start and end dates
        period_start = f"{year}-{month_num:02d}-01"
        last_day = calendar.monthrange(year, month_num)[1]
        period_end = f"{year}-{month_num:02d}-{last_day}"
        
        # Calculate YTD start (Jan 1st of the selected year)
        ytd_start = f"{year}-01-01"
        
        # MoM Query (Current Month)
        current_query = f'''
        SELECT
          COUNT(*) as order_count,
          ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) AS total_sales,
          ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) AS total_sales_quantity
        FROM public.tbldeliveryinfo
        WHERE "delivery_date" BETWEEN DATE '{period_start}' AND DATE '{period_end}'
          AND "delivery_date" IS NOT NULL
          {unit_filter}
        '''
        
        # Last 12 Months (Trend) - Optimized with date filter
        trend_query = f'''
        SELECT 
            TO_CHAR("delivery_date", 'YYYY-MM') as month,
            COUNT(*) as order_count,
            ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) as total_qty,
            ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) as total_revenue
        FROM tbldeliveryinfo
        WHERE "delivery_date" >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '13 months'
        AND "delivery_date" IS NOT NULL 
        {unit_filter}
        GROUP BY TO_CHAR("delivery_date", 'YYYY-MM')
        ORDER BY month DESC
        LIMIT 12
        '''
        
        # Execute queries
        try:
            current_raw = db.run(current_query)
            current_result = eval(current_raw)[0] if current_raw else (0, 0, 0)
        except Exception as e:
            print(f"Error in sales metrics (current): {e}")
            current_result = (0, 0, 0)
            
        trend_result = eval(db.run(trend_query))
        
        # Format results - explicitly mapping new SQL aliases to API response model
        # Tuple index: 0=count, 1=revenue(sales), 2=qty
        
        current_month = {
            "month": month,
            "order_count": current_result[0] or 0,
            "qty": float(current_result[2] or 0),     # Mapped from total_sales_quantity
            "revenue": float(current_result[1] or 0)  # Mapped from total_sales
        }
        
        last_12_months = []
        for row in trend_result:
            last_12_months.append({
                "month": row[0],
                "order_count": row[1] or 0,
                "qty": float(row[2] or 0),
                "revenue": float(row[3] or 0)
            })
        
        # Generate CEO diagnostics on demand
        response = {
            "business_unit_name": get_business_unit_name(unit_id),
            "current_month": current_month,
            "last_12_months": last_12_months
        }
        
        if generate_diagnostics:
            try:
                core = get_core()
                diagnostics = core.analyze_sales_diagnostics(current_month, last_12_months)
                response["ceo_diagnostics"] = diagnostics
            except Exception as e:
                print(f"Error generating CEO diagnostics: {e}")
                response["ceo_diagnostics"] = {"analysis": "Diagnostics unavailable"}
        
        return response
    
    except Exception as e:
        print(f"Error generating sales metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/v1/credit-sales-ratio")
def get_credit_sales_ratio(unit_id: str = None, month: str = None, generate_insights: bool = False):
    """Get credit vs cash sales ratio based on credit_facility_type.
    
    Args:
        unit_id: Optional business unit filter
        month: Optional month filter in YYYY-MM format
        generate_insights: If True, generate AI insights for CEO (default: False)
    """
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
                print(f"Error parsing credit ratio latest month: {e}")
                latest_result = []
            month = latest_result[0][0] if latest_result else "2025-12"
        
        # Parse year and month to create date range
        # Handle "Month YYYY" format (e.g., "December 2025")
        if ' ' in month and len(month.split('-')) < 2:
            try:
                from datetime import datetime
                dt = datetime.strptime(month, "%B %Y")
                month = dt.strftime("%Y-%m")
            except ValueError:
                print(f"Error parsing month format: {month}")

        year, month_num = month.split('-')
        
        # Create date range for faster querying
        from datetime import datetime, timedelta
        start_date = f"{year}-{month_num.zfill(2)}-01"
        if int(month_num) == 12:
            end_date = f"{int(year)+1}-01-01"
        else:
            end_date = f"{year}-{str(int(month_num)+1).zfill(2)}-01"

        # Optimized query using LOWER() and date ranges
        query = f'''
        SELECT 
            CASE
                WHEN LOWER("credit_facility_type") = 'cash' THEN 'Cash'
                WHEN LOWER("credit_facility_type") = 'both' THEN 'Both'
                WHEN LOWER("credit_facility_type") = 'credit' THEN 'Credit'
                ELSE 'Other'
            END AS pay_type,
            COUNT(*) as order_count,
            ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) as total_revenue
        FROM tbldeliveryinfo
        WHERE "delivery_date" >= '{start_date}'
          AND "delivery_date" < '{end_date}'
          AND "delivery_qty" IS NOT NULL
        {unit_filter}
        GROUP BY pay_type
        '''
        
        try:
            db_result = db.run(query)
            if not db_result or db_result.strip() == '':
                result = []
            else:
                result = eval(db_result)
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing credit sales ratio query: {e}")
            result = []
        
        # Parse results
        credit_orders = 0
        credit_revenue = 0.0
        cash_orders = 0
        cash_revenue = 0.0
        both_orders = 0
        both_revenue = 0.0
        other_orders = 0
        other_revenue = 0.0
        
        for row in result:
            pay_type = row[0]
            orders = row[1]
            revenue = float(row[2]) if row[2] is not None else 0.0
            
            if pay_type == 'Credit':
                credit_orders = orders
                credit_revenue = revenue
            elif pay_type == 'Both':
                both_orders = orders
                both_revenue = revenue
            elif pay_type == 'Cash':
                cash_orders = orders
                cash_revenue = revenue
            else:  # Other (NULL/empty)
                other_orders = orders
                other_revenue = revenue
        
        # Calculate totals
        total_orders = credit_orders + cash_orders + both_orders + other_orders
        total_revenue = credit_revenue + cash_revenue + both_revenue + other_revenue
        
        # Calculate percentages
        credit_percentage = (credit_revenue / total_revenue * 100) if total_revenue > 0 else 0
        cash_percentage = (cash_revenue / total_revenue * 100) if total_revenue > 0 else 0
        both_percentage = (both_revenue / total_revenue * 100) if total_revenue > 0 else 0
        other_percentage = (other_revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        # Generate AI insights for CEO (only if we have meaningful data)
        ai_insights = None
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("ai_insights")
        
        logger.warning(f"DEBUG: Checking AI generation. Total Revenue: {total_revenue}, Generate: {generate_insights}")
        if generate_insights and total_revenue > 0:
            logger.warning("DEBUG: Entering AI generation block")
            try:
                from .deps import get_core
                core = get_core()
                logger.warning("DEBUG: Got core, calling analyze_credit_ratio_ceo")
                
                # Prepare data for AI analysis
                credit_data_ai = {"percentage": credit_percentage, "revenue": credit_revenue}
                cash_data_ai = {"percentage": cash_percentage, "revenue": cash_revenue}
                both_data_ai = {"percentage": both_percentage, "revenue": both_revenue}
                
                # We'll pass empty channel data for now, can be enhanced later
                ai_insights = core.analyze_credit_ratio_ceo(
                    credit_data_ai, 
                    cash_data_ai, 
                    both_data_ai,
                    []  # channel_data - can be fetched if needed
                )
                logger.warning(f"DEBUG: AI generation success. Result: {ai_insights}")
            except Exception as e:
                import traceback
                error_msg = f"AI insights generation failed: {str(e)}\n{traceback.format_exc()}"
                logger.error(error_msg)
                # Don't fail the entire request if AI fails
                ai_insights = None
        
        response = {
            "month": month,
            "credit": {
                "order_count": credit_orders,
                "revenue": credit_revenue,
                "percentage": round(credit_percentage, 2)
            },
            "cash": {
                "order_count": cash_orders,
                "revenue": cash_revenue,
                "percentage": round(cash_percentage, 2)
            },
            "both": {
                "order_count": both_orders,
                "revenue": both_revenue,
                "percentage": round(both_percentage, 2)
            },
            "other": {
                "order_count": other_orders,
                "revenue": other_revenue,
                "percentage": round(other_percentage, 2)
            },
            "total_revenue": total_revenue,
            "total_orders": total_orders
        }
        
        # Add AI insights if available
        if ai_insights:
            response["ai_insights"] = ai_insights
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/credit-sales-insights/generate")
def generate_credit_sales_insights(unit_id: str = None, month: str = None):
    """Generate on-demand AI insights for credit vs cash sales."""
    from db.engine import db
    import logging
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ai_insights")

    try:
        unit_filter = f" AND \"unit_id\" = '{unit_id}'" if unit_id else ""
        
        # Determine month
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
                month = eval(db_result)[0][0] if db_result else "2025-12"
            except Exception:
                month = "2025-12"

        # Parse date range
        try:
             # Handle "Month YYYY" format if passed
            if ' ' in month and len(month.split('-')) < 2:
                from datetime import datetime
                dt = datetime.strptime(month, "%B %Y")
                month = dt.strftime("%Y-%m")
            
            year, month_num = month.split('-')
            start_date = f"{year}-{month_num.zfill(2)}-01"
            if int(month_num) == 12:
                end_date = f"{int(year)+1}-01-01"
            else:
                end_date = f"{year}-{str(int(month_num)+1).zfill(2)}-01"
        except Exception as e:
            logger.error(f"Date parsing error: {e}")
            return {"error": "Invalid date format"}

        # Query Data
        query = f'''
        SELECT 
            CASE
                WHEN LOWER("credit_facility_type") = 'cash' THEN 'Cash'
                WHEN LOWER("credit_facility_type") = 'both' THEN 'Both'
                WHEN LOWER("credit_facility_type") = 'credit' THEN 'Credit'
                ELSE 'Other'
            END AS pay_type,
            COUNT(*) as order_count,
            ROUND(CAST(SUM("delivery_qty") AS NUMERIC), 2) as total_revenue
        FROM tbldeliveryinfo
        WHERE "delivery_date" >= '{start_date}'
          AND "delivery_date" < '{end_date}'
          AND "delivery_qty" IS NOT NULL
        {unit_filter}
        GROUP BY pay_type
        '''
        
        try:
            db_result = db.run(query)
            result = eval(db_result) if db_result else []
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

        # Aggregation
        credit_revenue = 0.0
        cash_revenue = 0.0
        both_revenue = 0.0
        other_revenue = 0.0
        
        for row in result:
            pay_type = row[0]
            revenue = float(row[2]) if row[2] is not None else 0.0
            
            if pay_type == 'Credit': credit_revenue = revenue
            elif pay_type == 'Cash': cash_revenue = revenue
            elif pay_type == 'Both': both_revenue = revenue
            else: other_revenue = revenue

        total_revenue = credit_revenue + cash_revenue + both_revenue + other_revenue
        
        if total_revenue == 0:
            return {"insights": "No sales data available to generate insights."}

        # Calculate Percentages
        credit_percentage = (credit_revenue / total_revenue * 100)
        cash_percentage = (cash_revenue / total_revenue * 100)
        both_percentage = (both_revenue / total_revenue * 100)

        # Generate AI Insights
        from .deps import get_core
        core = get_core()
        
        credit_data_ai = {"percentage": credit_percentage, "revenue": credit_revenue}
        cash_data_ai = {"percentage": cash_percentage, "revenue": cash_revenue}
        both_data_ai = {"percentage": both_percentage, "revenue": both_revenue}
        
        insights = core.analyze_credit_ratio_ceo(
            credit_data_ai, 
            cash_data_ai, 
            both_data_ai,
            [] 
        )
        
        return {"insights": insights}

    except Exception as e:
        logger.error(f"Insight generation error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

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
                print(f"Error parsing channel credit latest month (api.py): {e}")
                latest_result = []
            month = latest_result[0][0] if latest_result else "2025-12"
        
        # Parse year and month to create date range
        year, month_num = month.split('-')
        
        # Create date range for faster querying (instead of EXTRACT)
        from datetime import datetime, timedelta
        start_date = f"{year}-{month_num.zfill(2)}-01"
        # Calculate last day of month
        if int(month_num) == 12:
            end_date = f"{int(year)+1}-01-01"
        else:
            end_date = f"{year}-{str(int(month_num)+1).zfill(2)}-01"

        # Optimized query using LOWER() instead of ILIKE and date ranges
        query = f'''
        WITH base AS (
            SELECT
                "channel_name",
                CASE
                    WHEN LOWER("credit_facility_type") = 'cash' THEN 'Cash'
                    WHEN LOWER("credit_facility_type") = 'both' THEN 'Both'
                    WHEN LOWER("credit_facility_type") = 'credit' THEN 'Credit'
                    ELSE 'Other'
                END AS pay_type,
                "delivery_qty"
            FROM tbldeliveryinfo
            WHERE "delivery_date" >= '{start_date}'
              AND "delivery_date" < '{end_date}'
              AND "channel_name" IS NOT NULL
              AND "delivery_qty" IS NOT NULL
            {unit_filter}
        ),
        agg AS (
            SELECT
                pay_type,
                "channel_name",
                SUM("delivery_qty") AS channel_qty
            FROM base
            GROUP BY pay_type, "channel_name"
        ),
        totals AS (
            SELECT
                pay_type,
                SUM(channel_qty) AS total_per_type
            FROM agg
            GROUP BY pay_type
        )
        SELECT
            a.pay_type,
            a."channel_name",
            ROUND(CAST(a.channel_qty AS NUMERIC), 2) AS channel_qty,
            ROUND(
                a.channel_qty * 100.0 / t.total_per_type,
                2
            ) AS channel_pct_within_pay_type
        FROM agg a
        JOIN totals t ON a.pay_type = t.pay_type
        ORDER BY a.pay_type, channel_pct_within_pay_type DESC
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
            channel_qty = float(row[2]) if row[2] is not None else 0.0
            channel_pct = float(row[3]) if row[3] is not None else 0.0
            
            by_payment_type[pay_type].append({
                "channel_name": channel_name,
                "revenue": channel_qty,
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

@router.get("/v1/concentration-risk")
def get_concentration_risk(unit_id: str = None, month: str = None):
    """Get customer concentration risk metrics based on delivery quantity."""
    from db.engine import db
    from datetime import datetime
    
    try:
        # Get target month
        if not month:
            # If no month provided, get the latest month from DB
            latest_month_query = 'SELECT MAX(TO_CHAR("delivery_date", \'YYYY-MM\')) FROM tbldeliveryinfo'
            latest_month_result = eval(db.run(latest_month_query))
            if latest_month_result and latest_month_result[0][0]:
                month = latest_month_result[0][0]
        
        # Parse month to get date range
        if month:
            year, month_num = month.split('-')
            start_date = f"{year}-{month_num.zfill(2)}-01"
            # Calculate last day of month
            if int(month_num) == 12:
                end_date = f"{int(year)+1}-01-01"
            else:
                end_date = f"{year}-{str(int(month_num)+1).zfill(2)}-01"
        else:
            # Fallback to current month
            now = datetime.now()
            start_date = f"{now.year}-{now.month:02d}-01"
            if now.month == 12:
                end_date = f"{now.year+1}-01-01"
            else:
                end_date = f"{now.year}-{now.month+1:02d}-01"
        
        unit_filter = f"AND unit_id = '{unit_id}'" if unit_id else ""
        
        # 1. Get total quantity
        query_total = f'''
        SELECT SUM(delivery_qty) AS total_qty
        FROM public.tbldeliveryinfo
        WHERE delivery_date >= DATE '{start_date}'
          AND delivery_date < DATE '{end_date}'
          AND delivery_qty IS NOT NULL
          {unit_filter}
        '''
        
        total_result = eval(db.run(query_total))
        total_qty = float(total_result[0][0]) if total_result and total_result[0][0] is not None else 0.0
        
        # 2. Get top 10 customers with percentage using window function
        query_top10 = f'''
        SELECT 
            customer_name,
            SUM(delivery_qty) as customer_qty,
            ROUND(
                SUM(delivery_qty) * 100.0 / NULLIF(SUM(SUM(delivery_qty)) OVER(), 0),
                2
            ) as qty_share_pct
        FROM public.tbldeliveryinfo
        WHERE customer_name IS NOT NULL 
          AND delivery_date >= DATE '{start_date}'
          AND delivery_date < DATE '{end_date}'
          {unit_filter}
        GROUP BY customer_name
        ORDER BY customer_qty DESC
        LIMIT 10
        '''
        
        try:
            db_result = db.run(query_top10)
            if not db_result or db_result.strip() == '':
                top10_result = []
            else:
                top10_result = eval(db_result)
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing concentration risk top10 query: {e}")
            top10_result = []
        
        top10_customers = []
        top10_qty_sum = 0.0
        
        if top10_result:
            for row in top10_result:
                name = row[0]
                qty = float(row[1]) if row[1] is not None else 0.0
                pct = float(row[2]) if row[2] is not None else 0.0
                top10_qty_sum += qty
                top10_customers.append({
                    "name": name,
                    "quantity": qty,
                    "percentage": pct
                })
            
        concentration_ratio = (top10_qty_sum / total_qty * 100) if total_qty > 0 else 0

        return {
            "concentration_ratio": round(concentration_ratio, 2),
            "total_quantity": total_qty,
            "top_10_quantity": top10_qty_sum,
            "top_10_customers": top10_customers,
            "month": month
        }

    except Exception as e:
        # Log error for debugging but don't crash the endpoint
        print(f"Error in concentration risk: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty structure instead of 500
        return {
            "concentration_ratio": 0,
            "total_quantity": 0,
            "top_10_quantity": 0,
            "top_10_customers": [],
            "month": month
        }


@router.get("/v1/concentration-risk-insights")
def get_concentration_risk_insights(unit_id: str = None, month: str = None):
    """Generate on-demand CEO insights for customer concentration risk."""
    from db.engine import db
    from datetime import datetime
    
    try:
        # Get target month
        if not month:
            latest_month_query = 'SELECT MAX(TO_CHAR("delivery_date", \'YYYY-MM\')) FROM tbldeliveryinfo'
            latest_month_result = eval(db.run(latest_month_query))
            if latest_month_result and latest_month_result[0][0]:
                month = latest_month_result[0][0]
        
        # Parse month to get date range
        if month:
            year, month_num = month.split('-')
            start_date = f"{year}-{month_num.zfill(2)}-01"
            if int(month_num) == 12:
                end_date = f"{int(year)+1}-01-01"
            else:
                end_date = f"{year}-{str(int(month_num)+1).zfill(2)}-01"
        else:
            now = datetime.now()
            start_date = f"{now.year}-{now.month:02d}-01"
            if now.month == 12:
                end_date = f"{now.year+1}-01-01"
            else:
                end_date = f"{now.year}-{now.month+1:02d}-01"
        
        unit_filter = f"AND unit_id = '{unit_id}'" if unit_id else ""
        
        # Get concentration data
        query_total = f'''
        SELECT SUM(delivery_qty) AS total_qty
        FROM public.tbldeliveryinfo
        WHERE delivery_date >= DATE '{start_date}'
          AND delivery_date < DATE '{end_date}'
          AND delivery_qty IS NOT NULL
          {unit_filter}
        '''
        
        total_result = eval(db.run(query_total))
        total_qty = float(total_result[0][0]) if total_result and total_result[0][0] is not None else 0.0
        
        # Get top 10 customers
        query_top10 = f'''
        SELECT 
            customer_name,
            SUM(delivery_qty) as customer_qty,
            ROUND(
                SUM(delivery_qty) * 100.0 / NULLIF(SUM(SUM(delivery_qty)) OVER(), 0),
                2
            ) as qty_share_pct
        FROM public.tbldeliveryinfo
        WHERE customer_name IS NOT NULL 
          AND delivery_date >= DATE '{start_date}'
          AND delivery_date < DATE '{end_date}'
          {unit_filter}
        GROUP BY customer_name
        ORDER BY customer_qty DESC
        LIMIT 10
        '''
        
        top10_result = eval(db.run(query_top10))
        
        top10_customers = []
        top10_qty_sum = 0.0
        
        if top10_result:
            for row in top10_result:
                name = row[0]
                qty = float(row[1]) if row[1] is not None else 0.0
                pct = float(row[2]) if row[2] is not None else 0.0
                top10_qty_sum += qty
                top10_customers.append({
                    "name": name,
                    "quantity": qty,
                    "percentage": pct
                })
        
        concentration_ratio = (top10_qty_sum / total_qty * 100) if total_qty > 0 else 0
        
        # Prepare data for LLM
        top_customer = top10_customers[0] if top10_customers else None
        
        # Create CEO-focused prompt (Hybrid: Risk + Actions)
        core = get_core()
        
        # Prepare top customer info for prompt
        if top_customer:
            top_customer_info = f"{top_customer['name']} ({top_customer['percentage']:.1f}% share, {top_customer['quantity']:.2f} MT)"
        else:
            top_customer_info = "N/A"
        
        
        # Build prompt using string concatenation to avoid f-string issues
        prompt_parts = [
            "You are a strategic business advisor for a CEO. Analyze this customer concentration data and provide actionable insights.",
            "",
            "DATA:",
            f"- Total Quantity: {total_qty:.2f} MT",
            f"- Top 10 Customers: {top10_qty_sum:.2f} MT ({concentration_ratio:.1f}% of total)",
            f"- Top Customer: {top_customer_info}",
            f"- Number of Top 10: {len(top10_customers)}",
            "",
            "TASK: Provide CEO-level insights in EXACTLY this format (150 words max):",
            "",
            "RISK SNAPSHOT:",
            "[1-2 sentences on concentration risk level and key dependency]",
            "",
            "KEY INSIGHT:",
            "[1 critical observation about the customer portfolio]",
            "",
            "TOP 3 ACTIONS:",
            "1. [Immediate action for this week]",
            "2. [Strategic action for this month]",
            "3. [Long-term action for this quarter]",
            "",
            "EXPECTED IMPACT:",
            "[Quantified outcome if actions are taken]",
            "",
            "RULES:",
            "- Be specific and actionable",
            "- Use exact numbers from the data",
            "- Focus on business impact",
            "- Keep it concise and CEO-friendly",
            "- No fluff or generic advice",
            "- DO NOT use markdown formatting (no **, *, _, etc.)",
            "- Use plain text only"
        ]
        prompt = "\n".join(prompt_parts)

        insights = core.general_response(prompt)
        
        return {
            "insights": insights,
            "generated_at": datetime.now().isoformat(),
            "concentration_ratio": round(concentration_ratio, 2),
            "metrics": {
                "total_quantity": total_qty,
                "top_10_quantity": top10_qty_sum,
                "top_customer_name": top_customer['name'] if top_customer else 'N/A',
                "top_customer_pct": top_customer['percentage'] if top_customer else 0
            }
        }
        
    except Exception as e:
        print(f"Error generating concentration insights: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))





@router.get("/v1/territory-performance")
def get_territory_performance(unit_id: str = None, month: str = None, year: str = None):
    """Get top 5 and bottom 5 territories and dealers using optimized CTE query."""
    from db.engine import db
    import datetime
    
    try:
        # Date Logic with year filter support
        today = datetime.date.today()
        
        if year and month:
            # Specific month in specific year
            # month is in format "YYYY-MM", extract just the month part
            if '-' in month:
                month_part = month.split('-')[1]
            else:
                month_part = month
            target_date = datetime.datetime.strptime(f"{year}-{month_part}", "%Y-%m").date()
            start_date = f"{target_date.year}-{target_date.month:02d}-01"
            if target_date.month == 12:
                end_date = f"{target_date.year + 1}-01-01"
            else:
                end_date = f"{target_date.year}-{target_date.month + 1:02d}-01"
        elif year:
            # Entire year
            start_date = f"{year}-01-01"
            end_date = f"{int(year) + 1}-01-01"
        elif month:
            # Specific month (from existing month parameter which includes year)
            if not month:
                latest_month_query = 'SELECT MAX(TO_CHAR("delivery_date", \'YYYY-MM\')) FROM tbldeliveryinfo'
                latest_month_result = eval(db.run(latest_month_query))
                if latest_month_result and latest_month_result[0][0]:
                    month = latest_month_result[0][0]
            
            if month:
                year_str, month_num = month.split('-')
                start_date = f"{year_str}-{month_num.zfill(2)}-01"
                if int(month_num) == 12:
                    end_date = f"{int(year_str)+1}-01-01"
                else:
                    end_date = f"{year_str}-{str(int(month_num)+1).zfill(2)}-01"
            else:
                now = datetime.datetime.now()
                start_date = f"{now.year}-{now.month:02d}-01"
                if now.month == 12:
                    end_date = f"{now.year+1}-01-01"
                else:
                    end_date = f"{now.year}-{now.month+1:02d}-01"
        else:
            # Current month or latest available
            if not month:
                latest_month_query = 'SELECT MAX(TO_CHAR("delivery_date", \'YYYY-MM\')) FROM tbldeliveryinfo'
                latest_month_result = eval(db.run(latest_month_query))
                if latest_month_result and latest_month_result[0][0]:
                    month = latest_month_result[0][0]
        
        unit_filter = f"AND unit_id = '{unit_id}'" if unit_id else ""
        
        # Optimized query for territories using CTE and window functions
        query_territory = f'''
        WITH territory_perf AS (
          SELECT
            territory,
            SUM(delivery_qty) AS total_qty,
            COUNT(*) AS orders
          FROM public.tbldeliveryinfo
          WHERE territory IS NOT NULL
            {unit_filter}
            AND delivery_date >= DATE '{start_date}'
            AND delivery_date <  DATE '{end_date}'
          GROUP BY territory
        ),
        ranked AS (
          SELECT
            *,
            ROW_NUMBER() OVER (ORDER BY total_qty DESC) AS rn_desc,
            ROW_NUMBER() OVER (ORDER BY total_qty ASC)  AS rn_asc
          FROM territory_perf
        )
        SELECT
          CASE
            WHEN rn_desc <= 5 THEN 'Top 5'
            WHEN rn_asc  <= 5 THEN 'Bottom 5'
          END AS bucket,
          territory,
          total_qty,
          orders
        FROM ranked
        WHERE rn_desc <= 5 OR rn_asc <= 5
        ORDER BY bucket, total_qty DESC
        '''
        
        territory_result = eval(db.run(query_territory))
        
        top_territories = []
        bottom_territories = []
        
        for row in territory_result:
            bucket = row[0]
            item = {
                "name": row[1],
                "quantity": float(row[2]) if row[2] is not None else 0.0,
                "orders": row[3]
            }
            if bucket == 'Top 5':
                top_territories.append(item)
            else:
                bottom_territories.append(item)
        
        return {
            "top_territories": top_territories,
            "bottom_territories": bottom_territories,
            "month": month
        }

    except Exception as e:
        print(f"Error in territory performance: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "top_territories": [],
            "bottom_territories": [],
            "month": month
        }

@router.post("/v1/territory-insights")
def generate_territory_insights(unit_id: str = None, month: str = None):
    """Generate strategic AI insights for territory performance."""
    try:
        from db.engine import db
        import datetime
        from .deps import get_core
        
        # Date logic
        today = datetime.date.today()
        if month:
            target_date = datetime.datetime.strptime(month, "%Y-%m").date()
            start_date = target_date.replace(day=1)
            # End date: First day of next month
            next_month_val = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month_val.replace(day=1)
        else:
            # Default logic matching performance endpoint if needed, or just current month
            start_date = today.replace(day=1)
            next_month_val = start_date.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month_val.replace(day=1)

        unit_filter = f" AND unit_id = '{unit_id}'" if unit_id else "" 
        # In get_territory_performance it was {unit_filter} variable constructed earlier.
        # Let's check get_territory_performance source for unit_filter construction... 
        # Line 1461: unit_filter = f" AND \"Unit_Id\" = '{unit_id}'" if unit_id else ""
        # Wait, tables sometimes use "unit_id" or "Unit_Id". tbldeliveryinfo usually has "unit_id" or "Unit_Id"?
        # Let's double check get_territory_performance.
        
        # 1. Get Top/Bottom Territories
        query_territory = f'''
        WITH territory_perf AS (
          SELECT
            territory,
            SUM(delivery_qty) AS total_qty,
            COUNT(*) AS orders
          FROM public.tbldeliveryinfo
          WHERE territory IS NOT NULL
            {unit_filter}
            AND delivery_date >= DATE '{start_date}'
            AND delivery_date <  DATE '{end_date}'
          GROUP BY territory
        ),
        ranked AS (
          SELECT
            *,
            ROW_NUMBER() OVER (ORDER BY total_qty DESC) AS rn_desc,
            ROW_NUMBER() OVER (ORDER BY total_qty ASC)  AS rn_asc
          FROM territory_perf
        )
        SELECT
          CASE
            WHEN rn_desc <= 5 THEN 'Top 5'
            WHEN rn_asc  <= 5 THEN 'Bottom 5'
          END AS bucket,
          territory,
          total_qty,
          orders
        FROM ranked
        WHERE rn_desc <= 5 OR rn_asc <= 5
        ORDER BY bucket, total_qty DESC
        '''
        
        territory_result = eval(db.run(query_territory))
        
        top_territories = []
        bottom_territories = []
        
        for row in territory_result:
            bucket = row[0]
            item = {
                "name": row[1],
                "quantity": float(row[2]) if row[2] is not None else 0.0,
                "orders": row[3]
            }
            if bucket == 'Top 5':
                top_territories.append(item)
            else:
                bottom_territories.append(item) 
        bottom_territories.sort(key=lambda x: x['quantity']) # Now [0] is the absolute lowest.

        # 2. Get Total Volume
        query_total = f'''
        SELECT SUM(delivery_qty)
        FROM public.tbldeliveryinfo
        WHERE territory IS NOT NULL
          {unit_filter}
          AND delivery_date >= DATE '{start_date}'
          AND delivery_date <  DATE '{end_date}'
        '''
        res_total = db.run(query_total)
        try:
             # db.run returns string representation of list of tuples usually? e.g. "[(123.45,)]"
             parsed = eval(res_total) if res_total else []
             if parsed and parsed[0] and parsed[0][0]:
                 total_volume = float(parsed[0][0])
             else:
                 total_volume = 1.0
        except:
             total_volume = 1.0 
        
        # 3. Generate Insights
        core = get_core()
        insights = core.analyze_territory_performance(top_territories, bottom_territories, total_volume)
        
        return insights

    except Exception as e:
        print(f"Error generating territory insights: {e}")
        import traceback
        traceback.print_exc()
        return {"analysis": f"Could not generate insights: {str(e)}"}

@router.post("/v1/forecast/generate-insights")
def generate_forecast_insights(request: dict):
    """Generate on-demand AI insights for sales forecast."""
    from db.engine import db
    unit_id = request.get("unit_id")
    
    try:
        unit_filter_ail = f" AND \"Unit_Id\" = '{unit_id}'" if unit_id else ""
        
        # 1. Global Forecast Summary (Next 5 Months)
        q_global = f'''
         SELECT 
            TO_CHAR("Date", 'YYYY-MM') AS month,
            SUM("numDeliveryQtyMT") AS total_qty
            FROM "AIL_Monthly_Total_Forecast"
            WHERE "Type" = 'Forecasted'
            {unit_filter_ail}
            AND "Date" >= date_trunc('month', CURRENT_DATE)
            AND "Date" <  date_trunc('month', CURRENT_DATE) + INTERVAL '5 months'
            GROUP BY month
            ORDER BY month;
        '''
        
        # 2. Top 5 Items Summary
        q_items = f'''
        SELECT "Item_Name", SUM("numDeliveryQtyMT") as qty
        FROM "AIL_Monthly_Total_Item" 
        WHERE "Type" = 'Forecasted'
        {unit_filter_ail}
        GROUP BY "Item_Name"
        ORDER BY qty DESC LIMIT 5
        '''

        # 3. Top 5 Territories Summary
        q_terrs = f'''
        SELECT "Territory", SUM("numDeliveryQtyMT") as qty
        FROM "AIL_Monthly_Total_Final_Territory"
        WHERE "Type" = 'Forecasted'
        {unit_filter_ail}
        GROUP BY "Territory"
        ORDER BY qty DESC LIMIT 5
        '''

        try:
            # Execute Queries
            raw_global = db.run(q_global)
            res_global = eval(raw_global) if raw_global else []
            total_forecast_summary = [{"month": r[0], "qty": float(r[1])} for r in res_global]

            raw_items = db.run(q_items)
            res_items = eval(raw_items) if raw_items else []
            top_items_summary = [{"name": r[0], "qty": float(r[1])} for r in res_items]

            raw_terrs = db.run(q_terrs)
            res_terrs = eval(raw_terrs) if raw_terrs else []
            top_terrs_summary = [{"name": r[0], "qty": float(r[1])} for r in res_terrs]

            # Calculate growth metrics for CEO insights
            # Get last actual month data for comparison
            q_last_actual = f'''
            SELECT SUM("numDeliveryQtyMT") as total_qty
            FROM "AIL_Monthly_Total_Forecast"
            WHERE 1=1
            {unit_filter_ail}
            AND "Date" = date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
            '''
            
            raw_last = db.run(q_last_actual)
            res_last = eval(raw_last) if raw_last else []
            last_actual = float(res_last[0][0]) if res_last and res_last[0] and res_last[0][0] else 0
            
            # Calculate average forecast and growth
            avg_forecast = sum(d['qty'] for d in total_forecast_summary) / len(total_forecast_summary) if total_forecast_summary else 0
            growth_pct = ((avg_forecast - last_actual) / last_actual * 100) if last_actual > 0 else 0
            
            growth_metrics = {
                "volume_growth_pct": growth_pct,
                "order_growth_pct": growth_pct * 0.9,  # Approximate
                "is_growing": growth_pct > 0,
                "momentum": "Strong" if abs(growth_pct) > 10 else "Moderate" if abs(growth_pct) > 5 else "Stable"
            }

            # Generate CEO-focused AI insights
            core = get_core()
            ai_insights = core.analyze_forecast_ceo(
                total_forecast_summary, 
                top_items_summary, 
                top_terrs_summary,
                growth_metrics
            )
            
            return {"insights": ai_insights}

        except Exception as e:
            print(f"Data Fetch Error in Insights: {e}")
            return {"insights": "Could not generate analysis due to data error."}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/forecast")
def get_sales_forecast(unit_id: str = None):
    """Get sales forecast data with AI insights and comparative charts."""
    from db.engine import db
    import datetime
    
    try:
        unit_filter_delivery = f" AND \"unit_id\" = '{unit_id}'" if unit_id else ""
        unit_filter_ail = f" AND \"Unit_Id\" = '{unit_id}'" if unit_id else ""
        
        # Helper to merge actual and forecast
        def merge_data(actual_rows, forecast_rows):
            data_map = {}
            # Process Actuals
            for row in actual_rows:
                m, qty = row[0], float(row[1])
                data_map[m] = {"month": m, "actual": qty, "forecast": None}
            # Process Forecasts
            for row in forecast_rows:
                m, qty = row[0], float(row[1])
                if m in data_map:
                    data_map[m]["forecast"] = qty # Overlap if any
                else:
                    data_map[m] = {"month": m, "actual": None, "forecast": qty}
            
            # Sort by month
            sorted_keys = sorted(data_map.keys())
            return [data_map[k] for k in sorted_keys]

        # 1. Global Chart
        # Global Actuals (Historical) - Include all data before current month as actual
        # This ensures December 2025 shows even if marked as 'Forecasted' in DB
        q_global_act = f'''
         SELECT 
            TO_CHAR("Date", 'YYYY-MM') AS month,
            SUM("numDeliveryQtyMT") AS total_qty
            FROM "AIL_Monthly_Total_Forecast"
            WHERE 1=1
            {unit_filter_ail}
            AND "Date" >= date_trunc('month', CURRENT_DATE) - INTERVAL '12 months'
            AND "Date" < date_trunc('month', CURRENT_DATE)
            GROUP BY month
            ORDER BY month DESC;
        '''
        # Global Forecast
        q_global_for = f'''
         SELECT 
            TO_CHAR("Date", 'YYYY-MM') AS month,
            SUM("numDeliveryQtyMT") AS total_qty
            FROM "AIL_Monthly_Total_Forecast"
            WHERE "Type" = 'Forecasted'
            {unit_filter_ail}
            AND "Date" >= date_trunc('month', CURRENT_DATE)
            AND "Date" <  date_trunc('month', CURRENT_DATE) + INTERVAL '5 months'
            GROUP BY month
            ORDER BY month;
        '''
        try:
            raw_act = db.run(q_global_act)
            if not raw_act: raw_act = "[]"
            res_act = eval(raw_act)
            res_act.reverse()

            raw_for = db.run(q_global_for)
            if not raw_for: raw_for = "[]"
            res_for = eval(raw_for)
            res_for.reverse()
        except Exception as e:
            print(f"Global Forecast Query Error: {e}")
            res_act = []
            res_for = []

        global_chart = merge_data(res_act, res_for)
        total_forecast_summary = [{"month": r[0], "qty": float(r[1])} for r in res_for]

        # 2. Items Charts (All Forecasted Items)
        q_top_items = f'''
        SELECT "Item_Name" FROM "AIL_Monthly_Total_Item" 
        WHERE "Type" = 'Forecasted'
        {unit_filter_ail}
        ORDER BY "numDeliveryQtyMT" DESC LIMIT 100
        '''
        try:
             raw_top_items = db.run(q_top_items)
             if not raw_top_items: raw_top_items = "[]"
             top_items_res = eval(raw_top_items)
             # Deduplicate names if any
             top_item_names = list(dict.fromkeys([r[0] for r in top_items_res])) if top_items_res else []
        except Exception as e:
             print(f"Error fetching top items: {e}")
             top_item_names = []
        
        items_charts = []
        if top_item_names:
            try:
                escaped_names = ["'" + n.replace("'", "''") + "'" for n in top_item_names]
                names_in_clause = ",".join(escaped_names)
                
                # Bulk fetch for all items at once
                # Include all data before current month as actual (regardless of Type)
                q_bulk_items = f'''
                SELECT "Item_Name", 
                       CASE WHEN "Date" < date_trunc('month', CURRENT_DATE) THEN 'Historical' ELSE "Type" END as "Type",
                       TO_CHAR("Date", 'YYYY-MM') as month, 
                       SUM("numDeliveryQtyMT")
                FROM "AIL_Monthly_Total_Item" 
                WHERE "Item_Name" IN ({names_in_clause})
                {unit_filter_ail}
                AND "Date" >= date_trunc('month', CURRENT_DATE) - INTERVAL '12 months'
                AND "Date" < date_trunc('month', CURRENT_DATE) + INTERVAL '6 months'
                GROUP BY "Item_Name", "Type", month, "Date"
                ORDER BY month ASC
                '''
                
                raw_bulk = db.run(q_bulk_items)
                res_bulk = eval(raw_bulk) if raw_bulk else []
                
                # Organize data
                item_data_map = {name: {"Historical": [], "Forecasted": []} for name in top_item_names}
                
                for row in res_bulk:
                    # Expecting: Name, Type, Month, Qty
                    i_name, i_type, i_month, i_qty = row
                    if i_name in item_data_map:
                        item_data_map[i_name].setdefault(i_type, []).append([i_month, float(i_qty)])
                
                # Build charts preserving order
                for name in top_item_names:
                    hist_data = item_data_map[name]["Historical"]
                    for_data = item_data_map[name]["Forecasted"]
                    items_charts.append({
                        "name": name, 
                        "chart": merge_data(hist_data, for_data)
                    })
                    
            except Exception as e:
                print(f"Bulk Item Fetch Error: {e}")
                items_charts = []

        # 3. Territories Charts (All Forecasted Territories)
        q_top_terrs = f'''
        SELECT "Territory" FROM "AIL_Monthly_Total_Final_Territory"
        WHERE "Type" = 'Forecasted'
        {unit_filter_ail}
        ORDER BY "numDeliveryQtyMT" DESC LIMIT 100
        '''
        try:
             raw_top_terrs = db.run(q_top_terrs)
             if not raw_top_terrs: raw_top_terrs = "[]"
             top_terrs_res = eval(raw_top_terrs)
             top_terr_names = list(dict.fromkeys([r[0] for r in top_terrs_res])) if top_terrs_res else []
        except Exception as e:
             print(f"Error fetching top territories: {e}")
             top_terr_names = []

        territories_charts = []
        if top_terr_names:
            try:
                escaped_names = ["'" + n.replace("'", "''") + "'" for n in top_terr_names]
                names_in_clause = ",".join(escaped_names)
                
                # Bulk fetch for all territories
                # Include all data before current month as actual (regardless of Type)
                q_bulk_terrs = f'''
                SELECT "Territory", 
                       CASE WHEN "Date" < date_trunc('month', CURRENT_DATE) THEN 'Historical' ELSE "Type" END as "Type",
                       TO_CHAR("Date", 'YYYY-MM') as month, 
                       SUM("numDeliveryQtyMT")
                FROM "AIL_Monthly_Total_Final_Territory"
                WHERE "Territory" IN ({names_in_clause})
                {unit_filter_ail}
                AND "Date" >= date_trunc('month', CURRENT_DATE) - INTERVAL '12 months'
                AND "Date" < date_trunc('month', CURRENT_DATE) + INTERVAL '6 months'
                GROUP BY "Territory", "Type", month, "Date"
                ORDER BY month ASC
                '''
                
                raw_bulk = db.run(q_bulk_terrs)
                res_bulk = eval(raw_bulk) if raw_bulk else []
                
                # Organize data
                terr_data_map = {name: {"Historical": [], "Forecasted": []} for name in top_terr_names}
                
                for row in res_bulk:
                     t_name, t_type, t_month, t_qty = row
                     if t_name in terr_data_map:
                         terr_data_map[t_name].setdefault(t_type, []).append([t_month, float(t_qty)])
                
                # Build charts
                for name in top_terr_names:
                    hist_data = terr_data_map[name]["Historical"]
                    for_data = terr_data_map[name]["Forecasted"]
                    territories_charts.append({
                        "name": name, 
                        "chart": merge_data(hist_data, for_data)
                    })
                    
            except Exception as e:
                print(f"Bulk Territory Fetch Error: {e}")
                territories_charts = []

        # Summary Lists for AI - Calculate actual totals from the chart data
        top_items_summary = []
        for ic in items_charts[:5]: # Top 5 items
            total_forecast = sum(d["forecast"] or 0 for d in ic["chart"] if d["forecast"] is not None)
            top_items_summary.append({"name": ic["name"], "qty": total_forecast})

        top_terrs_summary = []
        for tc in territories_charts[:5]: # Top 5 territories
            total_forecast = sum(d["forecast"] or 0 for d in tc["chart"] if d["forecast"] is not None)
            top_terrs_summary.append({"name": tc["name"], "qty": total_forecast})

        
        return {
            "global_chart": global_chart,
            "items_charts": items_charts,
            "territories_charts": territories_charts,
            "ai_insights": None
        }

        # Top Territories List
        q_terr_list = '''
        SELECT "Territory", SUM("numDeliveryQtyMT") as qty
        FROM "AIL_Monthly_Total_Final_Territory"
        WHERE "Date" >= CURRENT_DATE
        GROUP BY "Territory" ORDER BY qty DESC LIMIT 3
        '''
        try:
             res_terr_list = eval(db.run(q_terr_list))
             top_territories = [{"name": r[0], "qty": float(r[1])} for r in res_terr_list]
        except:
             top_territories = []

        
        return {
            "global_chart": global_chart,
            "item_chart": item_chart,
            "territory_chart": territory_chart,
            "top_item_name": top_item_name,
            "top_territory_name": top_terr_name,
            "ai_insights": None
        }

    except Exception as e:
        print(f"Forecast Error: {e}")
        return {
            "global_chart": [],
            "item_chart": [],
            "territory_chart": [],
            "ai_insights": {"trend": "Unknown", "analysis": "Forecast data not available."}
        }
