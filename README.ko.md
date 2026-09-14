# ytdlpGUI

**[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md)**

yt-dlp의 크로스 플랫폼 GUI 프론트엔드(Web / Linux / Windows)입니다. yt-dlp의 **모든 명령줄 옵션**을 지원하며, UI와 로직을 엄격히 분리한 설계로 향후 macOS / iOS / Android 클라이언트에서도 동일한 백엔드 API를 재사용할 수 있습니다.

## 주요 기능

- **듀얼 모드 UI**: 기본 간단 모드(제목 표시줄 + URL 입력 + 다운로드 대기열, 순수한 `yt-dlp <url>`. "⚙ 고급"에서 전체 설정 전개
- **모든 옵션**: yt-dlp 전체 옵션(숨겨진 옵션 수동 보완 포함)을 공식 카테고리별로 표시. 현지 언어 설명·사용 예시·툴팁 제공, 검색 가능
- **상호 배제 관리**: 51개의 3상태 그룹(기본/켜기/끄기) + 30쌍의 자동 제거 배제. 메타데이터를 프론트엔드와 백엔드가 공유하며 서버에서도 강제 검증
- **다운로드 관리**: 다중 URL 대기열, 실시간 진행률/속도/ETA/로그(SSE), 취소, 저장 경로 실시간 표시
- **정보 조회**: 플로팅 창에 제목/길이/포맷 표를 표시하고 행을 클릭해 `-f` 선택. 여러 링크는 개별 조회 + ↑↓ 탐색
- **다운로드 기록**: URL/제목/경로/시각/성공 여부를 모두 기록, 비우기 가능, 로그 경로 설정 가능
- **디렉터리 선택**: 서버 쪽 폴더 브라우저. LAN 공유·네트워크 마운트 지원(Windows 드라이브/UNC)
- **4개 언어 UI**: 中文 / English / 日本語 / 한국어, 완전 소프트 코딩(`frontend/js/i18n/*.json`)
- **프리셋**: 옵션 조합 저장/불러오기/삭제, 저장 시 검증
- **보안**: 옵션 화이트리스트 + 값 검증으로 인자 인젝션 차단. 기본적으로 127.0.0.1만 수신

## 아키텍처

```
frontend/   정적 HTML/CSS/JS(빌드 불필요, 모든 WebView에 삽입 가능)
backend/    FastAPI 서비스(순수 로직, 단독 import 가능)
  api/          얇은 HTTP 라우팅 계층
  services/     downloader / options / metadata / history / store
  data/         options_registry.json(yt_dlp.options에서 인트로스펙션 생성)
docs/       SDD 문서 + 2라운드 QA 보고서(UI 케이스 123건 + 수정 27건)
scripts/    generate_registry.py / run_checks.sh / regress_examples.py
```

옵션 레지스트리는 `scripts/generate_registry.py`가 yt-dlp 소스(`yt_dlp/options.py`)를 인트로스펙션하여 생성합니다 — 플래그/인자 수/반복 가능 여부/배제 관계가 모두 데이터 기반입니다. yt-dlp 업그레이드 후 스크립트를 다시 실행하면 자동으로 따라가고, `--check` 모드로 드리프트를 감지할 수 있습니다.

## 빠른 시작

```bash
# Linux / macOS
./run.sh                    # venv 생성, 의존성 설치, 브라우저 실행
./run.sh --lan              # LAN 모드(0.0.0.0 — 휴대폰/다른 PC에서 접근 가능)
```

```bat
:: Windows(소스 실행)
run.bat
```

수동: `python -m uvicorn backend.app.main:app --port 8765` → http://127.0.0.1:8765 열기
API 문서(OpenAPI): http://127.0.0.1:8765/docs

## Windows .exe 빌드

**방법 1(권장)**: Python 3.10+ 설치 후

```bat
build_windows.bat
```

단일 파일 `dist\ytdlpgui.exe`가 생성됩니다 — 콘솔 창 없이 더블클릭으로 실행되어 브라우저 UI를 자동으로 엽니다. 설정/프리셋/기록은 exe와 같은 위치의 `data\` 폴더에 저장되며, exe를 복사하기만 하면 배포할 수 있습니다.

**방법 2(수동)**:

```bat
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt pyinstaller
.venv\Scripts\pyinstaller --clean ytdlpgui.spec
```

참고: `ytdlpgui.spec`는 `console=False`(검은 창 없음). 디버깅 시 `True`로 바꾸고 다시 빌드하면 로그가 보입니다. exe에는 현재 버전의 레지스트리/프론트엔드 리소스가 포함되므로 yt-dlp 업그레이드 시 재빌드하거나 소스로 실행해야 합니다.

## 개발 품질 스위트

코드 변경이나 yt-dlp 업그레이드 후 `scripts/run_checks.sh` 실행(3단계 모두 통과해야 함):

1. 레지스트리 드리프트 감지 — yt-dlp 실제 옵션과 registry 불일치 시 경고;
2. 배제 메타데이터와 명령 구축 구조 어설션(양측 비어 있지 않음/대칭/multi/nargs/충돌 거부);
3. 전체 예시 회귀(build_args + yt-dlp --simulate 실증, 96건).

릴리스 전 3분 스모크 체크: 페이지 정상 부팅 → "모든 옵션"에서 3상태 그룹 ≥40 → 영어 UI에 중국어 잔여 없음.

## 알려진 트레이드오프

- URL 입력은 http(s), `ytsearch` 접두사, 콜론 없는 맨 도메인을 허용하며 기타 스킴/검색 접두사는 거부(공격 표면 고려)
- `--alias` / `--replace-in-metadata` / `--print-to-file`는 다중 인자 옵션으로, 하나의 입력 상자에 공백 구분으로 입력(세그먼트별 제한은 UI 힌트 참조)
- 순수 CLI 조회 옵션(`--help`/`--dump-json` 등)은 UI에서 숨겨지지만 기존 프리셋 호환을 위해 화이트리스트에서는 허용

## 향후 확장(macOS / iOS / Android)

백엔드 `services/` 계층은 웹 프레임워크 타입에 의존하지 않아 그대로 이식 가능합니다. 프론트엔드는 빌드 불필요한 정적 리소스로 WKWebView / WebView / Android WebView에서 직접 로드하거나 Tauri / Capacitor로 래핑할 수 있습니다.

## 문서

- 설계 및 작업: `docs/design.md`, `docs/tasks.md`
- QA: `docs/qa-report-1.md`(데이터/로직 계층), `docs/qa-ui-plan.md` + `docs/qa-ui-report.md`(UI 계층 123케이스)

## 이전 버전

이전 버전(tkinter, Windows 전용, 최소 기능)은 `ytdlpGUI@7c93372`를 참조하세요.
