"""LangGraph graph assembly and routing definitions."""

from __future__ import annotations

from functools import lru_cache
import logging

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
	AgentState,
	analyze_query_node,
	generate_answer_node,
	grade_documents_node,
	retrieve_documents_node,
)


logger = logging.getLogger(__name__)


def _route_after_grade(state: AgentState) -> str:
	"""Route either to retry retrieval or to answer generation."""
	if state.get("should_retry", False):
		logger.info("graph routing | from=grade_documents to=retrieve_documents")
		return "retry_retrieve"
	logger.info("graph routing | from=grade_documents to=generate_answer")
	return "generate"


def build_agent_graph():
	"""Create and compile the LangGraph workflow for legal QA."""
	workflow = StateGraph(AgentState)

	workflow.add_node("analyze_query", analyze_query_node)
	workflow.add_node("retrieve_documents", retrieve_documents_node)
	workflow.add_node("grade_documents", grade_documents_node)
	workflow.add_node("generate_answer", generate_answer_node)

	workflow.add_edge(START, "analyze_query")
	workflow.add_edge("analyze_query", "retrieve_documents")
	workflow.add_edge("retrieve_documents", "grade_documents")
	workflow.add_conditional_edges(
		"grade_documents",
		_route_after_grade,
		{
			"retry_retrieve": "retrieve_documents",
			"generate": "generate_answer",
		},
	)
	workflow.add_edge("generate_answer", END)

	return workflow.compile()


@lru_cache(maxsize=1)
def get_agent_graph():
	"""Return cached compiled graph instance for application usage."""
	return build_agent_graph()
