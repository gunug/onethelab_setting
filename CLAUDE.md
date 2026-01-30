# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT

**각각의 수정사항의 마지막에 반드시 CLAUDE.md 파일을 업데이트할 것.**

**기능이 완성되면 git에 커밋할 것. 오류가 있거나 디버깅 중일 때는 커밋하지 말 것. 자동으로 GitHub에 push 하지 말것.**

**할 일을 물어보면 `project_docs/todo.md` 파일을 읽고 답할 것. 할 일 추가 요청 시 해당 파일에 추가할 것.**

## Project Overview

Supabase Realtime 기반 실시간 통신 프로젝트 설정 저장소.
DB 없이 Broadcast 기능만 사용하여 WebSocket 통신 구현.

## Git 변경 추적 비활성화 파일

다음 파일들은 `git update-index --assume-unchanged`로 변경 추적이 비활성화되어 있음:
- `chat_bot/.env` - Supabase 연결 정보 (실제 키 입력 후 사용)
- `chat_client/config.js` - Supabase 연결 정보 (실제 키 입력 후 사용)

추적 다시 활성화하려면:
```bash
git update-index --no-assume-unchanged chat_bot/.env chat_client/config.js
```

## Project Structure

```
project_docs/
  install_list.md        # 설치 절차 체크리스트 (개발자용)
  user_install.md        # 사용자 설치 가이드 (패키징 배포용)
  python_chat_bot.md     # Python 채팅봇 문서
  html_chat_client.md    # HTML 클라이언트 문서
  claude_code_tools.md   # Claude Code 도구 목록 및 구현 상태
  security_risks.md      # 보안 위험 분석 문서
  security_measures.md   # 보안 조치 문서
  supabase_realtime.md   # Supabase Realtime 보안 설정 문서
  railway.md             # Railway 배포 가이드
  chat_socket.md         # 로컬 WebSocket 채팅 문서
  client_to_socket.md    # chat_client → chat_socket 이전 TODO
  todo.md                # 할 일 목록
install_tool/            # 설치 도우미 프로그램
  install.bat            # 설치 시작 배치파일 (Python 설치 지원)
  installer.py           # 웹 UI 기반 설치 마법사 (개발 중)
supabase/                # Supabase 프로젝트 설정
chat_bot/               # Python 채팅봇 클라이언트 (Supabase 버전)
chat_client/            # HTML/JS 웹 채팅 클라이언트 (Supabase 버전)
chat_socket/            # 로컬 WebSocket 채팅 (Supabase 불필요)
run_chat_bot.bat         # Python 채팅봇 실행 스크립트
README.md                # 프로젝트 소개 문서
```

## Python 채팅봇

상세 내용: [project_docs/python_chat_bot.md](project_docs/python_chat_bot.md)

## HTML/JS 웹 클라이언트

상세 내용: [project_docs/html_chat_client.md](project_docs/html_chat_client.md)

## Claude Code 도구

상세 내용: [project_docs/claude_code_tools.md](project_docs/claude_code_tools.md)

## 보안 위험 분석

상세 내용: [project_docs/security_risks.md](project_docs/security_risks.md)

## 배포 구조

상세 내용: [project_docs/railway.md](project_docs/railway.md)

```
HTML 클라이언트 (Railway 배포) ←→ Supabase Realtime ←→ Python 봇 (개발자 로컬 PC)
```

- **HTML 클라이언트**: Railway에 정적 파일로 배포
- **Python 봇**: Claude Code CLI가 설치된 개발자 PC에서 로컬 실행 (배포 불필요)

## Chat Socket (로컬 WebSocket 버전)

상세 내용: [project_docs/chat_socket.md](project_docs/chat_socket.md)

Supabase/Railway 없이 로컬에서 동작하는 경량 버전. HTTP + WebSocket 통합 서버.

```
[브라우저] ←── HTTP + WebSocket ──→ [Python 통합 서버] ←──CLI──→ [Claude]
                                    (localhost:8765)
```

### 실행 방법
```bash
# run.bat 더블클릭 또는
pip install aiohttp
python chat_socket/server.py
# 브라우저에서 http://localhost:8765 접속
```

### ngrok 외부 접속
```bash
# run_ngrok.bat 더블클릭 또는
python chat_socket/server.py  # 터미널 1
ngrok http 8765               # 터미널 2
```
브라우저에서 ngrok URL (https://xxxx.ngrok-free.app) 접속 → 자동 연결

### 주요 기능
- HTTP + WebSocket 통합 서버 (aiohttp, 포트 8765)
- `/` : index.html 자동 제공
- `/ws` : WebSocket 채팅 연결
- Claude CLI 스트리밍 연동
- 진행 상황 UI (chat_client와 동일한 방식)
  - 메시지 영역 내 동적 생성 (헤더 고정 패널 아님)
  - 도구별 step 표시 (턴 번호, 아이콘, 완료 체크 ✓)
  - 스피닝 아이콘 + 프로그레스 바 애니메이션
  - 모델명 표시 (Opus/Sonnet/Haiku)
- Edit/Write/TodoWrite 도구 UI
  - Edit: 변경 전/후 diff 비교 (접기/펼치기)
  - Write: 파일 내용 표시 (접기/펼치기)
  - TodoWrite: 할 일 목록 (○ 대기/◐ 진행중/✓ 완료)
  - Bash: 명령어 별도 스타일 블록
- 완료 통계 (시간, 비용 USD/KRW, 토큰, 턴)
- /clear 명령어 (세션 리셋)
- 마크다운 렌더링, 자동 스크롤
- 모바일 반응형 UI (미디어 쿼리: 768px, 480px 브레이크포인트)
- ngrok 터널링 지원 (URL 접속만으로 자동 연결)
- 요청 대기열 기능 (chat_client와 동일)
  - 여러 요청을 큐에 추가하여 순차 처리
  - 헤더 아래 대기열 UI (요청 수, 목록, 접기/펼치기)
  - 대기열 완료 시 알림음 (Web Audio API, 토글 지원)
- 서버 재시작 기능
  - "서버 재시작" 버튼 클릭 → Python 서버만 재시작
  - 코드 변경 사항 즉시 반영 (Python 인터프리터 특성)
  - ngrok은 유지되어 URL 변경 없음
  - run.bat/run_server_loop.bat이 exit code 100 감지하여 자동 재시작
  - run_ngrok.bat: run_server_loop.bat을 별도 창에서 실행하여 재시작 지원
- PWA (Progressive Web App) 지원
  - 안드로이드/iOS 홈 화면에 앱으로 설치 가능
  - manifest.json: 앱 이름, 아이콘, 테마색 정의
  - service-worker.js: 오프라인 캐싱, 네트워크 우선 전략
  - 앱 아이콘: 다양한 크기 PNG (16x16 ~ 512x512)
  - iOS Safari: apple-mobile-web-app 메타 태그 지원
  - 설치 프롬프트: beforeinstallprompt 이벤트 처리

## 주요 기능

- 메시지 서버 동기화: 모든 메시지를 서버(Supabase Broadcast)를 통해 수신하여 표시
  - HTML 클라이언트: `broadcast: { self: true }` 설정으로 자기 메시지도 서버에서 수신
  - 같은 계정 중복 접속 시 모든 탭에서 메시지 동기화
  - Python 봇: 자신의 메시지 로컬 출력 유지
- Python 채팅봇과 HTML 웹 클라이언트 간 실시간 통신
- Python: Ctrl+C 또는 'quit' 입력으로 안전한 종료 처리
- Python Claude 봇: 기본 이름 "Claude", 프린트 모드 (`-p -` 옵션, stdin으로 프롬프트 전달)
- Claude CLI 세션 유지: 첫 요청은 `--session-id`로 새 세션 생성, 이후 요청은 `-r`로 세션 재개
- Claude CLI 권한: `--dangerously-skip-permissions` 옵션으로 모든 권한 자동 허용
- Claude CLI 진행 상황 실시간 표시 (stream-json 파싱)
  - 모델 정보, 도구 호출 상태, 완료 통계 (시간, 비용, 토큰)
  - 다양한 JSON 형식에 대한 방어적 타입 체크
  - Edit 도구 사용 시 변경 내용 (old_string, new_string) 출력
  - Write 도구 사용 시 파일 내용 표시 (최대 500자, 접기/펼치기 지원)
  - Bash 도구 사용 시 실행 명령어 표시 (최대 100자, 별도 스타일 블록)
  - TodoWrite 도구 사용 시 할 일 목록 표시 (상태별 아이콘, 접기/펼치기 지원)
- 디버깅 로그: [DEBUG] 태그로 Python 콘솔에만 출력 (HTML 미전송)
- 비용 표시: USD와 원화(KRW) 동시 표시 (환율 상수: 1430원/USD, 2026년 1월 기준)
- HTML 클라이언트: 진행 상황 UI 표시 (프로그레스 바, 단계별 상태, 통계)
- HTML 클라이언트: Edit diff UI (변경 전/후 비교, 접기/펼치기 지원)
- HTML 클라이언트: Write content UI (파일 내용 표시, 접기/펼치기 지원)
- HTML 클라이언트: TodoWrite UI (할 일 목록 표시, 상태별 아이콘: ○ 대기/◐ 진행중/✓ 완료, 접기/펼치기 지원)
- HTML 클라이언트: AskUserQuestion UI (질문/옵션 버튼, 단일/멀티 선택, 기타 입력, 응답 제출)
- HTML 클라이언트: 요청 대기열 UI (헤더 아래 고정 표시, 항상 표시, 대기 중인 요청 수/목록, 접기/펼치기 지원)
- HTML 클라이언트: 대기열 완료 알림 소리 (모든 요청 처리 완료 시 Web Audio API로 알림음 재생, 토글 지원)
- HTML 클라이언트: 모든 메시지에 마크다운 렌더링 적용 (marked.js 사용, Claude뿐 아니라 모든 발신자)
- HTML 클라이언트: 헤더 화면 상단 고정 (한 줄 레이아웃, flexbox 다단 배치), 채팅 입력창 화면 하단 고정 (position: fixed)
- HTML 클라이언트: 자동 스크롤 체크박스 (켜면 항상 최신 메시지로 스크롤, 끄면 스크롤 유지, requestAnimationFrame으로 렌더링 후 스크롤)
- HTML 클라이언트: 사용자 이름 localStorage 저장 (재방문 시 자동 로그인, 이름변경 버튼 지원)
- 세션 클리어 기능: /clear 명령어로 Claude 세션 초기화 및 채팅 내역 삭제
- 사용량 표시: 요청 완료 시 및 접속 시 ccusage로 사용량 조회
  - 5시간 블록 사용량 및 블록 리셋까지 남은 시간 표시 (ccusage blocks)
  - 오늘 총 사용량 표시 (ccusage daily)
  - 남은 시간 경고 표시 (60분 이하 경고, 30분 이하 위험)
  - UI 레이블: "5시간 블록 사용:", "블록 리셋까지:", "오늘 총 사용:"
  - 접속 시 자동 조회: HTML 클라이언트 접속 시 request_usage 이벤트로 사용량 요청
  - 반응형 레이아웃: 좁은 화면에서 자동 줄바꿈 (flex-wrap)
  - 사용량 제한 정보 패널: ⓘ 아이콘 클릭 시 플랜별 예상 사용량, 5시간 롤링 윈도우, 주간 제한 정보 표시 (토글)
- Supabase Auth + MFA (TOTP): 이메일/비밀번호 인증 + 2단계 인증
  - HTML 클라이언트: Supabase Auth 로그인 (이메일/비밀번호)
  - HTML 클라이언트: MFA 인증 화면 (TOTP 검증)
  - HTML 클라이언트: TOTP 등록 화면 (QR 코드 표시, 최초 설정)
  - HTML 클라이언트: 로그아웃 시 페이지 새로고침 (상태 완전 초기화)
  - 토큰 보안: 메시지에 auth_token 포함하지 않음 (Broadcast 노출 방지)
  - 인증 방식: Supabase Auth 인증된 사용자만 채널 접속 가능
- Supabase Realtime Private Channel + RLS
  - 대시보드: "Allow public access" 비활성화
  - RLS 정책: realtime.messages 테이블에 authenticated 사용자만 접근 허용
  - Private Channel: 클라이언트에서 `{config: {private: true}}` 설정
  - Python 봇: Supabase Auth 로그인 (봇 전용 계정)

## 안정성 기능

### Python 봇
- 재연결 로직: 연결 실패 시 자동 재연결 (최대 10회, 5초 간격)
- Graceful shutdown: 프로그램 종료 시 Claude 프로세스 및 스레드 정리
- Claude CLI 타임아웃: 300초 타임아웃 설정 (무한 대기 방지)
- 요청 큐: 모든 요청을 대기열에 추가 후 순차 처리, 처리 완료 후 대기열에서 제거 (응답 출력 후 알림음)
- 연결 상태 관리: `is_connected` 플래그로 연결 상태 추적
- 예외 처리 강화: stdin/stdout 오류, 프로세스 종료 등 다양한 상황 처리
- 세션 유지: 봇 시작 시 UUID 생성하여 동일 세션으로 대화 컨텍스트 유지
- 인증: Supabase Auth 로그인 (봇 전용 계정으로 Private Channel 접속)
- 토큰 자동 갱신: 45분마다 `refresh_session()` 호출하여 토큰 갱신
- Heartbeat: 30초마다 연결 상태 확인, 3회 연속 실패 시 자동 재연결
- 절전 모드 복귀: 연결 끊김 감지 시 재인증 후 자동 재연결

### HTML 클라이언트
- 연결 끊김 처리: 자동 재연결 없이 "연결이 끊어졌습니다. 새로고침하여 연결을 다시 시도하세요." 메시지 표시
- 전송 실패 처리: 메시지 전송 실패 시 시스템 메시지 표시
- 중복 SUBSCRIBED 방지: `subscribedHandled` 플래그로 중복 이벤트 무시
- Supabase Auth: 이메일/비밀번호 로그인, MFA 인증, TOTP 등록
- 로그아웃: 페이지 새로고침으로 모든 상태 완전 초기화
- 토큰 자동 갱신: `onAuthStateChange`로 토큰 갱신 시 Realtime에 자동 반영
- 세션 만료 처리: refresh_token 만료 시 로그인 화면으로 자동 이동

## 버전 정보

### v2.5 (2026-01-30) - Python 봇 토큰 갱신 및 연결 안정성
- **토큰 자동 갱신 (Python)**: 45분마다 `refresh_session()` 호출하여 토큰 갱신
- **Heartbeat 모니터링**: 30초마다 연결 상태 확인, 3회 연속 실패 시 자동 재연결
- **재연결 시 재인증**: 토큰 갱신 실패 시 자동 재로그인
- **절전 모드 복귀 처리**: 연결 끊김 감지 시 재인증 후 채널 재연결
- **백그라운드 태스크 관리**: disconnect() 시 토큰 갱신/heartbeat 태스크 정리

### v2.4 (2026-01-30) - HTML 클라이언트 토큰 갱신 버그 수정
- **토큰 자동 갱신 반영**: `onAuthStateChange` 리스너로 토큰 갱신 시 Realtime에 자동 반영
- **재연결 루프 버그 수정**: Supabase 내부 재연결 시 만료된 토큰 사용 문제 해결
- **세션 만료 처리**: `SIGNED_OUT` 이벤트 시 로그인 화면으로 자동 이동 및 에러 메시지 표시
- **불필요한 코드 제거**: 사용되지 않는 `reconnectAttempts` 변수 제거

### v2.3 (2026-01-30) - 메시지 서버 동기화
- **Broadcast self 설정**: `broadcast: { self: true }`로 자기 메시지도 서버에서 수신
- **중복 접속 동기화**: 같은 계정으로 여러 탭/브라우저 접속 시 메시지 동기화
- **로컬 표시 제거**: sendMessage에서 로컬 메시지 표시 제거, 서버 응답으로 통일

### v2.2 (2026-01-30) - Railway 배포 (태그: v2.2)
- **Railway 배포**: HTML 클라이언트를 Railway에 정적 파일로 배포
- **배포 URL**: https://onethelabsetting-production.up.railway.app
- **Dockerfile**: nginx:alpine 기반 정적 파일 서버
- **Realtime 인증 수정**: `setAuth()` 호출로 Private Channel 인증 토큰 전달
- **config.js Git 추가**: Supabase ANON_KEY 포함 (RLS로 보호됨)

### v2.1 (2026-01-30) - Private Channel + RLS
- **Private Channel**: Supabase Realtime Private Channel 적용
- **RLS 정책**: realtime.messages 테이블에 인증된 사용자만 접근 가능
- **Python 봇 인증**: 봇 전용 계정으로 Supabase Auth 로그인
- **보안 강화**: ANON_KEY만으로는 채널 접속 불가 (서버 측 RLS 적용)

### v2.0 (2026-01-30) - Supabase Auth + MFA
- **Supabase Auth 통합**: 기존 자체 OTP 시스템을 Supabase Auth로 교체
- **이메일/비밀번호 로그인**: Supabase Auth signInWithPassword
- **MFA 지원**: Supabase MFA API로 TOTP 2단계 인증 (AAL1 → AAL2)
- **TOTP 등록 화면**: 새 사용자를 위한 QR 코드 기반 TOTP 등록
- **토큰 보안 강화**: 메시지에 auth_token 포함하지 않음 (Broadcast 노출 방지)
- **로그아웃 버그 수정**: 페이지 새로고침으로 상태 완전 초기화
- **중복 연결 메시지 방지**: `subscribedHandled` 플래그 추가
- **자동 재연결 제거**: 연결 끊김 시 새로고침 안내 메시지 표시

### v1.3 (2026-01-30) - OTP 인증 강화 (deprecated)
- 자체 OTP 시스템 (v2.0에서 Supabase Auth로 대체됨)

### v1.1 (2026-01-30) - 세션 클리어 기능 추가 (태그: v1.1)
- 세션 클리어 기능: /clear 명령어로 Claude 세션 초기화
- HTML 클라이언트: 채팅 내역 초기화 및 세션 리셋 알림 표시
- Python 봇: 새 세션 ID 생성하여 대화 컨텍스트 초기화
- 자동 스크롤 기능 안정화

### v1.0 (2026-01-29) - 안정적인 버전 (태그: v1.0)
- Python 채팅봇 + HTML 클라이언트 실시간 통신 완성
- Claude CLI 프린트 모드 (`-p -` stdin 방식)
- 정상 종료 처리 (quit 명령, 별도 입력 스레드 + Queue + asyncio.sleep)
- 진행 상황 UI, Edit diff 표시, 마크다운 렌더링
- 커밋: 이 버전 기준으로 안정적 작동 확인됨

## 설치 도우미 프로그램 (개발 중)

### 목표
`user_install.md`의 설치 과정을 웹 UI로 가이드하는 설치 마법사 프로그램

### 구조
```
install_tool/
  ├── install.bat    # 진입점 (Python 설치 지원)
  └── installer.py   # 웹 UI 설치 마법사
```

### 작동 방식
1. 사용자가 `install.bat` 더블클릭
2. Python 설치 여부 확인
   - 없으면: winget으로 Python 자동 설치 → 새 터미널에서 재실행
   - 있으면: `installer.py` 실행
3. 로컬 웹 서버 시작 (localhost)
4. 브라우저 자동 오픈
5. 웹 UI에서 단계별 설치 가이드
   - 버튼 클릭 → 터미널 명령 실행 → 결과 표시
   - 입력 폼으로 Supabase URL, API 키 등 설정

### 기술 스택
- Python 표준 라이브러리: `http.server`, `webbrowser`, `subprocess`
- 외부 의존성 없음 (설치 전 단계이므로)

### 현재 상태
- [x] `install.bat` 생성 (Python 설치 확인/설치 지원)
- [x] `installer.py` 기본 파일 생성
- [x] 웹 서버 구현 (http.server, 포트 8888)
- [x] HTML UI 구현 (다크 테마, 5단계 표시, 진행률)
- [x] 터미널 명령 실행 (subprocess, POST /run 엔드포인트)
- [x] CLI 도구 설치: Node.js, Claude CLI, Supabase CLI, Railway CLI
- [x] 자동 설치 fallback: 도구 미설치 시 자동 설치 (winget/npm)
- [x] 입력 폼 (Supabase URL, API 키, 봇 계정)
- [x] 설정 파일 자동 생성 (chat_bot/.env, chat_client/config.js)
- [x] Supabase CLI 연동: 프로젝트 목록/API 키 자동 가져오기
- [x] Supabase CLI 프로젝트 생성: 조직 선택, 프로젝트명, DB 비밀번호, 리전 설정
- [x] 4단계 가이드: 프로젝트 생성, 사용자 계정, 봇 계정 생성 안내
- [x] Supabase CLI 로그인: 로그인 버튼, 상태 확인, 자동 상태 체크
- [x] Authentication 설정 안내: Allow new users to sign up, Confirm email 옵션 설명
- [x] 설치 완료 화면: 채팅봇 실행 방법 안내 (run_chat_bot.bat 또는 python 명령어)
- [x] 오류 처리 개선: 포트 충돌, 예외 발생 시 에러 메시지 표시 및 창 유지
