import os
from pathlib import Path

from dotenv import load_dotenv
import truststore

load_dotenv()

# Use Windows certificate store for Databricks connections
truststore.inject_into_ssl()

from databricks.sdk import WorkspaceClient


# ============================================================
# Databricks authentication
# ============================================================

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")

if not DATABRICKS_HOST:
    raise RuntimeError(
        "DATABRICKS_HOST environment variable is not set."
    )

if not DATABRICKS_WAREHOUSE_ID:
    raise RuntimeError(
        "DATABRICKS_WAREHOUSE_ID environment variable is not set."
    )


if DATABRICKS_TOKEN:
    workspace_client = WorkspaceClient(
        host=DATABRICKS_HOST,
        token=DATABRICKS_TOKEN,
    )
else:
    workspace_client = WorkspaceClient(
        host=DATABRICKS_HOST,
    )


# ============================================================
# Databricks Volume / Lakehouse configuration
# ============================================================

# IMPORTANT:
# Change this to the Volume where Notebook 1 persists its assets.
#
# Example from Notebook 2:
# /Volumes/team_iipa_prod/retailer_compensation_ddp_dev/test_doc

VOLUME_PATH = os.getenv(
    "DATABRICKS_VOLUME_PATH",
    "/Volumes/team_iipa_prod/retailer_compensation_ddp_dev/test_doc",
)

PERSIST_PATH = f"{VOLUME_PATH}/persistence"


# Delta table containing page-level text
DELTA_TABLE = os.getenv(
    "DATABRICKS_DELTA_TABLE",
    "team_iipa_prod.retailer_compensation_ddp_dev.okf_bundle_auto",
)


# ============================================================
# Persisted retrieval assets
# ============================================================

OKF_CONCEPTS_FILE = f"{PERSIST_PATH}/okf_concepts.json"

OKF_BM25_INDEX_FILE = f"{PERSIST_PATH}/okf_bm25_index.pkl"

WHOOSH_INDEX_DIR = f"{PERSIST_PATH}/whoosh_index"

LLM_BUNDLE_ROOT = f"{PERSIST_PATH}/llm_concepts"

LLM_BUNDLE_MANIFEST_FILE = (
    f"{LLM_BUNDLE_ROOT}/llm-concept-manifest.json"
)


# ============================================================
# Databricks-hosted LLM
# ============================================================

LLM_ENDPOINT = os.getenv(
    "LLM_ENDPOINT",
    "databricks-qwen3-next-80b-a3b-instruct",
)


# ============================================================
# Local cache
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

CACHE_DIR = DATA_DIR / "cache"

CACHE_DIR.mkdir(parents=True, exist_ok=True)


LOCAL_PERSIST_PATH = CACHE_DIR / "persistence"

LOCAL_PERSIST_PATH.mkdir(parents=True, exist_ok=True)

LOCAL_OKF_CONCEPTS_FILE = (
    LOCAL_PERSIST_PATH / "okf_concepts.json"
)

LOCAL_OKF_BM25_INDEX_FILE = (
    LOCAL_PERSIST_PATH / "okf_bm25_index.pkl"
)

LOCAL_WHOOSH_INDEX_DIR = (
    LOCAL_PERSIST_PATH / "whoosh_index"
)

LOCAL_LLM_BUNDLE_ROOT = (
    LOCAL_PERSIST_PATH / "llm_concepts"
)

LOCAL_LLM_BUNDLE_MANIFEST_FILE = (
    LOCAL_LLM_BUNDLE_ROOT / "llm-concept-manifest.json"
)