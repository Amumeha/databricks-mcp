import truststore
import os
truststore.inject_into_ssl()

from mcp.server.fastmcp import FastMCP

from tools.volume_tools import (
    list_files,
)

from tools.ask_tool import (
    ask_question,
)


mcp = FastMCP(
    "databricks-lakehouse-mcp"
)


@mcp.tool()
def list_databricks_files() -> str:
    """
    List files available in the configured
    Databricks Volume.
    """

    return list_files()


@mcp.tool()
def ask(
    question: str,
) -> str:
    """
    Ask a natural-language question against
    the Databricks document knowledge base.

    The server performs:
    OKF routing → BM25 retrieval →
    Delta page retrieval → confidence gate →
    Databricks-hosted LLM.
    """

    return ask_question(
        question
    )


#if __name__ == "__main__":

#    mcp.run(
#        transport="streamable-http"
#   )

if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.getenv("PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port
    )