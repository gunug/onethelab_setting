# Railway 배포 가이드

## 개요

이 프로젝트의 배포 구조:

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  HTML 클라이언트    │     │  Supabase Realtime  │     │  Python 봇 (로컬)   │
│  (Railway 배포)     │ ←→  │  (Broadcast)        │ ←→  │  (개발자 PC)        │
│  chat_client/       │     │                     │     │  chat_bot/          │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
        ↑                                                        ↓
   외부 사용자 접속                                         Claude CLI 실행
```

### 컴포넌트별 역할

| 컴포넌트 | 위치 | 역할 |
|----------|------|------|
| **HTML 클라이언트** | Railway (배포) | 사용자 웹 인터페이스 |
| **Python 봇** | 개발자 로컬 PC | Claude CLI 실행, 메시지 처리 |
| **Supabase Realtime** | Supabase 클라우드 | 실시간 메시지 중계 |

> **참고**: Python 봇은 Claude Code CLI가 설치된 개발자 PC에서 실행됨. Railway 배포 불필요.

---

## 1단계: Railway 프로젝트 생성

### 1.1 Railway 계정 생성

1. [Railway](https://railway.app) 접속
2. GitHub 계정으로 로그인

### 1.2 새 프로젝트 생성

1. "New Project" 클릭
2. "Deploy from GitHub repo" 선택
3. 저장소 선택 및 연결

### 1.3 Root Directory 설정

Railway 대시보드 → Settings 탭:
- **Root Directory**: `chat_client`
- **Watch Paths**: `chat_client/**`

---

## 2단계: 정적 파일 배포 설정

### 2.1 Dockerfile 생성

`chat_client/Dockerfile` 파일 생성:

```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 2.2 .dockerignore 생성 (선택사항)

`chat_client/.dockerignore` 파일 생성:

```
*.md
.git
.gitignore
```

---

## 3단계: config.js 설정

### 3.1 config.js 수정

`chat_client/config.js`에 Supabase 연결 정보 입력:

```javascript
const SUPABASE_URL = 'https://your-project.supabase.co';
const SUPABASE_ANON_KEY = 'your-anon-key';
```

### 3.2 보안 주의사항

- `config.js`는 클라이언트에 노출됨
- ANON_KEY만 사용 (SERVICE_KEY 절대 노출 금지)
- Supabase RLS 정책으로 접근 제어

---

## 4단계: 배포 및 확인

### 4.1 배포 트리거

- GitHub에 push하면 자동 배포
- 또는 Railway 대시보드에서 수동 배포

### 4.2 도메인 설정

Railway 대시보드 → Settings → Domains:
1. "Generate Domain" 클릭 → `xxx.up.railway.app` 도메인 생성
2. 또는 커스텀 도메인 연결

### 4.3 배포 확인

1. 생성된 URL 접속
2. 로그인 화면 표시 확인
3. Supabase Auth 로그인 테스트

---

## 5단계: 로컬 Python 봇 실행

배포된 클라이언트와 통신하려면 로컬에서 Python 봇 실행:

```bash
cd chat_bot
python chat_bot.py
```

### 필수 조건
- Claude Code CLI 설치 및 로그인
- `.env` 파일에 Supabase 연결 정보 설정
- 봇 계정 (BOT_EMAIL, BOT_PASSWORD) 설정

---

## 배포 체크리스트

### Railway 설정
- [ ] GitHub 저장소 연결
- [ ] Root Directory를 `chat_client`로 설정
- [ ] `chat_client/Dockerfile` 생성
- [ ] 도메인 생성 또는 연결

### config.js 설정
- [ ] `SUPABASE_URL` 입력
- [ ] `SUPABASE_ANON_KEY` 입력

### 로컬 봇 설정
- [ ] `chat_bot/.env` 설정
- [ ] Claude Code CLI 로그인 확인
- [ ] `python chat_bot.py` 실행

### 테스트
- [ ] Railway URL 접속 확인
- [ ] 로그인/MFA 인증 테스트
- [ ] 메시지 송수신 테스트

---

## 대안 배포 옵션

### GitHub Pages (무료)

1. `chat_client/` 폴더를 `gh-pages` 브랜치로 푸시
2. 저장소 Settings → Pages → Source 설정
3. `config.js` Supabase 설정 확인

### Vercel / Netlify

1. 저장소 연결
2. Root Directory: `chat_client`
3. 빌드 명령: 없음 (정적 파일)
4. 출력 디렉토리: `.` 또는 `chat_client`

---

## 비용

| 서비스 | 무료 티어 | 유료 |
|--------|-----------|------|
| Railway | 월 $5 크레딧 | 사용량 기반 |
| GitHub Pages | 무료 | - |
| Vercel | 무료 (개인) | 팀 플랜 |
| Netlify | 무료 | 팀 플랜 |

---

## 현재 상태

- [ ] `chat_client/Dockerfile` 생성
- [ ] Railway 프로젝트 생성
- [ ] 도메인 설정
- [ ] 배포 테스트
