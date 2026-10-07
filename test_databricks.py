import os
import requests
import truststore

truststore.inject_into_ssl()

from databricks.sdk import WorkspaceClient


DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")


if not DATABRICKS_HOST:
    raise RuntimeError(
        "DATABRICKS_HOST environment variable is not set."
    )


print("=" * 60)
print("Testing Databricks connection")
print("=" * 60)

print(f"Host: {DATABRICKS_HOST}")


# ------------------------------------------------------------
# Test HTTPS connectivity
# ------------------------------------------------------------

try:
    headers = {}

    if DATABRICKS_TOKEN:
        headers["Authorization"] = f"Bearer {DATABRICKS_TOKEN}"

    response = requests.get(
        DATABRICKS_HOST,
        headers=headers,
        timeout=20,
    )

    print(
        f"HTTPS connectivity: SUCCESS "
        f"(HTTP {response.status_code})"
    )

except Exception as e:
    print(
        f"HTTPS connectivity: FAILED - "
        f"{type(e).__name__}: {e}"
    )


# ------------------------------------------------------------
# Test Databricks SDK
# ------------------------------------------------------------

try:

    if DATABRICKS_TOKEN:

        client = WorkspaceClient(
            host=DATABRICKS_HOST,
            token=DATABRICKS_TOKEN,
        )

    else:

        client = WorkspaceClient(
            host=DATABRICKS_HOST,
        )

    current_user = client.current_user.me()

    print("Databricks SDK: SUCCESS")
    print(f"Current user: {current_user.user_name}")

except Exception as e:

    print(
        f"Databricks SDK: FAILED - "
        f"{type(e).__name__}: {e}"
    )


print("=" * 60)