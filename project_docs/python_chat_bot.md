# Python 채팅봇 (chat_bot)

Supabase Realtime Broadcast를 사용한 Python 채팅 클라이언트.

## 폴더 구조

```
chat_bot/
  chat_bot.py        # 메인 채팅 코드
  requirements.txt   # 의존성 패키지
  .env               # 환경변수 (SUPABASE_URL, SUPABASE_ANON_KEY)
  .env.example       # 환경변수 예시
```

## 설치 절차

```bash
cd chat_bot

# Windows (pip이 PATH에 없는 경우)
py -m pip install -r requirements.txt

# 또는 pip이 PATH에 있는 경우
pip install -r requirements.txt
```

## API Key 확인 (CLI)

```bash
supabase projects api-keys --project-ref bgnhocgfbtnxosrjcxog
```

## 환경변수 설정

`.env` 파일에 아래 값 설정:
- `SUPABASE_URL`: 프로젝트 URL
- `SUPABASE_ANON_KEY`: anon 키 (위 명령어로 확인)

## 실행

```bash
# Windows
py chat_bot.py

# 또는
python chat_bot.py
```

## 사용법

- 실행 시 Claude CLI 테스트 후 자동 대기
- 채팅 메시지 수신 시 Claude CLI로 자동 전달
- `quit` 입력 시 종료

## 주요 기능

- Claude CLI 연동 (stream-json 출력 파싱)
- 진행 상황 실시간 전송 (모델, 도구 호출, 완료 통계)
- 웹 기반 권한 승인 시스템
  - 권한 요청을 웹 클라이언트로 전달
  - 웹에서 응답 대기 (5분 타임아웃)
  - 응답 수신 후 CLI에 전달하여 작업 계속
