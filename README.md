<a href="readme-en.md"><kbd>English Readme</kbd></a>

# LMS Video Downloader

LMS에서 **다운로드 및 소지가 허용된 영상·미디어 파일**을 저장하는 범용 Python 다운로드 엔진과 CLI입니다. 직접 HTTPS 영상 주소 또는 브라우저의 **Copy as cURL (bash)** 요청을 입력받습니다.

특정 학교나 서비스의 주소·Referer를 하드코딩하지 않습니다. 웹사이트 UI나 크롬 확장 프로그램은 포함하지 않으며, 로그인 자동화·접근 제한 우회·DRM 복호화 기능을 제공하지 않습니다.

## 설치

Python 3.10 이상이 필요합니다. 다운로드 엔진은 Python 표준 라이브러리만 사용합니다.

저장소를 내려받은 뒤 해당 폴더에서 실행하세요.

```sh
python -m pip install .
```

설치 없이 저장소 폴더에서 직접 실행할 수도 있습니다.

```sh
python -m lms_downloader --help
```

## 영상 주소로 다운로드

```sh
lms-download \
  --url 'https://media.example.edu/course/video.mp4' \
  --referer 'https://lms.example.edu/' \
  --output lecture.mp4
```

`--referer`는 필요한 경우에만 지정합니다. 실제 재생 요청에서 확인한 값을 사용해야 하며, 특정 서비스의 기본값은 제공하지 않습니다. 예시에 사용된 주소는 설명용입니다.

## 브라우저의 cURL 요청으로 다운로드

1. LMS에 로그인하고 저장이 허용된 영상을 재생합니다.
2. 개발자 도구 → **Network**에서 정상 응답을 받은 **본 영상 파일 요청**을 선택합니다. 도입 영상이나 로딩 영상을 선택하지 않도록 확인하세요.
3. 요청을 우클릭하고 **Copy → Copy as cURL (bash)**를 선택합니다.
4. 복사한 명령을 로컬 `request.curl` 파일에 붙여 넣습니다.
5. 다음 명령을 실행합니다.

```sh
lms-download --curl-file request.curl --output lecture.mp4
```

파일 대신 표준 입력으로 전달할 수도 있습니다. 아래 명령 실행 후 cURL을 붙여 넣고 macOS/Linux에서는 `Ctrl+D`로 입력을 마칩니다.

```sh
lms-download --curl-file - --output lecture.mp4
```

복사한 요청에는 쿠키·인증 헤더·서명된 URL이 포함될 수 있습니다. 본인 컴퓨터에만 보관하고 GitHub 이슈·로그·커밋에 올리지 마세요. 파일이나 표준 입력을 사용하면 전체 cURL이 프로세스 실행 인자에 노출되는 것을 피할 수 있습니다. `--url`과 `--header`에 직접 넣은 값은 셸 기록과 프로세스 목록에 남을 수 있으므로, 민감한 요청에는 표준 입력을 권장합니다.

## Python API

```python
from lms_downloader import MediaRequest, download, parse_curl

request = MediaRequest(
    'https://media.example.edu/course/video.mp4',
    {'Referer': 'https://lms.example.edu/'},
)
download(request, 'lecture.mp4')

# 복사한 cURL 문자열로 요청을 만들 수도 있습니다.
# request = parse_curl(copied_curl_text)
```

`download(request, output, progress=None, timeout=30)`의 선택적 콜백은 `(받은 바이트 수, 전체 바이트 수 또는 None)`을 전달받습니다. `timeout`은 전체 다운로드 시간이 아닌 소켓 작업의 제한 시간입니다. 성공하면 `pathlib.Path`를 반환하고, 실패하면 요청의 민감한 정보를 제외한 메시지를 담은 `DownloadError`를 발생시킵니다.

## 동작 방식

- `shlex`로 단일 GET cURL 요청을 데이터로 분석하며, 셸에서 실행하지 않습니다.
- 사용자가 제공한 Referer·쿠키 등의 요청 헤더를 전달합니다.
- 전체 파일을 요청하도록 Range·If-Range·조건부 캐시 헤더를 제거합니다.
- 부분 응답·HTML 로그인 페이지·빈 파일·길이가 맞지 않는 응답은 저장 완료로 처리하지 않습니다.
- 1MiB 단위로 `출력파일.part`에 기록하고, 완료된 파일을 기존 파일을 덮어쓰지 않는 방식으로 생성합니다.
- 같은 출처의 리디렉션만 허용하며, 다른 출처로 인증 정보가 전달되지 않도록 차단합니다.
- 요청 객체의 `repr`과 일반 오류 메시지에서 영상 URL과 요청 헤더를 숨깁니다.

## 지원 범위와 제한

MP4·WebM 등 직접 내려받을 수 있는 미디어 파일을 지원합니다. HLS/DASH 재생 목록·분할 영상 병합·브라우저 자동화·DRM·이어받기·일괄 다운로드·서버 API는 현재 버전의 지원 범위에 포함되지 않습니다.

로그인 세션이 만료됐다면 브라우저에서 새로운 요청을 복사해야 할 수 있습니다. 실패한 `.part` 파일은 남겨두므로, 재시도할 때 다른 파일명을 지정하거나 기존 부분 파일을 직접 삭제하세요. 완료 파일 생성에는 하드 링크를 사용하므로 이를 지원하지 않는 파일시스템에서는 동작하지 않으며, 생성 실패 시 파일은 `.part` 상태로 남습니다.

이 프로젝트는 로컬 CLI와 라이브러리입니다. 네트워크 서비스에 연결하려면 신뢰할 수 없는 URL에 대한 인증·허용 대상 제한·SSRF 방어·자원 제한을 별도로 구현해야 합니다.

## 테스트

```sh
python -m unittest discover -s tests -v
```

요청 분석·헤더 필터링·민감한 정보 숨김·스트리밍·진행률·부분 응답 및 잘린 응답 거부·HTML 응답 거부·리디렉션·CLI 오류 처리를 검사합니다. 실제 LMS 인증 정보 대신 모의 응답을 사용하며, 모든 LMS와의 호환성을 보장하지 않습니다.

## 라이선스

[MIT License](LICENSE)

## 사용 조건 및 책임 안내

모든 영상 및 미디어는 해당 콘텐츠의 권리자 또는 정당한 배포자가 **다운로드와 소지를 허용한 경우에만** 다운로드할 수 있습니다. LMS에서 재생할 수 있다는 사실만으로 다운로드·소지·복제·재배포가 허용되는 것은 아닙니다. 사용자는 다운로드 전에 관련 법령, 서비스 이용약관 및 소속 기관의 규정을 확인하고 필요한 허락을 받아야 합니다.

본 스크립트의 사용 여부와 사용 방식에 대한 책임은 사용자에게 있습니다. 본 프로젝트의 개발자 및 배포자는 관련 법령이 허용하는 범위 내에서, 본 스크립트의 사용 또는 오용으로 발생한 손해, 법적 분쟁, 징계 및 기타 불이익에 대해 책임을 지지 않습니다. 본 프로젝트는 콘텐츠에 대한 권리를 부여하거나 다운로드의 적법성을 보장하지 않습니다.
