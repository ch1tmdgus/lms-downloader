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

## 한국어 사용 안내

학교·서비스별 설정이 없는 범용 LMS 영상 다운로드 엔진입니다. 웹사이트와 크롬 확장 프로그램 UI는 포함하지 않습니다. 브라우저에서 로그인한 뒤 실제 영상 요청을 **Copy as cURL (bash)**로 복사하고, `request.curl`에 저장해 위 명령으로 다운로드합니다. 직접 영상 URL을 입력할 수도 있으며 Referer가 필요한 경우 직접 지정합니다. 인증 정보는 GitHub에 올리지 마세요.

## License

MIT. Use only for content you are authorized to access and save.
