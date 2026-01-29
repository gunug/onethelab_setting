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


def run_claude_stream(prompt: str, output_queue: Queue, stop_event: threading.Event):
    """별도 스레드에서 Claude CLI 스트리밍 실행"""
    process = None
    try:
        cmd = f'claude --output-format stream-json --verbose --dangerously-skip-permissions "{prompt}"'
        print(f"[실행 명령] {cmd}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            shell=True,
            text=True,
            encoding="utf-8"
        )

        # stderr 읽기 스레드
        def read_stderr():
            try:
                for line in process.stderr:
                    if stop_event.is_set():
                        break
                    line = line.strip()
                    if line:
                        output_queue.put(("stderr", line))
            except Exception:
                pass

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        # stdout 읽기
        try:
            for line in process.stdout:
                if stop_event.is_set():
                    break
                line = line.strip()
                if line:
                    output_queue.put(("line", line))
        except Exception as e:
            output_queue.put(("error", f"stdout 읽기 오류: {e}"))

        # 프로세스 종료 대기
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        output_queue.put(("done", process.returncode))

    except Exception as e:
        output_queue.put(("error", str(e)))
    finally:
        # 프로세스 정리
        if process and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=5)
            except Exception:
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
        self.current_claude_stop_event = None
        self.claude_processing = False

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
        """Claude CLI에 메시지 전달하고 응답 받기 (스트리밍)"""
        if self.claude_processing:
            print("[Claude] 이미 처리 중인 요청이 있습니다.")
            return

        self.claude_processing = True
        self.current_claude_stop_event = threading.Event()

        try:
            await self.send_progress("start", {"message": "Claude 처리 시작"})
            print(f"[Claude] 처리 시작...")

            prompt = f"[{sender}]: {message}"
            output_queue = Queue()

            # 별도 스레드에서 Claude 실행 (stdin 방식)
            thread = threading.Thread(
                target=run_claude_stream,
                args=(prompt, output_queue, self.current_claude_stop_event)
            )
            thread.start()

            final_result = ""
            current_turn = 0
            start_time = asyncio.get_event_loop().time()

            while self.should_run:
                # 타임아웃 체크
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > CLAUDE_TIMEOUT:
                    print(f"[Claude] 타임아웃 ({CLAUDE_TIMEOUT}초)")
                    self.current_claude_stop_event.set()
                    await self.send_progress("error", {"message": f"타임아웃 ({CLAUDE_TIMEOUT}초)"})
                    break

                # 큐에서 결과 가져오기 (타임아웃 포함)
                try:
                    item = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: output_queue.get(timeout=1)
                        ),
                        timeout=2
                    )
                except (asyncio.TimeoutError, Empty):
                    continue

                msg_type, content = item

                if msg_type == "done":
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


                    except json.JSONDecodeError:
                        continue

            # 스레드 종료 대기
            thread.join(timeout=10)
            if thread.is_alive():
                print("[경고] Claude 스레드가 아직 실행 중입니다.")

            if final_result:
                print(f"[{self.CLAUDE_USERNAME}]: {final_result}")
                await self.send_claude_response(final_result)
            elif self.should_run:
                print("[Claude 오류]: 응답 없음")
                await self.send_progress("error", {"message": "응답 없음"})

        except Exception as e:
            print(f"[Claude 오류]: {type(e).__name__}: {e}")
            await self.send_progress("error", {"message": str(e)})
        finally:
            self.claude_processing = False
            self.current_claude_stop_event = None

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

        # Claude 처리 중단
        if self.current_claude_stop_event:
            self.current_claude_stop_event.set()

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
