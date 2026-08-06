from __future__ import annotations

from app.services.retrieval import RetrievalResult, TermDocument


SYSTEM_PROMPT = """\ub2f9\uc2e0\uc740 \ud55c\uad6d\uc740\ud589 \uacbd\uc81c\uae08\uc735\uc6a9\uc5b4 \ucc57\ubd07\uc785\ub2c8\ub2e4.

\uaddc\uce59
- Retrieval \uacb0\uacfc\ub9cc \uc774\uc6a9\ud55c\ub2e4.
- Retrieval\uc5d0 \uc5c6\ub294 \ub0b4\uc6a9\uc744 \ucd94\uce21\ud558\uc9c0 \uc54a\ub294\ub2e4.
- \uae08\uc735 \uc9c0\uc2dd\uc744 \uc0c8\ub85c \ub9cc\ub4e4\uc5b4\ub0b4\uc9c0 \uc54a\ub294\ub2e4.
- \uacf5\uc2dd \uc815\uc758\ub97c \ucd5c\ub300\ud55c \uc720\uc9c0\ud55c\ub2e4.
- \uc26c\uc6b4 \uc124\uba85\uc744 \ucd94\uac00\ud560 \uc218 \uc788\ub2e4.
- \ub2f5\uc744 \ubaa8\ub974\uba74 \uac80\uc0c9 \uacb0\uacfc\uac00 \uc5c6\ub2e4\uace0 \ub9d0\ud55c\ub2e4.
"""


def build_user_prompt(user_query: str, retrieval_result: RetrievalResult) -> str:
    return "\n".join(
        [
            "\uc9c8\ubb38:",
            user_query,
            "",
            "\uac80\uc0c9 \uacb0\uacfc:",
            format_retrieval_result(retrieval_result),
            "",
            "\ub2f5\ubcc0 \uc0dd\uc131",
        ]
    )


def build_messages(user_query: str, retrieval_result: RetrievalResult) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(user_query, retrieval_result)},
    ]


def format_retrieval_result(retrieval_result: RetrievalResult) -> str:
    if retrieval_result.status == "matched":
        terms = retrieval_result.terms
        if not terms:
            return "\uac80\uc0c9 \uacb0\uacfc \uc5c6\uc74c"
        return "\n\n".join(format_matched_term(term) for term in terms)

    if retrieval_result.status == "candidates":
        if not retrieval_result.candidates:
            return "\ud6c4\ubcf4 \uc6a9\uc5b4 \uc5c6\uc74c"
        names = "\n".join(f"- {term.term_name}" for term in retrieval_result.candidates)
        return f"\ud6c4\ubcf4 \uc6a9\uc5b4:\n{names}"

    return "\uac80\uc0c9 \uacb0\uacfc \uc5c6\uc74c"


def format_matched_term(term: TermDocument) -> str:
    related_terms = ", ".join(term.related_terms) if term.related_terms else "\uc5c6\uc74c"
    similarity = f"{term.similarity:.2f}" if term.similarity is not None else "N/A"
    return "\n".join(
        [
            f"\uc6a9\uc5b4\uba85: {term.term_name}",
            f"\uc720\uc0ac\ub3c4: {similarity}",
            f"\uacf5\uc2dd \uc815\uc758: {term.official_definition or '\uc5c6\uc74c'}",
            f"\uad00\ub828 \uc6a9\uc5b4: {related_terms}",
        ]
    )
