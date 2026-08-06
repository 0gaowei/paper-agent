"""Core types, prompts, and readers for literature_qa package.

This module aggregates exports from the moved files:
- types.py: Doc, Text, DocDetails, PQASession, etc.
- prompts.py: QA prompts, citation prompts, etc.
- readers.py: PDF/text readers
- docs.py: Docs class (uses settings)

Owner: literature_qa package.

Note: Due to circular imports (Docs -> settings -> settings_config -> core),
we use lazy imports for settings-dependent exports.
"""

from __future__ import annotations

# Re-export types from types.py
from lmi import Embeddable
from .types import (
    AUTOPOPULATE_VALUE,
    BibTeXSource,
    ChunkMetadata,
    CITATION_FALLBACK_DATA,
    Context,
    create_multimodal_message,
    DEFAULT_FIELDS_TO_OVERWRITE_FROM_METADATA,
    Doc,
    DocDetails,
    DocKey,
    JOURNAL_EXPECTED_DOI_LENGTHS,
    ParsedMedia,
    ParsedMetadata,
    ParsedText,
    PQASession,
    SOURCE_QUALITY_MESSAGES,
    Text,
    VAR_MATCH_LOOKUP,
    VAR_MISMATCH_LOOKUP,
)

# CitationConversionError is in utils
from evoscholar.utils import CitationConversionError

# Re-export prompts from prompts.py
from .prompts import (
    CANNOT_ANSWER_PHRASE,
    answer_iteration_prompt_template,
    citation_prompt,
    CITATION_KEY_CONSTRAINTS,
    CONTEXT_INNER_PROMPT,
    CONTEXT_INNER_PROMPT_NOT_DETAILED,
    CONTEXT_OUTER_PROMPT,
    default_system_prompt,
    EMPTY_CONTEXTS,
    env_reset_prompt,
    env_system_prompt,
    EVAL_PROMPT_TEMPLATE,
    full_page_enrichment_prompt_template,
    individual_media_enrichment_prompt_template,
    qa_prompt,
    QA_PROMPT_TEMPLATE,
    select_paper_prompt,
    structured_citation_prompt,
    summary_json_multimodal_system_prompt,
    summary_json_prompt,
    summary_json_system_prompt,
    summary_prompt,
    text_with_tables_prompt_template,
)

# Re-export readers from readers.py
from .readers import (
    AsyncPDFParserFn,
    chunk_pdf,
    ImpossibleParsingError,
    parse_image,
    parse_text,
    PDFParserFn,
    read_doc,
    resolve_page_range,
    SyncPDFParserFn,
)

# Re-export from core_impl.py (depends on types and prompts)
from .core_impl import (
    LLMBadContextJSONError,
    LLMContextError,
    LLMContextRequestFailedError,
    LLMContextTimeoutError,
    llm_parse_json,
    map_fxn_summary,
)

# Lazy import for Docs to avoid circular import with settings
def __getattr__(name: str):
    if name == "Docs":
        from .docs import Docs
        return Docs
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Types
    "AUTOPOPULATE_VALUE",
    "BibTeXSource",
    "CANNOT_ANSWER_PHRASE",
    "ChunkMetadata",
    "CITATION_FALLBACK_DATA",
    "CitationConversionError",
    "Context",
    "CONTEXT_INNER_PROMPT",
    "CONTEXT_INNER_PROMPT_NOT_DETAILED",
    "CONTEXT_OUTER_PROMPT",
    "create_multimodal_message",
    "DEFAULT_FIELDS_TO_OVERWRITE_FROM_METADATA",
    "Doc",
    "DocDetails",
    "DocKey",
    "Embeddable",
    "EMPTY_CONTEXTS",
    "env_reset_prompt",
    "env_system_prompt",
    "EVAL_PROMPT_TEMPLATE",
    "full_page_enrichment_prompt_template",
    "individual_media_enrichment_prompt_template",
    "ImpossibleParsingError",
    "JOURNAL_EXPECTED_DOI_LENGTHS",
    "ParsedMedia",
    "ParsedMetadata",
    "ParsedText",
    "PQASession",
    "qa_prompt",
    "QA_PROMPT_TEMPLATE",
    "select_paper_prompt",
    "SOURCE_QUALITY_MESSAGES",
    "Text",
    "VAR_MATCH_LOOKUP",
    "VAR_MISMATCH_LOOKUP",
    # Prompts
    "answer_iteration_prompt_template",
    "citation_prompt",
    "CITATION_KEY_CONSTRAINTS",
    "default_system_prompt",
    "structured_citation_prompt",
    "summary_json_multimodal_system_prompt",
    "summary_json_prompt",
    "summary_json_system_prompt",
    "summary_prompt",
    "text_with_tables_prompt_template",
    # Readers
    "AsyncPDFParserFn",
    "chunk_pdf",
    "parse_image",
    "parse_text",
    "PDFParserFn",
    "read_doc",
    "resolve_page_range",
    "SyncPDFParserFn",
    # Core impl
    "LLMBadContextJSONError",
    "LLMContextError",
    "LLMContextRequestFailedError",
    "LLMContextTimeoutError",
    "llm_parse_json",
    "map_fxn_summary",
]
