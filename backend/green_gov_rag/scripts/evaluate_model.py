#!/usr/bin/env python3
"""Evaluate GreenGovRAG model with sample queries.

python scripts/evaluate_model.py
"""

from __future__ import annotations

from green_gov_rag.rag.agent_tools import RAGAgent


def run_sample_queries(agent: RAGAgent) -> None:
    sample_queries = [
        "What are the biodiversity offset requirements in NSW?",
        "Which regulations cover emissions reporting for coal mining?",
        "Show me the zoning rules for City of Adelaide parklands",
        "What are the building standards under the National Construction Code?",
    ]

    for query in sample_queries:
        print("=" * 80)
        print(f"Query: {query}")
        result = agent.query(query)  # type: ignore[attr-defined]
        print("Answer:\n", result.get("answer", "No answer"))
        print("Sources:")
        for s in result.get("sources", []):
            print(f"- {s['title']} ({s.get('region', 'Unknown')})")
        print("=" * 80, "\n")


def main() -> None:
    agent = RAGAgent()  # Ensure vector store & embedder are preloaded
    run_sample_queries(agent)


if __name__ == "__main__":
    main()
