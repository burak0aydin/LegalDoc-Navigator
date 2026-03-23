"""LangGraph node implementations for legal analysis flow."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from services.retrieval import RetrievalService


logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
	"""State object shared across LangGraph nodes."""

	query: str
	normalized_query: str
	query_intent: str
	retrieval_top_k: int
	rerank_top_n: int
	attempts: int
	max_attempts: int
	retrieval_results: list[dict[str, Any]]
	relevant_results: list[dict[str, Any]]
	should_retry: bool
	answer_markdown: str
	errors: list[str]


class AgentNodeError(Exception):
	"""Raised for agent node processing errors."""


def _normalize_query(query: str) -> str:
	return re.sub(r"\s+", " ", query).strip()


def _get_state_int(state: AgentState, key: str, default: int) -> int:
	value = state.get(key, default)
	try:
		return int(value)
	except Exception:  # noqa: BLE001
		return default


def _build_local_llm() -> ChatOpenAI:
	"""Create LM Studio-backed ChatOpenAI client."""
	return ChatOpenAI(
		base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
		api_key=os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
		model=os.getenv("LMSTUDIO_MODEL", "gemma-3-4b-it"),
		temperature=0.1,
	)


async def _call_llm(prompt: str, *, system_message: str | None = None) -> str:
	"""Call LM Studio directly and fail hard on connection/generation errors."""
	try:
		llm = _build_local_llm()
		messages = []
		if system_message:
			messages.append(SystemMessage(content=system_message))
		messages.append(HumanMessage(content=prompt))

		response = await llm.ainvoke(messages)
		text = response.content if isinstance(response.content, str) else str(response.content)
		if not text or not text.strip():
			raise AgentNodeError("LM Studio bos yanit dondurdu.")
		return text.strip()
	except Exception as e:  # noqa: BLE001
		logger.error(
			"LM Studio Bağlantı Hatası: Lütfen LM Studio'da Local Server'ı başlattığınızdan emin olun. | detail=%s",
			e,
		)
		raise AgentNodeError(
			"LM Studio Bağlantı Hatası: Lütfen LM Studio'da Local Server'ı başlattığınızdan emin olun."
		) from e


async def analyze_query_node(state: AgentState) -> AgentState:
	"""Analyze user query and prepare normalized intent query."""
	logger.info("node=analyze_query started")
	query = _normalize_query(state.get("query", ""))
	if not query:
		raise AgentNodeError("Kullanici sorgusu bos olamaz.")

	intent_prompt = (
		"Sen bir hukuk asistanisin. Asagidaki soruyu hukuki arama icin tek satirda yeniden yaz. "
		"Cikti sadece yeniden yazilmis sorgu olsun.\n\n"
		f"Soru: {query}"
	)
	intent = await _call_llm(intent_prompt)

	logger.info("node=analyze_query completed | normalized_query=%s", query)

	errors = list(state.get("errors", []))
	return {
		**state,
		"normalized_query": query,
		"query_intent": _normalize_query(intent),
		"attempts": _get_state_int(state, "attempts", 0),
		"max_attempts": _get_state_int(state, "max_attempts", 2),
		"retrieval_top_k": _get_state_int(state, "retrieval_top_k", 10),
		"rerank_top_n": _get_state_int(state, "rerank_top_n", 6),
		"errors": errors,
	}


async def retrieve_documents_node(state: AgentState) -> AgentState:
	"""Retrieve candidate chunks from vector DB using semantic search."""
	logger.info("node=retrieve_documents started | attempt=%s", _get_state_int(state, "attempts", 0) + 1)
	query = state.get("query_intent") or state.get("normalized_query") or state.get("query", "")
	top_k = _get_state_int(state, "retrieval_top_k", 10)
	rerank_top_n = _get_state_int(state, "rerank_top_n", 6)
	attempts = _get_state_int(state, "attempts", 0) + 1

	retrieval_service = RetrievalService()
	results = await retrieval_service.search(
		query=query,
		top_k=top_k,
		rerank_top_n=rerank_top_n,
	)

	serialized = [asdict(item) for item in results]
	logger.info("node=retrieve_documents completed | result_count=%s", len(serialized))
	return {
		**state,
		"attempts": attempts,
		"retrieval_results": serialized,
	}


def _parse_grade_output(output: str, max_index: int) -> list[int]:
	"""Parse comma-separated chunk indices from model output."""
	indices: list[int] = []
	for match in re.findall(r"\d+", output):
		value = int(match)
		if 1 <= value <= max_index and value not in indices:
			indices.append(value)
	return indices


async def grade_documents_node(state: AgentState) -> AgentState:
	"""Grade retrieved docs for query relevance using LLM-assisted filtering."""
	logger.info("node=grade_documents started")
	query = state.get("normalized_query") or state.get("query", "")
	retrieved = state.get("retrieval_results", [])
	max_attempts = _get_state_int(state, "max_attempts", 2)
	attempts = _get_state_int(state, "attempts", 0)

	if not retrieved:
		logger.info("node=grade_documents no_retrieval_results | should_retry=%s", attempts < max_attempts)
		return {
			**state,
			"relevant_results": [],
			"should_retry": attempts < max_attempts,
		}

	preview_lines = []
	for idx, item in enumerate(retrieved, start=1):
		text = str(item.get("content", ""))[:700]
		preview_lines.append(f"[{idx}] {text}")

	prompt = (
		"Kullanicinin hukuki sorusuna gore asagidaki parcaciklardan en alakali olanlarin sadece indexlerini yaz. "
		"Virgulle ayir. Ayni satirda sadece sayilar olsun.\n\n"
		f"Soru: {query}\n\n"
		"Parcaciklar:\n"
		+ "\n\n".join(preview_lines)
	)
	grade_output = await _call_llm(prompt)
	selected = _parse_grade_output(grade_output, max_index=len(retrieved))

	relevant = [retrieved[i - 1] for i in selected] if selected else []
	should_retry = not relevant and attempts < max_attempts
	logger.info(
		"node=grade_documents completed | relevant_count=%s should_retry=%s",
		len(relevant),
		should_retry,
	)

	return {
		**state,
		"relevant_results": relevant,
		"should_retry": should_retry,
		"retrieval_top_k": _get_state_int(state, "retrieval_top_k", 10) + (4 if should_retry else 0),
	}


async def generate_answer_node(state: AgentState) -> AgentState:
	"""Generate final markdown report based on relevant legal chunks."""
	logger.info("node=generate_answer started")
	query = state.get("normalized_query") or state.get("query", "")
	relevant = state.get("relevant_results", [])

	if not relevant:
		fallback = (
			"## Sonuc\n"
			"Yeterli derecede alakali hukuki metin bulunamadi.\n\n"
			"### Oneri\n"
			"- Soruyu daha spesifik bir kanun maddesi, tarih veya kurum baglaminda yeniden sorabilirsiniz."
		)
		logger.info("node=generate_answer no_relevant_results")
		return {**state, "answer_markdown": fallback}

	context_blocks = []
	for idx, item in enumerate(relevant, start=1):
		source = item.get("metadata", {}).get("source", "bilinmiyor")
		content = item.get("content", "")
		context_blocks.append(f"Kaynak {idx} ({source}):\n{content}")

	system_prompt = (
		"Sen kıdemli bir hukuk asistanısın. Sana sağlanan 'Kaynak Metinler' (Context) bölümündeki maddeleri "
		"kullanarak kullanıcının sorusuna net ve kesin bir yanıt ver. Soruya yanıt verirken ilgili Kanun "
		"maddesini (Örn: TCK m. 28) mutlaka belirt. Eğer sağlanan kaynaklarda sorunun cevabı YOKSA, varsayım "
		"yapma ve 'Bu kaynaklarda cevaba ulaşılamadı' de."
	)
	prompt = (
		f"Soru: {query}\n\n"
		"Kaynak Metinler:\n"
		+ "\n\n".join(context_blocks)
	)

	answer = await _call_llm(prompt, system_message=system_prompt)
	logger.info("node=generate_answer completed")
	return {**state, "answer_markdown": answer}
