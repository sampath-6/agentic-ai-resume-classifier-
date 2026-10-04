from app.config import settings


def get_llm():
    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        # temperature 0 keeps structured extraction and the guardrail judge repeatable
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )

    from langchain_anthropic import ChatAnthropic

    # temperature is intentionally omitted: newer Claude models (e.g. claude-sonnet-5)
    # reject the `temperature` parameter as deprecated.
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
    )
