# 할 일 목록

## 진행 중

(없음)

## 대기 중
- [ ] Tools 표시 업데이트 하기 (claude_code_tools.md 참고)
  - Read: 파일 줄 수 표시
  - Grep: 검색 패턴 및 경로 표시
  - Task: 서브 에이전트 유형 표시
  - Glob: 검색 패턴 표시
  - WebFetch/WebSearch: URL/쿼리 표시
- [ ] WebSearch 추가정보 출력
- [ ] WebFetch 추가정보 출력
- [ ] Glob 추가정보 출력

## 완료

- [x] 여러 요청 큐 기능
  - Python 봇: 요청 대기열 관리 (처리 중 추가 요청 큐에 저장)
  - Python 봇: 이전 요청 완료 후 자동으로 다음 요청 처리
  - HTML 클라이언트: 대기열 UI 표시 (대기 중인 요청 수, 접기/펼치기)
  - HTML 클라이언트: 대기열 실시간 업데이트 (queue_status 이벤트)
- [x] AskUserQuestion HTML UI 추가
  - 질문/옵션 버튼 UI 표시
  - 단일/멀티 선택 지원
  - 기타(직접 입력) 옵션 지원
  - 응답 제출 기능
- [x] 세션 클리어 기능 구현
  - HTML 클라이언트에서 채팅 내역 초기화
  - Python 봇의 Claude 세션 리셋
  - /clear 명령어로 세션 초기화
- [x] 자동 스크롤 기능 수정
- [x] 요청 완료 시 소리 알림
- [x] 사용량 표시 기능 구현
  - Python 봇: ccusage로 사용량 조회 및 Broadcast 전송
  - HTML 클라이언트: 헤더에 오늘/전체 비용 표시 (USD/KRW)
- [x] 5시간 블록 사용량 및 남은 시간 표시
  - Python 봇: ccusage blocks로 활성 블록 정보 조회
  - HTML 클라이언트: 블록 비용, 남은 시간 표시 (경고/위험 색상)
- [x] TodoWrite UI 표시 구현
- [x] Edit, Write, Bash, TodoWrite 추가 정보 줄 바꿈 표시
- [x] claude_code_tools.md 문서 작성

## 구현 불가

- [ ] ~~전체 요청 프로그래스 기능~~ - Claude가 작업 전 전체 단계 수를 알 수 없음 (실시간으로 다음 단계 결정)
