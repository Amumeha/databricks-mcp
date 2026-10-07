import time

from whoosh.index import open_dir
from whoosh.qparser import (
    QueryParser,
    OrGroup,
)
from whoosh.query import (
    Or,
    Term as WhooshTerm,
)

from services.lakehouse_service import (
    fetch_page_texts,
    compute_idfs,
)


class BM25Retriever:
    """
    BM25 retriever using the persisted Whoosh index.

    Page text is NOT loaded into memory.

    Text is fetched from Delta only for the
    pages returned by the current search.
    """

    def __init__(
        self,
        index_dir,
        total_pages,
        total_docs,
    ):

        self.ix = open_dir(
            str(index_dir)
        )

        self.total_pages = total_pages

        self.total_docs = total_docs

    def search(
        self,
        query: str,
        candidate_docs=None,
        top_k: int = 5,
    ) -> dict:

        start_time = time.time()

        # ----------------------------------------------------
        # Candidate document filter
        # ----------------------------------------------------

        if candidate_docs:

            candidate_set = set(
                candidate_docs
            )

            filter_q = Or(
                [
                    WhooshTerm(
                        "doc_name",
                        doc,
                    )
                    for doc in candidate_set
                ]
            )

        else:

            filter_q = None

        results = []

        with self.ix.searcher() as searcher:

            parser = QueryParser(
                "text",
                self.ix.schema,
                group=OrGroup,
            )

            parsed_query = parser.parse(
                query
            )

            hits = searcher.search(
                parsed_query,
                filter=filter_q,
                limit=top_k,
            )

            for hit in hits:

                results.append(
                    {
                        "doc_name":
                            hit["doc_name"],

                        "page":
                            hit["page"],

                        "score":
                            hit.score,
                    }
                )

            if candidate_docs:

                # Keep the same behavior as Notebook 2
                pages_searched = (
                    searcher.doc_count()
                )

                docs_searched = len(
                    candidate_set
                )

            else:

                pages_searched = (
                    self.total_pages
                )

                docs_searched = (
                    self.total_docs
                )

        elapsed_ms = (
            time.time() - start_time
        ) * 1000

        return {
            "results":
                results,

            "docs_searched":
                docs_searched,

            "pages_searched":
                pages_searched,

            "latency_ms":
                round(
                    elapsed_ms,
                    2,
                ),
        }

    def fetch_texts(
        self,
        hits: list[dict],
    ) -> dict:

        return fetch_page_texts(
            hits
        )

    def compute_idfs(
        self,
        content_words: list[str],
    ) -> dict:

        return compute_idfs(
            content_words,
            self.total_pages,
        )