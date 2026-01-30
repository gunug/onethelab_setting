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
│   ├── icons/              # PWA 앱 아이콘
│   ├── run.bat             # 로컬 실행 스크립트
│   ├── run_ngrok.bat       # ngrok 외부 접속 스크립트
│   └── run_server_loop.bat # 서버 재시작 루프 (내부용)
├── project_docs/           # 프로젝트 문서
│   ├── chat_socket.md      # Chat Socket 문서
│   ├── claude_code_tools.md
│   ├── python_install.md
│   └── todo.md
├── ChatSocket_Local.lnk    # 로컬 실행 바로가기
├── ChatSocket_Ngrok.lnk    # ngrok 실행 바로가기
├── CLAUDE.md               # Claude Code 작업 지침
└── README.md               # 프로젝트 소개 문서
```

## 요구 사항

- Python 3.8 이상
- aiohttp 패키지
- Claude CLI (`npm install -g @anthropic-ai/claude-code`)
- (선택) ngrok - 외부 접속용

## 설치 및 실행

### 1. 의존성 설치

```bash
# Python 패키지 설치
pip install aiohttp

# Claude CLI 설치
npm install -g @anthropic-ai/claude-code
```

### 2. 실행

**로컬 실행:**
```bash
# ChatSocket_Local.lnk 더블클릭 또는
python chat_socket/server.py
# 브라우저에서 http://localhost:8765 접속
```

**ngrok 외부 접속:**
```bash
# ChatSocket_Ngrok.lnk 더블클릭 또는
python chat_socket/server.py  # 터미널 1
ngrok http 8765               # 터미널 2
# 브라우저에서 ngrok URL (https://xxxx.ngrok-free.app) 접속
```

## 사용 방법

1. Python 서버를 실행합니다.
2. 브라우저에서 `http://localhost:8765` 또는 ngrok URL에 접속합니다.
3. 메시지를 보내면 Claude Code가 응답합니다.
4. `/clear` 명령어로 세션을 초기화할 수 있습니다.

## 기술 스택

- **Backend**: Python, aiohttp (HTTP + WebSocket 통합 서버)
- **Frontend**: HTML, CSS, JavaScript, marked.js
- **AI**: Claude Code CLI (Anthropic)
- **통신**: WebSocket

## 버전 히스토리

### v3.0 (2026-01-30) - chat_socket 단일화
- 프로젝트 구조 정리 (chat_bot, chat_client, supabase 삭제)
- chat_socket 로컬 WebSocket 서버만 사용
- 바로가기 파일 추가 (ChatSocket_Local.lnk, ChatSocket_Ngrok.lnk)

### v2.5 이전 버전 (deprecated)
- Supabase Realtime 기반 버전
- chat_bot (Python) + chat_client (HTML) 구조
- Railway 배포, Supabase Auth + MFA 지원

## 라이선스

개인 학습 및 실험 목적으로 제작되었습니다.
