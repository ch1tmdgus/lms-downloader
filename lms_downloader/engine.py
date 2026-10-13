"""Parse a browser cURL request and stream a complete media file to disk.

No shell execution, institution-specific headers, login automation or DRM bypass.
"""
from dataclasses import dataclass, field
from http.client import HTTPException
from pathlib import Path
import re
import os
import shlex
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class DownloadError(ValueError):
    """A sanitized, user-facing parse, network or file error."""


_DROP = {"range", "if-range", "if-none-match", "if-modified-since", "host",
         "content-length", "connection", "transfer-encoding", "accept-encoding"}


def _url(value: str) -> str:
    match = re.fullmatch(r"\[([^\]]+)\]\([^)]*\)", value.strip())
    value = match[1] if match else value.strip()
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise DownloadError("Invalid media URL.") from None
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.fragment or any(c.isspace() for c in value)):
        raise DownloadError("Use an HTTPS media URL without embedded credentials or a fragment.")
    return value


@dataclass(repr=False)
class MediaRequest:
    url: str
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.url = _url(self.url)
        cleaned = {}
        for name, value in self.headers.items():
            key = name.strip().lower()
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9a-z-]+", key) or any(c in value for c in "\r\n\0"):
                raise DownloadError("Invalid HTTP header.")
            if key not in _DROP:
                cleaned[key] = value.strip()
        self.headers = cleaned

    def __repr__(self):
        return "MediaRequest(url=<redacted>, headers=<redacted>)"


def parse_curl(command: str) -> MediaRequest:
    """Parse Chrome's Copy as cURL (bash) without executing any commands."""
    if len(command) > 128_000:
        raise DownloadError("cURL input is too large.")
    try:
        tokens = shlex.split(command.replace("\\\r\n", "").replace("\\\n", ""))
    except ValueError:
        raise DownloadError("Unclosed quotation mark in cURL input.") from None
    if not tokens or tokens[0] != "curl":
        raise DownloadError("Expected a Copy as cURL (bash) command.")
    url, headers = None, {}
    no_value = {"--compressed", "--location", "-L", "--silent", "-s", "--show-error", "-S", "--fail", "-f", "--globoff", "-g"}
    values = {"--url", "-H", "--header", "--referer", "-e", "--user-agent", "-A", "--cookie", "-b", "--range", "-r", "--request", "-X"}
    i = 1
    while i < len(tokens):
        token = tokens[i]
        if token in no_value:
            i += 1
            continue
        option, equal, attached = token.partition("=")
        if option in values:
            if equal:
                value = attached
            else:
                i += 1
                if i >= len(tokens):
                    raise DownloadError("Missing cURL option value.")
                value = tokens[i]
            if option == "--url":
                if url is not None:
                    raise DownloadError("Only one media URL is supported.")
                url = value
            elif option in {"-H", "--header"}:
                name, sep, content = value.partition(":")
                if not sep:
                    raise DownloadError("Expected a header in Name: value format.")
                headers[name.strip().lower()] = content.strip()
            elif option in {"--referer", "-e"}:
                headers["referer"] = value
            elif option in {"--user-agent", "-A"}:
                headers["user-agent"] = value
            elif option in {"--cookie", "-b"}:
                if "=" not in value:
                    raise DownloadError("Cookie files are not supported; use the browser's Cookie header.")
                headers["cookie"] = value
            elif option in {"--request", "-X"} and value.upper() != "GET":
                raise DownloadError("Only GET media requests are supported.")
            # Explicit cURL ranges are intentionally ignored for complete downloads.
        elif token.startswith("https://") or token.startswith("[https://"):
            if url is not None:
                raise DownloadError("Only one media URL is supported.")
            url = token
        else:
            raise DownloadError("Unsupported cURL option or extra command. Copy only the GET media request.")
        i += 1
    if url is None:
        raise DownloadError("No media URL found in cURL input.")
    return MediaRequest(url, headers)


class _SameOriginRedirect(HTTPRedirectHandler):
    """Never forward authentication headers to another origin."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urlsplit(req.full_url), urlsplit(newurl)
        if (new.scheme, new.hostname, new.port or 443) != (old.scheme, old.hostname, old.port or 443):
            raise DownloadError("Cross-origin redirect blocked. Copy the final media request from the browser.")
        _url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(media: MediaRequest, output: str | Path,
             progress: Callable[[int, int | None], None] | None = None,
             timeout: float = 30) -> Path:
    """Stream a complete MP4/WebM/media response in 1 MiB chunks.

    Write to OUTPUT.part and rename on success. Existing files are never overwritten.
    Failed partial downloads remain on disk for inspection; resuming is not implemented.
    """
    target = Path(output)
    part = target.with_name(target.name + ".part")
    if target.exists() or part.exists():
        raise DownloadError("Output or .part file already exists. Choose another filename.")
    if timeout <= 0:
        raise DownloadError("Timeout must be positive.")
    opener = build_opener(_SameOriginRedirect())
    request = Request(media.url, headers=media.headers, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            if response.status != 200 or response.headers.get("Content-Range"):
                raise DownloadError("Server returned a partial response; refusing to save an incomplete video.")
            mime = response.headers.get("Content-Type", "").split(";", 1)[0].lower().strip()
            if not (mime.startswith("video/") or mime == "application/octet-stream"):
                raise DownloadError("Response is not a media file. HTML login pages and streaming manifests are unsupported.")
            length = response.headers.get("Content-Length")
            try:
                total = int(length) if length is not None else None
                if total is not None and total < 0:
                    raise ValueError
            except ValueError:
                raise DownloadError("Invalid response length.") from None
            received = 0
            with part.open("xb") as stream:
                while chunk := response.read(1024 * 1024):
                    stream.write(chunk)
                    received += len(chunk)
                    if progress:
                        progress(received, total)
            if not received or (total is not None and total != received):
                raise DownloadError("Download was incomplete or empty. The .part file was retained.")
            # Hard-link publication is atomic and refuses to replace an existing output.
            os.link(part, target)
            part.unlink()
            return target
    except DownloadError:
        raise
    except HTTPError as error:
        raise DownloadError(f"Server returned HTTP {error.code}. Copy a fresh authorized browser request.") from None
    except (URLError, TimeoutError, OSError, HTTPException):
        raise DownloadError("Network or file operation failed. A partial .part file may remain.") from None
