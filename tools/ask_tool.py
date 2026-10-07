import json
import pickle
import time

from config import (
    LOCAL_OKF_CONCEPTS_FILE,
    LOCAL_OKF_BM25_INDEX_FILE,
    LOCAL_WHOOSH_INDEX_DIR,
    LOCAL_LLM_BUNDLE_MANIFEST_FILE,
    LOCAL_LLM_BUNDLE_ROOT,
)

from tools.volume_tools import (
    sync_persistence_assets,
)

from services.lakehouse_service import (
    get_metadata,
    get_document_names,
)

from services.llm_service import (
    call_llm,
)

from retrieval.okf_navigator import (
    OKFNavigator,
)

from retrieval.bm25_retriever import (
    BM25Retriever,
)

from retrieval.confidence import (
    extract_content_words,
    confidence_check,
)


# ============================================================
# Runtime initialization
# ============================================================

_initialized = False

navigator = None
bm25 = None

all_doc_names = []

llm_concept_by_doc = {}

total_pages = 0
total_docs = 0


def _load_runtime():
    """
    Load all lightweight query-time assets.

    Page text is NOT loaded into memory.
    """

    global _initialized
    global navigator
    global bm25
    global all_doc_names
    global llm_concept_by_doc
    global total_pages
    global total_docs

    if _initialized:
        return

    # --------------------------------------------------------
    # Download persisted assets from Databricks Volume
    # --------------------------------------------------------

    sync_persistence_assets()

    # --------------------------------------------------------
    # Delta metadata
    # --------------------------------------------------------

    metadata = get_metadata()

    total_pages = metadata[
        "total_pages"
    ]

    total_docs = metadata[
        "total_docs"
    ]

    all_doc_names = get_document_names()

    # --------------------------------------------------------
    # Load OKF concepts
    # --------------------------------------------------------

    with open(
        LOCAL_OKF_CONCEPTS_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        okf_concepts = json.load(f)

    # --------------------------------------------------------
    # Load persisted OKF BM25 index
    # --------------------------------------------------------

    with open(
        LOCAL_OKF_BM25_INDEX_FILE,
        "rb",
    ) as f:

        okf_bm25_index = pickle.load(f)

    # --------------------------------------------------------
    # OKF navigator
    # --------------------------------------------------------

    navigator = OKFNavigator(
        okf_concepts,
        okf_bm25_index,
    )

    # --------------------------------------------------------
    # Whoosh BM25 retriever
    # --------------------------------------------------------

    bm25 = BM25Retriever(
        LOCAL_WHOOSH_INDEX_DIR,
        total_pages,
        total_docs,
    )

    # --------------------------------------------------------
    # Load merged LLM concepts
    # --------------------------------------------------------

    llm_concept_by_doc = {}

    if LOCAL_LLM_BUNDLE_MANIFEST_FILE.exists():

        with open(
            LOCAL_LLM_BUNDLE_MANIFEST_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            manifest = json.load(f)

        for entry in manifest.get(
            "documents",
            [],
        ):

            merged_path = entry.get(
                "merged_path"
            )

            if not merged_path:
                continue

            file_name = (
                merged_path.split("/")[-1]
            )

            local_file = (
                LOCAL_LLM_BUNDLE_ROOT
                / file_name
            )

            if not local_file.exists():
                continue

            with open(
                local_file,
                "r",
                encoding="utf-8",
            ) as concept_file:

                merged_concept = json.load(
                    concept_file
                )

            doc_name = (
                merged_concept.get(
                    "source_file"
                )
                or entry.get("doc_name")
            )

            if doc_name:
                llm_concept_by_doc[
                    doc_name
                ] = merged_concept

    _initialized = True


# ============================================================
# Context building
# ============================================================

def _build_concept_context(
    candidate_docs,
    max_docs=3,
    max_tags=25,
    max_topics=12,
):
    """
    Build supplemental context from the merged
    LLM concept bundles.
    """

    parts = []

    seen = set()

    for doc_name in (
        candidate_docs or []
    ):

        if doc_name in seen:
            continue

        seen.add(doc_name)

        concept = (
            llm_concept_by_doc.get(
                doc_name
            )
        )

        if not concept:
            continue

        title = concept.get(
            "title",
            doc_name,
        )

        domain = concept.get(
            "domain",
            "Document Knowledge",
        )

        topic = concept.get(
            "topic",
            title,
        )

        tags = ", ".join(
            concept.get(
                "tags",
                [],
            )[:max_tags]
        )

        key_topics = "; ".join(
            concept.get(
                "key_topics",
                [],
            )[:max_topics]
        )

        parts.append(
            f"Document concept summary: "
            f"{doc_name}\n"
            f"Title: {title}\n"
            f"Domain: {domain}\n"
            f"Topic: {topic}\n"
            f"Key topics: {key_topics}\n"
            f"Tags: {tags}"
        )

        if len(parts) >= max_docs:
            break

    return "\n---\n".join(parts)


def _build_context(
    hits,
    page_texts,
    candidate_docs=None,
    max_chars=2000,
):
    """
    Build LLM context from concept bundles
    and retrieved page text.
    """

    parts = []

    concept_context = (
        _build_concept_context(
            candidate_docs
            or [
                hit["doc_name"]
                for hit in hits
            ]
        )
    )

    if concept_context:

        parts.append(
            "Merged concept bundle context\n"
            + concept_context
        )

    for hit in hits:

        text = page_texts.get(
            (
                hit["doc_name"],
                str(hit["page"]),
            ),
            "",
        )

        parts.append(
            f"Document: "
            f"{hit['doc_name']} | "
            f"Page: {hit['page']}\n"
            f"{text[:max_chars]}"
        )

    return "\n---\n".join(parts)


def _format_pages_referred(
    hits,
):
    if not hits:
        return []

    return [
        {
            "document":
                hit["doc_name"],
            "page":
                hit["page"],
            "score":
                hit["score"],
        }
        for hit in hits
    ]


# ============================================================
# Main query function
# ============================================================

def ask(
    question: str,
    top_k: int = 5,
) -> dict:
    """
    Main query-time RAG pipeline.

    Flow:

    1. Load persisted retrieval assets.
    2. Extract content words.
    3. Compute IDF from Delta.
    4. BM25 baseline retrieval.
    5. OKF routing.
    6. Candidate-document BM25 retrieval.
    7. Fetch only matching page text from Delta.
    8. Apply confidence gate.
    9. Call Databricks LLM only when relevant.
    10. Return answer + provenance.
    """

    if not question or not question.strip():

        return {
            "error":
                "Question cannot be empty."
        }

    _load_runtime()

    question = question.strip()

    # --------------------------------------------------------
    # Content words
    # --------------------------------------------------------

    content_words = (
        extract_content_words(
            question
        )
    )

    # --------------------------------------------------------
    # IDF
    # --------------------------------------------------------

    idfs = bm25.compute_idfs(
        content_words
    )

    # ========================================================
    # A. BM25 ONLY
    # ========================================================

    a_start = time.time()

    a_result = bm25.search(
        question,
        candidate_docs=None,
        top_k=top_k,
    )

    a_hits = a_result[
        "results"
    ]

    a_page_texts = (
        bm25.fetch_texts(
            a_hits
        )
    )

    a_top_score = (
        a_hits[0]["score"]
        if a_hits
        else 0
    )

    a_confident, a_gate_reason = (
        confidence_check(
            a_hits,
            content_words,
            a_top_score,
            a_page_texts,
            idfs,
        )
    )

    a_llm = {
        "answer": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }

    if a_confident:

        a_context = _build_context(
            a_hits,
            a_page_texts,
            candidate_docs=[
                hit["doc_name"]
                for hit in a_hits
            ],
        )

        a_llm = call_llm(
            question,
            a_context,
        )

    a_latency = (
        time.time()
        - a_start
    ) * 1000

    # ========================================================
    # B. OKF + BM25
    # ========================================================

    b_start = time.time()

    route = navigator.route_query(
        question
    )

    candidate_docs = [
        doc
        for doc in route[
            "candidate_docs"
        ]
        if doc in all_doc_names
    ]

    if candidate_docs:

        b_result = bm25.search(
            question,
            candidate_docs=candidate_docs,
            top_k=top_k,
        )

    else:

        b_result = bm25.search(
            question,
            candidate_docs=None,
            top_k=top_k,
        )

        candidate_docs = (
            all_doc_names
        )

    b_hits = b_result[
        "results"
    ]

    b_page_texts = (
        bm25.fetch_texts(
            b_hits
        )
    )

    b_top_score = (
        b_hits[0]["score"]
        if b_hits
        else 0
    )

    b_confident, b_gate_reason = (
        confidence_check(
            b_hits,
            content_words,
            b_top_score,
            b_page_texts,
            idfs,
        )
    )

    b_llm = {
        "answer": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }

    if b_confident:

        b_context = _build_context(
            b_hits,
            b_page_texts,
            candidate_docs=candidate_docs,
        )

        b_llm = call_llm(
            question,
            b_context,
        )

    b_latency = (
        time.time()
        - b_start
    ) * 1000

    # ========================================================
    # Token comparison
    # ========================================================

    token_diff = (
        a_llm["input_tokens"]
        -
        b_llm["input_tokens"]
    )

    savings_pct = (
        token_diff
        /
        a_llm["input_tokens"]
        * 100
        if a_llm["input_tokens"] > 0
        else 0
    )

    # ========================================================
    # Return MCP-friendly result
    # ========================================================

    return {
        "question": question,

        "answer": (
            b_llm["answer"]
            if b_confident
            else None
        ),

        "okf_bm25": {

            "answer":
                b_llm["answer"],

            "confident":
                b_confident,

            "confidence_reason":
                b_gate_reason,

            "candidate_docs":
                candidate_docs,

            "pages_referred":
                _format_pages_referred(
                    b_hits
                ),

            "tokens":
                b_llm["total_tokens"],

            "input_tokens":
                b_llm["input_tokens"],

            "output_tokens":
                b_llm["output_tokens"],

            "latency_ms":
                round(
                    b_latency,
                    2,
                ),

            "route":
                route,
        },

        "bm25_only": {

            "answer":
                a_llm["answer"],

            "confident":
                a_confident,

            "confidence_reason":
                a_gate_reason,

            "pages_referred":
                _format_pages_referred(
                    a_hits
                ),

            "tokens":
                a_llm["total_tokens"],

            "input_tokens":
                a_llm["input_tokens"],

            "output_tokens":
                a_llm["output_tokens"],

            "latency_ms":
                round(
                    a_latency,
                    2,
                ),
        },

        "token_savings":
            token_diff,

        "savings_pct":
            round(
                savings_pct,
                2,
            ),
    }


def ask_question(
    question: str,
) -> str:
    """
    MCP-facing tool.

    GitHub Copilot calls this tool with
    a natural-language question.
    """

    try:

        result = ask(
            question
        )

        return json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:

        return json.dumps(
            {
                "error":
                    type(e).__name__,
                "message":
                    str(e),
            },
            indent=2,
        )