from openai import OpenAI

from config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    LLM_ENDPOINT,
)


def _llm_client() -> OpenAI:
    """
    Create an OpenAI-compatible client for the
    Databricks Model Serving endpoint.
    """

    return OpenAI(
        base_url=(
            f"{DATABRICKS_HOST.rstrip('/')}"
            "/serving-endpoints"
        ),
        api_key=DATABRICKS_TOKEN,
    )


def call_llm(
    question: str,
    context: str,
) -> dict:
    """
    Call Databricks-hosted Claude using only
    the supplied document context.
    """

    client = _llm_client()

    response = client.chat.completions.create(
        model=LLM_ENDPOINT,

        messages=[
            {
                "role": "system",
                "content": (
                    "You answer questions using only "
                    "the provided document context. "

                    "The context can include merged "
                    "concept-bundle summaries and raw "
                    "page excerpts. "

                    "Use the bundle summaries to "
                    "understand likely terms and topics, "
                    "but ground factual answers in the "
                    "cited document pages whenever possible. "

                    "Cite document name and page for "
                    "factual statements. "

                    "If context is insufficient, "
                    "say so clearly."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    "---\n"
                    f"Question: {question}\n"
                    "Answer:"
                ),
            },
        ],

        max_tokens=800,
    )

    usage = response.usage

    input_tokens = (
        usage.prompt_tokens
        if usage
        else 0
    )

    output_tokens = (
        usage.completion_tokens
        if usage
        else 0
    )

    return {
        "answer":
            response.choices[
                0
            ].message.content.strip(),

        "input_tokens":
            input_tokens,

        "output_tokens":
            output_tokens,

        "total_tokens":
            input_tokens
            + output_tokens,
    }   