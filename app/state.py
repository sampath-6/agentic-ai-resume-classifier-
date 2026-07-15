from operator import add
from typing import Annotated, List, Literal, Optional, TypedDict


class ResumeRecord(TypedDict):
    resume_id: str
    file_path: str
    text: str


class ClassifiedRecord(TypedDict):
    resume_id: str
    file_path: str
    skills: List[str]
    seniority: str
    primary_role: str
    summary: str
    first_name: str
    last_name: str
    years_experience: float


class RetrievedChunk(TypedDict):
    text: str
    metadata: dict
    distance: float


class GraphState(TypedDict, total=False):
    intent: Literal["upload", "query"]

    # folder-drain loop
    file_paths: List[str]
    current_file: Optional[str]
    oversized: bool
    rejected_files: Annotated[List[str], add]

    # ingestion / classification branch (current_* fields hold this iteration's
    # working record; the Annotated fields accumulate a full-run audit trail)
    current_record: Optional[ResumeRecord]
    current_classified: Optional[ClassifiedRecord]
    current_stored_path: Optional[str]
    current_display_name: Optional[str]
    last_ingestion_result: Literal["success", "retry", "exhausted"]
    raw_texts: Annotated[List[ResumeRecord], add]
    parse_failures: Annotated[List[str], add]
    parse_retries: int
    classified: Annotated[List[ClassifiedRecord], add]
    indexed: Annotated[List[str], add]

    # query guardrail branch
    query_text: str
    guardrail_blocked: bool
    guardrail_reason: str

    # retrieval branch
    where_filter: Optional[dict]
    retrieved: List[RetrievedChunk]
    broaden_attempts: int
    answer: str
