import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request
from lms_downloader import DownloadError, MediaRequest, download, parse_curl
from lms_downloader.engine import _SameOriginRedirect
from lms_downloader.cli import main

URL = 'https://media.example.edu/course/video.mp4'

class Response(io.BytesIO):
    def __init__(self, content=b'video', status=200, headers=None):
        super().__init__(content)
        self.status = status
        self.headers = headers if headers is not None else {'Content-Type': 'video/mp4', 'Content-Length': str(len(content))}

class Tests(unittest.TestCase):
    def test_curl_headers_and_ranges(self):
        media = parse_curl(f"curl --url '{URL}' \\\n -H 'Range: bytes=100-200' -H 'If-Range: etag' -H 'Referer: https://lms.example.edu/' -H 'Cookie: session=sample' --compressed")
        self.assertEqual(media.url, URL)
        self.assertEqual(media.headers, {'referer': 'https://lms.example.edu/', 'cookie': 'session=sample'})
        self.assertNotIn('session', repr(media))
        self.assertNotIn('example.edu', repr(media))

    def test_flags_and_markdown_url(self):
        media = parse_curl(f'curl [{URL}]({URL}) --referer=https://lms.example.edu/ -A "Example UA" -r 1-2 -X GET')
        self.assertEqual(media.url, URL)
        self.assertEqual(media.headers['user-agent'], 'Example UA')
        self.assertNotIn('range', media.headers)

    def test_invalid_requests(self):
        for text in [f'curl {URL} ; echo bad', f'curl {URL} -X POST', f'curl {URL} --data abc', f'curl {URL} {URL}', 'curl -H', "curl 'broken", f'curl {URL} --cookie cookies.txt']:
            with self.subTest(text=text), self.assertRaises(DownloadError):
                parse_curl(text)
        for url in ['http://media.example.edu/v.mp4', 'https://user:pass@media.example.edu/v.mp4', 'https://media.example.edu:invalid/v.mp4']:
            with self.assertRaises(DownloadError):
                MediaRequest(url)
        with self.assertRaises(DownloadError):
            MediaRequest(URL, {'Cookie': 'x\r\ny'})

    def test_download_stream_and_progress(self):
        progress = []
        content = b'x' * (1024 * 1024 + 13)
        with tempfile.TemporaryDirectory() as folder, patch('lms_downloader.engine.build_opener') as opener:
            opener.return_value.open.return_value = Response(content)
            result = download(MediaRequest(URL), Path(folder)/'video.mp4', lambda n,t: progress.append((n,t)))
            self.assertEqual(result.read_bytes(), content)
            self.assertEqual(len(progress), 2)
            self.assertEqual(progress[-1], (len(content), len(content)))
            self.assertFalse(Path(str(result)+'.part').exists())
            with self.assertRaises(DownloadError):
                download(MediaRequest(URL), result)

    def test_partial_html_and_truncated(self):
        for response in [Response(status=206), Response(headers={'Content-Type':'text/html'}), Response(headers={'Content-Type':'video/mp4','Content-Length':'99'}), Response(b'')]:
            with tempfile.TemporaryDirectory() as folder, patch('lms_downloader.engine.build_opener') as opener:
                opener.return_value.open.return_value = response
                target = Path(folder)/'video.mp4'
                with self.assertRaises(DownloadError):
                    download(MediaRequest(URL), target)
                self.assertFalse(target.exists())

    def test_redirect_does_not_leak_credentials(self):
        handler = _SameOriginRedirect()
        request = Request(URL, headers={'Authorization':'sample'})
        with self.assertRaises(DownloadError):
            handler.redirect_request(request, None, 302, 'redirect', {}, 'https://other.example.edu/video.mp4')
        redirected = handler.redirect_request(request, None, 302, 'redirect', {}, 'https://media.example.edu/new.mp4')
        self.assertEqual(redirected.get_header('Authorization'), 'sample')

    def test_cli_error_no_secret_output(self):
        with patch('sys.stdin', io.StringIO(f'curl {URL} -H "Cookie: secret" --data invalid')), patch('sys.stderr', new_callable=io.StringIO) as stderr:
            self.assertEqual(main(['--curl-file','-','-o','video.mp4']), 1)
            self.assertNotIn('secret', stderr.getvalue())
            self.assertNotIn(URL, stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
