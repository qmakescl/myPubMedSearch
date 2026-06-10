# PubMed Scholar Search Engine

이 프로젝트는 PubMed API(NCBI E-utilities)를 활용하여 의생명과학 분야의 학술 논문을 실시간으로 검색하고 분석할 수 있는 Streamlit 기반의 대시보드 웹 애플리케이션입니다.  
기본 진입점인 `main.py`와 완전히 독립적으로 작동하도록 설계되었습니다.

---

## 🧬 핵심 기능 및 특징

1. **실시간 논문 검색 및 상세 정보 조회**:
   - PubMed API와 연동하여 제목, 저자, 저널, 출판일, DOI, 초록(Abstract) 데이터를 가져옵니다.
   - 구조화된 초록(Structured Abstracts - BACKGROUND, METHODS, RESULTS, CONCLUSION 등)의 레이블과 본문을 완벽하게 보존하여 파싱합니다.
2. **NCBI API Rate Limit 자동 준수**:
   - NCBI 서버의 호출 차단을 방지하기 위해 자동 딜레이(Rate limit delay) 제어 알고리즘이 적용되어 있습니다. (API Key 미사용 시 초당 3회, 등록 시 초당 10회 이내로 호출을 유지함)
3. **학술 데이터 분석 및 다이내믹 필터링**:
   - 검색 결과를 토대로 연도별 출판 논문 수 통계 그래프를 실시간으로 시각화합니다.
   - 출판 연도 범위 슬라이더 필터를 통해 브라우저 상에서 즉각적인 결과 필터링을 지원합니다.
4. **결과 다운로드**:
   - 필터링된 논문 데이터 세트를 CSV 파일 형식으로 즉시 다운로드할 수 있습니다.

---

## 📂 프로젝트 구조 및 파일 구성

```text
suppl/
├── .venv/                  # uv 가상환경 (Git 제외)
├── suppl/
│   └── pubmed_client.py    # PubMed API 연동 클라이언트 (검색, 상세 조회, XML 파싱, 딜레이 제어)
├── pyproject.toml          # 프로젝트 메타데이터 및 의존성 라이브러리 (streamlit, requests 포함)
├── search_app.py           # Streamlit 기반 다이내믹 웹 대시보드 UI 및 스타일링 코드
├── main.py                 # 기본 애플리케이션 진입점 (이 앱과 독립 실행)
└── README.md               # 프로젝트 안내 문서 (본 파일)
```

- **`search_app.py`**: Google Fonts (Inter, Outfit)를 로드하고, 다크 테마/그라데이션 스타일의 CSS가 내장된 프론트엔드 대시보드 소스입니다.
- **`suppl/pubmed_client.py`**: `requests` 모듈로 NCBI ESearch/EFetch API를 호출하고 파싱을 담당하는 재사용 모듈입니다.

---

## 🚀 작동 방법 및 실행 안내

### 1. 가상환경 의존성 동기화
프로젝트가 의존하는 라이브러리(`streamlit`, `requests` 등)를 로컬 가상환경에 동기화합니다.
```bash
uv sync
```

### 2. Streamlit 웹 애플리케이션 실행
독립적으로 동작하는 논문 검색 앱을 구동합니다.
```bash
uv run streamlit run search_app.py
```
서버가 기동되면 웹 브라우저에서 아래의 주소로 접속할 수 있습니다:
* **로컬 접속 주소**: [http://localhost:8501](http://localhost:8501)

---

## ✍️ 문서 정보
* **작성자**: Q의 지시에 의해  Antigravity (Gemini 3.5 Flash) 가 생성
* **작성시간**: 2026-06-10 11:41 (KST)
  
