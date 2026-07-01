"""Downloads routes for Aura Companion installers."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["downloads"])

# Define the downloads directory - adjust path as needed for production
DOWNLOADS_DIR = Path(__file__).parent.parent.parent.parent / "ev-companion" / "companion" / "release"


@router.get("/downloads/{filename}")
def download_file(filename: str):
    """Download an installer file.

    Args:
        filename: The name of the file to download (e.g., Aura-Companion-Portable-1.0.0.exe)

    Returns:
        The file as a downloadable attachment.

    Raises:
        HTTPException: If the file is not found or the filename is invalid.
    """
    # Validate filename to prevent directory traversal attacks
    allowed_files = [
        "Aura-Companion-Portable-1.0.0.exe",
        "Aura-Companion-Setup-1.0.0.exe",
    ]

    if filename not in allowed_files:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = DOWNLOADS_DIR / filename

    # Verify the file exists
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    # Verify the file is within the downloads directory (security check)
    if not str(file_path.resolve()).startswith(str(DOWNLOADS_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
