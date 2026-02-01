import re
import time
import json
import uuid
from typing import Optional, Any
from app.schemas.chat import ChatResponse, SessionState
from app.utils.cache import redis_client
from starlette.concurrency import run_in_threadpool
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, core_engine: Any):
        self.core = core_engine

    async def process_message(self, message: str, session_id: Optional[str], debug: bool = False) -> ChatResponse:
        t0 = time.time()
        
        # Ensure session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            
        # Get State
        state = await self._get_state(session_id)
        
        # 1. Conversational Check
        if self._is_conversational(message):
            answer = self._get_conversational_response(message)
            return ChatResponse(
                session_id=session_id,
                mode="conversational",
                answer=answer,
                meta={"latency_ms": int((time.time()-t0)*1000)}
            )

        # 2. Elaboration Check
        if self._is_elaboration_request(message) and state.last_descriptive:
            try:
                # Core.elaborate might be sync
                answer = await run_in_threadpool(
                    self.core.elaborate,
                    last_question=state.last_question or "",
                    last_answer=state.last_descriptive,
                    last_result=state.last_result or "",
                    user_request=message
                )
                return ChatResponse(
                    session_id=session_id,
                    mode="elaboration",
                    answer=answer,
                    used_question=state.last_question,
                    meta={"latency_ms": int((time.time()-t0)*1000)}
                )
            except Exception as e:
                logger.error(f"Elaboration failed: {e}")
                # Fallback to general processing if elaboration fails
                pass

        # 3. Core Processing
        question = message     
        try:
            # Run SQL Query
            out = await run_in_threadpool(self.core.run_sql_from_question, question)
            
            # Descriptive Answer
            desc = await run_in_threadpool(self.core.descriptive, out)
            
            # Analytical reasoning
            if re.search(r'\b(why|how|explain|cause)\b', message.lower()):
                 desc = await run_in_threadpool(
                     self.core.analyze_with_reasoning,
                     question=out["question"],
                     result=out["result"],
                     descriptive_answer=desc
                 )

            # Update State
            ent = await run_in_threadpool(self.core.extract_entities, out["query"], out["result"])
            
            new_state = SessionState(
                last_question=out["question"],
                last_sql=out["query"],
                last_result=str(out["result"]), # Ensure string
                last_descriptive=desc,
                entity_type=ent.get("entity_type", "unknown"),
                entities=ent.get("entities", []) or [],
                metric=ent.get("metric", "unknown")
            )
            await self._save_state(session_id, new_state)
            
            return ChatResponse(
                session_id=session_id,
                mode="descriptive",
                answer=desc,
                used_question=out["question"],
                sql=out["query"] if debug else None,
                meta={
                    "latency_ms": int((time.time()-t0)*1000),
                    "entity_type": new_state.entity_type,
                    "entities": new_state.entities[:3],
                    "metric": new_state.metric
                }
            )

        except Exception as e:
            # Fallback to General Conversation Check via AI
            try:
                gen_answer = await run_in_threadpool(self.core.general_response, message)
                return ChatResponse(
                    session_id=session_id,
                    mode="general",
                    answer=gen_answer,
                    meta={"latency_ms": int((time.time()-t0)*1000)}
                )
            except Exception:
                raise e

    # --- Helpers (Regex Logic from Legacy) ---
    def _is_conversational(self, message: str) -> bool:
        msg = message.strip().lower()
        if re.match(r'^(hi|hello|hey|good morning|greetings)[\s!.]*$', msg): return True
        if re.match(r'^(thanks|thank you|ok|great|cool)[\s!.]*$', msg): return True
        if any(p in msg for p in ['who are you', 'help me']): return True
        return False

    def _get_conversational_response(self, message: str) -> str:
        msg = message.strip().lower()
        if re.match(r'^(hi|hello|hey)', msg):
            return "Hello! I'm your sales analytics assistant. How can I help you today?"
        if 'thank' in msg: return "You're welcome!"
        if 'who are you' in msg: return "I'm an AI assistant for your sales data."
        return "I'm here to help with your analytics."

    def _is_elaboration_request(self, message: str) -> bool:
        msg = message.strip().lower()
        patterns = [
            r'^(explain|tell me)\s+(more|detail)',
            r'^elaborate',
            r'^why is that',
            r'^more\?'
        ]
        return any(re.search(p, msg) for p in patterns)

    # --- Redis State Management ---
    async def _get_state(self, session_id: str) -> SessionState:
        try:
            raw = await redis_client.get(f"chat:session:{session_id}")
            if raw:
                return SessionState.model_validate_json(raw)
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
        return SessionState()

    async def _save_state(self, session_id: str, state: SessionState):
        try:
            await redis_client.setex(
                f"chat:session:{session_id}",
                3600, # 1 hour TTL
                state.model_dump_json()
            )
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
