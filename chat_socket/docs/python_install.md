# Python 설치 마법사 개발 진행 상황

## 목표
`user_install.md`의 설치 과정을 웹 UI로 가이드하는 설치 마법사 프로그램

## 개발 단계

### 1단계: 기본 웹 서버
- [x] Python 표준 라이브러리로 HTTP 서버 구현
- [x] localhost에서 접속 가능 확인
- [x] 브라우저 자동 오픈

### 2단계: HTML UI 기본 구조
- [x] 설치 단계 목록 표시
- [x] 기본 CSS 스타일링

### 3단계: 터미널 명령 실행
- [x] 버튼 클릭 → subprocess로 명령 실행
- [x] 실행 결과 웹으로 반환
- [x] CLI 도구 설치: Node.js, Claude CLI, Supabase CLI, Railway CLI
- [x] 자동 설치 fallback: 도구 미설치 시 자동 설치 (winget/npm)

### 4단계: 설정 파일 생성
- [x] 입력 폼 UI (Supabase URL, API 키, 봇 계정)
- [x] .env 파일 생성 (chat_bot/.env)
- [x] config.js 파일 생성 (chat_client/config.js)
- [x] Supabase CLI 연동: 프로젝트 목록/API 키 자동 가져오기
- [x] Supabase CLI 프로젝트 생성: 조직 선택, 프로젝트명, DB 비밀번호, 리전 설정
- [x] 4단계 가이드: 프로젝트 생성, 사용자 계정, 봇 계정 생성 안내
- [x] Supabase CLI 로그인: 로그인 상태 확인 및 로그인 버튼
- [x] Authentication 설정 안내: Allow new users to sign up, Confirm email 옵션 설명

### 5단계: 설치 완료
- [x] 채팅봇 실행 버튼

---

## 진행 기록

### 1단계 완료 (2026-01-30)
- `http.server`, `socketserver`로 웹 서버 구현
- `webbrowser`로 브라우저 자동 오픈
- 포트 8888에서 정상 작동 확인

### 2단계 완료 (2026-01-30)
- 설치 단계 목록 UI 구현 (5단계: Python, 패키지, Node.js/CLI, Supabase 설정, 완료)
- CSS 스타일링: 다크 테마, 단계별 상태 표시 (완료/진행중/대기)
- 상태 바, 진행률 표시

### 3단계 완료 (2026-01-30)
- POST /run 엔드포인트 추가: JSON으로 명령 요청/응답
- subprocess.run으로 명령 실행 (300초 타임아웃)
- 명령 정의: pip_install, check_node, install_claude, run_bot
- UI: 실행 중 스피너, 결과 출력 박스, 단계 완료 시 자동 진행
- 에러 처리: 타임아웃, 명령 없음, 일반 예외

### 3단계 완료 + CLI 도구 추가 (2026-01-30)
- CLI 도구 설치 버튼 추가: Supabase CLI, Railway CLI
- 자동 설치 fallback: 도구 미설치 시 npm으로 자동 설치

### 4단계 완료 (2026-01-30)
- 설정 입력 폼 UI 구현 (Supabase URL, Anon Key, 봇 이메일/비밀번호)
- POST /save_config 엔드포인트 추가
- chat_bot/.env 파일 자동 생성
- chat_client/config.js 파일 자동 생성
- 유효성 검사: 필수 필드, URL 형식 확인

### 4단계 추가 기능 (2026-01-30)
- Supabase CLI 연동: 프로젝트 목록/API 키 자동 가져오기 (supabase projects list, api-keys)
- Supabase CLI 프로젝트 생성: 조직 선택, 프로젝트명, DB 비밀번호, 리전 설정 (supabase projects create)
- Supabase 조직 목록 가져오기 (supabase orgs list)
- 4단계 가이드 UI: 프로젝트 생성, 사용자 계정, 봇 계정 생성 단계별 안내

### 4단계 추가 기능 2 (2026-01-30)
- Supabase CLI 로그인: `/supabase_login` 엔드포인트 추가 (supabase login 실행)
- 로그인 상태 확인: `/supabase_login_status` 엔드포인트 추가 (orgs list로 상태 확인)
- UI: 로그인 버튼, 상태 표시, 페이지 로드 시 자동 상태 확인
- Authentication 설정 안내: "Allow new users to sign up" 활성화, "Confirm email" 비활성화 안내

### 설치 마법사 완료

**상태**: 완료
