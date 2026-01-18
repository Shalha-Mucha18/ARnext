from functools import lru_cache
from llm.client import get_llm
from llm.chain import SalesGPTCore
from memory.store import SessionStore

@lru_cache
def get_core() -> SalesGPTCore:
    llm = get_llm()
    return SalesGPTCore(llm)

@lru_cache
def get_store() -> SessionStore:
    return SessionStore()
