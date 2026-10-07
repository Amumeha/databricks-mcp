from pathlib import Path

from config import (
    VOLUME_PATH,
    PERSIST_PATH,
    LOCAL_PERSIST_PATH,
    workspace_client,
)


def list_files() -> str:
    """
    List files from the configured Databricks Volume.
    """

    try:

        files = workspace_client.files.list_directory_contents(
            VOLUME_PATH
        )

        file_names = []

        for file in files:

            if file.name:
                file_names.append(file.name)

        if not file_names:
            return "No files found."

        return "\n".join(file_names)

    except Exception as e:

        return (
            "Error listing Databricks Volume files: "
            f"{type(e).__name__}: {e}"
        )


def download_volume_file(
    remote_path: str,
    local_path: Path,
) -> None:
    """
    Download one file from Databricks Volume.
    """

    local_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    response = workspace_client.files.download(
        remote_path
    )

    contents = response.contents

    with open(local_path, "wb") as f:

        f.write(contents.read())


def sync_file(
    remote_path: str,
    local_path: Path,
) -> None:
    """
    Download a Databricks Volume file into local cache.
    """

    if local_path.exists():
        return

    download_volume_file(
        remote_path,
        local_path,
    )


def sync_persistence_assets() -> None:
    """
    Download the persisted query-time retrieval assets
    created by Notebook 1.

    The assets remain owned by Databricks.
    Local files are only a runtime cache for the MCP server.
    """

    # --------------------------------------------------------
    # OKF concepts
    # --------------------------------------------------------

    sync_file(
        f"{PERSIST_PATH}/okf_concepts.json",
        LOCAL_PERSIST_PATH / "okf_concepts.json",
    )

    # --------------------------------------------------------
    # OKF BM25 index
    # --------------------------------------------------------

    sync_file(
        f"{PERSIST_PATH}/okf_bm25_index.pkl",
        LOCAL_PERSIST_PATH / "okf_bm25_index.pkl",
    )

    # --------------------------------------------------------
    # Whoosh index
    # --------------------------------------------------------

    remote_whoosh = f"{PERSIST_PATH}/whoosh_index"

    whoosh_files = (
        workspace_client.files.list_directory_contents(
            remote_whoosh
        )
    )

    for item in whoosh_files:

        if not item.path:
            continue

        file_name = item.path.split("/")[-1]

        local_file = (
            LOCAL_PERSIST_PATH
            / "whoosh_index"
            / file_name
        )

        sync_file(
            item.path,
            local_file,
        )

    # --------------------------------------------------------
    # LLM concept bundle manifest
    # --------------------------------------------------------

    manifest_remote = (
        f"{PERSIST_PATH}/llm_concepts/"
        "llm-concept-manifest.json"
    )

    manifest_local = (
        LOCAL_PERSIST_PATH
        / "llm_concepts"
        / "llm-concept-manifest.json"
    )

    sync_file(
        manifest_remote,
        manifest_local,
    )

    # --------------------------------------------------------
    # LLM merged concept files
    # --------------------------------------------------------

    import json

    with open(
        manifest_local,
        "r",
        encoding="utf-8",
    ) as f:

        manifest = json.load(f)

    for entry in manifest.get("documents", []):

        merged_path = entry.get("merged_path")

        if not merged_path:
            continue

        file_name = merged_path.split("/")[-1]

        local_file = (
            LOCAL_PERSIST_PATH
            / "llm_concepts"
            / file_name
        )

        sync_file(
            merged_path,
            local_file,
        )