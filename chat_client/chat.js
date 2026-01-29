// USD to KRW 환율 (2026년 1월 기준)
const USD_TO_KRW = 1430;

// 재연결 설정
const RECONNECT_DELAY = 3000;  // 재연결 대기 시간 (ms)
const MAX_RECONNECT_ATTEMPTS = 10;  // 최대 재연결 시도 횟수
const HEARTBEAT_INTERVAL = 30000;  // 하트비트 간격 (ms)

class ChatClient {
    constructor() {
        this.supabase = null;
        this.channel = null;
        this.user = null;  // Supabase Auth 사용자 정보
        this.username = '';  // 표시용 이름 (이메일 또는 메타데이터)
        this.currentProgress = null;
        this.pendingPermissions = {};  // request_id -> element
        this.reconnectAttempts = 0;
        this.reconnectTimer = null;
        this.heartbeatTimer = null;
        this.isConnecting = false;
        this.hasConnectedOnce = false;  // 첫 연결 여부
        this.subscribedHandled = false;  // 현재 연결의 SUBSCRIBED 처리 여부
        this.queueElement = null;  // 대기열 UI 요소
        this.queueCollapsed = false;  // 대기열 접힘 상태
        this.previousQueueCount = 0;  // 이전 대기열 수 (완료 알림용)
        this.queueSoundEnabled = localStorage.getItem('queue_sound') !== 'false';  // 소리 알림 설정
        // MFA 관련
        this.mfaFactorId = null;  // MFA factor ID (challenge/verify에 필요)
        this.init();
    }

    init() {
        // Supabase 클라이언트 초기화
        this.supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

        // DOM 요소
        this.loginScreen = document.getElementById('loginScreen');
        this.chatScreen = document.getElementById('chatScreen');
        this.mfaScreen = document.getElementById('mfaScreen');
        this.totpEnrollScreen = document.getElementById('totpEnrollScreen');

        // 로그인 관련 DOM
        this.emailInput = document.getElementById('emailInput');
        this.passwordInput = document.getElementById('passwordInput');
        this.loginBtn = document.getElementById('loginBtn');
        this.loginError = document.getElementById('loginError');

        // MFA 인증 관련 DOM
        this.mfaInput = document.getElementById('mfaInput');
        this.mfaVerifyBtn = document.getElementById('mfaVerifyBtn');
        this.mfaError = document.getElementById('mfaError');

        // TOTP 등록 관련 DOM
        this.totpQrCode = document.getElementById('totpQrCode');
        this.totpSecret = document.getElementById('totpSecret');
        this.totpEnrollInput = document.getElementById('totpEnrollInput');
        this.totpEnrollBtn = document.getElementById('totpEnrollBtn');
        this.totpEnrollError = document.getElementById('totpEnrollError');

        // 채팅 관련 DOM
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.chatContainer = document.getElementById('chatContainer');
        this.statusEl = document.getElementById('status');
        this.logoutBtn = document.getElementById('logoutBtn');
        this.clearSessionBtn = document.getElementById('clearSessionBtn');
        this.autoScrollCheckbox = document.getElementById('autoScrollCheckbox');
        this.queueSoundCheckbox = document.getElementById('queueSoundCheckbox');

        // 로그인 이벤트
        this.loginBtn.addEventListener('click', () => this.login());
        this.emailInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.passwordInput.focus();
        });
        this.passwordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.login();
        });

        // MFA 인증 이벤트
        this.mfaVerifyBtn.addEventListener('click', () => this.verifyMfa());
        this.mfaInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.verifyMfa();
        });
        this.mfaInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });

        // TOTP 등록 이벤트
        this.totpEnrollBtn.addEventListener('click', () => this.verifyTotpEnroll());
        this.totpEnrollInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.verifyTotpEnroll();
        });
        this.totpEnrollInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });

        // 채팅 이벤트
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        this.logoutBtn.addEventListener('click', () => this.logout());
        this.clearSessionBtn.addEventListener('click', () => this.clearSession());

        // 소리 알림 체크박스 이벤트
        if (this.queueSoundCheckbox) {
            this.queueSoundCheckbox.checked = this.queueSoundEnabled;
            this.queueSoundCheckbox.addEventListener('change', () => {
                this.queueSoundEnabled = this.queueSoundCheckbox.checked;
                localStorage.setItem('queue_sound', this.queueSoundEnabled ? 'true' : 'false');
            });
        }

        // 페이지 가시성 변경 감지 (탭 전환 시 재연결)
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && this.user) {
                this.checkConnection();
            }
        });

        // 온라인/오프라인 감지
        window.addEventListener('online', () => {
            console.log('네트워크 연결됨');
            if (this.user) {
                this.reconnect();
            }
        });

        window.addEventListener('offline', () => {
            console.log('네트워크 연결 끊김');
            this.updateStatus('오프라인', false);
        });

        // 큐 UI 초기화
        this.initQueueUI();

        // 사용량 정보 패널 초기화
        this.initUsageInfoPanel();

        // 기존 세션 확인
        this.checkExistingSession();
    }

    async checkExistingSession() {
        // 기존 로그인 세션 확인
        const { data: { session }, error } = await this.supabase.auth.getSession();

        if (session && session.user) {
            this.user = session.user;
            this.username = this.user.email || 'User';

            // MFA 상태 확인
            await this.checkMfaStatus();
        }
    }

    async login() {
        const email = this.emailInput.value.trim();
        const password = this.passwordInput.value;

        if (!email || !password) {
            this.showLoginError('이메일과 비밀번호를 입력하세요.');
            return;
        }

        this.loginBtn.disabled = true;
        this.loginBtn.textContent = '로그인 중...';
        this.hideLoginError();

        try {
            const { data, error } = await this.supabase.auth.signInWithPassword({
                email,
                password
            });

            if (error) {
                throw error;
            }

            this.user = data.user;
            this.username = this.user.email || 'User';

            // MFA 상태 확인
            await this.checkMfaStatus();

        } catch (error) {
            console.error('로그인 오류:', error);
            this.showLoginError(error.message || '로그인에 실패했습니다.');
            this.loginBtn.disabled = false;
            this.loginBtn.textContent = '로그인';
        }
    }

    async checkMfaStatus() {
        try {
            const { data, error } = await this.supabase.auth.mfa.getAuthenticatorAssuranceLevel();

            if (error) {
                console.error('MFA 상태 확인 오류:', error);
                // MFA 없이 진행
                this.proceedToChat();
                return;
            }

            console.log('MFA 상태:', data);

            const { currentLevel, nextLevel, currentAuthenticationMethods } = data;

            if (nextLevel === 'aal2' && currentLevel === 'aal1') {
                // MFA가 설정되어 있고 인증 필요
                // factor ID 가져오기
                const { data: factorsData, error: factorsError } = await this.supabase.auth.mfa.listFactors();

                if (factorsError) {
                    console.error('MFA factor 목록 오류:', factorsError);
                    this.proceedToChat();
                    return;
                }

                const totpFactors = factorsData.totp || [];
                if (totpFactors.length > 0) {
                    // 검증된(verified) factor 찾기
                    const verifiedFactor = totpFactors.find(f => f.status === 'verified');
                    if (verifiedFactor) {
                        this.mfaFactorId = verifiedFactor.id;
                        this.showMfaScreen();
                        return;
                    }
                }

                // 검증된 factor가 없으면 등록 필요
                await this.startTotpEnroll();

            } else if (currentLevel === 'aal2') {
                // 이미 MFA 인증 완료
                this.proceedToChat();

            } else {
                // MFA 미설정 - 등록 화면으로 이동 (선택적으로 스킵 가능)
                // 여기서는 MFA 등록을 필수로 설정
                await this.startTotpEnroll();
            }

        } catch (error) {
            console.error('MFA 상태 확인 중 오류:', error);
            this.proceedToChat();
        }
    }

    async startTotpEnroll() {
        try {
            const { data, error } = await this.supabase.auth.mfa.enroll({
                factorType: 'totp',
                friendlyName: 'Authenticator App'
            });

            if (error) {
                throw error;
            }

            console.log('TOTP 등록 데이터:', data);

            // QR 코드 및 비밀키 표시
            this.mfaFactorId = data.id;
            this.totpQrCode.src = data.totp.qr_code;
            this.totpSecret.textContent = data.totp.secret;

            this.showTotpEnrollScreen();

        } catch (error) {
            console.error('TOTP 등록 시작 오류:', error);
            this.showLoginError('2단계 인증 설정 중 오류가 발생했습니다.');
            // 오류 시 로그인 화면으로
            this.showLoginScreen();
        }
    }

    async verifyTotpEnroll() {
        const code = this.totpEnrollInput.value.trim();

        if (code.length !== 6) {
            this.showTotpEnrollError('6자리 코드를 입력하세요.');
            return;
        }

        this.totpEnrollBtn.disabled = true;
        this.totpEnrollBtn.textContent = '확인 중...';
        this.hideTotpEnrollError();

        try {
            // Challenge 생성
            const { data: challengeData, error: challengeError } = await this.supabase.auth.mfa.challenge({
                factorId: this.mfaFactorId
            });

            if (challengeError) {
                throw challengeError;
            }

            // Verify
            const { data, error } = await this.supabase.auth.mfa.verify({
                factorId: this.mfaFactorId,
                challengeId: challengeData.id,
                code
            });

            if (error) {
                throw error;
            }

            console.log('TOTP 등록 완료:', data);
            this.proceedToChat();

        } catch (error) {
            console.error('TOTP 등록 인증 오류:', error);
            this.showTotpEnrollError('인증 코드가 올바르지 않습니다.');
            this.totpEnrollInput.value = '';
            this.totpEnrollInput.focus();
        } finally {
            this.totpEnrollBtn.disabled = false;
            this.totpEnrollBtn.textContent = '등록 완료';
        }
    }

    showMfaScreen() {
        this.loginScreen.classList.add('hidden');
        this.chatScreen.classList.add('hidden');
        this.totpEnrollScreen.classList.add('hidden');
        this.mfaScreen.classList.remove('hidden');
        this.mfaInput.value = '';
        this.hideMfaError();
        this.mfaInput.focus();
    }

    showTotpEnrollScreen() {
        this.loginScreen.classList.add('hidden');
        this.chatScreen.classList.add('hidden');
        this.mfaScreen.classList.add('hidden');
        this.totpEnrollScreen.classList.remove('hidden');
        this.totpEnrollInput.value = '';
        this.hideTotpEnrollError();
        this.totpEnrollInput.focus();
    }

    showLoginScreen() {
        this.chatScreen.classList.add('hidden');
        this.mfaScreen.classList.add('hidden');
        this.totpEnrollScreen.classList.add('hidden');
        this.loginScreen.classList.remove('hidden');
        this.loginBtn.disabled = false;
        this.loginBtn.textContent = '로그인';
    }

    async verifyMfa() {
        const code = this.mfaInput.value.trim();

        if (code.length !== 6) {
            this.showMfaError('6자리 코드를 입력하세요.');
            return;
        }

        this.mfaVerifyBtn.disabled = true;
        this.mfaVerifyBtn.textContent = '인증 중...';
        this.hideMfaError();

        try {
            // Challenge 생성
            const { data: challengeData, error: challengeError } = await this.supabase.auth.mfa.challenge({
                factorId: this.mfaFactorId
            });

            if (challengeError) {
                throw challengeError;
            }

            // Verify
            const { data, error } = await this.supabase.auth.mfa.verify({
                factorId: this.mfaFactorId,
                challengeId: challengeData.id,
                code
            });

            if (error) {
                throw error;
            }

            console.log('MFA 인증 완료:', data);
            this.proceedToChat();

        } catch (error) {
            console.error('MFA 인증 오류:', error);
            this.showMfaError('인증 코드가 올바르지 않습니다.');
            this.mfaInput.value = '';
            this.mfaInput.focus();
        } finally {
            this.mfaVerifyBtn.disabled = false;
            this.mfaVerifyBtn.textContent = '인증하기';
        }
    }

    proceedToChat() {
        // 이미 채팅 화면이면 무시 (중복 호출 방지)
        if (!this.chatScreen.classList.contains('hidden')) {
            console.log('이미 채팅 화면입니다.');
            return;
        }

        this.loginScreen.classList.add('hidden');
        this.mfaScreen.classList.add('hidden');
        this.totpEnrollScreen.classList.add('hidden');
        this.chatScreen.classList.remove('hidden');

        // Realtime 채널 연결
        this.connectChannel();
    }

    showLoginError(message) {
        this.loginError.textContent = message;
        this.loginError.classList.remove('hidden');
    }

    hideLoginError() {
        this.loginError.classList.add('hidden');
    }

    showMfaError(message) {
        this.mfaError.textContent = message;
        this.mfaError.classList.remove('hidden');
    }

    hideMfaError() {
        this.mfaError.classList.add('hidden');
    }

    showTotpEnrollError(message) {
        this.totpEnrollError.textContent = message;
        this.totpEnrollError.classList.remove('hidden');
    }

    hideTotpEnrollError() {
        this.totpEnrollError.classList.add('hidden');
    }

    async logout() {
        if (!confirm('로그아웃 하시겠습니까?')) {
            return;
        }

        try {
            await this.cleanup();
            await this.supabase.auth.signOut();

            // 페이지 새로고침으로 모든 상태 초기화
            window.location.reload();

        } catch (error) {
            console.error('로그아웃 오류:', error);
            // 오류가 발생해도 새로고침
            window.location.reload();
        }
    }

    async clearSession() {
        if (!confirm('새 세션을 시작하시겠습니까?\n채팅 내역이 초기화되고 Claude의 대화 컨텍스트가 리셋됩니다.')) {
            return;
        }

        // 채팅 내역 초기화
        this.chatContainer.innerHTML = '';
        this.currentProgress = null;

        // Python 봇에 세션 리셋 요청 전송
        if (this.channel) {
            try {
                const { data: { session } } = await this.supabase.auth.getSession();
                const accessToken = session?.access_token || '';

                await this.channel.send({
                    type: 'broadcast',
                    event: 'session_reset',
                    payload: {
                        username: this.username,
                        auth_token: accessToken
                    }
                });
                this.addSystemMessage('새 세션이 시작되었습니다.');
            } catch (error) {
                console.error('세션 리셋 요청 실패:', error);
                this.addSystemMessage('세션 리셋 요청 실패. 채팅 내역만 초기화되었습니다.');
            }
        } else {
            this.addSystemMessage('채팅 내역이 초기화되었습니다. (서버 연결 없음)');
        }
    }

    updateStatus(text, isConnected) {
        this.statusEl.textContent = text;
        if (isConnected) {
            this.statusEl.classList.add('connected');
        } else {
            this.statusEl.classList.remove('connected');
        }
    }

    async connectChannel() {
        if (this.isConnecting) {
            console.log('이미 연결 시도 중...');
            return;
        }

        this.isConnecting = true;
        this.subscribedHandled = false;  // 새 연결 시작 시 플래그 리셋
        this.updateStatus('연결 중...', false);

        try {
            // 기존 연결 정리
            await this.cleanup();

            this.channel = this.supabase.channel(CHANNEL_NAME);

            // 채널 이벤트 설정
            this.channel
                .on('broadcast', { event: 'message' }, (payload) => {
                    this.onMessage(payload.payload);
                })
                .on('broadcast', { event: 'progress' }, (payload) => {
                    this.onProgress(payload.payload);
                })
                .on('broadcast', { event: 'permission_request' }, (payload) => {
                    this.onPermissionRequest(payload.payload);
                })
                .on('broadcast', { event: 'queue_status' }, (payload) => {
                    this.onQueueStatus(payload.payload);
                })
                .on('broadcast', { event: 'usage_status' }, (payload) => {
                    this.onUsageStatus(payload.payload);
                })
                .subscribe((status, err) => {
                    this.isConnecting = false;

                    if (status === 'SUBSCRIBED') {
                        console.log('채널 연결 성공');
                        this.reconnectAttempts = 0;
                        this.updateStatus(`연결됨 - ${this.username}`, true);

                        // 중복 SUBSCRIBED 이벤트 방지
                        if (!this.subscribedHandled) {
                            this.subscribedHandled = true;

                            // 첫 연결과 재연결 구분
                            if (!this.hasConnectedOnce) {
                                this.hasConnectedOnce = true;
                                this.addSystemMessage(`${this.username}님이 입장했습니다.`);
                            } else {
                                this.addSystemMessage('다시 연결되었습니다.');
                            }

                            // 사용량 조회 요청
                            this.requestUsageStatus();
                        }

                        this.startHeartbeat();

                    } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR') {
                        console.log('채널 연결 실패/종료:', status, err);
                        this.subscribedHandled = false;  // 재연결 시 메시지 표시를 위해 리셋
                        this.updateStatus('연결 끊김', false);
                        this.scheduleReconnect();
                    } else if (status === 'TIMED_OUT') {
                        console.log('채널 연결 타임아웃');
                        this.subscribedHandled = false;  // 재연결 시 메시지 표시를 위해 리셋
                        this.updateStatus('연결 타임아웃', false);
                        this.scheduleReconnect();
                    }
                });

        } catch (error) {
            console.error('연결 오류:', error);
            this.isConnecting = false;
            this.updateStatus('연결 실패', false);
            this.scheduleReconnect();
        }
    }

    async cleanup() {
        // 타이머 정리
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }

        // 채널 정리 (완전히 제거)
        if (this.channel) {
            try {
                await this.supabase.removeChannel(this.channel);
            } catch (e) {
                console.log('채널 정리 중 오류:', e);
            }
            this.channel = null;
        }
    }

    scheduleReconnect() {
        if (this.reconnectTimer) return;

        this.reconnectAttempts++;

        if (this.reconnectAttempts > MAX_RECONNECT_ATTEMPTS) {
            this.updateStatus('연결 실패 - 새로고침 필요', false);
            this.addSystemMessage('연결을 복구할 수 없습니다. 페이지를 새로고침해주세요.');
            return;
        }

        // 지수 백오프: 재시도 횟수에 따라 대기 시간 증가
        const delay = Math.min(RECONNECT_DELAY * Math.pow(1.5, this.reconnectAttempts - 1), 30000);
        this.updateStatus(`재연결 중... (${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`, false);

        console.log(`${delay}ms 후 재연결 시도 (${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);

        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.reconnect();
        }, delay);
    }

    async reconnect() {
        console.log('재연결 시도...');
        await this.connectChannel();
    }

    checkConnection() {
        // 연결 중이면 무시
        if (this.isConnecting) {
            console.log('연결 상태 확인: 이미 연결 시도 중');
            return;
        }

        // 연결 상태 확인 및 필요시 재연결
        if (!this.channel) {
            console.log('연결 상태 확인: 연결되지 않음, 재연결 시도');
            this.reconnect();
        }
    }

    startHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
        }

        this.heartbeatTimer = setInterval(() => {
            this.checkConnection();
        }, HEARTBEAT_INTERVAL);
    }

    async requestUsageStatus() {
        // Python 봇에게 사용량 조회 요청 전송
        if (this.channel) {
            try {
                await this.channel.send({
                    type: 'broadcast',
                    event: 'request_usage',
                    payload: {}
                });
                console.log('사용량 조회 요청 전송');
            } catch (error) {
                console.error('사용량 조회 요청 실패:', error);
            }
        }
    }

    onMessage(data) {
        const { username, message } = data;
        if (username === this.username) return;
        this.addMessage(username, message, false);
    }

    onQueueStatus(data) {
        const { count, items } = data;
        console.log('대기열 상태:', count, items);

        // 대기열이 비워졌을 때 완료 알림 소리 재생
        if (this.previousQueueCount > 0 && count === 0 && this.queueSoundEnabled) {
            this.playQueueCompleteSound();
        }
        this.previousQueueCount = count;

        // 고정된 큐 UI 업데이트 (항상 표시, 숨기지 않음)
        this.updateQueueUI(count, items);
    }

    onUsageStatus(data) {
        const { today, totals, block } = data;
        console.log('사용량 상태:', data);

        const usageTodayEl = document.getElementById('usageToday');
        const usageBlockEl = document.getElementById('usageBlock');
        const usageRemainingEl = document.getElementById('usageRemaining');

        // 오늘 사용량 표시
        if (usageTodayEl) {
            if (today && today.totalCost !== undefined) {
                const todayCostUsd = today.totalCost;
                const todayCostKrw = todayCostUsd * USD_TO_KRW;
                usageTodayEl.textContent = `$${todayCostUsd.toFixed(2)} (₩${Math.round(todayCostKrw).toLocaleString()})`;

                // 비용에 따른 색상 변경 (경고: $50 이상, 위험: $100 이상)
                usageTodayEl.classList.remove('warning', 'danger');
                if (todayCostUsd >= 100) {
                    usageTodayEl.classList.add('danger');
                } else if (todayCostUsd >= 50) {
                    usageTodayEl.classList.add('warning');
                }
            } else {
                usageTodayEl.textContent = '$0.00';
            }
        }

        // 5시간 블록 사용량 표시
        if (usageBlockEl) {
            if (block && block.costUSD !== undefined) {
                const blockCostUsd = block.costUSD;
                const blockCostKrw = blockCostUsd * USD_TO_KRW;
                usageBlockEl.textContent = `$${blockCostUsd.toFixed(2)} (₩${Math.round(blockCostKrw).toLocaleString()})`;
            } else {
                usageBlockEl.textContent = '-';
            }
        }

        // 남은 시간 표시
        if (usageRemainingEl) {
            if (block && block.remainingMinutes !== undefined) {
                const remaining = block.remainingMinutes;
                if (remaining > 60) {
                    const hours = Math.floor(remaining / 60);
                    const mins = remaining % 60;
                    usageRemainingEl.textContent = `${hours}시간 ${mins}분`;
                } else {
                    usageRemainingEl.textContent = `${remaining}분`;
                }

                // 남은 시간에 따른 색상 변경 (경고: 60분 이하, 위험: 30분 이하)
                usageRemainingEl.classList.remove('warning', 'danger');
                if (remaining <= 30) {
                    usageRemainingEl.classList.add('danger');
                } else if (remaining <= 60) {
                    usageRemainingEl.classList.add('warning');
                }
            } else {
                usageRemainingEl.textContent = '-';
            }
        }
    }

    initQueueUI() {
        // HTML에 고정된 큐 UI 요소 참조
        this.queueElement = document.getElementById('queueContainer');
        if (!this.queueElement) return;

        // 헤더 클릭 시 접기/펼치기
        const header = this.queueElement.querySelector('.queue-header');
        header.addEventListener('click', () => {
            const body = this.queueElement.querySelector('.queue-body');
            const toggle = this.queueElement.querySelector('.queue-toggle');
            if (body.classList.contains('collapsed')) {
                body.classList.remove('collapsed');
                toggle.textContent = '접기';
                this.queueCollapsed = false;
            } else {
                body.classList.add('collapsed');
                toggle.textContent = '펼치기';
                this.queueCollapsed = true;
            }
        });
    }

    initUsageInfoPanel() {
        const infoIcon = document.getElementById('usageInfoIcon');
        const infoPanel = document.getElementById('usageInfoPanel');
        const closeBtn = document.getElementById('usageInfoClose');

        if (!infoIcon || !infoPanel) return;

        // 아이콘 클릭 시 토글
        infoIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            const isVisible = infoPanel.classList.contains('visible');
            if (isVisible) {
                infoPanel.classList.remove('visible');
                infoIcon.classList.remove('active');
            } else {
                infoPanel.classList.add('visible');
                infoIcon.classList.add('active');
            }
        });

        // 닫기 버튼 클릭
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                infoPanel.classList.remove('visible');
                infoIcon.classList.remove('active');
            });
        }

        // 패널 외부 클릭 시 닫기
        document.addEventListener('click', (e) => {
            if (!infoPanel.contains(e.target) && !infoIcon.contains(e.target)) {
                infoPanel.classList.remove('visible');
                infoIcon.classList.remove('active');
            }
        });
    }

    updateQueueUI(count, items) {
        if (!this.queueElement) return;

        const countEl = this.queueElement.querySelector('.queue-count');
        const bodyEl = this.queueElement.querySelector('.queue-body');

        countEl.textContent = count;

        if (items && items.length > 0) {
            let itemsHtml = '';
            items.forEach((item, index) => {
                itemsHtml += `
                    <div class="queue-item">
                        <div class="queue-item-number">${index + 1}</div>
                        <div class="queue-item-content">
                            <div class="queue-item-sender">${this.escapeHtml(item.sender)}</div>
                            <div class="queue-item-message">${this.escapeHtml(item.message)}</div>
                        </div>
                    </div>
                `;
            });
            bodyEl.innerHTML = itemsHtml;
        } else {
            bodyEl.innerHTML = '<div class="queue-empty">대기 중인 요청이 없습니다.</div>';
        }

        // 접힘 상태 유지
        const toggle = this.queueElement.querySelector('.queue-toggle');
        if (this.queueCollapsed) {
            bodyEl.classList.add('collapsed');
            toggle.textContent = '펼치기';
        } else {
            bodyEl.classList.remove('collapsed');
            toggle.textContent = '접기';
        }
    }

    onProgress(data) {
        const { type } = data;

        switch (type) {
            case 'start':
                this.createProgressUI();
                break;
            case 'init':
                this.updateProgressInit(data);
                break;
            case 'tool_start':
                this.updateProgressToolStart(data);
                break;
            case 'tool_end':
                this.updateProgressToolEnd(data);
                break;
            case 'complete':
                this.updateProgressComplete(data);
                break;
            case 'error':
                this.updateProgressError(data);
                break;
            case 'permission_request':
                // progress 이벤트로도 권한 요청이 올 수 있음
                this.onPermissionRequest(data);
                break;
        }
    }

    onPermissionRequest(data) {
        const { request_id, tool, detail } = data;
        if (!request_id) return;

        // 이미 처리된 요청인지 확인
        if (this.pendingPermissions[request_id]) return;

        const permissionEl = document.createElement('div');
        permissionEl.className = 'permission-container';
        permissionEl.id = `permission-${request_id}`;
        permissionEl.innerHTML = `
            <div class="permission-header">
                <div class="permission-icon">⚠</div>
                <div class="permission-title">권한 요청: ${this.escapeHtml(tool)}</div>
            </div>
            <div class="permission-detail">${this.escapeHtml(detail || '(상세 정보 없음)')}</div>
            <div class="permission-buttons">
                <button class="permission-btn approve" data-request-id="${request_id}">승인</button>
                <button class="permission-btn deny" data-request-id="${request_id}">거부</button>
            </div>
        `;

        // 버튼 이벤트 바인딩
        const approveBtn = permissionEl.querySelector('.permission-btn.approve');
        const denyBtn = permissionEl.querySelector('.permission-btn.deny');

        approveBtn.addEventListener('click', () => this.sendPermissionResponse(request_id, true, permissionEl));
        denyBtn.addEventListener('click', () => this.sendPermissionResponse(request_id, false, permissionEl));

        this.chatContainer.appendChild(permissionEl);
        this.pendingPermissions[request_id] = permissionEl;
        this.scrollToBottom();

        // 알림음 (선택사항)
        this.playNotificationSound();
    }

    async sendPermissionResponse(requestId, approved, element) {
        try {
            // 버튼 비활성화
            const buttons = element.querySelectorAll('.permission-btn');
            buttons.forEach(btn => btn.disabled = true);

            await this.channel.send({
                type: 'broadcast',
                event: 'permission_response',
                payload: {
                    request_id: requestId,
                    approved: approved
                }
            });

            // UI 업데이트
            element.classList.add('permission-resolved');
            const iconEl = element.querySelector('.permission-icon');
            const titleEl = element.querySelector('.permission-title');

            if (approved) {
                iconEl.textContent = '✓';
                iconEl.style.background = '#4ade80';
                titleEl.textContent += ' - 승인됨';
                titleEl.style.color = '#4ade80';
            } else {
                iconEl.textContent = '✕';
                iconEl.style.background = '#ef4444';
                titleEl.textContent += ' - 거부됨';
                titleEl.style.color = '#ef4444';
            }

            // 버튼 숨기기
            const buttonsDiv = element.querySelector('.permission-buttons');
            buttonsDiv.style.display = 'none';

            delete this.pendingPermissions[requestId];

        } catch (error) {
            console.error('권한 응답 전송 오류:', error);
            // 버튼 다시 활성화
            const buttons = element.querySelectorAll('.permission-btn');
            buttons.forEach(btn => btn.disabled = false);
        }
    }

    playNotificationSound() {
        // 간단한 비프음 (Web Audio API)
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            gainNode.gain.value = 0.1;

            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.15);
        } catch (e) {
            // 오디오 재생 실패는 무시
        }
    }

    playQueueCompleteSound() {
        // 대기열 완료 알림 소리 (두 음 연속 - 완료 느낌)
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const gainNode = audioContext.createGain();
            gainNode.connect(audioContext.destination);
            gainNode.gain.value = 0.15;

            // 첫 번째 음 (C5 - 523Hz)
            const osc1 = audioContext.createOscillator();
            osc1.connect(gainNode);
            osc1.frequency.value = 523;
            osc1.type = 'sine';
            osc1.start(audioContext.currentTime);
            osc1.stop(audioContext.currentTime + 0.15);

            // 두 번째 음 (G5 - 784Hz)
            const osc2 = audioContext.createOscillator();
            osc2.connect(gainNode);
            osc2.frequency.value = 784;
            osc2.type = 'sine';
            osc2.start(audioContext.currentTime + 0.15);
            osc2.stop(audioContext.currentTime + 0.3);
        } catch (e) {
            // 오디오 재생 실패는 무시
        }
    }

    toggleQueueSound() {
        this.queueSoundEnabled = !this.queueSoundEnabled;
        localStorage.setItem('queue_sound', this.queueSoundEnabled ? 'true' : 'false');
        return this.queueSoundEnabled;
    }

    createProgressUI() {
        // 기존 진행 UI 제거
        if (this.currentProgress) {
            this.currentProgress.remove();
        }

        const progressEl = document.createElement('div');
        progressEl.className = 'progress-container';
        progressEl.id = 'currentProgress';
        progressEl.innerHTML = `
            <div class="progress-header">
                <div class="progress-icon spinning">C</div>
                <div class="progress-title">Claude 처리 중...</div>
                <div class="progress-model"></div>
            </div>
            <div class="progress-steps"></div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: 10%"></div>
            </div>
            <div class="progress-stats"></div>
        `;

        this.chatContainer.appendChild(progressEl);
        this.currentProgress = progressEl;
        this.scrollToBottom();
    }

    updateProgressInit(data) {
        if (!this.currentProgress) return;

        const modelEl = this.currentProgress.querySelector('.progress-model');
        const barEl = this.currentProgress.querySelector('.progress-bar');

        // 모델명 간소화
        let modelName = data.model || 'unknown';
        if (modelName.includes('opus')) modelName = 'Opus';
        else if (modelName.includes('sonnet')) modelName = 'Sonnet';
        else if (modelName.includes('haiku')) modelName = 'Haiku';

        modelEl.textContent = modelName;
        barEl.style.width = '20%';
    }

    updateProgressToolStart(data) {
        if (!this.currentProgress) return;

        const stepsEl = this.currentProgress.querySelector('.progress-steps');
        const barEl = this.currentProgress.querySelector('.progress-bar');

        // 이전 step을 completed로 변경
        const prevStep = stepsEl.querySelector('.progress-step.active');
        if (prevStep) {
            prevStep.classList.remove('active');
            prevStep.classList.add('completed');
            prevStep.querySelector('.step-indicator').classList.remove('active');
            prevStep.querySelector('.step-indicator').classList.add('completed');
            prevStep.querySelector('.step-indicator').textContent = '✓';
        }

        // 새 step 추가
        const stepEl = document.createElement('div');
        stepEl.className = 'progress-step active';
        stepEl.dataset.turn = data.turn;

        const toolIcon = this.getToolIcon(data.tool);

        // Bash 명령어는 별도 표시, 나머지는 간략히 표시
        let detailHtml = '';
        if (data.tool === 'Bash' && data.detail) {
            detailHtml = `<div class="bash-command">${this.escapeHtml(data.detail)}</div>`;
        } else if (data.detail) {
            detailHtml = ` - ${this.escapeHtml(data.detail)}`;
        }

        let editDiffHtml = '';
        if (data.tool === 'Edit' && data.edit_info && !data.edit_info.type) {
            // Edit 도구: 변경 전/후 비교
            const editId = `edit-diff-${data.turn}`;
            editDiffHtml = `
                <div class="edit-diff" id="${editId}">
                    <div class="edit-diff-header">
                        <span>변경 내용</span>
                        <span class="edit-diff-toggle" onclick="toggleEditDiff('${editId}')">접기</span>
                    </div>
                    <div class="edit-diff-content">
                        <div class="diff-old">${this.escapeHtml(data.edit_info.old || '(없음)')}</div>
                        <div class="diff-new">${this.escapeHtml(data.edit_info.new || '(없음)')}</div>
                    </div>
                </div>
            `;
        } else if (data.tool === 'Write' && data.edit_info && data.edit_info.type === 'write') {
            // Write 도구: 파일 내용 표시
            const writeId = `write-content-${data.turn}`;
            editDiffHtml = `
                <div class="write-content" id="${writeId}">
                    <div class="write-content-header">
                        <span>파일 내용</span>
                        <span class="write-content-toggle" onclick="toggleWriteContent('${writeId}')">접기</span>
                    </div>
                    <div class="write-content-body">
                        <pre>${this.escapeHtml(data.edit_info.content || '(없음)')}</pre>
                    </div>
                </div>
            `;
        } else if (data.tool === 'TodoWrite' && data.edit_info && data.edit_info.type === 'todo') {
            // TodoWrite 도구: 할 일 목록 표시
            const todoId = `todo-list-${data.turn}`;
            const todos = data.edit_info.todos || [];
            let todoItemsHtml = '';
            for (const todo of todos) {
                const status = todo.status || 'pending';
                const content = todo.content || '';
                const statusIcon = status === 'pending' ? '○' : status === 'in_progress' ? '◐' : '✓';
                const contentClass = status === 'completed' ? 'todo-content completed' : 'todo-content';
                todoItemsHtml += `
                    <div class="todo-item">
                        <div class="todo-status ${status}">${statusIcon}</div>
                        <span class="${contentClass}">${this.escapeHtml(content)}</span>
                    </div>
                `;
            }
            editDiffHtml = `
                <div class="todo-list" id="${todoId}">
                    <div class="todo-list-header">
                        <span>📋 할 일 목록 (${todos.length}개)</span>
                        <span class="todo-list-toggle" onclick="toggleTodoList('${todoId}')">접기</span>
                    </div>
                    <div class="todo-list-body">
                        ${todoItemsHtml}
                    </div>
                </div>
            `;
        } else if (data.tool === 'AskUserQuestion' && data.edit_info && data.edit_info.type === 'ask_user') {
            // AskUserQuestion 도구: 사용자 질문 UI 표시
            const askId = `ask-user-${data.turn}`;
            const questions = data.edit_info.questions || [];
            let questionsHtml = '';

            for (let qIdx = 0; qIdx < questions.length; qIdx++) {
                const q = questions[qIdx];
                const questionText = q.question || '';
                const header = q.header || '';
                const options = q.options || [];
                const multiSelect = q.multiSelect || false;

                let optionsHtml = '';
                for (let oIdx = 0; oIdx < options.length; oIdx++) {
                    const opt = options[oIdx];
                    const label = opt.label || '';
                    const desc = opt.description || '';
                    optionsHtml += `
                        <button class="ask-option-btn" data-question="${qIdx}" data-option="${oIdx}" data-multi="${multiSelect}">
                            <div class="ask-option-label">${this.escapeHtml(label)}</div>
                            ${desc ? `<div class="ask-option-desc">${this.escapeHtml(desc)}</div>` : ''}
                        </button>
                    `;
                }
                // 기타 옵션 (Other) 추가
                optionsHtml += `
                    <button class="ask-option-btn" data-question="${qIdx}" data-option="other" data-multi="${multiSelect}">
                        <div class="ask-option-label">기타 (직접 입력)</div>
                    </button>
                    <input type="text" class="ask-other-input hidden" data-question="${qIdx}" placeholder="직접 입력...">
                `;

                questionsHtml += `
                    <div class="ask-question-item" data-question-idx="${qIdx}">
                        ${header ? `<span class="ask-question-header">${this.escapeHtml(header)}</span>` : ''}
                        <div class="ask-question-text">${this.escapeHtml(questionText)}</div>
                        <div class="ask-question-options">
                            ${optionsHtml}
                        </div>
                    </div>
                `;
            }

            editDiffHtml = `
                <div class="ask-user-question" id="${askId}">
                    <div class="ask-user-question-header">
                        <span>❓ 사용자 응답 필요 (${questions.length}개 질문)</span>
                    </div>
                    <div class="ask-user-question-body">
                        ${questionsHtml}
                        <button class="ask-submit-btn" data-ask-id="${askId}" disabled>응답 제출</button>
                    </div>
                </div>
            `;

            // 이벤트 바인딩을 위해 setTimeout 사용 (DOM 렌더링 후)
            setTimeout(() => this.bindAskUserEvents(askId), 0);
        }

        stepEl.innerHTML = `
            <div class="step-indicator active">${data.turn}</div>
            <span>${toolIcon} ${data.tool}${data.tool === 'Bash' || data.tool === 'Edit' || data.tool === 'Write' || data.tool === 'TodoWrite' ? '' : detailHtml}</span>
            ${data.tool === 'Bash' ? detailHtml : ''}
            ${editDiffHtml}
        `;

        stepsEl.appendChild(stepEl);
        barEl.style.width = `${Math.min(20 + data.turn * 20, 80)}%`;
        this.scrollToBottom();
    }

    updateProgressToolEnd(data) {
        if (!this.currentProgress) return;

        const stepEl = this.currentProgress.querySelector(`.progress-step[data-turn="${data.turn}"]`);
        if (stepEl) {
            stepEl.classList.remove('active');
            stepEl.classList.add('completed');
            const indicator = stepEl.querySelector('.step-indicator');
            indicator.classList.remove('active');
            indicator.classList.add('completed');
            indicator.textContent = '✓';

            if (data.lines) {
                const span = stepEl.querySelector('span');
                span.textContent += ` (${data.lines}줄)`;
            }
        }
    }

    updateProgressComplete(data) {
        if (!this.currentProgress) return;

        const iconEl = this.currentProgress.querySelector('.progress-icon');
        const titleEl = this.currentProgress.querySelector('.progress-title');
        const barEl = this.currentProgress.querySelector('.progress-bar');
        const statsEl = this.currentProgress.querySelector('.progress-stats');

        iconEl.classList.remove('spinning');
        iconEl.textContent = '✓';
        iconEl.style.background = '#4ade80';
        titleEl.textContent = 'Claude 완료';
        titleEl.style.color = '#4ade80';
        barEl.style.width = '100%';

        // 원화 계산 (서버에서 전달받거나 클라이언트에서 계산)
        const costKrw = data.cost_krw || (data.cost_usd * USD_TO_KRW);

        statsEl.innerHTML = `
            <div class="stat-item">
                <span>시간:</span>
                <span class="stat-value">${data.duration_sec.toFixed(1)}초</span>
            </div>
            <div class="stat-item">
                <span>비용:</span>
                <span class="stat-value">$${data.cost_usd.toFixed(4)} (₩${Math.round(costKrw).toLocaleString()})</span>
            </div>
            <div class="stat-item">
                <span>토큰:</span>
                <span class="stat-value">${data.input_tokens}/${data.output_tokens}</span>
            </div>
            <div class="stat-item">
                <span>턴:</span>
                <span class="stat-value">${data.turns}</span>
            </div>
        `;

        // 마지막 active step 완료 처리
        const lastStep = this.currentProgress.querySelector('.progress-step.active');
        if (lastStep) {
            lastStep.classList.remove('active');
            lastStep.classList.add('completed');
            const indicator = lastStep.querySelector('.step-indicator');
            indicator.classList.remove('active');
            indicator.classList.add('completed');
            indicator.textContent = '✓';
        }

        this.currentProgress = null;
    }

    updateProgressError(data) {
        if (!this.currentProgress) return;

        const iconEl = this.currentProgress.querySelector('.progress-icon');
        const titleEl = this.currentProgress.querySelector('.progress-title');
        const barEl = this.currentProgress.querySelector('.progress-bar');

        iconEl.classList.remove('spinning');
        iconEl.textContent = '!';
        iconEl.style.background = '#ef4444';
        titleEl.textContent = `오류: ${data.message}`;
        titleEl.style.color = '#ef4444';
        barEl.style.width = '100%';
        barEl.style.background = '#ef4444';

        this.currentProgress = null;
    }

    getToolIcon(tool) {
        const icons = {
            'Read': '📄',
            'Edit': '✏️',
            'Write': '📝',
            'Bash': '💻',
            'Grep': '🔍',
            'Glob': '📁',
            'WebFetch': '🌐',
            'WebSearch': '🔎',
            'AskUserQuestion': '❓'
        };
        return icons[tool] || '🔧';
    }

    bindAskUserEvents(askId) {
        const container = document.getElementById(askId);
        if (!container) return;

        const optionBtns = container.querySelectorAll('.ask-option-btn');
        const submitBtn = container.querySelector('.ask-submit-btn');
        const selectedAnswers = {};  // { questionIdx: [optionIdx...] or 'other' }

        optionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const questionIdx = btn.dataset.question;
                const optionIdx = btn.dataset.option;
                const isMulti = btn.dataset.multi === 'true';
                const otherInput = container.querySelector(`.ask-other-input[data-question="${questionIdx}"]`);

                if (optionIdx === 'other') {
                    // 기타 선택 시 입력창 표시
                    if (!selectedAnswers[questionIdx] || selectedAnswers[questionIdx] !== 'other') {
                        // 같은 질문의 다른 선택 해제
                        container.querySelectorAll(`.ask-option-btn[data-question="${questionIdx}"]`).forEach(b => {
                            b.classList.remove('selected');
                        });
                        btn.classList.add('selected');
                        selectedAnswers[questionIdx] = 'other';
                        otherInput.classList.remove('hidden');
                        otherInput.focus();
                    } else {
                        btn.classList.remove('selected');
                        delete selectedAnswers[questionIdx];
                        otherInput.classList.add('hidden');
                        otherInput.value = '';
                    }
                } else {
                    if (isMulti) {
                        // 멀티 선택
                        if (!selectedAnswers[questionIdx]) {
                            selectedAnswers[questionIdx] = [];
                        }
                        if (Array.isArray(selectedAnswers[questionIdx])) {
                            const idx = selectedAnswers[questionIdx].indexOf(optionIdx);
                            if (idx > -1) {
                                selectedAnswers[questionIdx].splice(idx, 1);
                                btn.classList.remove('selected');
                            } else {
                                selectedAnswers[questionIdx].push(optionIdx);
                                btn.classList.add('selected');
                            }
                            // 기타 선택 해제
                            const otherBtn = container.querySelector(`.ask-option-btn[data-question="${questionIdx}"][data-option="other"]`);
                            if (otherBtn) otherBtn.classList.remove('selected');
                            otherInput.classList.add('hidden');
                            otherInput.value = '';
                        }
                    } else {
                        // 단일 선택
                        container.querySelectorAll(`.ask-option-btn[data-question="${questionIdx}"]`).forEach(b => {
                            b.classList.remove('selected');
                        });
                        btn.classList.add('selected');
                        selectedAnswers[questionIdx] = [optionIdx];
                        otherInput.classList.add('hidden');
                        otherInput.value = '';
                    }
                }

                // 제출 버튼 활성화 여부 확인
                const totalQuestions = container.querySelectorAll('.ask-question-item').length;
                const answeredQuestions = Object.keys(selectedAnswers).filter(k => {
                    const val = selectedAnswers[k];
                    if (val === 'other') {
                        const input = container.querySelector(`.ask-other-input[data-question="${k}"]`);
                        return input && input.value.trim() !== '';
                    }
                    return Array.isArray(val) && val.length > 0;
                }).length;
                submitBtn.disabled = answeredQuestions < totalQuestions;
            });
        });

        // 기타 입력창 변경 시 제출 버튼 활성화 확인
        container.querySelectorAll('.ask-other-input').forEach(input => {
            input.addEventListener('input', () => {
                const totalQuestions = container.querySelectorAll('.ask-question-item').length;
                const answeredQuestions = Object.keys(selectedAnswers).filter(k => {
                    const val = selectedAnswers[k];
                    if (val === 'other') {
                        const inp = container.querySelector(`.ask-other-input[data-question="${k}"]`);
                        return inp && inp.value.trim() !== '';
                    }
                    return Array.isArray(val) && val.length > 0;
                }).length;
                submitBtn.disabled = answeredQuestions < totalQuestions;
            });
        });

        // 제출 버튼 클릭
        submitBtn.addEventListener('click', async () => {
            submitBtn.disabled = true;
            submitBtn.textContent = '제출 중...';

            // 응답 데이터 구성
            const answers = {};
            for (const [qIdx, val] of Object.entries(selectedAnswers)) {
                if (val === 'other') {
                    const input = container.querySelector(`.ask-other-input[data-question="${qIdx}"]`);
                    answers[qIdx] = input ? input.value.trim() : '';
                } else if (Array.isArray(val)) {
                    answers[qIdx] = val.join(',');
                }
            }

            try {
                // 응답을 채팅 메시지로 전송
                const responseText = Object.entries(answers).map(([qIdx, ans]) => {
                    return `Q${parseInt(qIdx) + 1}: ${ans}`;
                }).join(' | ');

                await this.channel.send({
                    type: 'broadcast',
                    event: 'message',
                    payload: {
                        username: this.username,
                        message: `[응답] ${responseText}`
                    }
                });

                // UI 업데이트
                container.classList.add('ask-user-resolved');
                submitBtn.textContent = '응답 완료';

                // 옵션 버튼 비활성화
                container.querySelectorAll('.ask-option-btn').forEach(btn => {
                    btn.classList.add('disabled');
                    btn.disabled = true;
                });
                container.querySelectorAll('.ask-other-input').forEach(input => {
                    input.disabled = true;
                });

                this.addMessage(this.username, `[응답] ${responseText}`, true);

            } catch (error) {
                console.error('응답 전송 오류:', error);
                submitBtn.disabled = false;
                submitBtn.textContent = '응답 제출';
                this.addSystemMessage('응답 전송 실패. 다시 시도해주세요.');
            }
        });
    }

    addMessage(sender, text, isMine = false) {
        const messageEl = document.createElement('div');
        messageEl.className = `message${isMine ? ' mine' : ''}`;

        // 모든 메시지에 마크다운 렌더링 적용
        const renderedText = this.renderMarkdown(text);

        messageEl.innerHTML = `
            <div class="sender">${this.escapeHtml(sender)}</div>
            <div class="text">${renderedText}</div>
        `;
        this.chatContainer.appendChild(messageEl);
        this.scrollToBottom();
    }

    renderMarkdown(text) {
        try {
            // marked 설정
            marked.setOptions({
                breaks: true,      // 줄바꿈을 <br>로 변환
                gfm: true,         // GitHub Flavored Markdown
                sanitize: false    // HTML 허용 (XSS 주의)
            });
            return marked.parse(text);
        } catch (e) {
            console.error('Markdown 렌더링 오류:', e);
            return this.escapeHtml(text);
        }
    }

    addSystemMessage(text) {
        const messageEl = document.createElement('div');
        messageEl.className = 'message';
        messageEl.style.background = '#2d2d44';
        messageEl.style.textAlign = 'center';
        messageEl.style.maxWidth = '100%';
        messageEl.innerHTML = `<div class="text" style="color: #888;">${this.escapeHtml(text)}</div>`;
        this.chatContainer.appendChild(messageEl);
        this.scrollToBottom();
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || !this.channel) return;

        try {
            // JWT 토큰 가져오기
            const { data: { session } } = await this.supabase.auth.getSession();
            const accessToken = session?.access_token || '';

            await this.channel.send({
                type: 'broadcast',
                event: 'message',
                payload: {
                    username: this.username,
                    message: message,
                    auth_token: accessToken
                }
            });

            this.addMessage(this.username, message, true);
            this.messageInput.value = '';
        } catch (error) {
            console.error('전송 오류:', error);
            this.addSystemMessage('메시지 전송 실패. 연결을 확인하세요.');
            this.checkConnection();
        }
    }

    scrollToBottom() {
        // 자동 스크롤 체크박스가 켜져있으면 항상 스크롤
        if (this.autoScrollCheckbox && this.autoScrollCheckbox.checked) {
            // DOM 업데이트 후 스크롤 (렌더링 완료 대기)
            requestAnimationFrame(() => {
                this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
            });
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Edit diff 접기/펼치기
function toggleEditDiff(editId) {
    const editEl = document.getElementById(editId);
    if (!editEl) return;

    const content = editEl.querySelector('.edit-diff-content');
    const toggle = editEl.querySelector('.edit-diff-toggle');

    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        toggle.textContent = '접기';
    } else {
        content.classList.add('collapsed');
        toggle.textContent = '펼치기';
    }
}

// Write content 접기/펼치기
function toggleWriteContent(writeId) {
    const writeEl = document.getElementById(writeId);
    if (!writeEl) return;

    const content = writeEl.querySelector('.write-content-body');
    const toggle = writeEl.querySelector('.write-content-toggle');

    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        toggle.textContent = '접기';
    } else {
        content.classList.add('collapsed');
        toggle.textContent = '펼치기';
    }
}

// TodoWrite 목록 접기/펼치기
function toggleTodoList(todoId) {
    const todoEl = document.getElementById(todoId);
    if (!todoEl) return;

    const content = todoEl.querySelector('.todo-list-body');
    const toggle = todoEl.querySelector('.todo-list-toggle');

    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        toggle.textContent = '접기';
    } else {
        content.classList.add('collapsed');
        toggle.textContent = '펼치기';
    }
}

// 앱 시작
document.addEventListener('DOMContentLoaded', () => {
    new ChatClient();
});
