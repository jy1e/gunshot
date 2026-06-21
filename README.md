# 🔫 GUNSHOT

> **AI 기반 블랙박스 테스트 자동화 플랫폼**
> 요구사항 문서를 입력하면 AI가 테스트케이스를 자동 설계하고, 선택한 드라이버로 대상 시스템까지 자동 검증합니다.

---

## 📌 한 줄 소개

```
요구사항 문서 → AI TC 자동 설계 → pytest 자동 실행 → 드라이버 → 대상 시스템 검증 → 결과 리포트
```

임베디드 하드웨어(RC카)부터 웹 애플리케이션까지, 드라이버만 교체하면 어떤 시스템에도 적용 가능한 확장형 테스트 자동화 프레임워크입니다.

---

## 🧱 시스템 아키텍처

```
요구사항 문서 (docx / pdf / txt)
        ↓
stage1_parser.py     — 문서 파싱 및 텍스트 추출
        ↓
stage2_api.py        — Groq API(LLaMA 3.3) TC 자동 설계
        ↓
stage3_pytest.py     — pytest 파일 자동 생성 및 실행
        ↓
stage4_driver.py     — 드라이버 레이어 (RC Car / Web/App)
        ↓
대상 시스템 검증
        ↓
stage5_gui.py        — GUI 결과 리포트
```

---

## 🎯 주요 기능

### 1. AI 기반 블랙박스 TC 자동 설계
Groq API(LLaMA 3.3)가 요구사항 문서를 분석하여 4가지 블랙박스 기법으로 TC를 자동 설계합니다.

| 기법 | 설명 |
|---|---|
| 상태전이 | 시스템 상태 변화 시나리오 검증 |
| 경계값 | 입력값의 최솟값/최댓값 경계 검증 |
| 동등분할 | 유효/무효 입력 그룹별 대표값 검증 |
| 무효전이 | 허용되지 않는 입력에 대한 에러 응답 검증 |

### 2. 확장 가능한 드라이버 구조

```
BaseDriver (추상 클래스)
├── RCCarDriver   — pyserial → 아두이노 JSON 양방향 통신
└── WebAppDriver  — Selenium → Chrome / Edge 브라우저 자동화
```

드라이버만 교체하면 임베디드 하드웨어, 웹앱, 모바일(Appium) 등 어떤 시스템에도 동일한 파이프라인 적용 가능합니다.

### 3. 보안 검증
AI가 생성한 pytest 파일을 실행 전 정적 분석으로 위험 코드(`exec`, `eval`, `os.system` 등)를 탐지하고 차단합니다.

### 4. 결과 리포트
- PASS / FAIL 요약 카드
- 기법별 TC 결과 테이블 (명령어 / 테스트 기법 / 결과 / 에러 메시지)
- PASS/FAIL 비율 파이차트

---

## 🗂️ 프로젝트 구조

```
GUNSHOT/
├── stage1_parser.py       # 문서 파싱 (docx/pdf/txt)
├── stage2_api.py          # Groq API TC 자동 설계
├── stage3_pytest.py       # pytest 자동 생성 및 실행
├── stage4_driver.py       # 드라이버 레이어
├── stage4_ar_driver.ino   # 아두이노 펌웨어
├── stage5_gui.py          # GUI
├── .env                   # API 키 관리 (Git 제외)
└── .gitignore
```

---

## ⚙️ 설치 방법

### 1. 패키지 설치

```bash
pip install python-docx pdfplumber groq python-dotenv
pip install pytest pytest-json-report
pip install pyserial
pip install selenium webdriver-manager
pip install customtkinter pillow
```

### 2. API 키 설정

`.env` 파일을 생성하고 Groq API 키를 입력합니다.

```
GROQ_API_KEY=your_api_key_here
```

Groq API 키 발급: [console.groq.com](https://console.groq.com)

### 3. 아두이노 설정 (RC Car 드라이버 사용 시)

Arduino IDE에서 `ArduinoJson` 라이브러리를 설치하고 `stage4_ar_driver.ino`를 업로드합니다.

---

## 🚀 실행 방법

```bash
python stage5_gui.py
```

1. **요구사항 문서 선택** — docx / pdf / txt 파일 업로드
2. **Driver Type 선택** — RC Car / Web/App
3. **연결 설정** — 시리얼 포트 또는 브라우저/URL 선택
4. **Generate TC** 클릭 → AI TC 자동 생성 및 실행
5. **결과 확인** — 결과 페이지에서 PASS/FAIL 확인

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|---|---|
| AI | Groq API (LLaMA 3.3 70B) |
| 테스트 | pytest, pytest-json-report |
| 임베디드 | pyserial, ArduinoJson |
| 웹 자동화 | Selenium, webdriver-manager |
| GUI | customtkinter |
| 문서 파싱 | python-docx, pdfplumber |

---

## 🔒 보안 고려사항

| 분류 | 위협 | 대응 |
|---|---|---|
| 데이터 | 요구사항 문서 외부 유출 | Groq Zero-Data Retention 정책 적용 |
| 코드 | AI 생성 악성 스크립트 | 정적 분석으로 위험 함수 탐지 및 차단 |
| AI | 프롬프트 인젝션 | 가드레일 프롬프트 + JSON 형식 강제 |
| 자산 | API Key 유출 | .env 파일 관리 + .gitignore 적용 |

---

## 📋 적용 도메인

| 드라이버 | 대상 | 통신 방식 |
|---|---|---|
| RCCarDriver | 임베디드 하드웨어 (RC카) | JSON / UART 시리얼 |
| WebAppDriver | 웹 애플리케이션 | Selenium (Chrome/Edge) |
| MobileDriver (예정) | 모바일 앱 | Appium |

---

## 📄 라이선스

MIT License
