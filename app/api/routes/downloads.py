"""Downloads routes for Aura Companion installers."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["downloads"])

# Absolute path to the directory that holds installer binaries.
# Resolved at import time so comparisons are stable regardless of cwd.
DOWNLOADS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "ev-companion"
    / "companion"
    / "release"
).resolve()

# Explicit allow-list; anything not in this set is rejected.
_ALLOWED_FILES = frozenset(
    [
        "Aura-Companion-Portable-1.0.0.exe",
        "Aura-Companion-Setup-1.0.0.exe",
    ]
)


@router.get("/downloads/{filename}")
def download_file(filename: str) -> FileResponse:
    """Download an installer file.

    Args:
        filename: The name of the file to download.

    Returns:
        The file as a downloadable attachment.

    Raises:
        HTTPException 404: If the filename is not in the allow-list or does not exist.
        HTTPException 403: If the resolved path escapes the downloads directory
            (directory-traversal guard).
    """
    # Allow-list check — reject unknown filenames before touching the FS.
    # The allow-list makes the path-traversal check redundant since every entry
    # is a plain filename inside DOWNLOADS_DIR.  We keep the traversal guard
    # anyway as defense-in-depth for any future dynamic entries.
    if filename not in _ALLOWED_FILES:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = (DOWNLOADS_DIR / filename).resolve()

    if not str(file_path).startswith(str(DOWNLOADS_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")

    # Existence check.
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
