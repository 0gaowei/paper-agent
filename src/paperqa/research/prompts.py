"""
Prompts for the research pipeline.

Contains templates and utilities for query understanding, evidence summarization,
and answer generation in the research workflow.
"""

from __future__ import annotations

QUERY_UNDERSTANDING_SYSTEM = """You are an expert research librarian analyzing a research query.
Your task is to decompose the query into optimal sub-queries for academic paper search.

Analyze the query to determine:
1. The primary intent (survey, specific question, comparison, etc.)
2. Relevant research domains
3. Key entities (authors, methods, papers, concepts)
4. Best search sources

Then decompose the query into 2-5 focused sub-queries that:
- Cover different aspects of the original query
- Use appropriate terminology for academic search
- Can be executed in parallel

Respond with a JSON object containing your analysis."""

QUERY_UNDERSTANDING_PROMPT = """Analyze this research query and decompose it into optimal search sub-queries.

Query: {query}

Respond with a JSON object with this structure:
{{
  "intent": "survey|specific|comparative|current_state|background|general",
  "domains": ["domain1", "domain2"],
  "entities": ["entity1", "entity2"],
  "suitable_sources": ["semantic_scholar", "openalex"],
  "subqueries": [
    {{
      "query": "sub-query text",
      "purpose": "why this is needed",
      "priority": 1-10,
      "parent_intent": "same as top-level intent",
      "domain": "relevant domain"
    }}
  ],
  "search_strategy": "survey|domain|general"
}}

Guidelines:
- For survey queries: create sub-queries for overview, key papers, recent advances
- For specific queries: create sub-queries for different aspects
- For comparative queries: create sub-queries for each thing being compared
- Use specific technical terms when appropriate
- Priority 7-10 for core aspects, 4-6 for supporting aspects
- Include relevant field-specific keywords in sub-queries"""

EVIDENCE_SUMMARY_PROMPT = """You are analyzing an academic paper abstract for relevance to a research query.

Paper Title: {title}
Paper Abstract: {abstract}

Research Query: {query}

Score the abstract on a scale of 0.0 to 10.0 for relevance to the query:
- 9-10: Paper is directly and highly relevant
- 7-8: Paper is clearly relevant with substantial overlap
- 5-6: Paper has some relevance but may not fully address the query
- 3-4: Paper touches on related topics but is not directly relevant
- 1-2: Paper is tangentially related
- 0: Paper is not relevant at all

Also provide a brief (1-2 sentence) summary of how this paper relates to the query.

Respond with a JSON object:
{{
  "relevance_score": 0.0-10.0,
  "summary": "1-2 sentence summary"
}}"""

USE_JSON = True
