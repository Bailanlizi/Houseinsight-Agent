from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from server.core.config import get_settings

logger = logging.getLogger(__name__)


def get_chat_model(*, temperature: float | None = None) -> BaseChatModel:
    s = get_settings()
    return ChatOpenAI(
        api_key=s.openai_api_key or "sk-mock",
        base_url=s.openai_base_url,
        model=s.openai_model,
        temperature=0.2 if temperature is None else temperature,
        timeout=s.llm_timeout_seconds,
        max_retries=s.llm_max_retries,
    )


def get_answer_chat_model() -> BaseChatModel:
    """answer 节点专用：更低温度，减少格式漂移与 JSON 泄漏。"""
    return get_chat_model(temperature=get_settings().answer_llm_temperature)
