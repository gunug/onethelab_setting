import asyncio
import json
import subprocess
import threading
import uuid
import sys
import os
import argparse
from datetime import datetime
from queue import Queue, Empty
from aiohttp import web
from collections import deque

# Windows asyncio 호환성
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 설정
CLAUDE_TIMEOUT = 300  # Claude CLI 타임아웃 (초)
USD_TO_KRW = 1430  # 환율
HOST = "0.0.0.0"
DEFAULT_PORT = 8765

# 현재 스크립트 디렉토리
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 프로젝트 루트 (chat_socket의 부모 디렉토리)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)


def get_relative_path(file_path: str) -> str:
    """절대 경로를 프로젝트 루트 기준 상대 경로로 변환"""
    if not file_path:
        return ""
    try:
        # 경로 정규화
        abs_path = os.path.abspath(file_path)
        # 프로젝트 루트 기준 상대 경로
        if abs_path.startswith(PROJECT_ROOT):
            rel_path = os.path.relpath(abs_path, PROJECT_ROOT)
            # Windows 경로를 Unix 스타일로 변환
            return rel_path.replace("\\", "/")
        # 프로젝트 외부 파일은 그대로 반환
        return file_path
    except Exception:
        return file_path


# 연결된 클라이언트 관리
connected_clients = set()

# Claude 처리 상태
claude_processing = False
current_stop_event = None
session_id = None
session_started = False

# 요청 큐 관리
request_queue = deque()  # 대기 중인 요청 큐
queue_lock = asyncio.Lock()  # 큐 접근 동기화


def get_claude_usage():
    """ccusage를 통해 오늘의 Claude 사용량 조회"""
    try:
        result = subprocess.run(
            'npx ccusage@latest daily --json',
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"[DEBUG] ccusage 실행 실패: {result.stderr}")
            return None

        data = json.loads(result.stdout)
        daily_data = data.get("daily", [])
        totals = data.get("totals", {})

        # 오늘 날짜의 데이터 찾기
        today = datetime.now().strftime("%Y-%m-%d")
        today_usage = None
        for day in daily_data:
            if day.get("date") == today:
                today_usage = day
                break

        return {
            "today": today_usage,
            "totals": totals,
            "date": today
        }
    except subprocess.TimeoutExpired:
        print("[DEBUG] ccusage 타임아웃")
        return None
    except json.JSONDecodeError as e:
        print(f"[DEBUG] ccusage JSON 파싱 실패: {e}")
        return None
    except Exception as e:
        print(f"[DEBUG] ccusage 오류: {e}")
        return None


def get_claude_blocks():
    """ccusage를 통해 5시간 블록 사용량 조회"""
    try:
        result = subprocess.run(
            'npx ccusage@latest blocks --json',
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"[DEBUG] ccusage blocks 실행 실패: {result.stderr}")
            return None

        data = json.loads(result.stdout)
        blocks = data.get("blocks", [])

        # 현재 활성 블록 찾기
        active_block = None
        for block in blocks:
            if block.get("isActive") and not block.get("isGap"):
                active_block = block
                break

        if not active_block:
            return None

        # 블록 정보 추출
        projection = active_block.get("projection", {})
        burn_rate = active_block.get("burnRate", {})

        return {
            "startTime": active_block.get("startTime"),
            "endTime": active_block.get("endTime"),
            "costUSD": active_block.get("costUSD", 0),
            "totalTokens": active_block.get("totalTokens", 0),
            "remainingMinutes": projection.get("remainingMinutes", 0) if projection else 0,
            "projectedCost": projection.get("totalCost", 0) if projection else 0,
            "costPerHour": burn_rate.get("costPerHour", 0) if burn_rate else 0,
            "models": active_block.get("models", [])
        }
    except subprocess.TimeoutExpired:
        print("[DEBUG] ccusage blocks 타임아웃")
        return None
    except json.JSONDecodeError as e:
        print(f"[DEBUG] ccusage blocks JSON 파싱 실패: {e}")
        return None
    except Exception as e:
        print(f"[DEBUG] ccusage blocks 오류: {e}")
        return None


def test_claude_cli():
    """Claude CLI 호출 테스트"""
    try:
        cmd = 'claude "test"'
        print(f"[테스트] {cmd}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=True,
            timeout=60
        )
        return result.returncode == 0 and result.stdout
    except subprocess.TimeoutExpired:
        print("  타임아웃: Claude CLI 응답 없음")
        return False
    except Exception as e:
        print(f"  예외: {e}")
        return False


def run_claude_stream(prompt: str, output_queue: Queue, stop_event: threading.Event,
                      sess_id: str = None, is_resume: bool = False):
    """별도 스레드에서 Claude CLI 스트리밍 실행"""
    process = None
    try:
        cmd = 'claude --output-format stream-json --verbose --dangerously-skip-permissions'
        if sess_id:
            if is_resume:
                cmd += f' -r "{sess_id}"'
                print(f"[DEBUG] 세션 재개: {sess_id}")
            else:
                cmd += f' --session-id "{sess_id}"'
                print(f"[DEBUG] 새 세션: {sess_id}")
        cmd += ' -p -'
        print(f"[실행] {cmd}")

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

        # stdin으로 프롬프트 전달
        process.stdin.write(prompt)
        process.stdin.close()

        # stderr 읽기 스레드
        def read_stderr():
            try:
                while not stop_event.is_set():
                    line = process.stderr.readline()
                    if not line:
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
            while not stop_event.is_set():
                line = process.stdout.readline()
                if not line:
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
        if process and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=5)
            except:
                pass


async def broadcast(message: dict, exclude=None):
    """모든 클라이언트에게 메시지 전송"""
    if not connected_clients:
        return

    message_str = json.dumps(message, ensure_ascii=False)
    disconnected = set()
    for client in connected_clients.copy():
        if client != exclude:
            try:
                await client.send_str(message_str)
            except Exception:
                disconnected.add(client)

    for client in disconnected:
        connected_clients.discard(client)


async def send_progress(progress_type: str, data: dict):
    """진행 상황 브로드캐스트"""
    await broadcast({
        "type": "progress",
        "progress_type": progress_type,
        **data
    })


async def send_queue_status():
    """현재 큐 상태를 모든 클라이언트에게 브로드캐스트"""
    items = []
    for req in request_queue:
        items.append({
            "sender": req["sender"],
            "message": req["message"][:50] + ("..." if len(req["message"]) > 50 else "")
        })

    await broadcast({
        "type": "queue_status",
        "count": len(request_queue),
        "items": items
    })


async def send_usage_status():
    """Claude 사용량 상태를 모든 클라이언트에게 브로드캐스트"""
    try:
        # 별도 스레드에서 ccusage 실행 (비동기) - daily와 blocks 병렬 실행
        loop = asyncio.get_event_loop()
        usage_task = loop.run_in_executor(None, get_claude_usage)
        blocks_task = loop.run_in_executor(None, get_claude_blocks)

        usage = await usage_task
        blocks = await blocks_task

        # 데이터 병합
        combined_data = {}
        if usage:
            combined_data["today"] = usage.get("today")
            combined_data["totals"] = usage.get("totals")
            combined_data["date"] = usage.get("date")

        if blocks:
            combined_data["block"] = blocks

        if combined_data:
            await broadcast({
                "type": "usage_status",
                **combined_data
            })

            # 디버그 로그
            today_cost = combined_data.get("today", {})
            if today_cost:
                cost_usd = today_cost.get("totalCost", 0)
                cost_krw = cost_usd * USD_TO_KRW
                print(f"[DEBUG] 사용량 전송: 오늘 ${cost_usd:.2f} (₩{cost_krw:,.0f})")

            if blocks:
                remaining = blocks.get("remainingMinutes", 0)
                block_cost = blocks.get("costUSD", 0)
                print(f"[DEBUG] 블록 전송: ${block_cost:.2f}, 남은 시간: {remaining}분")

    except Exception as e:
        print(f"[경고] 사용량 상태 전송 실패: {e}")


async def add_to_queue(message: str, sender: str):
    """요청을 큐에 추가"""
    async with queue_lock:
        request_queue.append({
            "sender": sender,
            "message": message
        })
        print(f"[큐] 요청 추가: {sender} (대기: {len(request_queue)}개)")
        await send_queue_status()

    # 처리 시작 (처리 중이 아닐 때만)
    if not claude_processing:
        asyncio.create_task(process_queue())


async def process_queue():
    """큐에서 요청을 꺼내 순차 처리"""
    global claude_processing

    while True:
        async with queue_lock:
            if not request_queue:
                print("[큐] 모든 요청 처리 완료")
                return
            request = request_queue[0]  # peek (아직 제거하지 않음)

        # 요청 처리
        await ask_claude(request["message"], request["sender"])

        # 처리 완료 후 큐에서 제거
        async with queue_lock:
            if request_queue and request_queue[0] == request:
                request_queue.popleft()
                print(f"[큐] 요청 완료 (남은: {len(request_queue)}개)")
            await send_queue_status()
            # 사용량 정보 전송
            await send_usage_status()


async def ask_claude(message: str, sender: str, retry_count: int = 0):
    """Claude CLI에 메시지 전달하고 응답 받기"""
    global claude_processing, current_stop_event, session_id, session_started

    MAX_RETRY = 1  # state error 시 최대 재시도 횟수

    claude_processing = True
    current_stop_event = threading.Event()

    try:
        await send_progress("start", {"message": "Claude 처리 시작"})
        print(f"[Claude] 처리 시작: {sender} - {message[:50]}...")

        prompt = f"[{sender}]: {message}"
        output_queue = Queue()

        # 별도 스레드에서 Claude 실행
        thread = threading.Thread(
            target=run_claude_stream,
            args=(prompt, output_queue, current_stop_event, session_id, session_started)
        )
        thread.start()

        final_result = ""
        current_turn = 0
        start_time = asyncio.get_event_loop().time()
        session_error_detected = False  # 세션 에러 감지 플래그

        while True:
            # 타임아웃 체크
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > CLAUDE_TIMEOUT:
                print(f"[Claude] 타임아웃 ({CLAUDE_TIMEOUT}초)")
                current_stop_event.set()
                await send_progress("error", {"message": f"타임아웃 ({CLAUDE_TIMEOUT}초)"})
                # 타임아웃 시 세션 리셋 (다음 요청에서 새 세션 시작)
                reset_session()
                break

            # 큐에서 결과 가져오기
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
                # 세션 에러가 감지되었고 재시도 가능하면 재시도
                if session_error_detected and retry_count < MAX_RETRY:
                    print(f"[Claude] 세션 에러로 인한 재시도 ({retry_count + 1}/{MAX_RETRY})")
                    thread.join(timeout=5)
                    reset_session()
                    claude_processing = False
                    await send_progress("retry", {"message": "세션 에러 - 새 세션으로 재시도 중..."})
                    return await ask_claude(message, sender, retry_count + 1)
                break
            elif msg_type == "error":
                print(f"[Claude 오류]: {content}")
                await send_progress("error", {"message": content})
                break
            elif msg_type == "stderr":
                # stderr에서 세션/상태 에러 감지
                content_lower = content.lower()
                if "state" in content_lower or "session" in content_lower or "invalid" in content_lower:
                    print(f"[Claude] 세션 에러 감지: {content}")
                    session_error_detected = True
                else:
                    print(f"[DEBUG] stderr: {content}")
            elif msg_type == "line":
                try:
                    data = json.loads(content)
                    json_type = data.get("type", "")

                    if json_type == "system" and data.get("subtype") == "init":
                        model = data.get("model", "unknown")
                        print(f"[Claude] 모델: {model}")
                        await send_progress("init", {
                            "model": model,
                            "session_id": data.get("session_id", "")
                        })

                    elif json_type == "assistant":
                        msg = data.get("message", {})
                        if isinstance(msg, dict):
                            msg_content = msg.get("content", [])
                            if isinstance(msg_content, list):
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
                                            detail = get_relative_path(file_path) if file_path else ""
                                        elif tool_name == "Bash":
                                            cmd = tool_input.get("command", "")
                                            detail = cmd[:100] if cmd else ""
                                        elif tool_name == "Edit":
                                            file_path = tool_input.get("file_path", "")
                                            rel_path = get_relative_path(file_path)
                                            detail = rel_path if file_path else ""
                                            old_string = tool_input.get("old_string", "")
                                            new_string = tool_input.get("new_string", "")
                                            if old_string or new_string:
                                                edit_info = {
                                                    "type": "edit",
                                                    "file": rel_path,
                                                    "old": old_string[:500] if old_string else "",
                                                    "new": new_string[:500] if new_string else ""
                                                }
                                        elif tool_name == "Write":
                                            file_path = tool_input.get("file_path", "")
                                            rel_path = get_relative_path(file_path)
                                            detail = rel_path if file_path else ""
                                            write_content = tool_input.get("content", "")
                                            if write_content:
                                                edit_info = {
                                                    "type": "write",
                                                    "file": rel_path,
                                                    "content": write_content[:500] if write_content else ""
                                                }
                                        elif tool_name == "Grep":
                                            detail = tool_input.get("pattern", "") or ""
                                        elif tool_name == "TodoWrite":
                                            todos = tool_input.get("todos", [])
                                            if todos and isinstance(todos, list):
                                                edit_info = {
                                                    "type": "todo",
                                                    "todos": todos
                                                }
                                                detail = f"{len(todos)}개 항목"

                                        print(f"[Claude] [{current_turn}] {tool_name} {detail}")
                                        progress_data = {
                                            "turn": current_turn,
                                            "tool": tool_name,
                                            "detail": detail
                                        }
                                        if edit_info:
                                            progress_data["edit_info"] = edit_info
                                        await send_progress("tool_start", progress_data)

                                    elif content_item.get("type") == "text":
                                        final_result = content_item.get("text", "")

                    elif json_type == "user":
                        tool_result = data.get("tool_use_result", {})
                        if tool_result and isinstance(tool_result, dict):
                            file_info = tool_result.get("file", {})
                            if file_info and isinstance(file_info, dict):
                                lines = file_info.get("numLines", 0)
                                await send_progress("tool_end", {
                                    "turn": current_turn,
                                    "lines": lines
                                })
                            else:
                                await send_progress("tool_end", {"turn": current_turn})

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
                        print(f"[Claude] 완료 | {duration_sec:.1f}초 | ${cost_usd:.4f} (₩{cost_krw:.0f})")
                        await send_progress("complete", {
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

        if final_result:
            print(f"[Claude]: {final_result[:100]}...")
            await broadcast({
                "type": "message",
                "username": "Claude",
                "message": final_result
            })
            # 첫 번째 성공 후 세션 시작됨으로 표시
            if not session_started:
                session_started = True
                print(f"[DEBUG] 세션 시작됨: {session_id}")

    except Exception as e:
        print(f"[Claude 오류]: {type(e).__name__}: {e}")
        await send_progress("error", {"message": str(e)})
    finally:
        claude_processing = False


def reset_session():
    """Claude 세션 리셋"""
    global session_id, session_started
    session_id = str(uuid.uuid4())
    session_started = False
    print(f"[세션] 리셋됨: {session_id}")
    return session_id


# ============================================================
# HTTP + WebSocket 통합 서버 (aiohttp)
# ============================================================

async def handle_index(request):
    """HTTP GET / - index.html 제공"""
    index_path = os.path.join(SCRIPT_DIR, "index.html")
    if os.path.exists(index_path):
        return web.FileResponse(index_path)
    return web.Response(text="index.html not found", status=404)


async def handle_manifest(request):
    """HTTP GET /manifest.json - PWA 매니페스트 제공"""
    manifest_path = os.path.join(SCRIPT_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        return web.FileResponse(manifest_path, headers={"Content-Type": "application/manifest+json"})
    return web.Response(text="manifest.json not found", status=404)


async def handle_service_worker(request):
    """HTTP GET /service-worker.js - Service Worker 제공"""
    sw_path = os.path.join(SCRIPT_DIR, "service-worker.js")
    if os.path.exists(sw_path):
        return web.FileResponse(sw_path, headers={"Content-Type": "application/javascript"})
    return web.Response(text="service-worker.js not found", status=404)


async def handle_icon(request):
    """HTTP GET /icons/{filename} - 앱 아이콘 제공"""
    filename = request.match_info.get("filename", "")
    icon_path = os.path.join(SCRIPT_DIR, "icons", filename)
    if os.path.exists(icon_path):
        content_type = "image/png"
        if filename.endswith(".svg"):
            content_type = "image/svg+xml"
        return web.FileResponse(icon_path, headers={"Content-Type": content_type})
    return web.Response(text=f"Icon {filename} not found", status=404)


async def handle_websocket(request):
    """WebSocket /ws - 채팅 처리"""
    ws = web.WebSocketResponse(heartbeat=30)  # 30초마다 ping/pong으로 연결 유지
    await ws.prepare(request)

    connected_clients.add(ws)
    client_id = id(ws)
    print(f"[연결] 클라이언트 접속 (ID: {client_id}, 총 {len(connected_clients)}명)")

    # 연결 확인 메시지
    await ws.send_str(json.dumps({
        "type": "system",
        "message": "WebSocket 서버에 연결되었습니다."
    }, ensure_ascii=False))

    # 접속 시 사용량 정보 전송
    asyncio.create_task(send_usage_status())

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    msg_type = data.get("type", "message")

                    if msg_type == "message":
                        username = data.get("username", "익명")
                        content = data.get("message", "")
                        print(f"[{username}]: {content}")

                        # 모든 클라이언트에게 브로드캐스트
                        await broadcast({
                            "type": "message",
                            "username": username,
                            "message": content
                        })

                        # Claude에게 전달 (Claude 자신의 메시지 제외)
                        if username != "Claude":
                            await add_to_queue(content, username)

                    elif msg_type == "command":
                        command = data.get("command", "")
                        print(f"[명령]: {command}")

                        if command == "clear":
                            new_session = reset_session()
                            await broadcast({
                                "type": "system",
                                "message": f"세션이 리셋되었습니다. (새 세션: {new_session[:8]}...)"
                            })
                        elif command == "request_usage":
                            # 사용량 조회 요청
                            asyncio.create_task(send_usage_status())
                        elif command == "restart":
                            print("[명령] 서버 재시작 요청됨")
                            await broadcast({
                                "type": "system",
                                "message": "서버가 재시작됩니다. 잠시 후 페이지를 새로고침하세요."
                            })
                            # 잠시 대기 후 재시작 (메시지 전송 시간 확보)
                            await asyncio.sleep(1)
                            # exit code 100으로 종료 → run.bat이 재시작
                            os._exit(100)

                except json.JSONDecodeError:
                    print(f"[오류] JSON 파싱 실패: {msg.data}")

            elif msg.type == web.WSMsgType.ERROR:
                print(f"[오류] WebSocket 오류: {ws.exception()}")

    except Exception as e:
        print(f"[오류] 클라이언트 처리 중 예외: {e}")
    finally:
        connected_clients.discard(ws)
        print(f"[연결 해제] 클라이언트 종료 (ID: {client_id}, 남은 {len(connected_clients)}명)")

        # 마지막 클라이언트가 나가면 세션 리셋
        if len(connected_clients) == 0:
            global claude_processing, current_stop_event
            # 처리 중인 작업이 있으면 중단
            if claude_processing and current_stop_event:
                current_stop_event.set()
                print("[정리] 처리 중인 Claude 작업 중단")
            claude_processing = False
            reset_session()
            print("[정리] 모든 클라이언트 종료 - 세션 리셋 완료")

    return ws


async def init_app():
    """aiohttp 앱 초기화"""
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/ws", handle_websocket)
    # PWA 지원
    app.router.add_get("/manifest.json", handle_manifest)
    app.router.add_get("/service-worker.js", handle_service_worker)
    app.router.add_get("/icons/{filename}", handle_icon)
    return app


def main():
    global session_id

    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description="Chat Socket 통합 서버")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"서버 포트 (기본값: {DEFAULT_PORT})")
    args = parser.parse_args()
    port = args.port

    print("=" * 50)
    print("Chat Socket 통합 서버 (HTTP + WebSocket)")
    print("=" * 50)

    # Claude CLI 테스트
    print("Claude CLI 테스트 중...")
    if test_claude_cli():
        print("Claude CLI: OK")
    else:
        print("Claude CLI: 실패 - claude CLI를 확인하세요.")
        return

    # 세션 ID 초기화
    session_id = str(uuid.uuid4())
    print(f"세션 ID: {session_id}")

    print("-" * 50)
    print(f"HTTP:      http://{HOST}:{port}/")
    print(f"WebSocket: ws://{HOST}:{port}/ws")
    print("-" * 50)
    print("ngrok 사용 시:")
    print(f"  ngrok http {port}")
    print("  브라우저에서 ngrok URL 접속")
    print("-" * 50)
    print("종료: Ctrl+C")
    print("=" * 50)

    # 서버 실행
    web.run_app(init_app(), host=HOST, port=port, print=None)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n서버 종료")
