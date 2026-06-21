import ast
import json
import os
import subprocess
from datetime import datetime

from stage2_api import call_api

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def validate_test_code(code):
    """AI가 생성한 pytest 파일에 위험 코드가 있는지 정적 분석"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        print(f"[보안] 코드 구문 오류: {e}")
        return False

    dangerous = {"exec", "eval", "compile", "os.system", "subprocess", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ""
            if hasattr(node.func, "id"):
                func_name = node.func.id
            elif hasattr(node.func, "attr"):
                func_name = node.func.attr
            if func_name in dangerous:
                print(f"[보안] 위험 함수 탐지: {func_name} → 실행 차단")
                return False
    return True


def _normalize_technique(value):
    mapping = {
        "상태전이": "상태전이",
        "state_transition": "상태전이",
        "state transition": "상태전이",
        "경계값": "경계값",
        "boundary": "경계값",
        "boundary_value": "경계값",
        "boundary value": "경계값",
        "동등분할": "동등분할",
        "equivalence": "동등분할",
        "equivalence_partition": "동등분할",
        "equivalence partition": "동등분할",
        "무효전이": "무효전이",
        "invalid_transition": "무효전이",
        "invalid transition": "무효전이",
    }
    if not value:
        return None
    key = str(value).strip().lower()
    return mapping.get(key, value if value in mapping.values() else None)


def _command_key(command):
    if isinstance(command, (dict, list)):
        return json.dumps(command, ensure_ascii=False, sort_keys=True)
    return str(command)


def _infer_technique(tc, seen_valid_commands):
    explicit = tc.get("technique") or tc.get("test_technique") or tc.get("method")
    normalized = _normalize_technique(explicit)
    if normalized:
        return normalized

    command = tc.get("command", "")
    expected = tc.get("expected", {})
    if expected.get("error") == "error":
        return "무효전이"
    if expected.get("ultrasonic") in (0, 100):
        return "경계값"
    if _command_key(command) in seen_valid_commands:
        return "동등분할"
    return "상태전이"


def _save_technique_file(timestamp, tc_list):
    items = []
    seen_valid_commands = set()
    for index, tc in enumerate(tc_list):
        technique = _infer_technique(tc, seen_valid_commands)
        items.append(
            {
                "index": index,
                "cmd": tc.get("command", ""),
                "technique": technique,
            }
        )
        if tc.get("expected", {}).get("error") != "error":
            seen_valid_commands.add(_command_key(tc.get("command", "")))

    technique_path = os.path.join(BASE_DIR, f"technique_{timestamp}.json")
    with open(technique_path, "w", encoding="utf-8") as f:
        json.dump(
            {"timestamp": timestamp, "items": items},
            f,
            ensure_ascii=False,
            indent=2,
        )


def _build_test_code(driver_type, port, browser, base_url, params):
    return f"""
import pytest
from stage4_driver import create_driver

DRIVER_TYPE = {driver_type!r}
DRIVER_PORT = {port!r}
DRIVER_BROWSER = {browser!r}
DRIVER_BASE_URL = {base_url!r}

@pytest.fixture
def driver():
    driver_instance = create_driver(
        DRIVER_TYPE,
        port=DRIVER_PORT,
        browser=DRIVER_BROWSER,
        base_url=DRIVER_BASE_URL,
    )
    try:
        driver_instance.connect()
    except Exception:
        if DRIVER_TYPE == "rc_car":
            raise
    yield driver_instance
    close_method = getattr(driver_instance, "close", None)
    if callable(close_method):
        close_method()

@pytest.mark.parametrize("cmd, technique, expected", {params})
def test_target(driver, cmd, technique, expected):
    response = driver.send_command(cmd)
    assert response is not None, "No response returned from driver."

    for key in expected:
        if key == "ultrasonic":
            assert isinstance(response.get("ultrasonic"), int), "ultrasonic must be int"
            continue
        if key == "ir":
            assert isinstance(response.get("ir"), bool), "ir must be bool"
            continue
        assert response.get(key) == expected[key], f"{{key}} mismatch: {{response.get(key)}} != {{expected[key]}}"
"""


def generate_test_file(text, port="COM3", driver_type="rc_car", browser="chrome", base_url=""):
    result = call_api(text)
    if result is None:
        print("TC 생성 실패: API 응답 오류")
        return {"report_generated": False}

    tc_list = result["tc"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    params = []
    seen_valid_commands = set()
    for tc in tc_list:
        technique = _infer_technique(tc, seen_valid_commands)
        params.append((tc["command"], technique, tc["expected"]))
        if tc.get("expected", {}).get("error") != "error":
            seen_valid_commands.add(_command_key(tc.get("command", "")))

    _save_technique_file(timestamp, tc_list)

    filename = f"test_case_{timestamp}.py"
    file_path = os.path.join(BASE_DIR, filename)
    test_code = _build_test_code(
        driver_type=driver_type,
        port=port,
        browser=browser,
        base_url=base_url,
        params=params,
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    if not validate_test_code(test_code):
        print("[보안] 위험 코드 탐지 — pytest 실행 차단")
        return {"timestamp": timestamp, "filename": filename, "report_generated": False}

    report_generated = driver_type != "none"
    if report_generated:
        subprocess.run(["pytest", filename, "--json-report"], cwd=BASE_DIR)
    else:
        print(f"TC 생성 완료: {filename}")
        print(f"선택한 드라이버 타입({driver_type})은 현재 실행 없이 TC 생성만 수행합니다.")

    return {
        "timestamp": timestamp,
        "filename": filename,
        "report_generated": report_generated,
    }
