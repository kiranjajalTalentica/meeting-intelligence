"""
LangGraph Workflow Assembly.

This module builds the processing graph.

Two layouts are supported:

1. PARALLEL (default False): fan-out after topic detection so all
   extractors run concurrently. Fastest, but fires 5 LLM calls at once —
   this can trip strict rate limits (e.g. Gemini free tier = 5 req/min).

2. SEQUENTIAL (default True): nodes run one after another. Slower, but
   only one LLM call is in flight at a time, which respects tight quotas.

The conceptual pipeline is the same either way:
START → topics → summary → decisions → actions → open questions → END
"""

from langgraph.graph import StateGraph, START, END

from app.graph.state import MeetingState
from app.graph.nodes import (
    detect_topics,
    generate_summary,
    extract_decisions,
    extract_action_items,
    extract_open_questions,
)


def build_workflow(parallel: bool = False):
    """
    Construct and compile the Meeting Intelligence graph.

    Args:
        parallel: If True, extractors fan out and run concurrently.
                  If False (default), they run sequentially — safer for
                  rate-limited providers like the Gemini free tier.

    Returns a compiled LangGraph workflow.
    """
    graph = StateGraph(MeetingState)

    # Register all nodes
    graph.add_node("detect_topics", detect_topics)
    graph.add_node("generate_summary", generate_summary)
    graph.add_node("extract_decisions", extract_decisions)
    graph.add_node("extract_action_items", extract_action_items)
    graph.add_node("extract_open_questions", extract_open_questions)

    graph.add_edge(START, "detect_topics")

    if parallel:
        # Fan-out: all extractors run at once after topic detection
        graph.add_edge("detect_topics", "generate_summary")
        graph.add_edge("detect_topics", "extract_decisions")
        graph.add_edge("detect_topics", "extract_action_items")
        graph.add_edge("detect_topics", "extract_open_questions")
        # Fan-in: converge to END
        graph.add_edge("generate_summary", END)
        graph.add_edge("extract_decisions", END)
        graph.add_edge("extract_action_items", END)
        graph.add_edge("extract_open_questions", END)
    else:
        # Sequential chain: one LLM call in flight at a time
        graph.add_edge("detect_topics", "generate_summary")
        graph.add_edge("generate_summary", "extract_decisions")
        graph.add_edge("extract_decisions", "extract_action_items")
        graph.add_edge("extract_action_items", "extract_open_questions")
        graph.add_edge("extract_open_questions", END)

    return graph.compile()
