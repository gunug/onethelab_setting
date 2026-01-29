# HTML/JS 채팅 클라이언트 (chat_client)

Supabase Realtime Broadcast를 사용한 웹 채팅 클라이언트.

## 폴더 구조

```
chat_client/
  index.html    # 메인 HTML
  config.js     # Supabase 설정 (URL, KEY)
  chat.js       # 채팅 로직
```

## 실행 방법

### 방법 1: 파일 직접 열기
`index.html` 파일을 브라우저에서 직접 열기

### 방법 2: 로컬 서버 사용
```bash
cd chat_client

# Python
py -m http.server 8000

# Node.js (npx)
npx serve
```
브라우저에서 `http://localhost:8000` 접속

## 사용법

1. 사용자 이름 입력
2. "참가하기" 클릭
3. 메시지 입력 후 Enter 또는 "전송" 클릭

## 주요 기능

- Claude 응답 마크다운 렌더링 (marked.js 사용)
  - 코드 블록, 리스트, 테이블, 인용문, 링크 등 지원
- Claude 처리 진행 상황 실시간 UI 표시
  - 프로그레스 바, 단계별 상태, 완료 통계
- 웹 기반 권한 승인 시스템
  - Claude CLI 권한 요청 시 승인/거부 버튼 표시
  - 알림음으로 권한 요청 알림
  - 승인/거부 후 상태 표시

## Python 채팅봇과 연동

동일한 채널(`chat-room`)을 사용하므로 Python 채팅봇과 실시간 통신 가능.
