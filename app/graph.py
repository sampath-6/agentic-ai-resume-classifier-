from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.analyzer import analyzer_agent
from app.agents.classifier import classifier_agent
from app.agents.indexer import indexer_agent
from app.agents.ingestion import ingestion_agent
from app.agents.query_guardrail import query_guardrail_agent
from app.agents.rename import rename_agent
from app.agents.retrieval import retrieval_agent
from app.agents.synthesizer import synthesizer_agent
from app.config import settings
from app.state import GraphState

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def supervisor(state: GraphState) -> dict:
    return {}


def scan_folder(state: GraphState) -> dict:
    inbox = Path(settings.inbox_dir)
    files = sorted(
        str(p) for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in _ALLOWED_EXTENSIONS
    )
    return {"file_paths": files}


def route_intent(state: GraphState) -> str:
    return "ingest" if state.get("intent") == "upload" else "query"


def route_has_work(state: GraphState) -> str:
    return "has_files" if state.get("file_paths") else "empty"


def route_by_size(state: GraphState) -> str:
    return "over_2mb" if state.get("oversized") else "under_2mb"


def route_after_ingestion(state: GraphState) -> str:
    result = state.get("last_ingestion_result")
    if result == "retry":
        return "retry"
    if result == "success":
        return "continue"
    return "retries_exhausted"


def route_after_guardrail(state: GraphState) -> str:
    return "reject" if state.get("guardrail_blocked") else "pass"


def route_after_retrieval(state: GraphState) -> str:
    got_nothing = not state.get("retrieved")
    under_broaden_cap = state.get("broaden_attempts", 0) < settings.max_broaden_attempts
    return "broaden" if got_nothing and under_broaden_cap else "synthesize"


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("supervisor", supervisor)
    graph.add_node("scan_folder", scan_folder)
    graph.add_node("analyzer_agent", analyzer_agent)
    graph.add_node("ingestion_agent", ingestion_agent)
    graph.add_node("classifier_agent", classifier_agent)
    graph.add_node("rename_agent", rename_agent)
    graph.add_node("indexer_agent", indexer_agent)
    graph.add_node("query_guardrail_agent", query_guardrail_agent)
    graph.add_node("retrieval_agent", retrieval_agent)
    graph.add_node("synthesizer_agent", synthesizer_agent)

    graph.set_entry_point("supervisor")

    # --- routing: supervisor decides which branch handles this request ---
    graph.add_conditional_edges(
        "supervisor",
        route_intent,
        {"ingest": "scan_folder", "query": "query_guardrail_agent"},
    )

    # --- loop: folder-drain. Re-scans the inbox after every file so files ---
    # --- dropped in mid-run get picked up too, not just the starting batch ---
    graph.add_conditional_edges(
        "scan_folder",
        route_has_work,
        {"has_files": "analyzer_agent", "empty": END},
    )

    graph.add_conditional_edges(
        "analyzer_agent",
        route_by_size,
        {"over_2mb": "scan_folder", "under_2mb": "ingestion_agent"},
    )

    # --- loop: retry parsing (with a fallback backend) up to max_parse_retries ---
    graph.add_conditional_edges(
        "ingestion_agent",
        route_after_ingestion,
        {
            "retry": "ingestion_agent",
            "continue": "classifier_agent",
            "retries_exhausted": "scan_folder",
        },
    )

    graph.add_edge("classifier_agent", "rename_agent")
    graph.add_edge("rename_agent", "indexer_agent")
    graph.add_edge("indexer_agent", "scan_folder")

    # --- query branch: deterministic keyword screen, LLM judge only on a hit ---
    graph.add_conditional_edges(
        "query_guardrail_agent",
        route_after_guardrail,
        {"pass": "retrieval_agent", "reject": END},
    )

    # --- loop: broaden the search (drop metadata filter) if nothing came back ---
    graph.add_conditional_edges(
        "retrieval_agent",
        route_after_retrieval,
        {"broaden": "retrieval_agent", "synthesize": "synthesizer_agent"},
    )

    graph.add_edge("synthesizer_agent", END)

    return graph.compile(checkpointer=MemorySaver())


resume_graph = build_graph()
