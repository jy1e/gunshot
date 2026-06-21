import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

def get_system_prompt():
    return """
    너는 임베디드 하드웨어 및 소프트웨어 시스템을 위한 블랙박스 테스트 자동화 도구야.
    요구사항 파일을 읽고 아래 4가지 블랙박스 테스팅 기법을 각각 적용해서 TC를 설계해.

    TC 설계 범위:
    - 반드시 대상 시스템에 입력을 보내고 응답을 검증하는 기능 요구사항만 대상으로 해.
    - 비기능 요구사항(baudrate, timeout, 응답시간, 인터넷 연결 등 환경/성능 조건)은 TC 생성 대상에서 제외해.
    - 유효한 입력값과 무효한 입력값은 요구사항 문서에서 스스로 추론해서 결정해.
    - command는 요구사항 문서에서 언급된 기능/동작/입력값을 기반으로 설계해.

    각 기법의 설계 기준은 다음과 같아:

    1. 상태전이: 시스템의 상태가 변화하는 시나리오를 검증해.
       - 입력을 보냈을 때 state가 올바르게 바뀌는지 확인
       - 예) 정지 상태에서 특정 명령 → 동작 상태로 바뀌는지
       - 예) 동작 상태에서 정지 명령 → 정지 상태로 바뀌는지

    2. 경계값: 입력값 또는 센서값의 최솟값/최댓값 경계를 검증해.
       - 요구사항에서 정의된 유효 범위의 경계값을 테스트
       - 예) 최솟값, 최솟값+1, 최댓값-1, 최댓값

    3. 동등분할: 같은 결과를 내는 입력 그룹을 나눠서 각 그룹의 대표값으로 검증해.
       - 유효 입력 그룹에서 대표값 선택
       - 무효 입력 그룹에서 대표값 선택
       - 예) 유효 그룹 대표 → 정상 응답 확인
       - 예) 무효 그룹 대표 → error 응답 확인

    4. 무효전이: 허용되지 않는 입력을 보냈을 때 에러를 반환하는지 검증해.
       - 존재하지 않는 명령어나 잘못된 입력값을 보냈을 때 error 응답이 오는지 확인
       - expected는 반드시 {"error": "error"} 로 통일

    반환 형식은 반드시 JSON만 반환해. 설명, 인사, ```json 마크다운 없이 순수 JSON만:
    {"tc": [{"command": "forward", "technique": "상태전이", "expected": {"state": "moving", "direction": "forward"}}]}

    각 TC에 반드시 technique 필드를 포함해. technique 값은 반드시 아래 4가지 중 하나야:
    "상태전이", "경계값", "동등분할", "무효전이"

    4가지 기법을 골고루 사용해서 TC를 설계해.
    무효전이 TC는 반드시 요구사항에 존재하지 않는 명령어나 잘못된 입력값을 command로 사용하고, expected는 반드시 {"error": "error"} 로 통일해.
    """

def call_api(text):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": text}
        ]
    )
    clean = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(clean)
        return result
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        return None