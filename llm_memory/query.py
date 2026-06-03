"""Query the knowledge base using index-guided retrieval (no RAG)."""

from __future__ import annotations

import argparse
import asyncio

from llm_memory.config import KNOWLEDGE_DIR, QA_DIR, ROOT_DIR, now_iso
from llm_memory.utils import load_state, read_all_wiki_content, save_state


async def run_query(question: str, file_back: bool = False) -> str:
    from llm_memory.providers import get_provider

    wiki_content = read_all_wiki_content()

    tools = ["Read", "Glob", "Grep"]
    if file_back:
        tools.extend(["Write", "Edit"])

    file_back_instructions = ""
    if file_back:
        timestamp = now_iso()
        file_back_instructions = f"""

## File Back Instructions

After answering, do the following:
1. Create a Q&A article at {QA_DIR}/ with the filename being a slugified version
   of the question (e.g., knowledge/qa/how-to-handle-auth-redirects.md)
2. Use the Q&A article format from the schema (frontmatter with title, question,
   consulted articles, filed date)
3. Update {KNOWLEDGE_DIR / 'index.md'} with a new row for this Q&A article
4. Append to {KNOWLEDGE_DIR / 'log.md'}:
   ## [{timestamp}] query (filed) | question summary
   - Question: {question}
   - Consulted: [[list of articles read]]
   - Filed to: [[qa/article-name]]
"""

    prompt = f"""You are a knowledge base query engine. Answer the user's question by
consulting the knowledge base below.

## How to Answer

1. Read the INDEX section first - it lists every article with a one-line summary
2. Identify 3-10 articles that are relevant to the question
3. Read those articles carefully (they're included below)
4. Synthesize a clear, thorough answer
5. Cite your sources using [[wikilinks]] (e.g., [[concepts/supabase-auth]])
6. If the knowledge base doesn't contain relevant information, say so honestly

## Knowledge Base

{wiki_content}

## Question

{question}
{file_back_instructions}"""

    answer = ""
    cost = 0.0
    provider = get_provider()

    try:
        answer, cost = await provider.call(
            prompt,
            allowed_tools=tools,
            max_turns=15,
            cwd=str(ROOT_DIR),
            use_code_preset=True,
        )
    except Exception as e:
        answer = f"Error querying knowledge base: {e}"

    state = load_state()
    state["query_count"] = state.get("query_count", 0) + 1
    state["total_cost"] = state.get("total_cost", 0.0) + cost
    save_state(state)

    return answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the personal knowledge base")
    parser.add_argument("question", help="The question to ask")
    parser.add_argument(
        "--file-back",
        action="store_true",
        help="File the answer back into the knowledge base as a Q&A article",
    )
    args = parser.parse_args()

    print(f"Question: {args.question}")
    print(f"File back: {'yes' if args.file_back else 'no'}")
    print("-" * 60)

    answer = asyncio.run(run_query(args.question, file_back=args.file_back))
    print(answer)

    if args.file_back:
        print("\n" + "-" * 60)
        qa_count = len(list(QA_DIR.glob("*.md"))) if QA_DIR.exists() else 0
        print(f"Answer filed to knowledge/qa/ ({qa_count} Q&A articles total)")


if __name__ == "__main__":
    main()
