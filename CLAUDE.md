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
  install_list.md        # 설치 절차 체크리스트
  python_chat_bot.md     # Python 채팅봇 문서
  html_chat_client.md    # HTML 클라이언트 문서
  claude_code_tools.md   # Claude Code 도구 목록 및 구현 상태
  todo.md                # 할 일 목록
supabase/                # Supabase 프로젝트 설정
chat_bot/               # Python 채팅봇 클라이언트
chat_client/            # HTML/JS 웹 채팅 클라이언트
run_chat_bot.bat         # Python 채팅봇 실행 스크립트
README.md                # 프로젝트 소개 문서
```

## Python 채팅봇

상세 내용: [project_docs/python_chat_bot.md](project_docs/python_chat_bot.md)

## HTML/JS 웹 클라이언트

상세 내용: [project_docs/html_chat_client.md](project_docs/html_chat_client.md)

## Claude Code 도구

상세 내용: [project_docs/claude_code_tools.md](project_docs/claude_code_tools.md)

## 주요 기능

- 자신의 채팅 메시지 로컬 출력 (Python, HTML/JS 모두 지원)
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

## 안정성 기능

### Python 봇
- 재연결 로직: 연결 실패 시 자동 재연결 (최대 10회, 5초 간격)
- Graceful shutdown: 프로그램 종료 시 Claude 프로세스 및 스레드 정리
- Claude CLI 타임아웃: 300초 타임아웃 설정 (무한 대기 방지)
- 요청 큐: 모든 요청을 대기열에 추가 후 순차 처리, 처리 완료 후 대기열에서 제거 (응답 출력 후 알림음)
- 연결 상태 관리: `is_connected` 플래그로 연결 상태 추적
- 예외 처리 강화: stdin/stdout 오류, 프로세스 종료 등 다양한 상황 처리
- 세션 유지: 봇 시작 시 UUID 생성하여 동일 세션으로 대화 컨텍스트 유지

### HTML 클라이언트
- 자동 재연결: 연결 끊김 시 지수 백오프로 재연결 (최대 10회)
- 네트워크 감지: online/offline 이벤트로 네트워크 상태 감지
- 페이지 가시성 감지: 탭 전환 시 연결 상태 확인
- 하트비트: 30초 간격으로 연결 상태 점검 (연결 중 상태 체크하여 중복 방지)
- 연결 정리: 재연결 전 기존 채널/클라이언트 정리
- 전송 실패 처리: 메시지 전송 실패 시 시스템 메시지 표시
- 첫 연결/재연결 구분: 입장 메시지는 첫 연결 시에만, 재연결 시 "다시 연결되었습니다" 표시

## 버전 정보

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
