"""HTTP fetching for portfolio scraping.

Single Responsibility: Fetch content from URLs with proper headers/timeouts.
"""

import socket
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Protocol
from urllib.parse import urlparse

import httpx

from ...utils.logging import get_logger

logger = get_logger(__name__)

# Private IP ranges that should be blocked (SSRF protection)
BLOCKED_IP_PREFIXES = (
    "127.",  # Loopback
    "10.",  # Private Class A
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",  # Private Class B
    "192.168.",  # Private Class C
    "169.254.",  # Link-local
    "0.",  # Invalid
    "::1",  # IPv6 loopback
    "fe80:",  # IPv6 link-local
    "fc00:",  # IPv6 unique local
    "fd00:",  # IPv6 unique local
)


@dataclass
class FetchResult:
    """Result of an HTTP fetch."""

    url: str
    content: str
    status_code: int
    content_type: str


class ContentFetcher(Protocol):
    """Protocol for fetching URL content - enables dependency injection."""

    def fetch(self, url: str) -> FetchResult:
        """Fetch content from URL."""
        ...


class PortfolioFetcher:
    """Handles HTTP requests for portfolio scraping.

    Single responsibility: Fetch content from URLs with proper headers/timeouts.
    Implements context manager for proper resource cleanup.
    """

    DEFAULT_TIMEOUT = 30.0
    USER_AGENT = "FutureProof/1.0 (Career Intelligence System)"

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize fetcher with timeout configuration.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def __enter__(self) -> "PortfolioFetcher":
        """Enter context manager, create HTTP client."""
        self._client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            max_redirects=5,  # Limit redirects to prevent loops
            verify=True,  # Explicitly enable SSL verification
            headers={"User-Agent": self.USER_AGENT},
        )
        return self

    def __exit__(self, *args) -> None:
        """Exit context manager, close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe to fetch (SSRF protection).

        Args:
            url: URL to validate

        Returns:
            True if URL is safe, False otherwise
        """
        try:
            parsed = urlparse(url)

            # Only allow http/https schemes
            if parsed.scheme not in ("http", "https"):
                logger.warning("Blocked non-HTTP scheme: %s", parsed.scheme)
                return False

            hostname = parsed.hostname
            if not hostname:
                return False

            # Check if hostname is an IP address
            try:
                ip = ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    logger.warning("Blocked private IP: %s", hostname)
                    return False
            except ValueError:
                # Not an IP, resolve hostname
                try:
                    resolved_ip = socket.gethostbyname(hostname)
                    if resolved_ip.startswith(BLOCKED_IP_PREFIXES):
                        logger.warning(
                            "Blocked hostname resolving to private IP: %s -> %s",
                            hostname,
                            resolved_ip,
                        )
                        return False
                except socket.gaierror:
                    # DNS resolution failed, let httpx handle it
                    pass

            return True
        except Exception as e:
            logger.warning("URL validation error: %s", e)
            return False

    def fetch(self, url: str) -> FetchResult:
        """Fetch content from URL.

        Args:
            url: URL to fetch

        Returns:
            FetchResult with content and metadata

        Raises:
            RuntimeError: If fetcher not used as context manager
            ValueError: If URL fails SSRF protection checks
            httpx.HTTPError: On network/HTTP errors
        """
        if not self._client:
            raise RuntimeError("PortfolioFetcher must be used as context manager")

        # SSRF protection
        if not self._is_safe_url(url):
            raise ValueError(f"URL blocked by security policy: {url}")

        logger.debug("Fetching: %s", url)
        response = self._client.get(url)
        response.raise_for_status()

        logger.debug("Fetched %d bytes from %s", len(response.text), url)

        return FetchResult(
            url=url,
            content=response.text,
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
        )
