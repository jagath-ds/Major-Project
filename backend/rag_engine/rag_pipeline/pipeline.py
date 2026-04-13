from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Dict

from rag_engine.rag_pipeline.chunking.semantic_chunker import SemanticChunker
from rag_engine.rag_pipeline.embeddings.bge_engine import EmbeddingEngine
from rag_engine.rag_pipeline.vectorstore.store import build_vector_store, VectorStore
from rag_engine.rag_pipeline.retrieval.retrieval_engine import RetrievalEngine
from rag_engine.rag_pipeline.llm.orchestrator import LLMOrchestrator, LLMResponse

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Configuration ────────────────────────────────────────────────────────────

@dataclass
class PipelineConfig:
    # Chunking
    chunk_size_tokens:    int   = 400
    chunk_overlap_tokens: int   = 80

    # Embeddings
    embedding_model:      str   = "BAAI/bge-large-en-v1.5"
    embedding_batch_size: int   = 32
    embedding_cache:      bool  = True

    # Vector store
    vector_backend:       str   = "faiss"
    vector_persist_dir:   str   = "./data/vector_store"
    collection_name:      str   = "enterprise_rag"

    # Retrieval
    # fast model: more chunks (5) but stricter relevance filter → higher precision
    # deep model: even more chunks for broad coverage
    retrieval_top_k_fast: int   = 5     # raised from 3 → better recall before MMR filters
    retrieval_top_k_deep: int   = 6
    retrieval_fetch_k:    int   = 25
    min_relevance_score:  float = 0.45  # raised from 0.30 → filters noise chunks
    mmr_lambda_fast:      float = 0.80  # NEW: relevance-first for fast path
    mmr_lambda_deep:      float = 0.60  # original balanced value for deep path

    # LLM
    fast_model:           str   = "phi3:mini"
    deep_model:           str   = "mistral:latest"
    llm_backend:          str   = "ollama"
    llm_base_url:         str   = "http://localhost:11434"
    llm_temperature:      float = 0.1
    llm_max_tokens:       int   = 800


# ─── Pipeline ─────────────────────────────────────────────────────────────────

class RAGPipeline:
    """
    End-to-end RAG pipeline.

    Public API
    ----------
    index_document(...)   — chunk → embed → store
    index_pages(...)      — multi-page variant
    delete_document(...)  — remove by doc_id
    query(...)            — embed → retrieve → LLM → LLMResponse
    stats()               — diagnostics
    """

    def __init__(
        self,
        chunker:              SemanticChunker,
        embedder:             EmbeddingEngine,
        store:                VectorStore,
        retriever:            RetrievalEngine,
        llm:                  LLMOrchestrator,
        retrieval_top_k_fast: int   = 5,
        retrieval_top_k_deep: int   = 6,
        mmr_lambda_fast:      float = 0.80,
        mmr_lambda_deep:      float = 0.60,
    ):
        self.chunker              = chunker
        self.embedder             = embedder
        self.store                = store
        self.retriever            = retriever
        self.llm                  = llm
        self.retrieval_top_k_fast = retrieval_top_k_fast
        self.retrieval_top_k_deep = retrieval_top_k_deep
        self.mmr_lambda_fast      = mmr_lambda_fast
        self.mmr_lambda_deep      = mmr_lambda_deep
        logger.info("RAGPipeline initialised.")

    # ── Factory ───────────────────────────────────────────────────────────
    @staticmethod
    def _is_short_query(question: str) -> bool:
        words = question.strip().split()
        return 1 <= len(words) <= 3

    @staticmethod
    def _extract_query_terms(question: str) -> List[str]:
        terms = re.findall(r"[a-zA-Z0-9_]+", question.lower())
        stopwords = {"what", "is", "the", "a", "an", "who", "how"}
        return [term for term in terms if term not in stopwords]

    @staticmethod
    def _retrieved_chunks_contain_terms(chunks, query_terms: List[str]) -> bool:
        if not query_terms:
            return False

        for chunk in chunks:
            text = chunk.text.lower()
            if any(term in text for term in query_terms):
                return True

        return False

    @classmethod
    def from_config(cls, cfg: Optional[PipelineConfig] = None) -> "RAGPipeline":
        if cfg is None:
            cfg = PipelineConfig()

        logger.info("Building RAGPipeline from config…")
        os.makedirs(cfg.vector_persist_dir, exist_ok=True)

        chunker = SemanticChunker(
            chunk_size = cfg.chunk_size_tokens,
            overlap    = cfg.chunk_overlap_tokens,
        )
        embedder = EmbeddingEngine(
            model_name = cfg.embedding_model,
            batch_size = cfg.embedding_batch_size,
            cache      = cfg.embedding_cache,
        )
        if cfg.vector_backend == "faiss":
            store = build_vector_store(
                backend    = "faiss",
                index_path = cfg.vector_persist_dir,
            )
        elif cfg.vector_backend == "chroma":
            store = build_vector_store(
                backend         = "chroma",
                persist_dir     = cfg.vector_persist_dir,
                collection_name = cfg.collection_name,
            )
        else:
            raise ValueError(f"Unknown vector backend: {cfg.vector_backend!r}")

        retriever = RetrievalEngine(
            embedding_engine = embedder,
            vector_store     = store,
            top_k            = cfg.retrieval_top_k_deep,   # default; overridden per query
            fetch_k          = cfg.retrieval_fetch_k,
            min_score        = cfg.min_relevance_score,
            mmr_lambda       = cfg.mmr_lambda_deep,
        )
        llm = LLMOrchestrator(
            fast_model  = cfg.fast_model,
            deep_model  = cfg.deep_model,
            backend     = cfg.llm_backend,
            base_url    = cfg.llm_base_url,
            temperature = cfg.llm_temperature,
            max_tokens  = cfg.llm_max_tokens,
        )
        return cls(
            chunker,
            embedder,
            store,
            retriever,
            llm,
            retrieval_top_k_fast = cfg.retrieval_top_k_fast,
            retrieval_top_k_deep = cfg.retrieval_top_k_deep,
            mmr_lambda_fast      = cfg.mmr_lambda_fast,
            mmr_lambda_deep      = cfg.mmr_lambda_deep,
        )

    # ── Indexing ──────────────────────────────────────────────────────────

    def index_document(
        self,
        text:        str,
        doc_id:      str,
        source_path: str,
        page_number: Optional[int]  = None,
        extra_meta:  Optional[dict] = None,
    ) -> int:
        """
        Full indexing pipeline for a single document / page:
          text → chunks → embeddings → vector store
        Returns number of chunks indexed.
        """
        logger.info(f"Indexing doc_id={doc_id!r}  source={source_path!r}")

        chunks = self.chunker.chunk_document(
            text        = text,
            doc_id      = doc_id,
            source_path = source_path,
            page_number = page_number,
            extra_meta  = extra_meta or {},
        )
        if not chunks:
            logger.warning(f"No chunks produced for doc_id={doc_id!r}. Skipping.")
            return 0

        avg_tokens = sum(c.token_count for c in chunks) // len(chunks)
        logger.info(f"  → {len(chunks)} chunks (avg {avg_tokens} tokens each)")

        embedded = self.embedder.embed_chunks(chunks)
        self.store.upsert(embedded)
        logger.info(
            f"  → Indexed {len(embedded)} vectors. "
            f"Store total: {self.store.count()}"
        )
        return len(chunks)

    def index_pages(
        self,
        pages:       List[Dict],    # [{"text": ..., "page": 1}, ...]
        doc_id:      str,
        source_path: str,
        extra_meta:  Optional[dict] = None,
    ) -> int:
        """Index a multi-page document preserving page numbers."""
        chunks   = self.chunker.chunk_pages(pages, doc_id, source_path, extra_meta or {})
        embedded = self.embedder.embed_chunks(chunks)
        self.store.upsert(embedded)
        logger.info(f"Indexed {len(embedded)} chunks for multi-page doc {doc_id!r}")
        return len(embedded)

    def delete_document(self, doc_id: str) -> None:
        """Remove all chunks for a document (useful before re-indexing)."""
        self.store.delete_document(doc_id)
        logger.info(f"Deleted all chunks for doc_id={doc_id!r}")

    # ── Querying ──────────────────────────────────────────────────────────

    def query(
        self,
        question:      str,
        model_mode:    str           = "auto",   # 'auto' | 'fast' | 'deep'
        top_k:         Optional[int] = None,
        filter_doc_id: Optional[str] = None,
    ) -> LLMResponse:
        """
        Full RAG query pipeline:
          question → select model → [rewrite query for fast path]
                   → retrieve context → LLM → LLMResponse

        Fast path improvements vs original:
          - Query rewriting: short/vague queries are expanded before embedding
          - Higher retrieval top_k (5 vs 3): more candidates for MMR to filter
          - Relevance-first MMR (λ=0.80 vs 0.60): picks the most on-topic chunks
          - Stricter score threshold (0.45 vs 0.30): noise chunks are rejected
          - Tighter grounding prompt with per-bullet relevance check instruction
        """
        logger.info(f"Query: {question!r}  |  mode={model_mode!r}")

        # 1. Select model — single call, no internal override
        self.llm.select_model(question, model_mode)
        logger.info(f"  → Active model: {self.llm.model!r}")

        is_fast = (self.llm.model == self.llm.fast_model)

        # 2. For the fast path, rewrite short/ambiguous queries to improve
        #    embedding recall before retrieval.
        retrieval_query = question
        if is_fast:
            retrieval_query = self.llm._rewrite_query_for_retrieval(question)
            if retrieval_query != question:
                logger.info(f"  → Query rewritten for retrieval: {retrieval_query!r}")

        # 3. Resolve retrieval depth and MMR lambda
        if top_k is not None:
            effective_top_k = top_k
        elif is_fast:
            effective_top_k = self.retrieval_top_k_fast
        else:
            effective_top_k = self.retrieval_top_k_deep

        effective_mmr = self.mmr_lambda_fast if is_fast else self.mmr_lambda_deep
        logger.info(
            f"  → Retrieval top_k={effective_top_k}  mmr_lambda={effective_mmr}"
        )

        # 4. Retrieve context (rewritten query used for embedding; original
        #    question is preserved in the RetrievedContext for the LLM prompt)
        raw_context = self.retriever.retrieve(
            query         = retrieval_query,
            top_k         = effective_top_k,
            filter_doc_id = filter_doc_id,
            mmr_lambda    = effective_mmr,
        )
        
        if self._is_short_query(question):
            query_terms = self._extract_query_terms(question)
            has_exact_support = self._retrieved_chunks_contain_terms(
                raw_context.chunks,
                query_terms,
            )

            if not has_exact_support:
                logger.info(
                    "Short query failed exact-term validation. Returning fallback-safe empty context."
                )
                from rag_engine.rag_pipeline.retrieval.retrieval_engine import RetrievedContext
                raw_context = RetrievedContext(
                    query        = retrieval_query,
                    chunks       = [],
                    context_text = "",
                    sources      = [],
                    total_tokens = 0,
                    strategy_used= "short_query_exact_match_failed",
                )

        # Restore the user's original question in the context object so the
        # LLM prompt shows what the user actually asked (not the rewritten form)
        from rag_engine.rag_pipeline.retrieval.retrieval_engine import RetrievedContext
        context = RetrievedContext(
            query        = question,        # original question for the prompt
            chunks       = raw_context.chunks,
            context_text = raw_context.context_text,
            sources      = raw_context.sources,
            total_tokens = raw_context.total_tokens,
            strategy_used= raw_context.strategy_used,
        )

        logger.info(
            f"  → Retrieved {len(context.chunks)} chunks "
            f"(~{context.total_tokens} tokens)"
        )

        # 5. Generate answer
        response = self.llm.answer(context)
        logger.info(
            f"  → {'Grounded' if response.is_grounded else 'FALLBACK'} answer | "
            f"model={response.model_used!r}"
        )

        return response

    # ── Diagnostics ───────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "total_indexed_chunks":  self.store.count(),
            "embedding_cache":       self.embedder.cache_stats(),
            "active_model":          self.llm.model,
            "fast_model":            self.llm.fast_model,
            "deep_model":            self.llm.deep_model,
            "retrieval_top_k_fast":  self.retrieval_top_k_fast,
            "retrieval_top_k_deep":  self.retrieval_top_k_deep,
            "mmr_lambda_fast":       self.mmr_lambda_fast,
            "mmr_lambda_deep":       self.mmr_lambda_deep,
        }
