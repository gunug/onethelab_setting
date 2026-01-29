import os
import sys
import json
import asyncio
import subprocess
import threading
import signal
import uuid
from queue import Queue, Empty
from dotenv import load_dotenv
from supabase._async.client import create_client, AsyncClient

# Windows asyncio SSL 종료 문제 해결
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# USD to KRW 환율 (2026년 1월 기준)
USD_TO_KRW = 1430

# 설정
RECONNECT_DELAY = 5  # 재연결 대기 시간 (초)
MAX_RECONNECT_ATTEMPTS = 10  # 최대 재연결 시도 횟수
CLAUDE_TIMEOUT = 300  # Claude CLI 타임아웃 (초)


def test_claude_cli():
    """Claude CLI 호출 테스트"""
    try:
        cmd = 'claude "test"'
        print(f"[실행 명령] {cmd}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=True,
            timeout=60
        )
        if result.returncode != 0:
            print(f"  stderr: {result.stderr}")
        return result.returncode == 0 and result.stdout
    except subprocess.TimeoutExpired:
        print("  타임아웃: Claude CLI 응답 없음")
        return False
    except Exception as e:
        print(f"  예외: {e}")
        return False


def run_claude_stream(prompt: str, output_queue: Queue, stop_event: threading.Event, session_id: str = None, is_resume: bool = False):
    """별도 스레드에서 Claude CLI 스트리밍 실행 (프린트 모드, stdin 방식, 세션 유지)"""
    process = None
    try:
        cmd = 'claude --output-format stream-json --verbose --dangerously-skip-permissions'
        if session_id:
            if is_resume:
                # 기존 세션 재개
                cmd += f' -r "{session_id}"'
                print(f"[DEBUG] 세션 재개 모드: {session_id}")
            else:
                # 새 세션 시작
                cmd += f' --session-id "{session_id}"'
                print(f"[DEBUG] 새 세션 시작: {session_id}")
        cmd += ' -p -'
        print(f"[DEBUG] run_claude_stream 시작")
        print(f"[실행 명령] {cmd}")
        print(f"[stdin 입력] {prompt}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            shell=True,
            text=True,
            encoding="utf-8",
            bufsize=1
        )
        print(f"[DEBUG] 프로세스 생성 완료, PID: {process.pid}")

        # stdin으로 프롬프트 전달
        print(f"[DEBUG] stdin 쓰기 중...")
        process.stdin.write(prompt)
        process.stdin.close()
        print(f"[DEBUG] stdin 닫힘")

        # stderr 읽기 스레드
        def read_stderr():
            print(f"[DEBUG] stderr 스레드 시작")
            try:
                while not stop_event.is_set():
                    line = process.stderr.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        print(f"[DEBUG] stderr: {line[:100]}")
                        output_queue.put(("stderr", line))
            except Exception as e:
                print(f"[DEBUG] stderr 예외: {e}")
            print(f"[DEBUG] stderr 스레드 종료")

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        # stdout 읽기
        print(f"[DEBUG] stdout 읽기 시작")
        line_count = 0
        try:
            while not stop_event.is_set():
                line = process.stdout.readline()
                if not line:
                    print(f"[DEBUG] stdout: EOF")
                    break
                line = line.strip()
                if line:
                    line_count += 1
                    print(f"[DEBUG] stdout [{line_count}]: {line[:100]}...")
                    output_queue.put(("line", line))
        except Exception as e:
            print(f"[DEBUG] stdout 예외: {e}")
            output_queue.put(("error", f"stdout 읽기 오류: {e}"))
        print(f"[DEBUG] stdout 읽기 완료, 총 {line_count}줄")

        # 프로세스 종료 대기
        print(f"[DEBUG] 프로세스 종료 대기 중...")
        try:
            process.wait(timeout=10)
            print(f"[DEBUG] 프로세스 종료, returncode: {process.returncode}")
        except subprocess.TimeoutExpired:
            print(f"[DEBUG] 타임아웃, 강제 종료")
            process.kill()
            process.wait()

        output_queue.put(("done", process.returncode))

    except Exception as e:
        print(f"[DEBUG] run_claude_stream 예외: {e}")
        output_queue.put(("error", str(e)))
    finally:
        if process and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=5)
            except:
                pass


class ChatBot:
    CLAUDE_USERNAME = "Claude"

    def __init__(self, username: str = "Claude", enable_claude: bool = True):
        self.username = username
        self.supabase: AsyncClient = None
        self.channel = None
        self.enable_claude = enable_claude
        self.loop = None
        self.is_connected = False
        self.should_run = True
        self.reconnect_attempts = 0
        self.claude_processing = False
        self.current_stop_event = None
        self.session_id = str(uuid.uuid4())  # 세션 ID 생성
        self.session_started = False  # 세션 시작 여부
        # 요청 큐 관련
        self.request_queue = []  # 대기 중인 요청 목록 [{"sender": str, "message": str}, ...]
        self.queue_lock = threading.Lock()  # 큐 접근 동기화

    def reset_session(self):
        """Claude 세션 리셋 - 새 세션 ID 생성"""
        self.session_id = str(uuid.uuid4())
        self.session_started = False

    def add_to_queue(self, sender: str, message: str):
        """요청을 대기열에 추가"""
        with self.queue_lock:
            self.request_queue.append({"sender": sender, "message": message})
            queue_length = len(self.request_queue)
            print(f"[대기열] 요청 추가: {sender} - '{message[:30]}...' (대기: {queue_length}개)")
            return queue_length

    def get_next_from_queue(self):
        """대기열에서 다음 요청 가져오기 (제거)"""
        with self.queue_lock:
            if self.request_queue:
                return self.request_queue.pop(0)
            return None

    def peek_next_in_queue(self):
        """대기열의 다음 요청 확인 (제거하지 않음)"""
        with self.queue_lock:
            if self.request_queue:
                return self.request_queue[0]
            return None

    def get_queue_status(self):
        """대기열 상태 조회"""
        with self.queue_lock:
            return {
                "count": len(self.request_queue),
                "items": [{"sender": r["sender"], "message": r["message"][:50]} for r in self.request_queue]
            }

    def on_broadcast(self, payload):
        """수신된 메시지 출력 및 Claude 전달"""
        data = payload.get("payload", {})
        event_type = payload.get("event", "message")

        if event_type == "progress":
            return

        if event_type == "session_reset":
            sender = data.get("username", "unknown")
            self.reset_session()
            print(f"[시스템] {sender}님이 세션을 리셋했습니다. 새 세션 ID: {self.session_id}")
            return

        sender = data.get("username", "unknown")
        message = data.get("message", "")
        print(f"[{sender}]: {message}")

        if self.enable_claude and sender != self.username and sender != self.CLAUDE_USERNAME:
            if self.loop:
                # 모든 요청을 먼저 대기열에 추가
                queue_length = self.add_to_queue(sender, message)
                # 대기열 상태 브로드캐스트
                asyncio.run_coroutine_threadsafe(
                    self.send_queue_status(), self.loop
                )
                # 처리 중이 아니면 대기열에서 꺼내서 처리 시작
                if not self.claude_processing:
                    asyncio.run_coroutine_threadsafe(
                        self.process_next_in_queue(), self.loop
                    )

    async def send_progress(self, progress_type: str, data: dict):
        """진행 상황을 채팅방에 전송"""
        if self.channel and self.is_connected:
            try:
                await self.channel.send_broadcast(
                    event="progress",
                    data={
                        "type": progress_type,
                        **data
                    }
                )
            except Exception as e:
                print(f"[경고] 진행 상황 전송 실패: {e}")

    async def send_queue_status(self):
        """대기열 상태를 채팅방에 전송"""
        if self.channel and self.is_connected:
            try:
                status = self.get_queue_status()
                await self.channel.send_broadcast(
                    event="queue_status",
                    data=status
                )
                print(f"[DEBUG] 대기열 상태 전송: {status['count']}개")
            except Exception as e:
                print(f"[경고] 대기열 상태 전송 실패: {e}")

    async def process_next_in_queue(self):
        """대기열의 다음 요청 처리"""
        next_request = self.peek_next_in_queue()
        if next_request:
            print(f"[대기열] 다음 요청 처리: {next_request['sender']} - '{next_request['message'][:30]}...'")
            # 요청 처리 (완료 후 대기열에서 제거됨)
            await self.ask_claude(next_request["message"], next_request["sender"])
        else:
            # 대기열이 비었음을 알림
            await self.send_queue_status()

    async def ask_claude(self, message: str, sender: str):
        """Claude CLI에 메시지 전달하고 응답 받기 (프린트 모드)"""
        print(f"[DEBUG] ask_claude 호출: sender={sender}, message={message[:50]}...")

        if self.claude_processing:
            print("[Claude] 이미 처리 중인 요청이 있습니다.")
            return

        self.claude_processing = True
        self.current_stop_event = threading.Event()

        try:
            await self.send_progress("start", {"message": "Claude 처리 시작"})
            print(f"[Claude] 처리 시작...")

            prompt = f"[{sender}]: {message}"
            output_queue = Queue()

            # 별도 스레드에서 Claude 실행 (세션 ID 전달)
            # 첫 요청: --session-id로 새 세션 생성, 이후: -r로 기존 세션 재개
            thread = threading.Thread(
                target=run_claude_stream,
                args=(prompt, output_queue, self.current_stop_event, self.session_id, self.session_started)
            )
            thread.start()

            final_result = ""
            current_turn = 0
            start_time = asyncio.get_event_loop().time()
            queue_poll_count = 0

            while self.should_run:
                # 타임아웃 체크
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > CLAUDE_TIMEOUT:
                    print(f"[Claude] 타임아웃 ({CLAUDE_TIMEOUT}초)")
                    self.current_stop_event.set()
                    await self.send_progress("error", {"message": f"타임아웃 ({CLAUDE_TIMEOUT}초)"})
                    break

                # 큐에서 결과 가져오기
                try:
                    queue_poll_count += 1
                    if queue_poll_count % 10 == 0:
                        print(f"[DEBUG] 큐 폴링 #{queue_poll_count}, 경과: {elapsed:.1f}초")

                    item = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: output_queue.get(timeout=1)
                        ),
                        timeout=2
                    )
                except (asyncio.TimeoutError, Empty):
                    continue

                msg_type, content = item
                print(f"[DEBUG] 큐에서 수신: type={msg_type}, content={str(content)[:80]}...")

                if msg_type == "done":
                    print(f"[DEBUG] done 수신")
                    break
                elif msg_type == "error":
                    print(f"[Claude 오류]: {content}")
                    await self.send_progress("error", {"message": content})
                    break
                elif msg_type == "stderr":
                    print(f"[Claude stderr]: {content}")
                elif msg_type == "line":
                    try:
                        data = json.loads(content)
                        json_type = data.get("type", "")
                        print(f"[DEBUG] JSON 파싱 성공: type={json_type}")

                        if json_type == "system" and data.get("subtype") == "init":
                            model = data.get("model", "unknown")
                            print(f"[Claude] 모델: {model}")
                            await self.send_progress("init", {
                                "model": model,
                                "session_id": data.get("session_id", "")
                            })

                        elif json_type == "assistant":
                            msg = data.get("message", {})
                            if not isinstance(msg, dict):
                                continue
                            msg_content = msg.get("content", [])
                            if not isinstance(msg_content, list):
                                continue
                            for content_item in msg_content:
                                if not isinstance(content_item, dict):
                                    continue
                                if content_item.get("type") == "tool_use":
                                    tool_name = content_item.get("name", "unknown")
                                    tool_input = content_item.get("input", {})
                                    if not isinstance(tool_input, dict):
                                        tool_input = {}
                                    current_turn += 1

                                    detail = ""
                                    edit_info = None

                                    if tool_name == "Read":
                                        file_path = tool_input.get("file_path", "")
                                        detail = file_path.split("\\")[-1] if file_path else ""
                                    elif tool_name == "Bash":
                                        cmd = tool_input.get("command", "")
                                        detail = cmd[:100] if cmd else ""  # Bash 명령어는 더 길게 표시
                                    elif tool_name == "Edit":
                                        file_path = tool_input.get("file_path", "")
                                        detail = file_path.split("\\")[-1] if file_path else ""
                                        old_string = tool_input.get("old_string", "")
                                        new_string = tool_input.get("new_string", "")
                                        if old_string or new_string:
                                            edit_info = {
                                                "file": detail,
                                                "old": old_string[:500] if old_string else "",
                                                "new": new_string[:500] if new_string else ""
                                            }
                                            print(f"[Claude] [{current_turn}] Edit 변경 내용:")
                                            print(f"  - 파일: {detail}")
                                            print(f"  - 이전: {old_string[:100]}..." if len(old_string) > 100 else f"  - 이전: {old_string}")
                                            print(f"  - 이후: {new_string[:100]}..." if len(new_string) > 100 else f"  - 이후: {new_string}")
                                    elif tool_name == "Write":
                                        file_path = tool_input.get("file_path", "")
                                        detail = file_path.split("\\")[-1] if file_path else ""
                                        content = tool_input.get("content", "")
                                        if content:
                                            # Write 정보를 edit_info와 동일한 형태로 전송 (write_info 키 사용)
                                            edit_info = {
                                                "type": "write",
                                                "file": detail,
                                                "content": content[:500] if content else ""
                                            }
                                            print(f"[Claude] [{current_turn}] Write 파일 생성:")
                                            print(f"  - 파일: {detail}")
                                            print(f"  - 내용: {content[:100]}..." if len(content) > 100 else f"  - 내용: {content}")
                                    elif tool_name == "Grep":
                                        detail = tool_input.get("pattern", "") or ""
                                    elif tool_name == "TodoWrite":
                                        todos = tool_input.get("todos", [])
                                        if todos and isinstance(todos, list):
                                            # TodoWrite 정보를 edit_info로 전송
                                            edit_info = {
                                                "type": "todo",
                                                "todos": todos
                                            }
                                            detail = f"{len(todos)}개 항목"
                                            print(f"[Claude] [{current_turn}] TodoWrite:")
                                            for todo in todos:
                                                status = todo.get("status", "pending")
                                                content = todo.get("content", "")
                                                status_icon = "⏳" if status == "pending" else "🔄" if status == "in_progress" else "✅"
                                                print(f"  {status_icon} {content}")
                                    elif tool_name == "AskUserQuestion":
                                        questions = tool_input.get("questions", [])
                                        if questions and isinstance(questions, list):
                                            # AskUserQuestion 정보를 edit_info로 전송
                                            edit_info = {
                                                "type": "ask_user",
                                                "questions": questions
                                            }
                                            detail = f"{len(questions)}개 질문"
                                            print(f"[Claude] [{current_turn}] AskUserQuestion:")
                                            for q in questions:
                                                question = q.get("question", "")
                                                options = q.get("options", [])
                                                print(f"  Q: {question}")
                                                for opt in options:
                                                    label = opt.get("label", "") if isinstance(opt, dict) else str(opt)
                                                    print(f"    - {label}")

                                    print(f"[Claude] [{current_turn}] {tool_name} 실행 중... {detail}")
                                    progress_data = {
                                        "turn": current_turn,
                                        "tool": tool_name,
                                        "detail": detail
                                    }
                                    if edit_info:
                                        progress_data["edit_info"] = edit_info
                                    await self.send_progress("tool_start", progress_data)

                                elif content_item.get("type") == "text":
                                    final_result = content_item.get("text", "")

                        elif json_type == "user":
                            tool_result = data.get("tool_use_result", {})
                            if tool_result and isinstance(tool_result, dict):
                                file_info = tool_result.get("file", {})
                                if file_info and isinstance(file_info, dict):
                                    lines = file_info.get("numLines", 0)
                                    print(f"[Claude] [{current_turn}] 완료 ({lines}줄)")
                                    await self.send_progress("tool_end", {
                                        "turn": current_turn,
                                        "lines": lines
                                    })
                                else:
                                    print(f"[Claude] [{current_turn}] 완료")
                                    await self.send_progress("tool_end", {
                                        "turn": current_turn
                                    })
                            elif tool_result:
                                print(f"[Claude] [{current_turn}] 완료")
                                await self.send_progress("tool_end", {
                                    "turn": current_turn
                                })

                        elif json_type == "result":
                            total_turns = data.get("num_turns", 0)
                            duration_ms = data.get("duration_ms", 0)
                            cost_usd = data.get("total_cost_usd", 0)
                            usage = data.get("usage", {})
                            if not isinstance(usage, dict):
                                usage = {}

                            duration_sec = duration_ms / 1000
                            input_tokens = usage.get("input_tokens", 0)
                            output_tokens = usage.get("output_tokens", 0)
                            cache_tokens = usage.get("cache_read_input_tokens", 0)

                            final_result = data.get("result", final_result)

                            cost_krw = cost_usd * USD_TO_KRW
                            print(f"[Claude] 완료 | {duration_sec:.1f}초 | ${cost_usd:.4f} (₩{cost_krw:.0f}) | 토큰: {input_tokens + cache_tokens}/{output_tokens}")
                            await self.send_progress("complete", {
                                "duration_sec": duration_sec,
                                "cost_usd": cost_usd,
                                "cost_krw": cost_krw,
                                "input_tokens": input_tokens + cache_tokens,
                                "output_tokens": output_tokens,
                                "turns": total_turns
                            })

                    except json.JSONDecodeError as e:
                        print(f"[DEBUG] JSON 파싱 실패: {e}")
                        continue

            # 스레드 종료 대기
            thread.join(timeout=10)
            if thread.is_alive():
                print("[경고] Claude 스레드가 아직 실행 중")

            if final_result:
                print(f"[DEBUG] 최종 결과 있음, 길이: {len(final_result)}")
                print(f"[{self.CLAUDE_USERNAME}]: {final_result}")
                await self.send_claude_response(final_result)
                # 첫 번째 성공 후 세션 시작됨으로 표시
                if not self.session_started:
                    self.session_started = True
                    print(f"[DEBUG] 세션 시작됨: {self.session_id}")
            elif self.should_run:
                print("[DEBUG] 최종 결과 없음")
                print("[Claude 오류]: 응답 없음")
                await self.send_progress("error", {"message": "응답 없음"})

        except Exception as e:
            print(f"[DEBUG] ask_claude 예외: {type(e).__name__}: {e}")
            print(f"[Claude 오류]: {type(e).__name__}: {e}")
            await self.send_progress("error", {"message": str(e)})
        finally:
            print(f"[DEBUG] ask_claude 종료")
            self.claude_processing = False
            # 처리 완료 후 대기열에서 제거하고 상태 업데이트
            self.get_next_from_queue()  # 현재 요청 제거
            await self.send_queue_status()  # 상태 전송 (알림음은 여기서 발생)
            # 대기열에 다음 요청이 있으면 처리
            if self.should_run:
                await self.process_next_in_queue()

    async def send_claude_response(self, response: str):
        """Claude 응답을 채팅방에 전송"""
        if self.channel and self.is_connected:
            try:
                await self.channel.send_broadcast(
                    event="message",
                    data={
                        "username": self.CLAUDE_USERNAME,
                        "message": response
                    }
                )
            except Exception as e:
                print(f"[경고] Claude 응답 전송 실패: {e}")

    async def connect(self, channel_name: str = "chat-room"):
        """채널에 연결 (재연결 로직 포함)"""
        while self.should_run and self.reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
            try:
                self.loop = asyncio.get_event_loop()

                if self.supabase is None:
                    self.supabase = await create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

                self.channel = self.supabase.realtime.channel(channel_name)

                self.channel.on_broadcast(
                    event="message",
                    callback=self.on_broadcast
                )

                self.channel.on_broadcast(
                    event="session_reset",
                    callback=self.on_broadcast
                )

                await self.channel.subscribe()
                self.is_connected = True
                self.reconnect_attempts = 0  # 연결 성공 시 카운터 리셋

                mode = " (Claude 모드)" if self.enable_claude else ""
                print(f"'{channel_name}' 채널에 연결되었습니다.{mode}")
                return True

            except Exception as e:
                self.is_connected = False
                self.reconnect_attempts += 1
                print(f"[연결 오류] {e} (시도 {self.reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS})")

                if self.reconnect_attempts < MAX_RECONNECT_ATTEMPTS and self.should_run:
                    print(f"{RECONNECT_DELAY}초 후 재연결 시도...")
                    await asyncio.sleep(RECONNECT_DELAY)
                else:
                    print("[오류] 최대 재연결 시도 횟수 초과")
                    return False

        return False

    async def send_message(self, message: str):
        """메시지 발송"""
        if self.channel and self.is_connected:
            try:
                await self.channel.send_broadcast(
                    event="message",
                    data={
                        "username": self.username,
                        "message": message
                    }
                )
                print(f"[{self.username}]: {message}")
            except Exception as e:
                print(f"[전송 오류]: {e}")
                self.is_connected = False

    async def disconnect(self):
        """연결 해제"""
        self.should_run = False

        # 현재 실행 중인 Claude 스레드 중지
        if self.current_stop_event:
            self.current_stop_event.set()

        if self.channel and self.supabase:
            try:
                await self.channel.unsubscribe()
                await asyncio.sleep(0.2)
            except Exception:
                pass
            self.channel = None
            self.is_connected = False
            print("연결이 해제되었습니다.")


async def main():
    print("Claude 채팅봇 초기화 중...")

    print("Claude CLI 테스트 중...")
    if test_claude_cli():
        print("Claude CLI: OK")
    else:
        print("Claude CLI: 실패 - claude CLI를 확인하세요.")
        return

    bot = ChatBot()

    # 시그널 핸들러 설정
    def signal_handler():
        bot.should_run = False

    # Windows에서는 SIGINT만 지원
    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
        loop.add_signal_handler(signal.SIGINT, signal_handler)

    if not await bot.connect():
        print("연결 실패. 종료합니다.")
        return

    print("-" * 40)
    print("Claude가 준비되었습니다.")
    print(f"세션 ID: {bot.session_id}")
    print("다른 사용자의 메시지에 자동 응답합니다.")
    print("'quit' 입력 시 종료")
    print("-" * 40)

    # 입력 처리용 큐와 스레드
    input_queue = Queue()

    def input_thread():
        while bot.should_run:
            try:
                line = input()
                input_queue.put(line)
            except EOFError:
                input_queue.put(None)
                break

    input_t = threading.Thread(target=input_thread, daemon=True)
    input_t.start()

    try:
        while bot.should_run:
            # 비동기로 큐 체크 (이벤트 루프 블로킹 방지)
            try:
                message = input_queue.get_nowait()
            except Empty:
                await asyncio.sleep(0.1)  # 이벤트 루프가 다른 작업 처리할 수 있게 함
                continue

            if message is None:
                print("[DEBUG] EOF, 루프 탈출")
                break

            print(f"[DEBUG] 입력 받음: '{message}'")

            if message.lower() == "quit":
                print("[DEBUG] quit 감지, 루프 탈출")
                break

            if message.strip():
                await bot.send_message(message)

    except KeyboardInterrupt:
        print("\n종료합니다...")
    finally:
        print("[DEBUG] finally 블록 진입")
        await bot.disconnect()
        print("프로그램을 종료합니다.")
        os._exit(0)


if __name__ == "__main__":
    import logging
    import warnings
    from concurrent.futures import ThreadPoolExecutor
    import atexit

    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # 명시적 ThreadPoolExecutor 생성
    executor = ThreadPoolExecutor(max_workers=4)

    def cleanup_executor():
        executor.shutdown(wait=False, cancel_futures=True)

    atexit.register(cleanup_executor)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_default_executor(executor)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        # executor 즉시 종료
        executor.shutdown(wait=False, cancel_futures=True)

        try:
            # 모든 태스크 정리
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass

        # 이벤트 루프 정리
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass

        loop.close()
