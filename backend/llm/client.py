from langchain_groq import ChatGroq
from core.config import settings

def get_llm() -> ChatGroq:
    print(f"[DEBUG] Initializing ChatGroq with model: {settings.GROQ_MODEL}")
    return ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        api_key=settings.GROQ_API_KEY,
    )
