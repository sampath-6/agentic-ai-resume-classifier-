from typing import List

from pydantic import BaseModel, Field

from app.services.llm import get_llm
from app.state import GraphState


class ResumeClassification(BaseModel):
    first_name: str = Field(description="Candidate's first name")
    last_name: str = Field(description="Candidate's last name")
    years_experience: float = Field(description="Total years of professional experience, best estimate from the resume")
    skills: List[str] = Field(description="Normalized technical + professional skills, e.g. 'Python', 'AWS', 'Stakeholder management'")
    seniority: str = Field(description="One of: junior, mid, senior, lead, unknown")
    primary_role: str = Field(description="Best single job title summarizing this candidate, e.g. 'Backend Engineer'")
    summary: str = Field(description="2-3 sentence summary of the candidate's background")


_PROMPT = """You are an expert technical recruiter. Read the resume text below and extract structured \
information about the candidate. Be concise and only include skills actually evidenced in the text.

Resume:
---
{text}
---
"""


def classifier_agent(state: GraphState) -> dict:
    record = state["current_record"]
    llm = get_llm().with_structured_output(ResumeClassification)
    result: ResumeClassification = llm.invoke(_PROMPT.format(text=record["text"][:8000]))

    classified_rec = {
        "resume_id": record["resume_id"],
        "file_path": record["file_path"],
        "skills": result.skills,
        "seniority": result.seniority,
        "primary_role": result.primary_role,
        "summary": result.summary,
        "first_name": result.first_name,
        "last_name": result.last_name,
        "years_experience": result.years_experience,
    }

    return {"classified": [classified_rec], "current_classified": classified_rec}
