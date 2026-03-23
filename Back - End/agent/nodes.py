"""LangGraph node implementations for legal analysis flow."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import asdict
from typing import Any, TypedDict

import google.generativeai as genai

from services.retrieval import RetrievalResult, RetrievalService, RetrievalServiceError


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


async def _call_gemini_with_retry(
	prompt: str,
	*,
	timeout_sec: int = 45,
	max_retries: int = 3,
	retry_delay_sec: float = 1.0,
) -> str:
	"""Run Gemini generation with timeout and retry handling."""
	api_key = os.getenv("GEMINI_API_KEY", "").strip()
	if not api_key:
		raise AgentNodeError("GEMINI_API_KEY bulunamadi.")

	model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
	genai.configure(api_key=api_key)
	model = genai.GenerativeModel(model_name)

	delay = retry_delay_sec
	for attempt in range(1, max_retries + 1):
		try:
			response = await asyncio.wait_for(
				asyncio.to_thread(model.generate_content, prompt),
				timeout=timeout_sec,
			)
			text = getattr(response, "text", "") or ""
			if text.strip():
				return text.strip()
			raise AgentNodeError("Gemini bos yanit dondurdu.")
		except asyncio.TimeoutError as exc:
			if attempt == max_retries:
				raise AgentNodeError("Gemini cagrisinda timeout olustu.") from exc
		except Exception as exc:  # noqa: BLE001
			message = str(exc).lower()
			retryable = any(token in message for token in ["429", "rate", "quota", "timeout", "unavailable"])
			if attempt == max_retries or not retryable:
				raise AgentNodeError(f"Gemini cagrisi basarisiz: {exc}") from exc
		time.sleep(delay)
		delay *= 2

	raise AgentNodeError("Gemini yanit uretemedi.")


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

	try:
		intent = await _call_gemini_with_retry(intent_prompt, timeout_sec=30, max_retries=2)
	except AgentNodeError:
		intent = query

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
	try:
		results = await retrieval_service.search(
			query=query,
			top_k=top_k,
			rerank_top_n=rerank_top_n,
		)
	except RetrievalServiceError as exc:
		errors = list(state.get("errors", []))
		errors.append(f"Retrieve node hatasi: {exc}")
		logger.warning("node=retrieve_documents failed | error=%s", exc)
		return {
			**state,
			"attempts": attempts,
			"retrieval_results": [],
			"relevant_results": [],
			"should_retry": attempts < _get_state_int(state, "max_attempts", 2),
			"errors": errors,
		}

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


def _tokenize_for_overlap(text: str) -> set[str]:
	"""Simple tokenizer for lexical fallback ranking."""
	tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
	return {token for token in tokens if len(token) >= 3}


def _normalize_tr_text(text: str) -> str:
	"""Normalize Turkish-specific chars to ASCII-like lowercase for matching."""
	translation = str.maketrans({
		"Ç": "c",
		"Ğ": "g",
		"İ": "i",
		"I": "i",
		"Ö": "o",
		"Ş": "s",
		"Ü": "u",
		"ç": "c",
		"ğ": "g",
		"ı": "i",
		"ö": "o",
		"ş": "s",
		"ü": "u",
	})
	return text.translate(translation).lower()


def _select_by_keyword_overlap(query: str, retrieved: list[dict[str, Any]], max_items: int = 3) -> list[int]:
	"""Return 1-based indices ranked by query-token overlap with chunk content."""
	query_tokens = _tokenize_for_overlap(query)
	if not query_tokens:
		return [1] if retrieved else []

	scored: list[tuple[int, int]] = []
	for index, item in enumerate(retrieved, start=1):
		content = str(item.get("content", ""))
		content_tokens = _tokenize_for_overlap(content)
		overlap = len(query_tokens.intersection(content_tokens))
		scored.append((index, overlap))

	scored.sort(key=lambda pair: pair[1], reverse=True)
	selected = [idx for idx, score in scored if score > 0][:max_items]
	if selected:
		return selected
	return [idx for idx, _ in scored[:1]] if scored else []


def _derive_direct_conclusion(query: str, relevant: list[dict[str, Any]]) -> str | None:
	"""Extract a concise legal conclusion from retrieved context when possible."""
	norm_query = _normalize_tr_text(query)
	needs_self_defense_rule = all(token in norm_query for token in ["savunma", "sinir", "asil"])
	if not needs_self_defense_rule:
		return None

	for item in relevant:
		content = str(item.get("content", ""))
		norm_content = _normalize_tr_text(content)
		if "madde 27" not in norm_content and "sinirin asilmasi" not in norm_content:
			continue

		if "ceza verilmez" in norm_content:
			return (
				"Mesru savunmada sinirin asilmasi mazur gorulebilecek bir heyecan, korku veya telastan "
				"ileri gelmisse faile ceza verilmez (TCK m.27/2)."
			)

	return None


def _build_local_markdown_report(query: str, relevant: list[dict[str, Any]]) -> str:
	"""Create a useful markdown response without LLM generation.

	This fallback keeps the agent functional when external generation fails
	(e.g. quota/model/network issues).
	"""
	max_sources = min(len(relevant), 3)
	selected = relevant[:max_sources]

	dayanaklar: list[str] = []
	for idx, item in enumerate(selected, start=1):
		metadata = item.get("metadata", {})
		source = str(metadata.get("source", "bilinmiyor"))
		chunk_index = metadata.get("chunk_index")
		content = re.sub(r"\s+", " ", str(item.get("content", "")).strip())
		excerpt = content[:500] + ("..." if len(content) > 500 else "")
		chunk_label = f", parcacik #{chunk_index}" if chunk_index is not None else ""
		dayanaklar.append(f"- Kaynak {idx}: {source}{chunk_label}\n  - Alinti: {excerpt}")

	if not dayanaklar:
		dayanaklar.append("- Kaynak bulunamadi.")

	degerlendirme = (
		"Sistem, ilgili kaynak metinlerden secilen bolumleri listeler. "
		"Kesin hukuki kanaat yerine metin temelli bir on-degerlendirme sunar. "
		"Nihai yorum icin tam metin ve guncel mevzuat birlikte incelenmelidir."
	)
	direct_conclusion = _derive_direct_conclusion(query, relevant)
	sonuc = direct_conclusion or (
		"Bu soruya iliskin dogrudan hukmi otomatik olarak cikaramadim; "
		"asagidaki dayanaklardan manuel dogrulama yapabilirsiniz."
	)

	return (
		"## Ozet\n"
		f"Soru: {query}\n\n"
		"Gemini servisinde gecici bir sorun oldugu icin yanit yerel fallback modunda olusturuldu. "
		"Asagida soruyla en ilgili kaynak bolumleri listelenmistir.\n\n"
		"## Sonuc\n"
		f"{sonuc}\n\n"
		"## Dayanaklar\n"
		f"{chr(10).join(dayanaklar)}\n\n"
		"## Degerlendirme\n"
		f"{degerlendirme}\n\n"
		"## Uyari\n"
		"Bu cikti hukuki tavsiye degildir; avukat incelemesi yerine gecmez."
	)


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

	try:
		grade_output = await _call_gemini_with_retry(prompt, timeout_sec=35, max_retries=2)
		selected = _parse_grade_output(grade_output, max_index=len(retrieved))
	except AgentNodeError as exc:
		errors = list(state.get("errors", []))
		errors.append(f"Grade node LLM hatasi: {exc}")
		selected = _select_by_keyword_overlap(query=query, retrieved=retrieved, max_items=3)
		state = {**state, "errors": errors}

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
		logger.info("node=generate_answer fallback_response_generated")
		return {**state, "answer_markdown": fallback}

	context_blocks = []
	for idx, item in enumerate(relevant, start=1):
		source = item.get("metadata", {}).get("source", "bilinmiyor")
		content = item.get("content", "")
		context_blocks.append(f"Kaynak {idx} ({source}):\n{content}")

	prompt = (
		"Sen bir hukuk metni analiz asistanisin. Asagidaki kaynaklara dayanarak cevap ver. "
		"Cevabi Markdown formatinda yaz.\n"
		"Bolumler: Ozet, Dayanaklar, Degerlendirme, Uyari.\n"
		"Kesin hukum vermeden, kaynak baglamina sadik kal.\n\n"
		f"Soru: {query}\n\n"
		"Kaynaklar:\n"
		+ "\n\n".join(context_blocks)
	)

	try:
		answer = await _call_gemini_with_retry(prompt, timeout_sec=60, max_retries=3)
	except AgentNodeError as exc:
		errors = list(state.get("errors", []))
		errors.append(f"Generate node hatasi: {exc}")
		answer = _build_local_markdown_report(query=query, relevant=relevant)
		logger.warning("node=generate_answer failed | error=%s", exc)
		return {**state, "answer_markdown": answer, "errors": errors}

	logger.info("node=generate_answer completed")
	return {**state, "answer_markdown": answer}
