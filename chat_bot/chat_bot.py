import os
import sys
import json
import asyncio
import subprocess
import threading
import signal
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


class ClaudeProcess:
    """Claude CLI 프로세스 관리 (채팅 모드)"""

    def __init__(self):
        self.process = None
        self.output_queue = Queue()
        self.stderr_thread = None
        self.stdout_thread = None
        self.stop_event = threading.Event()
        self.is_running = False
        self.waiting_response = False

    def start(self):
        """Claude 프로세스 시작"""
        if self.process and self.process.poll() is None:
            print("[DEBUG] Claude 프로세스 이미 실행 중")
            return True

        cmd = 'claude --output-format stream-json --verbose --dangerously-skip-permissions'
        print(f"[DEBUG] Claude 프로세스 시작 (채팅 모드)")
        print(f"[실행 명령] {cmd}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                shell=True,
                text=True,
                encoding="utf-8",
                bufsize=1
            )
            print(f"[DEBUG] 프로세스 생성 완료, PID: {self.process.pid}")

            self.stop_event.clear()
            self.is_running = True

            # stderr 읽기 스레드
            self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            self.stderr_thread.start()

            # stdout 읽기 스레드
            self.stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
            self.stdout_thread.start()

            return True

        except Exception as e:
            print(f"[DEBUG] 프로세스 시작 실패: {e}")
            return False

    def _read_stderr(self):
        """stderr 읽기 스레드"""
        print(f"[DEBUG] stderr 스레드 시작")
        try:
            while not self.stop_event.is_set() and self.process:
                line = self.process.stderr.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    print(f"[DEBUG] stderr: {line[:100]}")
                    self.output_queue.put(("stderr", line))
        except Exception as e:
            print(f"[DEBUG] stderr 예외: {e}")
        print(f"[DEBUG] stderr 스레드 종료")

    def _read_stdout(self):
        """stdout 읽기 스레드"""
        print(f"[DEBUG] stdout 스레드 시작")
        try:
            while not self.stop_event.is_set() and self.process:
                line = self.process.stdout.readline()
                if not line:
                    print(f"[DEBUG] stdout: EOF")
                    self.output_queue.put(("eof", None))
                    break
                line = line.strip()
                if line:
                    print(f"[DEBUG] stdout: {line[:100]}...")
                    self.output_queue.put(("line", line))
        except Exception as e:
            print(f"[DEBUG] stdout 예외: {e}")
            self.output_queue.put(("error", str(e)))
        print(f"[DEBUG] stdout 스레드 종료")
        self.is_running = False

    def send_message(self, message: str):
        """메시지 전송"""
        if not self.process or self.process.poll() is not None:
            print(f"[DEBUG] 프로세스가 없어서 재시작")
            if not self.start():
                return False

        try:
            print(f"[DEBUG] stdin 전송: {message[:50]}...")
            self.process.stdin.write(message + "\n")
            self.process.stdin.flush()
            self.waiting_response = True
            return True
        except Exception as e:
            print(f"[DEBUG] stdin 전송 실패: {e}")
            return False

    def get_output(self, timeout=1):
        """출력 가져오기"""
        try:
            return self.output_queue.get(timeout=timeout)
        except Empty:
            return None

    def stop(self):
        """프로세스 종료"""
        print(f"[DEBUG] Claude 프로세스 종료 중...")
        self.stop_event.set()
        self.is_running = False

        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                print(f"[DEBUG] 종료 실패, 강제 종료: {e}")
                try:
                    self.process.kill()
                except:
                    pass

        print(f"[DEBUG] Claude 프로세스 종료 완료")


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
        self.claude_process = ClaudeProcess() if enable_claude else None

    def on_broadcast(self, payload):
        """수신된 메시지 출력 및 Claude 전달"""
        data = payload.get("payload", {})
        event_type = payload.get("event", "message")

        if event_type == "progress":
            return

        sender = data.get("username", "unknown")
        message = data.get("message", "")
        print(f"[{sender}]: {message}")

        if self.enable_claude and sender != self.username and sender != self.CLAUDE_USERNAME:
            if self.loop and not self.claude_processing:
                asyncio.run_coroutine_threadsafe(
                    self.ask_claude(message, sender), self.loop
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

    async def ask_claude(self, message: str, sender: str):
        """Claude CLI에 메시지 전달하고 응답 받기 (채팅 모드)"""
        print(f"[DEBUG] ask_claude 호출: sender={sender}, message={message[:50]}...")

        if self.claude_processing:
            print("[Claude] 이미 처리 중인 요청이 있습니다.")
            return

        if not self.claude_process:
            print("[Claude] Claude 프로세스가 없습니다.")
            return

        self.claude_processing = True

        try:
            await self.send_progress("start", {"message": "Claude 처리 시작"})
            print(f"[Claude] 처리 시작...")

            prompt = f"[{sender}]: {message}"

            # 메시지 전송
            if not self.claude_process.send_message(prompt):
                print("[Claude 오류] 메시지 전송 실패")
                await self.send_progress("error", {"message": "메시지 전송 실패"})
                return

            final_result = ""
            current_turn = 0
            start_time = asyncio.get_event_loop().time()
            queue_poll_count = 0
            response_complete = False

            while self.should_run and not response_complete:
                # 타임아웃 체크
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > CLAUDE_TIMEOUT:
                    print(f"[Claude] 타임아웃 ({CLAUDE_TIMEOUT}초)")
                    await self.send_progress("error", {"message": f"타임아웃 ({CLAUDE_TIMEOUT}초)"})
                    break

                # 큐에서 결과 가져오기
                try:
                    queue_poll_count += 1
                    if queue_poll_count % 10 == 0:
                        print(f"[DEBUG] 큐 폴링 #{queue_poll_count}, 경과: {elapsed:.1f}초")

                    item = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: self.claude_process.get_output(timeout=1)
                        ),
                        timeout=2
                    )
                except asyncio.TimeoutError:
                    continue

                if item is None:
                    continue

                msg_type, content = item
                print(f"[DEBUG] 큐에서 수신: type={msg_type}, content={str(content)[:80] if content else 'None'}...")

                if msg_type == "eof":
                    print(f"[DEBUG] EOF 수신, 프로세스 종료됨")
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
                                        detail = cmd[:30] if cmd else ""
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
                                    elif tool_name == "Grep":
                                        detail = tool_input.get("pattern", "") or ""

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

                            # 응답 완료
                            response_complete = True
                            print(f"[DEBUG] 응답 완료")

                    except json.JSONDecodeError as e:
                        print(f"[DEBUG] JSON 파싱 실패: {e}")
                        continue

            if final_result:
                print(f"[DEBUG] 최종 결과 있음, 길이: {len(final_result)}")
                print(f"[{self.CLAUDE_USERNAME}]: {final_result}")
                await self.send_claude_response(final_result)
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

        # Claude 프로세스 종료
        if self.claude_process:
            self.claude_process.stop()

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
    print("다른 사용자의 메시지에 자동 응답합니다.")
    print("'quit' 입력 시 종료")
    print("-" * 40)

    try:
        while bot.should_run:
            try:
                message = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, input, ""),
                    timeout=1.0
                )

                if message.lower() == "quit":
                    break

                if message.strip():
                    await bot.send_message(message)

            except asyncio.TimeoutError:
                continue
            except EOFError:
                break

    except KeyboardInterrupt:
        print("\n종료합니다...")
    finally:
        await bot.disconnect()


if __name__ == "__main__":
    import logging
    import warnings
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
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
