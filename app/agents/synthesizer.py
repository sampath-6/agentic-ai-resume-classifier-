from app.config import settings
from app.services.llm import get_llm
from app.state import GraphState

_PROMPT = """A recruiter is searching resumes for: "{query}"

Here are the top matching candidates (most relevant first):
{context}

Write a concise, ranked summary of which candidates match and why. Reference candidates by name.
"""


def synthesizer_agent(state: GraphState) -> dict:
    retrieved = state.get("retrieved", [])
    if not retrieved:
        return {"answer": "No matching resumes found."}

    top = retrieved[: settings.narration_count]
    context = "\n\n".join(
        f"- {r['metadata'].get('display_name')}: skills=[{r['metadata'].get('skills')}], "
        f"seniority={r['metadata'].get('seniority')}, role={r['metadata'].get('primary_role')}"
        for r in top
    )

    llm = get_llm()
    response = llm.invoke(_PROMPT.format(query=state["query_text"], context=context))
    return {"answer": response.content}
