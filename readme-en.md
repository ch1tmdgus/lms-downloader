<a href="README.md"><kbd>한국어 Readme</kbd></a>

# LMS Video Downloader

A provider-neutral Python engine and CLI for downloading **authorized LMS media files** from a direct HTTPS URL or a browser's **Copy as cURL (bash)** request.

No website UI, institution branding, fixed media hosts or hardcoded Referer. No login automation, access-control bypass or DRM decryption.

## Install

Python 3.10 or newer. The engine uses only the Python standard library.

```sh
python -m pip install .
```

Or run directly from the checkout:

```sh
python -m lms_downloader --help
```

## Download from a URL

```sh
lms-download \
  --url 'https://media.example.edu/course/video.mp4' \
  --referer 'https://lms.example.edu/' \
  --output lecture.mp4
```

Referer is optional and must come from the actual playback request; no provider-specific default is supplied.

## Download from a browser request

1. Sign in to your LMS and play a video you are allowed to save.
2. Open Developer Tools → Network and select the successful **actual media file request**, not an intro or loading video.
3. Right-click → Copy → Copy as cURL (bash).
4. Paste the command into a local `request.curl` file.
5. Run:

```sh
lms-download --curl-file request.curl --output lecture.mp4
```

Or paste the command into stdin and finish with EOF (Ctrl+D on macOS/Linux):

```sh
lms-download --curl-file - --output lecture.mp4
```

Copied requests may contain cookies, signed URLs or authorization headers. Keep them on your machine and out of issues, logs and commits. File/stdin input keeps the full cURL command out of process arguments. URL or --header arguments can still appear in shell history and process listings, so use cURL stdin for sensitive requests.

## Python API

```python
from lms_downloader import MediaRequest, download, parse_curl

request = MediaRequest(
    'https://media.example.edu/course/video.mp4',
    {'Referer': 'https://lms.example.edu/'},
)
download(request, 'lecture.mp4')

# Or: request = parse_curl(copied_curl_text)
```

`download(request, output, progress=None, timeout=30)` reports `(bytes_received, total_bytes_or_none)` through an optional callback. Timeout applies to socket operations, not the overall download duration. Successful calls return a pathlib.Path; failures raise DownloadError with a sanitized message.

## Behavior

- Parse a single GET cURL command as data using shlex; never execute it in a shell.
- Preserve supplied Referer, cookies and other request headers.
- Drop Range, If-Range and conditional cache headers to request the complete file.
- Reject partial responses, HTML login pages, empty downloads and length mismatches.
- Stream in 1 MiB chunks into `OUTPUT.part`; publish without replacing an existing output.
- Follow same-origin redirects only; block cross-origin redirects to avoid forwarding authentication.
- Hide request URLs and headers from the request object's repr and normal error messages.

## Limitations

Direct media files such as MP4/WebM only. HLS/DASH manifests, segment assembly, browser automation, DRM, resumable downloads, batch downloads and server endpoints are outside this version's scope. Expired sessions may require copying a fresh browser request. Failed `.part` files are retained; choose a new filename or remove the partial file before retrying. Final publication uses a hard link; filesystems without hard-link support are unsupported. Files remain in `.part` if publication fails.

This is a local CLI/library. Before embedding it in a network service, add authentication, destination allowlists, SSRF protection and resource limits for untrusted URLs.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests cover parsing, header filtering, redaction, streaming, progress, partial/truncated/HTML response rejection, redirects and CLI errors. Tests use mocked responses, not real LMS credentials. Compatibility with every LMS provider is not claimed.

## License

[MIT License](LICENSE)

## Conditions of use and disclaimer

Videos and other media may be downloaded only when the rights holder or an authorized distributor **permits both downloading and possession** of that content. Being able to play a video in an LMS does not, by itself, grant permission to download, possess, copy or redistribute it. Before downloading, users must review applicable laws, service terms and institutional rules, and obtain any required permission.

Users are responsible for deciding whether and how to use this script. To the extent permitted by applicable law, the developers and distributors of this project accept no responsibility for damages, legal disputes, disciplinary action or other adverse consequences arising from its use or misuse. This project does not grant rights to any content or guarantee that a download is lawful.
