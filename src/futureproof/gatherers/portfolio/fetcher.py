"""HTTP fetching for portfolio scraping.

Single Responsibility: Fetch content from URLs with proper headers/timeouts.
"""

import contextlib
import socket
import threading
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from urllib.parse import urljoin, urlparse

import httpx

from ...utils.logging import get_logger

logger = get_logger(__name__)

# CGNAT (RFC 6598) — not covered by Python's is_private
_CGNAT_RANGE = ip_network("100.64.0.0/10")

_dns_lock = threading.Lock()

_MAX_REDIRECTS = 5


@contextlib.contextmanager
def _pinned_dns(hostname: str, addrinfo: list[tuple]):
    """Pin DNS for hostname to pre-validated results during fetch.

    Prevents DNS rebinding (TOCTOU) by ensuring httpx connects to the
    same addresses that passed SSRF validation, not a fresh resolution
    that an attacker could point at a private IP.

    Thread-safe: acquires a lock before monkey-patching socket.getaddrinfo.
    """
    orig = socket.getaddrinfo

    def _getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host != hostname:
            return orig(host, port, family, type, proto, flags)
        int_port = port if isinstance(port, int) else 0
        results = [
            (fam, typ, pr, cn, (sa[0], int_port, *sa[2:]))
            for fam, typ, pr, cn, sa in addrinfo
            if (not family or fam == family) and (not type or typ == type)
        ]
        return results or orig(host, port, family, type, proto, flags)

    with _dns_lock:
        socket.getaddrinfo = _getaddrinfo
        try:
            yield
        finally:
            socket.getaddrinfo = orig


@dataclass
class FetchResult:
    """Result of an HTTP fetch."""

    url: str
    content: str


def _is_blocked_ip(addr_str: str) -> bool:
    """Check if an IP address is private or in CGNAT range."""
    addr = ip_address(addr_str)
    return addr.is_private or addr in _CGNAT_RANGE


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
            follow_redirects=False,  # Manual redirect handling for SSRF safety
            verify=True,
            headers={"User-Agent": self.USER_AGENT},
        )
        return self

    def __exit__(self, *args) -> None:
        """Exit context manager, close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def _validate_url(self, url: str) -> list[tuple] | None:
        """Validate URL is safe to fetch (SSRF protection).

        Checks scheme and resolves ALL IPs (IPv4 + IPv6) via getaddrinfo,
        blocking any that fall in private or CGNAT ranges. Returns resolved
        addrinfo for DNS pinning (prevents TOCTOU / DNS rebinding).

        Args:
            url: URL to validate

        Returns:
            Resolved addrinfo list for hostname URLs (used to pin DNS),
            or None for literal-IP URLs (no pinning needed).

        Raises:
            ValueError: If URL is unsafe (private IP, bad scheme, etc.)
        """
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Blocked non-HTTP scheme: {parsed.scheme}")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("URL has no hostname")

        # Check if hostname is a literal IP address
        try:
            if _is_blocked_ip(hostname):
                raise ValueError(f"Blocked private/CGNAT IP: {hostname}")
            return None  # Public literal IP — no DNS to pin
        except ValueError as exc:
            if "Blocked" in str(exc):
                raise
            # Not a literal IP — resolve DNS below

        # Resolve hostname and check ALL addresses (IPv4 + IPv6)
        try:
            addrinfo = socket.getaddrinfo(
                hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM,
            )
        except socket.gaierror:
            raise ValueError(f"DNS resolution failed for {hostname}")

        for _family, _type, _proto, _canonname, sockaddr in addrinfo:
            addr = str(sockaddr[0])
            if _is_blocked_ip(addr):
                raise ValueError(
                    f"Blocked hostname resolving to private/CGNAT IP: "
                    f"{hostname} -> {addr}"
                )

        return addrinfo

    def _get_with_pinning(self, url: str, addrinfo: list[tuple] | None) -> httpx.Response:
        """Send GET request with optional DNS pinning."""
        assert self._client is not None
        if addrinfo:
            hostname = urlparse(url).hostname or ""
            with _pinned_dns(hostname, addrinfo):
                return self._client.get(url)
        return self._client.get(url)

    def fetch(self, url: str) -> FetchResult:
        """Fetch content from URL with per-hop SSRF validation.

        Each redirect is re-validated against SSRF rules before following,
        preventing attackers from using open redirects to reach internal IPs.

        Args:
            url: URL to fetch

        Returns:
            FetchResult with content and metadata

        Raises:
            RuntimeError: If fetcher not used as context manager
            ValueError: If URL fails SSRF protection checks or too many redirects
            httpx.HTTPError: On network/HTTP errors
        """
        if not self._client:
            raise RuntimeError("PortfolioFetcher must be used as context manager")

        # Prepend https:// if no scheme provided
        if not urlparse(url).scheme:
            url = f"https://{url}"

        for _ in range(_MAX_REDIRECTS):
            addrinfo = self._validate_url(url)

            logger.debug("Fetching: %s", url)
            response = self._get_with_pinning(url, addrinfo)

            if response.is_redirect:
                location = response.headers.get("location", "")
                if not location:
                    raise ValueError("Redirect with no Location header")
                url = urljoin(url, location)
                continue

            response.raise_for_status()

            logger.debug("Fetched %d bytes from %s", len(response.text), url)
            return FetchResult(url=url, content=response.text)

        raise ValueError(f"Too many redirects (>{_MAX_REDIRECTS})")
