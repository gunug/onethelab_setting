# Chat Socket - 로컬 WebSocket 기반 Claude 채팅

Supabase/Railway 없이 로컬 WebSocket으로 동작하는 Claude 채팅 시스템.

## 개요

```
[브라우저] ←── HTTP (index.html) ──→ [Python 통합 서버] ←──CLI──→ [Claude]
          ←── WebSocket (/ws) ────→   (localhost:8765)
```

- **Python 통합 서버**: HTTP + WebSocket 통합 서버 (aiohttp)
  - `/` : index.html 제공
  - `/ws` : WebSocket 채팅 연결
- **외부 서비스 불필요**: Supabase, Railway 없이 로컬에서만 동작
- **ngrok 지원**: ngrok URL 접속 시 자동으로 WebSocket 연결

## 기술 스택

- Python 3.8+
- `aiohttp` 라이브러리 (pip install aiohttp)
- HTML/CSS/JavaScript + marked.js (마크다운 렌더링)
- Claude CLI

## 파일 구조

```
chat_socket/
├── server.py           # WebSocket 서버 + Claude CLI 연동
├── index.html          # 웹 클라이언트 UI
├── requirements.txt    # Python 의존성
├── run.bat             # 서버 실행 스크립트 (로컬용)
└── run_ngrok.bat       # 서버 + ngrok 실행 스크립트 (외부 접속용)
```

---

## 실행 방법

### Windows

```bash
# 방법 1: run.bat 더블클릭
chat_socket/run.bat

# 방법 2: 수동 실행
pip install websockets
python chat_socket/server.py
```

### 브라우저 접속

1. 서버 실행 후 `chat_socket/index.html` 파일을 브라우저에서 열기
2. 이름 입력 후 메시지 전송
3. Claude가 자동 응답

---

## 구현된 기능

### 서버 (server.py)
- [x] WebSocket 서버 (포트 8765)
- [x] 클라이언트 연결/해제 관리
- [x] 메시지 브로드캐스트
- [x] Claude CLI 스트리밍 연동
- [x] 세션 관리 (--session-id, -r)
- [x] /clear 명령어 (세션 리셋)
- [x] 진행 상황 전송 (progress 이벤트)
- [x] 도구 정보 전송 (Edit, Write, TodoWrite)

### 클라이언트 (index.html)
- [x] 채팅 UI (메시지 목록, 입력창)
- [x] WebSocket 연결 상태 표시
- [x] 메시지 전송/수신
- [x] 마크다운 렌더링 (marked.js)
- [x] 진행 상황 패널 (프로그레스 바, 도구 상태)
- [x] Edit diff 표시 (변경 전/후 비교, 접기/펼치기)
- [x] Write content 표시 (파일 내용, 접기/펼치기)
- [x] TodoWrite 표시 (할 일 목록, 상태별 아이콘)
- [x] 완료 통계 (시간, 비용, 토큰, 턴)
- [x] 자동 스크롤 체크박스
- [x] /clear 버튼 및 명령어

---

## 메시지 프로토콜

### 클라이언트 → 서버

```json
{
  "type": "message",
  "username": "user",
  "message": "안녕하세요"
}
```

```json
{
  "type": "command",
  "command": "clear"
}
```

### 서버 → 클라이언트

```json
{
  "type": "message",
  "username": "Claude",
  "message": "안녕하세요!"
}
```

```json
{
  "type": "progress",
  "progress_type": "start|init|tool_start|tool_end|complete|error",
  "tool": "Read",
  "detail": "file.py",
  "edit_info": { "type": "edit|write|todo", ... }
}
```

```json
{
  "type": "system",
  "message": "연결되었습니다."
}
```

---

## 진행 상태

| 단계 | 상태 | 설명 |
|------|------|------|
| 1단계 | ✅ 완료 | WebSocket 서버 기본 구조 |
| 2단계 | ✅ 완료 | HTML 클라이언트 기본 UI |
| 3단계 | ✅ 완료 | Claude CLI 연동 |
| 4단계 | ✅ 완료 | 진행 상황 UI |
| 5단계 | ✅ 완료 | 추가 기능 (/clear, 자동 스크롤, 마크다운) |
| 6단계 | ✅ 완료 | 테스트 및 문서화 |

---

## 기존 chat_bot과의 차이점

| 항목 | chat_bot (Supabase) | chat_socket (로컬) |
|------|---------------------|-------------------|
| 통신 방식 | Supabase Realtime | 로컬 WebSocket |
| 외부 서비스 | Supabase, Railway | 없음 |
| 인증 | Supabase Auth + MFA | 없음 (로컬 전용) |
| 배포 | Railway 배포 필요 | 로컬 실행만 |
| 사용 환경 | 원격 접속 가능 | 같은 PC에서만 |

---

## ngrok을 통한 외부 접속

로컬 서버를 외부에서 접속 가능하게 하려면 ngrok을 사용합니다.

### 1. ngrok 설치

```bash
# Windows (winget)
winget install ngrok.ngrok

# 또는 https://ngrok.com/download 에서 다운로드
```

### 2. ngrok 계정 설정

```bash
# https://dashboard.ngrok.com 에서 가입 후 authtoken 복사
ngrok config add-authtoken <YOUR_AUTH_TOKEN>
```

### 3. 서버 실행

**방법 1: 배치파일 (권장)**
```bash
# run_ngrok.bat 더블클릭
chat_socket/run_ngrok.bat
```

**방법 2: 수동 실행**
```bash
# 터미널 1: WebSocket 서버 실행
python chat_socket/server.py
```

```bash
# 터미널 2: ngrok 터널 실행
ngrok http 8765
```

### 4. 클라이언트 접속

ngrok 실행 시 표시되는 URL을 브라우저에서 직접 접속합니다:
```
Forwarding   https://xxxx-xx-xx-xxx-xx.ngrok-free.app -> http://localhost:8765
```

1. 브라우저에서 ngrok URL 접속 (예: `https://xxxx-xx-xx-xxx-xx.ngrok-free.app`)
2. 서버가 자동으로 index.html을 제공하고 WebSocket 연결됨
3. 별도 설정 없이 바로 채팅 가능

### 주의사항

- ngrok 무료 플랜: 세션당 2시간 제한, 동시 연결 1개
- ngrok URL은 재시작마다 변경됨 (유료 플랜에서 고정 가능)
- WebSocket 연결 시 `wss://` (SSL) 프로토콜 사용 필요

---

## 향후 추가 가능 기능

- [ ] 사용량 조회 (ccusage)
- [ ] 요청 대기열
- [x] 터널링 연동 (ngrok)
- [ ] 간단한 비밀번호 인증
