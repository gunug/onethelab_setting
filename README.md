# Supabase Realtime 채팅 프로젝트

Supabase Realtime Broadcast 기능을 활용한 실시간 채팅 시스템입니다.
Python 채팅봇과 HTML 웹 클라이언트 간의 실시간 통신을 구현합니다.

## 주요 기능

- **실시간 통신**: Supabase Realtime Broadcast를 통한 WebSocket 기반 메시지 전송
- **Claude AI 통합**: Claude CLI를 활용한 AI 채팅봇 응답
- **세션 관리**: 대화 컨텍스트를 유지하는 세션 기능
- **진행 상황 표시**: Claude 응답 생성 과정을 실시간으로 확인
- **마크다운 렌더링**: 채팅 메시지에 마크다운 문법 지원

## 프로젝트 구조

```
├── chat_bot/           # Python 채팅봇 클라이언트
│   └── chat_bot.py     # Claude AI 연동 채팅봇
├── chat_client/        # HTML/JS 웹 채팅 클라이언트
│   ├── index.html      # 웹 채팅 인터페이스
│   └── chat.js         # 채팅 클라이언트 로직
├── supabase/           # Supabase 프로젝트 설정
├── project_docs/       # 프로젝트 문서
└── run_chat_bot.bat    # Python 채팅봇 실행 스크립트
```

## 요구 사항

- Python 3.8 이상
- Node.js (Supabase CLI 설치용)
- Claude CLI
- Supabase 계정 및 프로젝트

## 설치 및 실행

### 1. 의존성 설치

```bash
# Python 패키지 설치
pip install realtime supabase

# Supabase CLI 설치
npm install -g supabase
```

### 2. 환경 설정

`chat_bot/chat_bot.py` 파일에서 Supabase URL과 API 키를 설정합니다.

### 3. 실행

**Python 채팅봇 실행:**
```bash
run_chat_bot.bat
# 또는
python chat_bot/chat_bot.py
```

**웹 클라이언트:**
`chat_client/index.html` 파일을 브라우저에서 열거나 로컬 서버로 실행합니다.

## 사용 방법

1. Python 채팅봇을 실행합니다.
2. 웹 브라우저에서 HTML 클라이언트를 엽니다.
3. 이름을 입력하고 채팅을 시작합니다.
4. `@Claude` 멘션으로 AI에게 질문할 수 있습니다.
5. `/clear` 명령어로 세션을 초기화할 수 있습니다.

## 기술 스택

- **Backend**: Python, Supabase Realtime
- **Frontend**: HTML, CSS, JavaScript
- **AI**: Claude CLI (Anthropic)
- **통신**: WebSocket (Supabase Broadcast)

## 라이선스

개인 학습 및 실험 목적으로 제작되었습니다.
