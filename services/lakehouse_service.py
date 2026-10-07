from typing import Any

from databricks import sql

from config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    DATABRICKS_WAREHOUSE_ID,
    DELTA_TABLE,
)


def _get_connection():
    """
    Create a Databricks SQL connection.
    """

    hostname = (
        DATABRICKS_HOST
        .replace("https://", "")
        .replace("http://", "")
        .rstrip("/")
    )

    return sql.connect(
        server_hostname=hostname,
        http_path=(
            f"/sql/1.0/warehouses/"
            f"{DATABRICKS_WAREHOUSE_ID}"
        ),
        access_token=DATABRICKS_TOKEN,
    )


def execute_query(
    query: str,
) -> list[tuple]:
    """
    Execute SQL against Databricks SQL Warehouse.
    """

    connection = _get_connection()

    try:

        cursor = connection.cursor()

        try:

            cursor.execute(query)

            return cursor.fetchall()

        finally:

            cursor.close()

    finally:

        connection.close()


def get_metadata() -> dict[str, int]:
    """
    Get total page and document counts.

    Equivalent to Notebook 2 Cell 3.
    """

    query = f"""
        SELECT
            COUNT(*) AS total_pages,
            COUNT(DISTINCT doc_name) AS total_docs
        FROM {DELTA_TABLE}
    """

    rows = execute_query(query)

    if not rows:
        return {
            "total_pages": 0,
            "total_docs": 0,
        }

    row = rows[0]

    return {
        "total_pages": int(row[0]),
        "total_docs": int(row[1]),
    }


def get_document_names() -> list[str]:
    """
    Get distinct document names.

    Only document names are cached, not page text.
    """

    query = f"""
        SELECT DISTINCT doc_name
        FROM {DELTA_TABLE}
    """

    rows = execute_query(query)

    return [
        str(row[0])
        for row in rows
        if row[0] is not None
    ]


def fetch_page_texts(
    hits: list[dict[str, Any]],
) -> dict[tuple[str, str], str]:
    """
    Fetch only the page text required by the current query.

    Equivalent to BM25Retriever.fetch_texts()
    in Notebook 2.
    """

    if not hits:
        return {}

    conditions = []

    for hit in hits:

        doc_name = str(
            hit["doc_name"]
        ).replace("'", "''")

        page = int(hit["page"])

        conditions.append(
            "("
            f"doc_name = '{doc_name}' "
            f"AND page = {page}"
            ")"
        )

    where_clause = " OR ".join(
        conditions
    )

    query = f"""
        SELECT
            doc_name,
            page,
            text
        FROM {DELTA_TABLE}
        WHERE {where_clause}
    """

    rows = execute_query(query)

    return {
        (
            str(row[0]),
            str(row[1]),
        ): row[2] or ""
        for row in rows
    }


def compute_idfs(
    content_words: list[str],
    total_pages: int,
) -> dict[str, float]:
    """
    Compute IDF for query content words.

    Equivalent to Notebook 2's
    BM25Retriever.compute_idfs().
    """

    if not content_words:
        return {}

    parts = []

    for word in content_words:

        safe_word = (
            word
            .replace("'", "''")
        )

        parts.append(
            f"""
            SELECT
                '{safe_word}' AS term,
                COUNT(*) AS df
            FROM {DELTA_TABLE}
            WHERE LOWER(text)
                  LIKE '%{safe_word}%'
            """
        )

    query = " UNION ALL ".join(parts)

    rows = execute_query(query)

    result = {}

    import math

    for row in rows:

        term = str(row[0])
        df = int(row[1])

        result[term] = math.log(
            (total_pages + 1)
            /
            (df + 1)
        )

    return result