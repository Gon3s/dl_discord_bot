class DebridError(Exception):
    """Base exception for debrid provider API errors."""


class DebridAPIError(DebridError):
    """Raised when a debrid provider API returns an error status."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class DebridHTTPError(DebridError):
    """Raised when the HTTP request to a debrid provider fails."""

    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP error {status}")
        self.status = status


class AllDebridError(DebridError):
    """Base exception for AllDebrid API errors."""


class AllDebridAPIError(DebridAPIError, AllDebridError):
    """Raised when the AllDebrid API returns an error status."""


class AllDebridHTTPError(DebridHTTPError, AllDebridError):
    """Raised when the HTTP request to AllDebrid fails."""


class DownloadError(Exception):
    """Raised when a download fails."""


class DownloadNotFoundError(DownloadError):
    """Raised when a download ID does not exist in the database."""

    def __init__(self, download_id: str) -> None:
        super().__init__(f"Download not found: {download_id}")
        self.download_id = download_id
