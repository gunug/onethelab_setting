# Claude Code Remote Access

로컬 PC의 Claude Code CLI 환경을 외부에서 원격으로 접근하여 사용하기 위한 프로젝트입니다.

## 프로젝트 목적

- **로컬 개발환경 원격 접근**: 로컬 PC에 Claude Code CLI 환경을 구축하고, 외부에서 WebSocket 통신으로 접근
- **실시간 통신**: Python 통합 서버(HTTP + WebSocket)를 통해 브라우저와 Claude CLI 간 실시간 메시지 전송
- **웹 기반 인터페이스**: 어디서든 브라우저로 접속하여 Claude Code와 상호작용

## 시스템 구조

```
[브라우저] ←── HTTP + WebSocket ──→ [Python 통합 서버] ←──CLI──→ [Claude]
                                    (localhost:8765)
```

### 연동 방식

1. **Python 통합 서버**: HTTP와 WebSocket을 동시에 제공하는 aiohttp 기반 서버
2. **웹 인터페이스**: 서버의 `/` 경로에서 자동으로 index.html 제공
3. **WebSocket 채팅**: `/ws` 경로로 실시간 양방향 통신
4. **Claude Code CLI**: 프린트 모드(`-p -`)로 프롬프트 수신 및 응답

## 주요 기능

- **실시간 통신**: WebSocket 기반 양방향 메시지 전송
- **Claude AI 통합**: Claude CLI를 활용한 AI 채팅봇 응답
- **세션 관리**: 대화 컨텍스트를 유지하는 세션 기능 (`--session-id`, `-r` 옵션)
- **진행 상황 표시**: Claude 응답 생성 과정을 실시간으로 확인 (도구 호출, 비용, 토큰)
- **마크다운 렌더링**: 채팅 메시지에 마크다운 문법 지원
- **요청 대기열**: 여러 요청을 순차 처리, 대기열 UI 표시
- **사용량 모니터링**: 5시간 블록 사용량, 오늘 총 사용량, 남은 시간 표시
- **PWA 지원**: 모바일에서 앱처럼 설치 가능
- **ngrok 터널링**: 외부에서 접속 가능

## 프로젝트 구조

```
├── chat_socket/            # 로컬 WebSocket 채팅 서버
│   ├── server.py           # Python 통합 서버 (HTTP + WebSocket)
│   ├── index.html          # 웹 채팅 인터페이스
│   ├── manifest.json       # PWA 설정
│   ├── service-worker.js   # PWA 서비스 워커
│   ├── requirements.txt    # Python 의존성
│   ├── icons/              # PWA 앱 아이콘
│   ├── docs/               # 문서 폴더
│   │   ├── chat_socket.md  # Chat Socket 문서
│   │   ├── claude_code_tools.md
│   │   ├── python_install.md
│   │   └── todo.md
│   ├── install.bat         # 의존성 설치 스크립트
│   ├── config.bat          # ngrok 설정 스크립트
│   ├── run.bat             # 로컬 실행 스크립트
│   ├── run_ngrok.bat       # ngrok 외부 접속 스크립트 (config.bat으로 생성, .gitignore)
│   └── run_server_loop.bat # 서버 재시작 루프 (내부용)
├── CLAUDE.md               # Claude Code 작업 지침
└── README.md               # 프로젝트 소개 문서
```

## 요구 사항

- Python 3.8 이상
- aiohttp 패키지
- Claude CLI (`npm install -g @anthropic-ai/claude-code`)
- (선택) ngrok - 외부 접속용

## ngrok 설정 (외부 접속 시 필수)

외부에서 접속하려면 ngrok 설정이 필요합니다.

### 1. ngrok 가입 및 유료 플랜 구독

1. [ngrok.com](https://ngrok.com)에서 계정 가입
2. **유료 플랜 구독 필요** (Personal 플랜 이상)
   - 고정 도메인 사용을 위해 필요
   - 접속 계정 제한(OAuth) 기능 사용을 위해 필요
   - 무료 플랜은 임시 URL만 제공되어 매번 URL이 변경됨

### 2. config.bat 실행

`config.bat`를 실행하여 다음 정보를 입력합니다:

- **ngrok Auth Token**: ngrok 대시보드 → Your Authtoken에서 복사
- **ngrok 도메인**: ngrok 대시보드 → Domains에서 생성한 고정 도메인 (예: `your-domain.ngrok-free.app`)
- **OAuth 허용 계정**: 접속을 허용할 Google/GitHub 이메일 주소

### 3. 유료 플랜이 필요한 이유

| 기능 | 무료 플랜 | 유료 플랜 (Personal+) |
|------|----------|---------------------|
| 고정 도메인 | ❌ | ✅ |
| OAuth 접속 제한 | ❌ | ✅ |
| 동시 터널 수 | 1개 | 3개+ |

## 설치 및 실행

### 1. 프로젝트 다운로드

```bash
git clone https://github.com/gunug/onethelab_setting.git
cd onethelab_setting
```

### 2. 의존성 설치

```bash
# install.bat 실행 (Python, Node.js, ngrok, aiohttp, Claude CLI 자동 설치)
cd chat_socket
install.bat
```

또는 수동 설치:
```bash
pip install aiohttp
npm install -g @anthropic-ai/claude-code
```

### 3. ngrok 설정 (외부 접속 시 필수)

```bash
# config.bat 실행하여 ngrok 설정 및 run_ngrok.bat 생성
config.bat
```

입력 항목:
- ngrok Auth Token
- ngrok 도메인
- OAuth 허용 계정 (이메일)

**중요:** `config.bat` 실행 시 `run_ngrok.bat` 파일이 자동 생성됩니다. 이 파일은 개인 설정(도메인, 이메일)이 포함되어 있어 `.gitignore`에 등록되어 있습니다. 외부 접속을 위해서는 반드시 `config.bat`을 먼저 실행해야 합니다.

### 4. 실행

**로컬 실행:**
```bash
cd chat_socket
run.bat
# 또는 직접 실행: python server.py
```
브라우저에서 http://localhost:8765 접속

**ngrok 외부 접속:**
```bash
cd chat_socket
run_ngrok.bat
# (config.bat 실행 후 생성됨)
```
브라우저에서 ngrok URL (https://your-domain.ngrok-free.app) 접속

## 문제 해결

### ngrok 접속 시 OAuth state error 발생

ngrok 터널을 재시작한 후 접속할 때 OAuth state error가 발생할 수 있습니다.

**원인**: 브라우저에 저장된 이전 세션의 OAuth 쿠키가 새 터널 세션과 충돌

**해결 방법**:
1. 브라우저 쿠키 삭제 후 재접속
   - Chrome: `F12` → Application → Cookies → ngrok 관련 쿠키 삭제
   - 또는 `Ctrl+Shift+Delete` → 쿠키 삭제
2. 시크릿/프라이빗 창에서 접속

## 사용 방법

### 기본 사용

1. 서버 실행 (`run.bat` 또는 `run_ngrok.bat`)
2. 브라우저에서 접속
   - 로컬: `http://localhost:8765`
   - 외부: ngrok 도메인 URL
3. 메시지 입력란에 질문/명령 입력
4. Claude Code가 실시간으로 응답

### 명령어

| 명령어 | 설명 |
|--------|------|
| `/clear` | 세션 초기화 (대화 기록 삭제) |

### 인터페이스 기능

- **진행 상황 표시**: Claude가 사용하는 도구(파일 읽기, 편집 등) 실시간 확인
- **요청 대기열**: 여러 요청을 큐에 추가하여 순차 처리
- **사용량 모니터링**: 헤더에서 API 사용량 및 남은 시간 확인
- **알림음**: 대기열 완료 시 알림 (토글 가능)
- **서버 재시작**: 코드 변경 후 서버만 재시작 (ngrok URL 유지)

## 기술 스택

- **Backend**: Python, aiohttp (HTTP + WebSocket 통합 서버)
- **Frontend**: HTML, CSS, JavaScript, marked.js
- **AI**: Claude Code CLI (Anthropic)
- **통신**: WebSocket

## 버전 히스토리

### v3.1 (2026-01-31)
- 바로가기 파일(.lnk) 제거, bat 파일로 통일

### v3.0 (2026-01-30) - chat_socket 단일화
- 프로젝트 구조 정리 (chat_bot, chat_client, supabase 삭제)
- chat_socket 로컬 WebSocket 서버만 사용

### v2.5 이전 버전 (deprecated)
- Supabase Realtime 기반 버전
- chat_bot (Python) + chat_client (HTML) 구조
- Railway 배포, Supabase Auth + MFA 지원

## 라이선스

개인 학습 및 실험 목적으로 제작되었습니다.
