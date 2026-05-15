from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from server.core.config import get_settings

logger = logging.getLogger(__name__)


def get_chat_model() -> BaseChatModel:
    s = get_settings()
    return ChatOpenAI(
        api_key=s.openai_api_key or "sk-mock",
        base_url=s.openai_base_url,
        model=s.openai_model,
        temperature=0.2,
        timeout=s.llm_timeout_seconds,
        max_retries=s.llm_max_retries,
    )
