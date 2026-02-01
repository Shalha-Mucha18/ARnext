import json
import re
from typing import Dict, Any, List, Optional

from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_community.tools import QuerySQLDatabaseTool
from langchain_classic.chains.sql_database.query import create_sql_query_chain

from core.config import settings
from db.sql_safety import extract_sql, is_select_only, ensure_limit, enforce_allowlist
from db.engine import db
from llm.prompts import (
    contextualize_prompt, descriptive_prompt, prescriptive_prompt, entity_extract_prompt,
    reasoning_step1_prompt, reasoning_step2_prompt, reasoning_step3_prompt, reasoning_step4_prompt,
    general_chat_prompt
)

parser = StrOutputParser()

def looks_like_why(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(re.search(r"\b(why|reason|explain|root cause|what happened|recommend|suggest|how to|action)\b", t))

def looks_like_followup(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(re.search(r"\b(now|same|also|only|filter|breakdown|by\b|for\b|last\b|previous|compare|trend)\b", t))

def safe_json_load(s: str) -> dict:
    try:
        return json.loads(s)
    except Exception:
        return {"entity_type":"unknown","entities":[],"metric":"unknown"}

class SalesGPTCore:
    """
    Orchestrates:
    - contextualize follow-up
    - SQL generation + validation + execution
    - descriptive answer
    - prescriptive answer on why
    - entity extraction for context
    - general chat fallback
    """

    def __init__(self, llm):
        self.llm = llm
        self.allowed_tables = [t.strip() for t in settings.ALLOWED_TABLES.split(",") if t.strip()]
        
        # Use custom SQL prompt for speed and accuracy (1 call vs 5 calls)
        from llm.sql_prompt_enhanced import sql_prompt
        
        self.sql_writer = create_sql_query_chain(llm, db, prompt=sql_prompt)
        self.sql_executor = QuerySQLDatabaseTool(db=db)

        self.contextualize_chain = contextualize_prompt | llm | parser
        self.descriptive_chain = descriptive_prompt | llm | parser
        self.prescriptive_chain = prescriptive_prompt | llm | parser
        self.entity_extract_chain = entity_extract_prompt | llm | parser
        self.general_chain = general_chat_prompt | llm | parser

    def general_response(self, question: str) -> str:
        """Provide a general response when SQL fails or isn't needed."""
        return self.general_chain.invoke({"question": question}).strip()


    def elaborate(self, last_question: str, last_answer: str, last_result: str, user_request: str) -> str:
        """Provide more details about the previous answer based on context."""
        elaboration_prompt = f"""You are a knowledgeable sales analytics assistant. The user wants more details about your previous answer.

Previous Question: {last_question}
Previous Answer: {last_answer}
Context Data: {last_result}
User Request: {user_request}

IMPORTANT: 
- Answer in English.
- **DO NOT** mention "SQL", "database", or "query".
- Be conversational and helpful.

Provide a deeper explanation based on the previous answer and data:
- Elaborate on the insights mentioned
- Provide additional context or implications
- Suggest what this means for the business
- Keep it conversational and concise (3-5 paragraphs)
- Use **bold** for key points
- Reference specific numbers from the data

Build upon the previous answer with more depth and context."""
        
        return self.llm.invoke(elaboration_prompt).content.strip()

    def analyze_with_reasoning(self, question: str, result: str, descriptive_answer: str) -> str:
        """Multi-step reasoning for analytical questions."""
        
        # Step 1: Data Understanding - Identify key observations
        step1_chain = reasoning_step1_prompt | self.llm | parser
        observations = step1_chain.invoke({
            "question": question,
            "result": result,
            "descriptive_answer": descriptive_answer
        })

        
        # Step 2: Pattern Identification
        step2_chain = reasoning_step2_prompt | self.llm | parser
        patterns = step2_chain.invoke({
            "observations": observations
        })
        
        # Step 3: Implication Analysis
        step3_chain = reasoning_step3_prompt | self.llm | parser
        implications = step3_chain.invoke({
            "patterns": patterns
        })
        
        # Step 4: Recommendations
        step4_chain = reasoning_step4_prompt | self.llm | parser
        recommendations = step4_chain.invoke({
            "implications": implications
        })
        
        # Combine all steps into structured response
        structured_answer = f"""**Analysis:**

📊 **Data Insights:**
{observations}

🔍 **Patterns Identified:**
{patterns}

💡 **Business Implications:**
{implications}

✅ **Recommendations:**
{recommendations}"""
        
        return structured_answer

    def run_sql_from_question(self, question: str) -> Dict[str, Any]:
        """Generate and execute SQL from natural language using custom prompt chain."""
        
        # 1. Generate SQL using the improved prompt
        raw = self.sql_writer.invoke({"question": question})
        sql = extract_sql(raw)
        
        print(f"\\n[DEBUG] Original SQL generated:\\n{sql}\\n")

        # 2. Safety checks
        if not is_select_only(sql):
            raise ValueError(f"Unsafe SQL blocked:\\n{sql}")

        enforce_allowlist(sql, self.allowed_tables)
        sql = ensure_limit(sql, settings.DEFAULT_LIMIT)
        
        print(f"[DEBUG] SQL after ensure_limit:\\n{sql}\\n")

        # 3. Execution with auto-fix logic
        try:
            result = self.sql_executor.invoke(sql)
            
            # Check if result contains SQL error text (LangChain sometimes returns errors as strings)
            result_str = str(result).lower()
            if "error" in result_str and ("syntax" in result_str or "relation" in result_str or "column" in result_str or "limit" in result_str):
                 raise ValueError(f"SQL Error in result: {result}")
                 
            print(f"[DEBUG] Query executed successfully. Result: {str(result)[:200]}\\n")
            return {"question": question, "query": sql, "result": result}
        except Exception as e:
            error_msg = str(e).lower()
            print(f"[DEBUG] Query execution failed: {error_msg}\\n")
            
            # Auto-fix common SQL errors (LIMIT, syntax)
            if "limit" in error_msg or "syntax error" in error_msg:
                print("[DEBUG] Attempting auto-fix by removing LIMIT...\\n")
                # Remove all LIMIT clauses and let ensure_limit add the correct one
                sql_fixed = re.sub(r'\\s*LIMIT\\s+\\d+', '', sql, flags=re.IGNORECASE)
                sql_fixed = ensure_limit(sql_fixed, settings.DEFAULT_LIMIT)
                
                print(f"[DEBUG] Fixed SQL:\\n{sql_fixed}\\n")
                
                try:
                    result = self.sql_executor.invoke(sql_fixed)
                    print(f"[DEBUG] Auto-fix successful!\\n")
                    return {"question": question, "query": sql_fixed, "result": result}
                except Exception:
                    pass  # If still fails, raise original error
            
            # If auto-fix didn't work, raise the original error
            raise ValueError(f"SQL execution failed: {str(e)}\\n\\nQuery:\\n{sql}")

    def contextualize(self, last_question: str, entity_type: str, entities: List[str], metric: str, user_message: str) -> str:
        return self.contextualize_chain.invoke({
            "last_question": last_question,
            "entity_type": entity_type,
            "entities": entities,
            "metric": metric,
            "user_message": user_message
        }).strip()

    def descriptive(self, out: Dict[str, Any]) -> str:
        return self.descriptive_chain.invoke(out).strip()

    def prescriptive(self, question: str, query: str, result: str, descriptive_answer: str) -> str:
        return self.prescriptive_chain.invoke({
            "question": question,
            "query": query,
            "result": result,
            "descriptive_answer": descriptive_answer
        }).strip()

    def extract_entities(self, query: str, result: str) -> dict:
        js = self.entity_extract_chain.invoke({"query": query, "result": result})
        return safe_json_load(js)



    def analyze_sales_metrics(self, current_month: dict, trend_data: list) -> dict:
        """Generate AI insights for sales metrics."""
        from llm.prompts import sales_metrics_prompt
        
        # Format data for prompt
        current_summary = f"{current_month['qty']:.0f} MT, ৳{current_month['revenue']/1000000:.0f}M revenue"
        
        # Calculate trend
        if len(trend_data) >= 2:
            recent_qty = trend_data[0]['qty']
            prev_qty = trend_data[1]['qty']
            growth = ((recent_qty - prev_qty) / prev_qty * 100) if prev_qty > 0 else 0
            trend_summary = f"Last month: {recent_qty:.0f} MT vs prev: {prev_qty:.0f} MT ({growth:+.1f}%)"
        else:
            trend_summary = "Insufficient data"
        
        # Generate insights
        chain = sales_metrics_prompt | self.llm | parser
        analysis = chain.invoke({
            "current_month": current_summary,
            "trend": trend_summary
        })
        
        # Determine health status from analysis
        analysis_lower = analysis.lower()
        if 'strong' in analysis_lower:
            health_status = "Strong"
        elif 'weak' in analysis_lower:
            health_status = "Weak"
        else:
            health_status = "Moderate"
        
        # Determine trend
        if 'growing' in analysis_lower or 'growth' in analysis_lower:
            trend = "Growing"
        elif 'declining' in analysis_lower or 'decline' in analysis_lower:
            trend = "Declining"
        else:
            trend = "Stable"
        
        return {
            "health_status": health_status,
            "trend": trend,
            "analysis": analysis
        }

    def analyze_sales_diagnostics(self, current_month: dict, trend_data: list) -> dict:
        """Generate diagnostic and prescriptive CEO insights for sales metrics."""
        from llm.prompts import sales_diagnostic_prompt
        
        # Calculate MoM changes
        if len(trend_data) >= 2:
            last_month = trend_data[1]
            revenue_change = ((current_month['revenue'] - last_month['revenue']) / last_month['revenue'] * 100) if last_month['revenue'] > 0 else 0
            volume_change = ((current_month['qty'] - last_month['qty']) / last_month['qty'] * 100) if last_month['qty'] > 0 else 0
            order_change = ((current_month['order_count'] - last_month['order_count']) / last_month['order_count'] * 100) if last_month['order_count'] > 0 else 0
        else:
            revenue_change = volume_change = order_change = 0
        
        # Format trend summary (last 3 months)
        trend_summary = "Last 3 months: " + ", ".join([
            f"{row['month']}: ৳{row['revenue']/1000000:.0f}M"
            for row in trend_data[:3]
        ])
        
        # Generate insights
        chain = sales_diagnostic_prompt | self.llm | parser
        analysis = chain.invoke({
            "revenue": f"{current_month['revenue']/1000000:.0f}",
            "volume": f"{current_month['qty']:.0f}",
            "order_count": current_month['order_count'],
            "revenue_change": f"{revenue_change:+.1f}",
            "volume_change": f"{volume_change:+.1f}",
            "order_change": f"{order_change:+.1f}",
            "trend_summary": trend_summary
        })
        
        return {"analysis": analysis}


    def analyze_b2b_b2c_mix(self, b2b_data: dict, b2c_data: dict) -> dict:
        """Generate AI insights for B2B vs B2C sales mix."""
        from llm.prompts import b2b_b2c_mix_prompt
        
        # Format data
        b2b_summary = f"{b2b_data['percentage']:.1f}% (৳{b2b_data['revenue']/1000000000:.2f}B, {b2b_data['qty']:.0f} MT)"
        b2c_summary = f"{b2c_data['percentage']:.1f}% (৳{b2c_data['revenue']/1000000:.0f}M, {b2c_data['qty']:.0f} MT)"
        
        # Generate insights
        chain = b2b_b2c_mix_prompt | self.llm | parser
        analysis = chain.invoke({
            "b2b_data": b2b_summary,
            "b2c_data": b2c_summary
        })
        
        # Determine channel balance
        b2b_pct = b2b_data['percentage']
        if b2b_pct > 85:
            balance = "B2B-Heavy"
        elif b2b_pct < 40:
            balance = "B2C-Heavy"
        else:
            balance = "Balanced"
        
        return {
            "channel_balance": balance,
            "analysis": analysis
        }

    def analyze_credit_ratio_ceo(self, credit_data: dict, cash_data: dict, both_data: dict, channel_data: list) -> dict:
        """Generate CEO-focused AI insights for credit sales ratio."""
        
        credit_pct = credit_data.get('percentage', 0)
        cash_pct = cash_data.get('percentage', 0)
        both_pct = both_data.get('percentage', 0)
        
        total_revenue = credit_data.get('revenue', 0) + cash_data.get('revenue', 0) + both_data.get('revenue', 0)
        
        # Find top credit channel
        top_channel = "N/A"
        channel_credit_pct = 0
        if channel_data and len(channel_data) > 0:
            top_channel = channel_data[0]['channel_name']
            channel_credit_pct = channel_data[0]['percentage_within_type']
            
        prompt = f"""You are a Strategic Financial Advisor to the CEO. Provide a COMPREHENSIVE deep-dive analysis of the Credit vs Cash Sales Split.

Data Context:
- Total Revenue: {total_revenue/1000000:.2f} Million
- Credit Sales: {credit_pct:.1f}%
- Cash Sales: {cash_pct:.1f}%
- Split/Mixed Payment: {both_pct:.1f}%
- Top Credit Channel: {top_channel} ({channel_credit_pct:.1f}% credit reliance)

Produce a detailed financial strategy report (300-400 words) covering:

1. **Cash Flow & Risk Diagnosis**
   - Analyze the liquidity impact of the current {credit_pct:.1f}% credit ratio.
   - Is the business over-leveraged on credit sales? Diagnose the risk to working capital.
   - Compare Cash vs Credit performance drivers.

2. **Channel Performance Deep Dive**
   - Evaluate the credit dependency of key channels (e.g. {top_channel}).
   - Is credit being used as a sales crutch or a strategic growth tool?

3. **Strategic Receivables Directive**
   - Provide concrete actions for the CFO and Sales Director.
   - Example targets for credit collection or cash discount policies.

**Style Guidelines:**
- Tone: Financial, executive, and risk-aware.
- Format: Use structured Markdown with sub-bullets. Bold key financial metrics.
- Focus: Cash cycle optimization and risk mitigation."""

        result = self._invoke_json(prompt)
        
        # Fallback balance calculation still needed for UI badges if used elsewhere, 
        # but here we focus on the text analysis.
        balance = "Balanced"
        if credit_pct > 75: balance = "High Risk"
        elif cash_pct > 75: balance = "Liquidity Secure"

        return {
            "channel_balance": balance,
            "analysis": result.get("analysis", result)
        }

    def analyze_forecast_ceo(self, total_forecast: list, top_items: list, top_territories: list) -> dict:
        """Generate CEO-focused AI insights for sales forecast."""
        
        # Prepare summaries
        total_summary = "\n".join([f"{x['month']}: {x['qty']:.1f} MT" for x in total_forecast[:6]]) if total_forecast else "No data"
        item_summary = "\n".join([f"{x['name']}: {x['qty']:.1f} MT" for x in top_items[:5]]) if top_items else "No data"
        territory_summary = "\n".join([f"{x['name']}: {x['qty']:.1f} MT" for x in top_territories[:5]]) if top_territories else "No data"
        
        prompt = f"""You are a Strategic AI Advisor to the CEO. Provide a COMPREHENSIVE deep-dive analysis of the Sales Forecast.

Data Context:
Global Forecast Trend (Next 6 Months):
{total_summary}

Top Product Forecast:
{item_summary}

Top Territory Forecast:
{territory_summary}

Produce a highly PRECISE strategic outlook report for the CEO.

CONSTRAINT: Focus on strategic implications and directional trends. Avoid extensive lists of numbers, but cite critical KPIs (e.g. "20% drop") if they drive the strategy.

1. **Growth Trajectory Assessment**
   - Precisely define the trend (e.g. "Stable with upward bias" or "Sharp contraction").
   - Assess confident in meeting targets based on the trajectory.
   - Example: "The forecast indicates a robust recovery trajectory..."

2. **Portfolio & Market Dynamics**
   - Identify the specific products/territories driving the trend.
   - Highlight structural risks (e.g. over-dependence on a single top territory).
   - Use terms like "dominant share", "lagging", "accelerating".

3. **Strategic Forward Guidance**
   - Issue precise directives for Supply Chain (e.g. "Build inventory for [Product]") and Sales.
   - Focus on *actions* to capitalize on the trend or mitigate the decline.

**Style Guidelines:**
- Tone: Executive, concise, and ultra-precise. No fluff.
- Format: Use structured Markdown with sub-bullets.
- STRICT RULE: Use numbers sparingly to support key points. Focus on qualitative descriptors (Significant, Moderate, Critical)."""

        analysis = self._invoke_json(prompt)
        
        # Determine trend direction programmatically
        trend = "Stable"
        if len(total_forecast) >= 2:
            start_qty = total_forecast[0]['qty']
            end_qty = total_forecast[-1]['qty']
            if end_qty > start_qty * 1.05:
                trend = "Rising"
            elif end_qty < start_qty * 0.95:
                trend = "Declining"
            
        return {
            "trend": trend,
            "analysis": analysis.get("analysis", analysis)
        }

    
    
    def analyze_channel_credit_ratio(self, channels_list: list) -> dict:
        """Generate AI insights for credit sales ratio by channel."""
        if not channels_list:
            return {
                "summary": "No channel data available for analysis.",
                "recommendations": []
            }
        
        # Build channel summary
        channel_summaries = []
        for channel in channels_list:
            channel_summaries.append(
                f"{channel['channel_name']}: {channel['credit']['percentage']:.1f}% credit, "
                f"৳{channel['total_revenue']/1000000000:.2f}B total"
            )
        
        # Simple rule-based insights
        highest_credit_channel = max(channels_list, key=lambda x: x['credit']['percentage'])
        lowest_credit_channel = min(channels_list, key=lambda x: x['credit']['percentage'])
        
        analysis = f"Channel analysis shows {highest_credit_channel['channel_name']} has the highest credit exposure at {highest_credit_channel['credit']['percentage']:.1f}%, while {lowest_credit_channel['channel_name']} has {lowest_credit_channel['credit']['percentage']:.1f}% credit sales. "
        
        # Add recommendations based on patterns
        recommendations = []
        for channel in channels_list:
            if channel['credit']['percentage'] > 95:
                recommendations.append(f"Consider tightening credit terms for {channel['channel_name']} to improve cash flow")
            elif channel['credit']['percentage'] < 30:
                recommendations.append(f"{channel['channel_name']} shows strong cash sales - maintain current strategy")
        
        return {
            "summary": analysis,
            "recommendations": recommendations,
            "channels": channel_summaries
        }

    def analyze_concentration_risk(self, top10_pct: float, top1_data: dict) -> dict:
        """Generate AI insights for customer concentration risk."""
        from llm.prompts import concentration_risk_prompt
        
        others_pct = 100.0 - top10_pct
        
        # Generate insights
        chain = concentration_risk_prompt | self.llm | parser
        analysis = chain.invoke({
            "top10_pct": f"{top10_pct:.2f}",
            "others_pct": f"{others_pct:.2f}",
            "top1_name": top1_data['name'],
            "top1_pct": f"{top1_data['pct']:.2f}"
        })
        
        # Determine risk level for the UI badge (redundant with LLM but good for structured response if needed, 
        # though we rely on LLM for the text)
        if top10_pct > 50:
            risk_level = "High"
        elif top10_pct > 30:
            risk_level = "Moderate"
        else:
            risk_level = "Low"
            
        return {
            "risk_level": risk_level,
            "analysis": analysis
        }

    def analyze_sales_growth(self, current_data: dict, prev_data: dict, trend_data: list) -> dict:
        """Generate AI insights for sales growth momentum."""
        from llm.prompts import sales_growth_prompt
        
        # Calculate MoM
        if prev_data['revenue'] > 0:
            mom_growth = ((current_data['revenue'] - prev_data['revenue']) / prev_data['revenue']) * 100
        else:
            mom_growth = 0
            
        # Describe trend briefly
        trend_desc = "Variable"
        if len(trend_data) >= 3:
            # Simple check of last 3 months
            last_3 = [x['revenue'] for x in trend_data[:3]] # trend_data is typically descending by date
            if last_3[0] > last_3[1] > last_3[2]:
                trend_desc = "Consistently Rising"
            elif last_3[0] < last_3[1] < last_3[2]:
                trend_desc = "Consistently Falling"
        
        # Generate insights
        chain = sales_growth_prompt | self.llm | parser
        analysis = chain.invoke({
            "current_month": current_data['month'],
            "current_revenue": f"{current_data['revenue']/1000000:.0f}",
            "prev_month": prev_data['month'],
            "prev_revenue": f"{prev_data['revenue']/1000000:.0f}",
            "mom_growth": f"{mom_growth:.1f}",
            "trend_desc": trend_desc
        })
        
        return {
            "mom_growth": mom_growth,
            "trend_desc": trend_desc,
            "analysis": analysis
        }



    def analyze_regional_performance(self, top_regions: list, bottom_regions: list, total_volume: float) -> dict:
        """Generate CEO strategic brief for regional sales."""
        from llm.prompts import regional_strategy_prompt
        
        if not top_regions or not bottom_regions:
             return {"analysis": "Insufficient data for strategic analysis."}

        # metrics for top performer
        top = top_regions[0]
        top_qty = top['quantity']
        
        # metrics for bottom performer
        low = bottom_regions[0] 
        low_qty = low['quantity']
        
        # Top Dominance
        top_share = (top_qty / total_volume * 100) if total_volume > 0 else 0
        
        # Gap
        gap_efficiency = top_qty / low_qty if low_qty > 0 else 1.0

        # Generate insights
        chain = regional_strategy_prompt | self.llm | parser
        analysis = chain.invoke({
            "top_region": top['name'],
            "top_qty": f"{top_qty:.1f}",
            "top_share": f"{top_share:.1f}",
            "low_region": low['name'],
            "low_qty": f"{low_qty:.1f}",
            "gap_efficiency": f"{gap_efficiency:.1f}"
        })
        
        return {
            "analysis": analysis
        }

    def _invoke_json(self, prompt_text: str) -> dict:
        import json
        import re

        # Invoke directly to allow brace characters in prompt
        response = self.llm.invoke(prompt_text)
        
        # Handle response (it might be AIMessage or string)
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)
        
        # Extract JSON
        try:
            # Try to find JSON block
            json_match = re.search(r'\{.*\}', response_text.replace('\n', ' '), re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"analysis": response_text}
        except:
            return {"analysis": response_text}

    def analyze_area_performance(self, top_areas: list, bottom_areas: list, total_volume: float) -> dict:
        """Analyze area-level performance within regions."""
        prompt = f"""You are a Strategic AI Advisor to the CEO. Provide a COMPREHENSIVE deep-dive analysis of Area sales performance.

Data Context:
- Total Sales Volume: {total_volume:,.2f} MT
- Top Performing Areas: {json.dumps(top_areas)}
- Underperforming Areas: {json.dumps(bottom_areas)}

Produce a detailed strategic report (300-400 words) covering:

1. **Top Performance Drivers (Detailed Breakdown)**
   - Analyze *why* the top areas are winning. Is it volume concentration? Efficiency?
   - Cite specific metrics (Volume, Contribution %) to validate success.

2. **Underperformance Diagnosis (Root Cause Analysis)**
   - Don't just list low numbers. Diagnose the *problem*.
   - Compare top vs. bottom gaps. Is it a market coverage issue or execution failure?

3. **Strategic Assignments for Area Managers**
   - Provide granular, tactical instructions for specific Area Managers.
   - Example: "Manager of [Area X] must focus on [Specific Action] to recover [Metric]."

**Style Guidelines:**
- Tone: Executive but highly detailed and analytical.
- Format: Use structured Markdown with sub-bullets. Bold all key data points.
- Depth: Do not summarize. Go deep into the data implications."""
        
        return self._invoke_json(prompt)

    def analyze_territory_performance(self, top_territories: list, bottom_territories: list, total_volume: float) -> dict:
        """Generate CEO strategic brief for territory performance."""
        from llm.prompts import territory_strategy_prompt
        
        if not top_territories or not bottom_territories:
             return {"analysis": "Insufficient data for strategic analysis."}

        # metrics for top performer
        top = top_territories[0]
        top_qty = top['quantity']
        top_orders = top['orders']
        top_ticket = top_qty / top_orders if top_orders > 0 else 0
        
        # metrics for bottom performer
        low = bottom_territories[0] 
        low_qty = low['quantity']
        
        # Calculate Top 1 Dominance 
        top_share = (top_qty / total_volume * 100) if total_volume > 0 else 0
        
        # EFFICIENCY GAP: Compare Avg Ticket of Top 3 vs Bottom 3
        top_3_qty = sum(t['quantity'] for t in top_territories[:3])
        top_3_orders = sum(t['orders'] for t in top_territories[:3])
        top_avg_ticket = top_3_qty / top_3_orders if top_3_orders > 0 else 0
        
        bot_3_qty = sum(t['quantity'] for t in bottom_territories[:3])
        bot_3_orders = sum(t['orders'] for t in bottom_territories[:3])
        bot_avg_ticket = bot_3_qty / bot_3_orders if bot_3_orders > 0 else 0
        
        ticket_gap = top_avg_ticket / bot_avg_ticket if bot_avg_ticket > 0 else 1.0

        # Generate insights
        chain = territory_strategy_prompt | self.llm | parser
        analysis = chain.invoke({
            "top_territory": top['name'],
            "top_qty": f"{top_qty:.1f}",
            "top_orders": top_orders,
            "top_ticket": f"{top_ticket:.2f}",
            "top_share": f"{top_share:.1f}",
            "ticket_gap": f"{ticket_gap:.1f}",
            "low_territory": low['name'],
            "low_qty": f"{low_qty:.1f}"
        })
        
        return {
            "analysis": analysis
        }


    def analyze_forecast(self, total_forecast: list, top_items: list, top_territories: list) -> dict:
        """Generate AI insights for sales forecast."""
        from llm.prompts import forecast_prompt
        
        # Prepare summaries (Handle cases where lists might be empty)
        total_summary = "\n".join([f"{x['month']}: {x['qty']:.1f} MT" for x in total_forecast[:6]]) if total_forecast else "No data"
        item_summary = "\n".join([f"{x['name']}: {x['qty']:.1f} MT" for x in top_items[:5]]) if top_items else "No data"
        territory_summary = "\n".join([f"{x['name']}: {x['qty']:.1f} MT" for x in top_territories[:5]]) if top_territories else "No data"
        
        # Generate analysis
        chain = forecast_prompt | self.llm | parser
        analysis = chain.invoke({
            "total_forecast": total_summary,
            "item_forecast": item_summary,
            "territory_forecast": territory_summary
        })
        
        # Determine trend direction
        trend = "Stable"
        if len(total_forecast) >= 2:
            start_qty = total_forecast[0]['qty']
            end_qty = total_forecast[-1]['qty']
            if end_qty > start_qty * 1.05:
                trend = "Rising"
            elif end_qty < start_qty * 0.95:
                trend = "Declining"
            
        return {
            "trend": trend,
            "analysis": analysis
        }
    
