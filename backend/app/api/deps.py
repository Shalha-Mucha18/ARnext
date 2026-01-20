"""
Common dependencies for API endpoints.
"""
from typing import Generator
from llm.chain import SalesGPTCore
from llm.client import get_llm
from memory.store import SessionStore

# Singleton instances
_core_instance = None
_store_instance = None


def get_core() -> SalesGPTCore:
    """
    Get or create SalesGPTCore instance.
    
    Returns:
        SalesGPTCore instance
    """
    global _core_instance
    if _core_instance is None:
        llm = get_llm()
        _core_instance = SalesGPTCore(llm)
    return _core_instance


def get_store() -> SessionStore:
    """
    Get or create SessionStore instance.
    
    Returns:
        SessionStore instance
    """
    global _store_instance
    if _store_instance is None:
        _store_instance = SessionStore()
    return _store_instance
