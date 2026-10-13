"""Command-line interface. Sensitive cURL input is read from a file or stdin."""
import argparse
from pathlib import Path
import sys
from .engine import DownloadError, MediaRequest, download, parse_curl


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download an authorized LMS media file. No login or DRM bypass.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="HTTPS media file URL")
    source.add_argument("--curl-file", help="Copy as cURL (bash) file; use - for stdin")
    parser.add_argument("--referer", help="Playback page origin or URL, if required")
    parser.add_argument("--header", action="append", default=[], help="Additional Name: value header (non-secret values recommended)")
    parser.add_argument("--output", "-o", required=True, help="Destination file")
    parser.add_argument("--timeout", type=float, default=30, help="Socket timeout in seconds")
    args = parser.parse_args(argv)
    try:
        if args.curl_file:
            text = sys.stdin.read(128001) if args.curl_file == "-" else Path(args.curl_file).read_text(encoding="utf-8")
            media = parse_curl(text)
        else:
            media = MediaRequest(args.url)
        headers = dict(media.headers)
        if args.referer:
            headers["referer"] = args.referer
        for header in args.header:
            name, sep, value = header.partition(":")
            if not sep:
                raise DownloadError("Expected --header 'Name: value'.")
            headers[name.strip().lower()] = value.strip()
        media = MediaRequest(media.url, headers)
        def progress(done, total):
            text = f"{done / 1048576:.1f} MiB"
            if total:
                text += f" / {total / 1048576:.1f} MiB ({done / total:.0%})"
            print("\r" + text, end="", file=sys.stderr, flush=True)
        result = download(media, args.output, progress, args.timeout)
        print(f"\nSaved: {result}", file=sys.stderr)
        return 0
    except (DownloadError, OSError, UnicodeError):
        # DownloadError contains sanitized messages; raw OS exceptions can include inputs.
        error = sys.exc_info()[1]
        print(f"\nError: {error if isinstance(error, DownloadError) else 'Unable to read input or write output.'}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCanceled. A partial .part file may remain.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
