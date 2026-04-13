from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from rag_engine.rag_pipeline.retrieval.retrieval_engine import RetrievedContext

logger = logging.getLogger(__name__)


# ─── Deep-trigger keywords ────────────────────────────────────────────────────

DEEP_TRIGGERS: set[str] = {
    "explain", "describe", "compare", "analyze", "analyse",
    "summarise", "summarize", "why", "how does", "how do",
    "what is the difference", "elaborate", "detail",
    "break down", "walk me through", "illustrate",
    "what are the steps", "in depth", "overview",
    "pros and cons", "advantages", "disadvantages",
}


# ─── Prompt templates ─────────────────────────────────────────────────────────

FAST_PROMPT = """\
You are an Enterprise Knowledge Assistant that answers questions strictly from company documents.

CRITICAL RULES — follow every one without exception:
1. Read the CONTEXT carefully. Your answer MUST be directly supported by words or facts present in the context.
2. Answer in 2–4 concise bullet points. Each bullet should be one clear sentence.
3. Only include bullets that are clearly answerable from the context. Fewer accurate bullets beats more irrelevant ones.
4. Do NOT add outside knowledge, assumptions, or filler statements not grounded in the context.
5. Do NOT mention "the context", "the documents", or repeat the question.
6. If the context does not contain enough information to answer, output ONLY the exact fallback phrase — nothing else.

RELEVANCE CHECK: Before writing each bullet, verify it is directly supported by text in the context above. If it is not, skip it.\
"""

DEEP_PROMPT = """\
You are an Enterprise Knowledge Assistant.
Answer using ONLY the information provided in the context below.

RULES:
- Always complete your answer fully. Never stop mid-sentence or mid-point.
- Every section, point, or explanation you begin MUST be finished completely.
- Begin with a 1-2 sentence summary, then expand with full structured detail.
- Use numbered lists or headers where helpful for clarity.
- Combine related ideas into a cohesive, flowing explanation.
- Explain relationships between concepts and steps clearly.
- Do NOT add any information not present in the context.
- Do NOT mention the documents or context explicitly.

If the answer is not found in the context, respond EXACTLY with:
"I could not find an answer to this question in the provided documents."\
"""

FALLBACK_RESPONSE = (
    "I could not find an answer to this question in the provided documents."
)

# ─── Fast-path user prompt — tighter relevance grounding ──────────────────────

FAST_USER_PROMPT_TEMPLATE = """\
CONTEXT FROM DOCUMENTS:
{context}

---

QUESTION: {question}

INSTRUCTIONS:
- Re-read the context above carefully.
- Answer ONLY with information that is explicitly stated in the context.
- If a fact is not in the context, do NOT include it.
- If the context has no relevant information at all, respond with EXACTLY: "{fallback}"

Answer (bullet points only, grounded in the context):\
"""

# ─── Deep-path user prompt ────────────────────────────────────────────────────

DEEP_USER_PROMPT_TEMPLATE = """\
CONTEXT FROM DOCUMENTS:
{context}

---

QUESTION: {question}

INSTRUCTIONS:
- Answer strictly using the context above.
- If the context is insufficient, say exactly: "{fallback}"
- Do not invent, infer, or add outside knowledge.

Answer:\
"""

# Backward-compatible alias
USER_PROMPT_TEMPLATE = DEEP_USER_PROMPT_TEMPLATE


# ─── Response dataclass ───────────────────────────────────────────────────────

@dataclass
class LLMResponse:
    question:     str
    answer:       str
    sources:      List[dict]
    is_grounded:  bool
    model_used:   str
    context_used: str = ""
    raw_output:   str = ""


# ─── Orchestrator ─────────────────────────────────────────────────────────────

class LLMOrchestrator:
    """
    Wraps the Ollama / HuggingFace LLM call with:
      · Smart fast / deep model selection (single call, no double-override)
      · Metadata-clean context (strips score annotations before prompt)
      · Hard token split: 400 (fast) vs 1200 (deep)
      · Separate, relevance-focused prompt for the fast path
      · Strict grounding prompt with injected fallback string
      · Fallback detection
      · Source citation passthrough
    """

    def __init__(
        self,
        fast_model:  str   = "phi3:mini",
        deep_model:  str   = "mistral:latest",
        backend:     str   = "ollama",
        base_url:    str   = "http://localhost:11434",
        max_tokens:  int   = 800,
        temperature: float = 0.1,
    ):
        self.fast_model  = fast_model
        self.deep_model  = deep_model
        self.model       = fast_model       # active model; set by select_model()
        self.backend     = backend
        self.base_url    = base_url
        self.max_tokens  = max_tokens
        self.temperature = temperature
        self._client     = None
        self._pipe       = None

        if backend == "ollama":
            self._setup_ollama()
        elif backend == "huggingface":
            self._setup_hf()
        else:
            raise ValueError(
                f"Unknown backend: {backend!r}. Use 'ollama' or 'huggingface'."
            )

    # ── Setup ─────────────────────────────────────────────────────────────

    def _setup_ollama(self) -> None:
        try:
            from ollama import Client
            self._client = Client(host=self.base_url)
            logger.info(
                f"Ollama client ready → {self.base_url} | "
                f"fast={self.fast_model} | deep={self.deep_model}"
            )
        except ImportError:
            raise ImportError("Run: pip install ollama")

    def _setup_hf(self) -> None:
        try:
            from transformers import pipeline
            import torch
            logger.info(f"Loading HuggingFace model: {self.model} …")
            self._pipe = pipeline(
                "text-generation",
                model          = self.model,
                device_map     = "auto",
                torch_dtype    = torch.float16,
                max_new_tokens = self.max_tokens,
            )
            logger.info("HuggingFace pipeline ready.")
        except ImportError:
            raise ImportError("Run: pip install transformers torch")

    # ── Model selection ───────────────────────────────────────────────────

    def select_model(self, query: str, mode: str = "auto") -> None:
        """
        Set self.model based on explicit mode or keyword auto-detection.
        Called ONCE from pipeline.query() — never internally from answer().
        """
        if mode == "fast":
            self.model = self.fast_model

        elif mode == "deep":
            self.model = self.deep_model

        else:  # auto
            q = query.lower()
            is_complex = (
                len(query) > 120
                or q.count("?") > 1
                or any(kw in q for kw in DEEP_TRIGGERS)
            )
            self.model = self.deep_model if is_complex else self.fast_model

        logger.info(f"Model selected: {self.model!r}  (mode={mode!r})")

    # ── Per-model config ──────────────────────────────────────────────────

    def _get_model_config(self) -> dict:
        """
        Fast path: relevance-first prompt, slightly higher token budget (400)
                   so the model has room to be precise without being forced
                   into truncated or hallucinated bullets.
        Deep path: full structured explanation, 1200 tokens.
        """
        if self.model == self.fast_model:
            return {
                "system_prompt": FAST_PROMPT,
                "user_template": FAST_USER_PROMPT_TEMPLATE,
                "temperature":   0.05,   # near-deterministic for factual retrieval
                "max_tokens":    400,    # raised from 300 → avoids cut-off bullets
            }
        else:
            return {
                "system_prompt": DEEP_PROMPT,
                "user_template": DEEP_USER_PROMPT_TEMPLATE,
                "temperature":   0.25,
                "max_tokens":    1200,
            }

    # ── Metadata cleaner ──────────────────────────────────────────────────

    @staticmethod
    def _clean_context(raw_context: str) -> str:
        """
        Strip retrieval metadata (score, page score annotations) that leak
        from the vector store into the prompt and appear in model output.
        """
        cleaned_lines = []
        for line in raw_context.splitlines():
            if re.match(r"^\s*\(?\s*(score|page score)\s*:", line, re.IGNORECASE):
                continue
            line = re.sub(r"\s*\(\s*score\s*:\s*[\d.]+\)", "", line, flags=re.IGNORECASE)
            line = re.sub(r"\s*\(\s*page score\s*:\s*[\d.]+\)", "", line, flags=re.IGNORECASE)
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    # ── Query rewriter (fast path only) ───────────────────────────────────

    @staticmethod
    def _rewrite_query_for_retrieval(query: str) -> str:
        """
        Expand short/ambiguous queries so the embedding search finds more
        relevant chunks.  This is a lightweight heuristic rewrite — no LLM
        call required.

        Examples:
          "leave policy"   → "What is the leave policy?"
          "refund"         → "What is the refund process or policy?"
          "password reset" → "How do I reset my password?"
        """
        q = query.strip()

        # Already a full question — return as-is
        if q.endswith("?") or len(q.split()) > 8:
            return q

        # Very short keyword phrase — wrap it in a question
        word_count = len(q.split())
        if word_count <= 3:
            return f"What is {q}?"

        # Medium phrase without a verb — add "What is" or "How to"
        lower = q.lower()
        has_verb = any(v in lower for v in (
            "is", "are", "was", "were", "do", "does", "did",
            "can", "could", "should", "would", "will", "how", "what", "when", "why"
        ))
        if not has_verb:
            return f"What is {q}?"

        return q

    # ── Main entry point ──────────────────────────────────────────────────

    def answer(self, context: RetrievedContext) -> LLMResponse:
        """
        Given a RetrievedContext, build prompt → call LLM → return LLMResponse.

        NOTE: select_model() must be called by the pipeline BEFORE this method.
        """
        # Short-circuit: no context → return fallback without an LLM call
        if context.is_empty():
            logger.warning("Empty context — returning fallback without LLM call.")
            return LLMResponse(
                question    = context.query,
                answer      = FALLBACK_RESPONSE,
                sources     = [],
                is_grounded = False,
                model_used  = self.model,
            )

        # Clean metadata before building prompt
        clean_ctx = self._clean_context(context.context_text)

        cfg = self._get_model_config()
        prompt = cfg["user_template"].format(
            context  = clean_ctx,
            question = context.query,
            fallback = FALLBACK_RESPONSE,
        )

        raw_output  = self._call_llm(prompt)
        is_grounded = FALLBACK_RESPONSE.lower() not in raw_output.lower()

        return LLMResponse(
            question    = context.query,
            answer      = raw_output.strip(),
            sources     = context.sources,
            is_grounded = is_grounded,
            model_used  = self.model,
            context_used= clean_ctx,
            raw_output  = raw_output,
        )

    # ── LLM backends ──────────────────────────────────────────────────────

    def _call_llm(self, user_prompt: str) -> str:
        if self.backend == "ollama":
            return self._call_ollama(user_prompt)
        if self.backend == "huggingface":
            return self._call_hf(user_prompt)
        raise ValueError(f"Unknown backend: {self.backend!r}")

    def _call_ollama(self, user_prompt: str) -> str:
        if self._client is None:
            raise RuntimeError("Ollama client not initialized.")

        cfg = self._get_model_config()
        response = self._client.chat(
            model    = self.model,
            messages = [
                {"role": "system", "content": cfg["system_prompt"]},
                {"role": "user",   "content": user_prompt},
            ],
            options  = {
                "temperature": cfg["temperature"],
                "num_predict": cfg["max_tokens"],
                "stop":        [],
                "num_ctx":     4096,
            },
        )
        return response["message"]["content"]

    def _call_hf(self, user_prompt: str) -> str:
        if self._pipe is None:
            raise RuntimeError("HuggingFace pipeline not initialized.")

        cfg         = self._get_model_config()
        full_prompt = (
            f"[INST] <<SYS>>\n{cfg['system_prompt']}\n<</SYS>>\n\n"
            f"{user_prompt} [/INST]"
        )
        output = self._pipe(full_prompt, return_full_text=False)
        return output[0]["generated_text"]
