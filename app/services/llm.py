from langchain_anthropic import ChatAnthropic

from app.config import settings


def get_llm() -> ChatAnthropic:
    # temperature is intentionally omitted: newer Claude models (e.g. claude-sonnet-5)
    # reject the `temperature` parameter as deprecated.
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
    )
