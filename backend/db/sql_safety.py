import re
from typing import List

FORBIDDEN_SQL = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b", r"\bALTER\b",
    r"\bTRUNCATE\b", r"\bCREATE\b", r"\bGRANT\b", r"\bREVOKE\b",
]

BLOCKED_SCHEMAS = [
    "pg_catalog",
    "information_schema",
]

def extract_sql(text_out: str) -> str:
    if not text_out:
        return ""
    m = re.search(r"```sql\s*(.*?)```", text_out, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    if "SQLQuery:" in text_out:
        return text_out.split("SQLQuery:", 1)[1].strip()
    return text_out.strip().strip("`").strip()

def is_select_only(sql: str) -> bool:
    s = (sql or "").strip()
    if not s.lower().startswith("select"):
        return False
    for pat in FORBIDDEN_SQL:
        if re.search(pat, s, flags=re.IGNORECASE):
            return False
    # prevent multi-statement
    if ";" in s.rstrip().rstrip(";"):
        return False
    return True

def ensure_limit(sql: str, default_limit: int) -> str:
   
    # Check if query uses aggregates (no need for LIMIT - they return 1 row)
    if re.search(r'\b(SUM|COUNT|AVG|MIN|MAX)\s*\(', sql, flags=re.IGNORECASE):
        # Aggregate query - don't add LIMIT, just return as-is
        return sql
    
    # Check if LIMIT already exists
    limit_match = re.search(r'\bLIMIT\s+(\d+)\b', sql, flags=re.IGNORECASE)
    
    if limit_match:
        existing_limit = int(limit_match.group(1))
        # Use the minimum for safety - don't allow LLM to request more than default
        final_limit = min(existing_limit, default_limit)
        # Replace the existing LIMIT with the final limit
        return re.sub(r'\bLIMIT\s+\d+\b', f'LIMIT {final_limit}', sql, flags=re.IGNORECASE)
    else:
        # No LIMIT exists, add the default
        # Remove trailing semicolon if present to avoid syntax error (LIMIT must be before ;)
        cleaned_sql = sql.strip().rstrip(';')
        return cleaned_sql + f"\nLIMIT {default_limit}"

def enforce_allowlist(sql: str, allowed_tables: List[str]) -> None:
    s = sql.lower()
    if any(schema in s for schema in BLOCKED_SCHEMAS):
        raise ValueError("Query references blocked schemas.")
    if allowed_tables:
        if not any(t.lower() in s for t in allowed_tables):
            raise ValueError(f"Query must reference allowed tables only: {allowed_tables}")
