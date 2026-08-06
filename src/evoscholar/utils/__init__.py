"""Cross-package utilities shared by ≥2 feature packages.

Per refactor-plan §3.5.3, this package is for code shared across multiple
feature packages (literature_qa / iterative_search / paper_ranker / synthesis /
query_understanding / metadata_clients / server). Code used by only one
package should live in that package's own ``core.py`` instead.

Module layout:

- ``paths.py`` — path / directory constants
- ``llms.py`` — generic LLM factory helpers and vector store base classes
- ``_helpers.py`` — generic helpers (entropy checks, retries, formatting, etc.)
"""

from __future__ import annotations

from ._helpers import (
    BIBTEX_MAPPING,
    CitationConversionError,
    INVALID_UNICODE_CHARS,
    ImpossibleParsingError,
    MAX_TEXT_ENTROPY,
    REPLACEMENT_CHAR,
    _get_with_retrying,
    batch_iter,
    bibtex_field_extract,
    citation_to_docname,
    clean_invalid_unicode,
    clean_possessives,
    clean_upbibtex,
    compute_unique_doc_id,
    create_bibtex_key,
    encode_id,
    extract_doi,
    extract_score,
    extract_thought,
    format_bibtex,
    get_citation_ids,
    get_loop,
    get_parenthetical_substrings,
    get_stable_str,
    get_year,
    hexdigest,
    is_retryable,
    logging_filters,
    maybe_get_date,
    maybe_is_html,
    maybe_is_pdf,
    maybe_is_text,
    md5sum,
    mutate_acute_accents,
    name_in_text,
    parse_enrichment_irrelevance,
    pqa_directory,
    remove_substrings,
    run_or_ensure,
    setup_default_logs,
    strings_similarity,
    strip_citations,
    union_collections_to_ordered_list,
)

__all__ = [
    "BIBTEX_MAPPING",
    "CitationConversionError",
    "INVALID_UNICODE_CHARS",
    "ImpossibleParsingError",
    "MAX_TEXT_ENTROPY",
    "REPLACEMENT_CHAR",
    "_get_with_retrying",
    "batch_iter",
    "bibtex_field_extract",
    "citation_to_docname",
    "clean_invalid_unicode",
    "clean_possessives",
    "clean_upbibtex",
    "compute_unique_doc_id",
    "create_bibtex_key",
    "encode_id",
    "extract_doi",
    "extract_score",
    "extract_thought",
    "format_bibtex",
    "get_citation_ids",
    "get_loop",
    "get_parenthetical_substrings",
    "get_stable_str",
    "get_year",
    "hexdigest",
    "is_retryable",
    "logging_filters",
    "maybe_get_date",
    "maybe_is_html",
    "maybe_is_pdf",
    "maybe_is_text",
    "md5sum",
    "mutate_acute_accents",
    "name_in_text",
    "parse_enrichment_irrelevance",
    "pqa_directory",
    "remove_substrings",
    "run_or_ensure",
    "setup_default_logs",
    "strings_similarity",
    "strip_citations",
    "union_collections_to_ordered_list",
]
