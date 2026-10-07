STOPWORDS = {
    "what", "when", "where", "who", "which",
    "how", "why", "is", "was", "were",
    "are", "the", "a", "an", "in", "of",
    "to", "and", "or", "did", "does", "do",
    "has", "have", "had", "it", "its",
    "for", "with", "from", "that", "this",
    "at", "by", "on", "be", "been", "me",
    "tell", "give", "show", "can", "could",
    "would", "i", "my", "about", "not", "no",
    "but", "if", "so", "than", "then",
    "there", "their", "they", "them",
    "we", "our", "you", "your", "he",
    "she", "his", "her", "will", "shall",
    "may", "might", "must", "also", "very",
    "just", "any", "some", "all", "each",
    "every", "many", "much", "more", "most",
    "other", "another", "such", "only",
    "own", "same", "made", "get",
}


def extract_content_words(
    question: str,
) -> list[str]:

    tokens = question.lower().split()

    content = [
        token.strip(
            ".,;:!?'\"()[]{}/-"
        )
        for token in tokens
    ]

    return [
        word
        for word in content
        if (
            word
            and len(word) > 1
            and word not in STOPWORDS
        )
    ]


def confidence_check(
    hits,
    content_words,
    top_score,
    page_texts,
    idfs,
):
    """
    Multi-signal confidence gate.

    Signal 1:
        IDF-weighted coverage >= 0.40

    Signal 2:
        BM25 top score >= 10.0
        AND raw overlap >= 0.30
    """

    if not hits or not content_words:

        return (
            False,
            "no results or no content words",
        )

    combined_text = " ".join(
        page_texts.get(
            (
                hit["doc_name"],
                str(hit["page"]),
            ),
            "",
        ).lower()
        for hit in hits[:3]
    )

    matched = [
        word
        for word in content_words
        if word in combined_text
    ]

    unmatched = [
        word
        for word in content_words
        if word not in combined_text
    ]

    total_idf = sum(
        idfs.values()
    )

    matched_idf = sum(
        idfs.get(word, 0)
        for word in matched
    )

    idf_coverage = (
        matched_idf / total_idf
        if total_idf > 0
        else 0
    )

    overlap = (
        len(matched)
        /
        len(content_words)
    )

    signal1_pass = (
        idf_coverage >= 0.40
    )

    signal2_pass = (
        top_score >= 10.0
        and overlap >= 0.30
    )

    if signal1_pass or signal2_pass:

        reason_parts = [
            f"idf_cov={idf_coverage:.2f}",
            (
                f"overlap="
                f"{len(matched)}"
                f"/"
                f"{len(content_words)}"
            ),
            f"top_score={top_score:.1f}",
        ]

        if (
            signal2_pass
            and not signal1_pass
        ):

            reason_parts.append(
                "[passed via BM25 score]"
            )

        return (
            True,
            ", ".join(reason_parts),
        )

    top_missing = sorted(
        unmatched,
        key=lambda word:
            idfs.get(word, 0),
        reverse=True,
    )[:3]

    missing_str = ", ".join(
        (
            f"'{word}'"
            f"(idf="
            f"{idfs.get(word, 0):.1f}"
            f")"
        )
        for word in top_missing
    )

    return (
        False,
        (
            f"idf_cov="
            f"{idf_coverage:.2f}"
            f" (<0.40), "
            f"top_score="
            f"{top_score:.1f}"
            f" (<10.0), "
            f"missing high-IDF: "
            f"[{missing_str}]"
        ),
    )