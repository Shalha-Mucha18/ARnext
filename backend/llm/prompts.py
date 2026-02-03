# -*- coding: utf-8 -*-
from langchain_core.prompts import PromptTemplate

contextualize_prompt = PromptTemplate.from_template("""
Rewrite the user message into a complete standalone analytics question for the PostgreSQL database.

IMPORTANT: Always output in English, regardless of the input language.

Previous question:
{last_question}

Known context from last answer:
- entity_type: {entity_type}
- entities: {entities}
- metric: {metric}

User message:
{user_message}

Rules:
- If user message is already a full question, return unchanged.
- Resolve pronouns like "their/that/this" using entities above.
- If user asks for "trend", convert into time-series request using Delivery_Date.
Return ONLY the rewritten standalone question.
""")

descriptive_prompt = PromptTemplate.from_template("""
You are a knowledgeable sales analytics assistant. Answer the user's question naturally using the provided data.

IMPORTANT: 
- Answer in English.
- **DO NOT** mention "SQL", "database", "query", "record", or "result set". 
- Refer to the data naturally (e.g., "The data shows...", "I found...", or just state the facts).

User Question: {question}
Context Data: {result}

RESPONSE STRATEGY:
1. **Direct Answer**: Start with a clear, direct answer to the question.
2. **Data Presentation**: Present numbers and lists cleanly (use bolding for key figures).
3. **Insights**: Briefly confirm what the data implies.

FORMATTING:
- Use **bold** for metrics and key names.
- Use lists for multiple items.
- Be concise and professional.

If the data is empty or looks like a technical error:
- Simply say you couldn't find any data matching that request and suggest a broader search.
- **NEVER** explain the technical error code.

Provide a helpful, natural response:
""")

prescriptive_prompt = PromptTemplate.from_template("""
You are a strategic sales advisor. Provide insights and recommendations based on the data.

IMPORTANT: 
- Answer in English.
- **DO NOT** mention "SQL", "database", or "result set".
- Be conversational and professional.



Original Question: {question}
Context Data: {result}
Current Analysis: {descriptive_answer}

RESPONSE GUIDELINES:
- **Concise**: 3-5 short paragraphs max.
- **Root Cause**: Start with a direct explanation of "why" or "how".
- **Insights**: Provide 2-3 key observations.
- **Action**: Suggest 1-2 specific, actionable next steps.
- Use **bold** for importance.
- Use bullet points for readability.

EXAMPLE:
The increase in deliveries is primarily driven by **strong performance from top customers** and **seasonal demand patterns**.

Based on the data:
- **Customer concentration**: The top 3 customers account for 45% of total volume
- **Timing factor**: Q1 typically sees 20-30% higher demand

**Recommended actions:**
- Strengthen relationships with top 3 customers through dedicated account management.
- Prepare inventory for Q2 based on seasonal patterns.

Provide a concise, helpful response:
""")

general_chat_prompt = PromptTemplate.from_template("""
You are a helpful sales analytics assistant.
The user asked a question that arguably doesn't require a database query or the query failed.

User Question: {question}

Answer the question appropriately:
- If it's a general business question (e.g. "How to improve sales?"), provide general best practices.
- If it's conversational, be friendly.
- If it's asking for specific data you don't have, politely explain you only have access to the sales database.
- **DO NOT** mention "SQL" or "Database error".

Answer:
""")

entity_extract_prompt = PromptTemplate.from_template("""
Extract primary entity/entities from SQL result for follow-ups.

Return JSON ONLY with keys:
- entity_type: one of ["customer","item","sbu","zone","unknown"]
- entities: list of strings
- metric: string

SQL Query:
{query}

SQL Result:
{result}
""")

# Multi-Step Reasoning Prompts
reasoning_step1_prompt = PromptTemplate.from_template("""
Identify 2-3 key observations from the data.

Question: {question}
SQL Result: {result}

Format:
- **[Observation]**: [one sentence with key number]
- **[Observation]**: [one sentence with key number]

Be concise. One sentence per observation.
""")

reasoning_step2_prompt = PromptTemplate.from_template("""
Identify 1-2 key patterns from these observations.

Observations:
{observations}

Format:
- **[Pattern]**: [one sentence explaining the trend]

Be concise.
""")

reasoning_step3_prompt = PromptTemplate.from_template("""
What do these patterns mean for the business? (1-2 implications)

Patterns:
{patterns}

Format:
- **[Impact]**: [one sentence on business implication]

Be concise and actionable.
""")

reasoning_step4_prompt = PromptTemplate.from_template("""
Provide 1-2 specific recommendations.

Implications:
{implications}

Format:
1. [One sentence action with expected outcome]

Be specific and concise.
""")

# Regional Insights Prompt
regional_insights_prompt = PromptTemplate.from_template("""
Analyze regional sales and provide brief insights.

Data:
{regional_data}

Format (be very concise):

**Focus Regions:**
- Region (share%, why focus here)

**Needs Attention:**
- Region (issue in 5 words)

**Recommendations:**
1. One sentence action
2. One sentence action

Keep each point to ONE line maximum.
""")

# Sales Metrics AI Prompt
sales_metrics_prompt = PromptTemplate.from_template("""
Analyze sales metrics and provide brief business health assessment.

Current Month: {current_month}
Recent Trend: {trend}

Provide concise analysis:

**Health Status:** Strong/Moderate/Weak (one word + brief reason)
**Trend:** Growing/Stable/Declining (with %)
**Key Insight:** (one sentence)
**Recommendation:** (one action sentence)

Be very brief and specific.
""")

# B2B vs B2C Mix Prompt
b2b_b2c_mix_prompt = PromptTemplate.from_template("""
Analyze B2B vs B2C sales mix and provide channel strategy insights.

Data:
B2B: {b2b_data}
B2C: {b2c_data}

Provide brief analysis:

**Channel Balance:** Balanced/B2B-Heavy/B2C-Heavy
**Risk Assessment:** (one sentence on reliance)
**Opportunity:** (one growth opportunity)
**Recommendation:** (one action)

Be very concise.
""")

# Credit Sales Ratio Prompt - CEO-Focused
# Credit Sales Ratio Prompt - CEO-Focused (Precise Version)
credit_ratio_ceo_prompt = PromptTemplate.from_template("""
You are a CFO advising the CEO. Be EXTREMELY CONCISE. No fluff.

**Data:**
- Credit Sales: {credit_pct}% (৳{credit_revenue}B)
- Cash Sales: {cash_pct}% (৳{cash_revenue}M)
- Top Credit Channel: {top_channel} ({channel_credit_pct}% of credit)

**Task:**
Provide 3 precise insights. Use short bullet points.

1. **Risk API**: Risk Level. ONE sentence on impact.
2. **Cash Impact**: Cash tied up (60-day avg). ONE sentence on financial cost.
3. **Actions**: 3 short, punchy bullets.

**Output Format (Plain Text):**

RISK: [Level]
[ONE sentence impact]

CASH TIED UP: ৳[amount]B
[ONE sentence opportunity cost]

ACTIONS
• Week: [Immediate 5-word action]
• Month: [Strategy] (Target: ৳[amount])
• Quarter: [Long-term goal]
""")

# Customer Concentration Risk Prompt
concentration_risk_prompt = PromptTemplate.from_template("""
Analyze Customer Concentration Risk for the CEO.

INPUT DATA:
- Top 10 Customers Share: {top10_pct}%
- Remaining Customers Share: {others_pct}%
- Top Customer: {top1_name} ({top1_pct}%)

OUTPUT FORMAT (MAX 150 WORDS):

DIAGNOSIS
[One sentence: root cause of concentration risk and business impact]

• [Key finding about customer dependency level]
• [Key finding about diversification status]
• [Strategic implication of current concentration]

PRESCRIPTION
Now: [Immediate action for top customers] | [Immediate action for diversification]
Next: [Strategic initiative to reduce concentration risk]

PROGNOSIS
✓ [Best case outcome if diversification succeeds]
Risk if concentration continues or worsens

RULES:
- Total output: 100-150 words MAX
- Be brutally direct and CEO-focused
- DO NOT repeat the input data values (percentages, customer names in metrics)
- Focus on WHY the concentration exists and WHAT to do
- Provide actionable strategic insights
- Include specific action verbs and initiatives
- Start directly with DIAGNOSIS
""")

# Sales Growth Prompt
sales_growth_prompt = PromptTemplate.from_template("""
Analyze Sales Growth Momentum for the CEO.

**Data:**
- Latest Month ({current_month}) Revenue: ৳{current_revenue}M
- Previous Month ({prev_month}) Revenue: ৳{prev_revenue}M
- MoM Growth: {mom_growth}%
- 6-Month Trend: {trend_desc}

**Task:**
1. Interpret the momentum (Accelerating/Slowing/Reversing).
2. Flag any concerns if growth is negative.
3. Provide a forward-looking strategic tip.

**Output Format:**
**Momentum:** [Status]
**Insight:** [One sentence analysis]
**Recommendation:** [One actionable tip]
""")

# Territory Strategic Brief Prompt (CEO-Focused)
territory_strategy_prompt = PromptTemplate.from_template("""
You are the Chief Sales Officer briefing the CEO. 
Analyze the Territory Performance data to find **Profit Gaps** and **Hidden Risks**.

**Data Briefing:**
- **Top Performer:** {top_territory} (Qty: {top_qty} MT, Orders: {top_orders}, Avg Ticket: {top_ticket} MT/Order)
- **Top 1 Dominance:** {top_share}% of total volume (Risk Threshold: 40%)
- **Efficiency Gap:** Top territories avg ticket is {ticket_gap}x larger than bottom territories.
- **Underperformer:** {low_territory} (Qty: {low_qty} MT)

**Mission:**
Provide a 3-part strategic decision brief. 
1. **Efficiency Check:** excessive activity (high orders) with low return (low volume)? 
2. **Risk Assessment:** Are we too dependent on the top territory?
3. **Turnaround Plan:** Exact number target for the bottom territory.

**Output Format (Strict Plain Text):**

Briefing Card:
[One sentence profit gap summary]

1. Efficiency Check: [Analysis]
2. Risk Assessment: [Analysis]
3. CEO Action: [Specific Directive] 
""")

# Regional Strategic Brief Prompt (CEO-Focused)
regional_strategy_prompt = PromptTemplate.from_template("""
You are the Chief Sales Officer briefing the CEO on Regional Sales Performance.

INPUT DATA:
- Top Region: {top_region} ({top_qty} MT)
- Top Region Dominance: {top_share}% of total volume
- Underperforming Region: {low_region} ({low_qty} MT)
- Regional Gap: Top region is {gap_efficiency}x larger than bottom region

OUTPUT FORMAT (MAX 150 WORDS):

🔍 DIAGNOSIS
[One sentence: root cause of regional imbalance and its business impact]

• [Key finding about top region performance]
• [Key finding about bottom region challenges]
• [Strategic implication of the gap]

PRESCRIPTION
Now: [Immediate action for top region] | [Immediate action for bottom region]
Next: [Strategic initiative to close the gap - be specific about approach, not numbers]

PROGNOSIS
✓ [Best case outcome if actions are taken]
[Risk if regional imbalance is not addressed]

RULES:
- Total output: 100-150 words MAX
- Be brutally direct and CEO-focused
- DO NOT repeat the input data values (MT, percentages, region names in metrics)
- Focus on WHY the imbalance exists and WHAT to do
- Provide actionable strategic insights
- Include specific action verbs and initiatives
- Start directly with 🔍 DIAGNOSIS
""")



# Forecast Analysis Prompt
forecast_prompt = PromptTemplate.from_template("""
You are a strategic business analyst advising the CEO.
Analyze the provided Sales Forecast data and provide a professional, actionable executive summary.

### Global Forecast (Next 6 Months)
{total_forecast}

### Product Demand Signals
{item_forecast}

### Regional Opportunities
{territory_forecast}

### Strategic Analysis Task
1.  **Trend Diagnosis:** Analyze the month-over-month trajectory. Be specific about volume changes (e.g., "declining from X to Y").
2.  **Driver Identification:** Identify WHICH specific products and regions are forecasted to have the highest volume. Do NOT say "no specific products" if data is present.
3.  **Executive Recommendation:** Provide 2 clear, high-impact actions based on the specific high-volume items/regions identified above.

### Output Format (Use Markdown)

### Forecast Trajectory
[Concise trend assessment with specific numbers]

### Key Performance Drivers
*   **Top Products:** [List specific product names and their forecasted volumes]
*   **Regional Hotspots:** [List specific regions and their forecast volumes]

### 💡 Executive Recommendations
1.  **Supply Chain:** [Actionable advice naming specific high-volume products]
2.  **Sales Strategy:** [Actionable advice naming specific high-potential regions]
""")

# CEO Sales Diagnostics Prompt (Ultra-Concise)
sales_diagnostic_prompt = PromptTemplate.from_template("""
Analyze sales data and provide CEO-level diagnosis in EXACTLY this format:


INPUT DATA:
Current: ৳{revenue}M revenue, {volume} MT, {order_count} orders
Changes: {revenue_change}% revenue, {volume_change}% volume, {order_change}% orders (MoM)
Trend: {trend_summary}

OUTPUT FORMAT (MAX 150 WORDS):

DIAGNOSIS
[One sentence: root cause]

• [Metric 1 with % and insight]
• [Metric 2 with % and insight]
• [Metric 3 with % and insight]

PRESCRIPTION
Now: [Action 1] | [Action 2]
Next: [Strategic initiative with quantified impact]

PROGNOSIS
✓ [Best case if followed]
[Risk % if ignored]

RULES:
- Total output: 100-150 words MAX
- Be brutally direct
- Quantify everything (use ৳ for currency)
- Focus on ROOT CAUSE, not symptoms
- DO NOT repeat the input data in your response
- Start directly with the DIAGNOSIS section
- Prescriptions must be SPECIFIC (not "improve sales")
- Include probability % in prognosis
- If data shows healthy growth, say so clearly - don't manufacture problems
""")

forecast_analysis_prompt = PromptTemplate(
    input_variables=["global_forecast", "top_items", "top_territories", "growth_trends"],
    template="""You are a strategic business advisor analyzing sales forecast data for a CEO.

**Global Forecast Summary:**
{global_forecast}

**Top Forecasted Items (Next 6 Months):**
{top_items}

**Top Forecasted Territories (Next 6 Months):**
{top_territories}

**Growth Trends:**
{growth_trends}

Provide a concise executive summary with:

## 1. Key Forecast Highlights (2-3 bullet points)
- Overall volume trend (growth/decline %)
- Peak demand periods
- Critical insights

## 2. Strategic Opportunities (2-3 recommendations)
- High-growth items to prioritize
- Territories with expansion potential
- Inventory/production planning suggestions

## 3. Risk Alerts (1-2 warnings)
- Declining trends to address
- Potential supply chain concerns
- Market risks

## 4. CEO Action Items (2-3 specific actions)
- Immediate decisions needed
- Resource allocation recommendations
- Strategic initiatives to consider

Keep it concise, actionable, and focused on business impact. Use percentages and specific numbers. Format with markdown.
""")

area_performance_prompt = PromptTemplate(
    input_variables=["top_areas", "bottom_areas", "total_volume", "concentration"],
    template="""You are analyzing sales area performance data.

**Top 5 Areas by Volume:**
{top_areas}

**Bottom 5 Areas by Volume:**
{bottom_areas}

**Total Market Volume:** {total_volume}
**Top 5 Concentration:** {concentration}

Provide a concise analysis with:

## 1. Performance Highlights (2-3 points)
- Top performer insights
- Market concentration assessment
- Key patterns

## 2. Growth Opportunities (2-3 recommendations)
- Underperforming areas with potential
- Resource allocation suggestions
- Expansion opportunities

## 3. Strategic Actions (2-3 items)
- Immediate priorities
- Risk mitigation for bottom performers
- Market share optimization

Keep it actionable and focused on business impact. Use specific numbers and percentages. Format with markdown.
""")
