# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT

**각각의 수정사항의 마지막에 반드시 CLAUDE.md 파일을 업데이트할 것.**

**기능이 완성되면 git에 커밋할 것. 오류가 있거나 디버깅 중일 때는 커밋하지 말 것. 자동으로 GitHub에 push 하지 말것.**

**할 일을 물어보면 `chat_socket/docs/todo.md` 파일을 읽고 답할 것. 할 일 추가 요청 시 해당 파일에 추가할 것.**

## Project Overview

로컬 WebSocket 기반 Claude Code 원격 접근 프로젝트.
Python 통합 서버(HTTP + WebSocket)로 브라우저에서 Claude CLI와 실시간 통신.

## Project Structure

```
chat_socket/            # 로컬 WebSocket 채팅 서버
  server.py             # Python 통합 서버 (HTTP + WebSocket)
  index.html            # 웹 채팅 인터페이스
  manifest.json         # PWA 설정
  service-worker.js     # PWA 서비스 워커
  icons/                # PWA 앱 아이콘
  install.bat           # 의존성 설치 스크립트 (Python, Node.js, ngrok, aiohttp, Claude CLI)
  config.bat            # ngrok 설정 스크립트 (authtoken, domain, OAuth)
  run.bat               # 로컬 실행 스크립트
  run_ngrok.bat         # ngrok 외부 접속 스크립트
  run_server_loop.bat   # 서버 재시작 루프 (내부용)
  docs/                 # 문서 폴더
    chat_socket.md      # Chat Socket 문서
    claude_code_tools.md # Claude Code 도구 목록
    python_install.md   # Python 설치 가이드
    todo.md             # 할 일 목록
ChatSocket_Local.lnk    # 로컬 실행 바로가기
ChatSocket_Ngrok.lnk    # ngrok 실행 바로가기
README.md               # 프로젝트 소개 문서
```

## 시스템 구조

```
[브라우저] ←── HTTP + WebSocket ──→ [Python 통합 서버] ←──CLI──→ [Claude]
                                    (localhost:8765)
```

## 설치 방법

### 1. 프로젝트 다운로드
```bash
git clone https://github.com/gunug/onethelab_setting.git
cd onethelab_setting/chat_socket
```

### 2. 의존성 설치
```bash
install.bat  # Python, Node.js, ngrok, aiohttp, Claude CLI 자동 설치
```

### 3. ngrok 설정 (외부 접속 시)
```bash
config.bat  # ngrok authtoken, domain, OAuth 설정
```

## 실행 방법

### 로컬 실행
```bash
# ChatSocket_Local.lnk 더블클릭 또는
python chat_socket/server.py
# 브라우저에서 http://localhost:8765 접속
```

### ngrok 외부 접속
```bash
# ChatSocket_Ngrok.lnk 더블클릭 또는
run_ngrok.bat
```
브라우저에서 ngrok URL (https://your-domain.ngrok-free.app) 접속 → 자동 연결

## 주요 기능

- HTTP + WebSocket 통합 서버 (aiohttp, 포트 8765)
- `/` : index.html 자동 제공
- `/ws` : WebSocket 채팅 연결
- Claude CLI 스트리밍 연동
- 진행 상황 UI
  - 메시지 영역 내 동적 생성
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
- 요청 대기열 기능
  - 여러 요청을 큐에 추가하여 순차 처리
  - 헤더 아래 대기열 UI (요청 수, 목록, 접기/펼치기)
  - 대기열 완료 시 알림음 (Web Audio API, 토글 지원)
  - AudioContext 전역 관리 (사용자 상호작용 후 활성화)
- 사용량 표시 (ccusage 연동)
  - 접속 시 자동 사용량 조회
  - 요청 완료 시 사용량 갱신
  - 헤더에 블록 사용량, 리셋까지 남은 시간, 오늘 총 사용량 표시
  - 남은 시간 경고 색상 (60분 이하 노랑, 30분 이하 빨강)
  - ⓘ 아이콘 클릭 시 사용량 제한 정보 패널 표시
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
  - 안드로이드 PWA 레이아웃 최적화: body position:fixed + app-container flex 구조로 화면 고정
- ngrok OAuth 파라미터 정리 (ERR_NGROK_3303 방지)
  - 페이지 로드 시 URL에서 code, state, error 파라미터 자동 제거
  - 새로고침 버튼 클릭 시 클린 URL로 이동 (OAuth 파라미터 없이)
  - history.replaceState로 뒤로가기 시 OAuth URL로 가지 않도록 처리
- 세션 자동 복구 기능
  - 타임아웃 발생 시 자동 세션 리셋
  - 모든 클라이언트 연결 종료 시 세션 리셋 및 처리 중인 작업 중단
  - Claude CLI state/session error 감지 시 새 세션으로 자동 재시도 (최대 1회)
  - stderr에서 "state", "session", "invalid" 키워드 감지

## Claude CLI 연동

- Claude CLI 세션 유지: 첫 요청은 `--session-id`로 새 세션 생성, 이후 요청은 `-r`로 세션 재개
- Claude CLI 권한: `--dangerously-skip-permissions` 옵션으로 모든 권한 자동 허용
- Claude CLI 프린트 모드: `-p -` 옵션으로 stdin에서 프롬프트 전달
- Claude CLI 진행 상황 실시간 표시 (stream-json 파싱)
  - 모델 정보, 도구 호출 상태, 완료 통계 (시간, 비용, 토큰)
  - 다양한 JSON 형식에 대한 방어적 타입 체크
  - Edit 도구 사용 시 변경 내용 (old_string, new_string) 출력
  - Write 도구 사용 시 파일 내용 표시 (최대 500자, 접기/펼치기 지원)
  - Bash 도구 사용 시 실행 명령어 표시 (최대 100자, 별도 스타일 블록)
  - TodoWrite 도구 사용 시 할 일 목록 표시 (상태별 아이콘, 접기/펼치기 지원)
- 비용 표시: USD와 원화(KRW) 동시 표시 (환율 상수: 1430원/USD, 2026년 1월 기준)
- 디버깅 로그: [DEBUG] 태그로 Python 콘솔에만 출력 (클라이언트 미전송)

## Claude Code 도구

상세 내용: [chat_socket/docs/claude_code_tools.md](chat_socket/docs/claude_code_tools.md)

## 버전 정보

### v3.0 (2026-01-30) - chat_socket 단일화
- **프로젝트 구조 정리**: chat_bot, chat_client, supabase, install_tool 삭제
- **chat_socket 단일화**: Supabase 없이 로컬 WebSocket 서버만 사용
- **바로가기 추가**: ChatSocket_Local.lnk, ChatSocket_Ngrok.lnk

### v2.5 이전 버전
- Supabase Realtime 기반 버전 (deprecated)
- chat_bot (Python) + chat_client (HTML) 구조
- Railway 배포, Supabase Auth + MFA 지원
