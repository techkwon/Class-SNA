# PRD: 학급 관계 네트워크 분석 시스템 (Class-SNA)

## 1. 개요 및 목적

**Class-SNA**는 교사가 수집한 학생 간 관계 설문조사 데이터를 소셜 네트워크 분석(SNA) 그래프로 자동 변환하여 시각화하는 웹 애플리케이션입니다. 본 시스템은 Streamlit Cloud 기반으로 배포되며, Google Gemini AI를 활용하여 다양한 형태의 설문조사 데이터를 자동으로 분석하고 적절한 네트워크 그래프로 변환합니다.

**주요 목적:**
- 교사가 학급 내 학생 관계를 시각적으로 파악할 수 있는 도구 제공
- 복잡한 데이터 가공 과정 없이 설문조사 결과를 즉시 네트워크 그래프로 변환
- 학급 내 사회적 관계, 학습 그룹, 소외 학생 등을 식별하여 교육 환경 개선에 활용

## 2. 사용자 프로필

- **주요 사용자**: K-12 중등 교사
- **기술 수준**: 기본적인 컴퓨터 활용 능력을 갖추었으나, 데이터 분석이나 프로그래밍 지식은 제한적
- **사용 목적**: 학급 내 학생 관계 파악, 소그룹 활동 구성, 학생 지원 전략 수립

## 3. 주요 기능

### 3.1 데이터 입력
- 구글 시트 공유 링크 입력을 통한 데이터 가져오기
- 다양한 형식의 설문조사 데이터 지원 (체크박스, 드롭다운, 단답형 등)

### 3.2 AI 기반 데이터 가공
- Gemini-2.0-flash 모델을 활용한 설문조사 데이터 구조 자동 인식
- 설문 응답을 From-To 관계형 데이터로 자동 변환
- 누락되거나 불일치하는 학생 이름 자동 수정 및 통합

### 3.3 네트워크 시각화
- 학생 간 관계를 나타내는 네트워크 그래프 생성
- 다양한 레이아웃 알고리즘 선택 옵션 (ForceAtlas2, Fruchterman-Reingold 등)
- 노드(학생) 크기, 색상 등 시각화 요소 커스터마이징
- 관계 강도에 따른 엣지(연결선) 두께 조정

### 3.4 분석 기능
- 중심성 지표(연결 중심성, 근접 중심성, 매개 중심성 등) 자동 계산
- 주요 하위 그룹(클러스터) 자동 식별
- 소외 학생(연결이 적은 노드) 강조 표시
- 주요 지표 요약 통계 제공

### 3.5 결과 내보내기
- 생성된 그래프 이미지(PNG, SVG) 다운로드
- 가공된 데이터 및 분석 결과 CSV/Excel 형식 내보내기
- 분석 보고서 PDF 생성

## 4. 사용자 흐름

1. 사용자가 Streamlit 애플리케이션에 접속
2. 구글 시트 공유 링크 입력
3. 설문조사 형식 확인 및 데이터 매핑 설정 (AI가 자동으로 제안)
4. 네트워크 그래프 시각화 옵션 선택
5. 그래프 생성 및 표시
6. 분석 결과 확인
7. 결과 다운로드 또는 공유

## 5. 기술 요구사항

### 5.1 기본 프레임워크
- **프론트엔드**: Streamlit
- **배포**: Streamlit Cloud
- **버전 관리**: GitHub
- **인공지능**: Google Gemini API (gemini-2.0-flash 모델)

### 5.2 주요 라이브러리
- **데이터 처리**: pandas, numpy
- **네트워크 분석**: networkx, python-louvain
- **시각화**: matplotlib, plotly, pyvis
- **외부 연동**: gspread, google-auth

### 5.3 API 관리
- **사용 모델**: gemini-2.0-flash
- **API 키 관리**: 10개의 미리 준비된 API 키를 순환 사용
- **API 키 활용 방식**: 
  - 랜덤 방식으로 API 키 선택 및 사용
  - API 오류 발생 시 자동으로 다른 API 키로 전환
  - API 사용량 모니터링 및 로깅

- **API 키 목록**:
  1. AIzaSyD2UzkUP2jxjwzAc3eSZkq9CR1Rrk0szJQ
  2. AIzaSyCv3YJc4QiJtlhymRqpo0rirH3ploC0yR8
  3. AIzaSyB_KV2WIdo21usPYRAUXnlyHIrq9qV2Hzo
  4. AIzaSyDwj5tIYg8X5ASilXiqKnpxrScRdZ1QAUs
  5. AIzaSyDS8RQWjEgB_9pmLUvaAeMoxxYBduVeyJQ
  6. AIzaSyCsExDCjCLZjMHdRaIjo9wZZ_qd9SA-9Es
  7. AIzaSyBltJa9K3bDpbulMvNoWL6OlrUjvfNNIGY
  8. AIzaSyBqmvWg6HOREWX00h3udxF5HwbquF5qIEU
  9. AIzaSyD0UW-mslCxaqMBKAN_AX6C0xhofKaRoLk
  10. AIzaSyAc6I3KtFKFnVJ11JvRtVlYbtaw76siC5I

### 5.4 시스템 요구사항
- Python 3.9 이상
- Google Cloud API 연동
- Streamlit Cloud 무료 티어 내 리소스 사용

## 6. 데이터 처리 프로세스

1. **데이터 가져오기**:
   - 구글 시트 API를 통한 데이터 접근
   - 기본 데이터 구조 검증 및 전처리

2. **AI 기반 데이터 매핑**:
   - Gemini AI를 통한 설문 문항 분석
   - 관계형 질문 자동 인식
   - 적절한 데이터 변환 방법 추천

3. **네트워크 데이터 생성**:
   - From-To 형식의 엣지 리스트 생성
   - 관계 가중치 계산 (언급 빈도 등)
   - 노드 속성 정의 (학생 이름, 학년 등)

4. **네트워크 분석**:
   - 중심성 지표 계산
   - 커뮤니티 탐지 알고리즘 적용
   - 주요 통계 지표 계산

## 7. UI/UX 요구사항

### 7.1 인터페이스 구성
- 직관적이고 단순한 사용자 인터페이스
- 단계별 가이드 형태의 워크플로우
- 모바일 기기 호환성 (반응형 디자인)

### 7.2 시각화 옵션
- 다양한 그래프 레이아웃 제공
- 노드/엣지 스타일 커스터마이징 옵션
- 인터랙티브 그래프 (확대/축소, 노드 드래그, 정보 툴팁)

### 7.3 사용자 가이드
- 각 단계별 도움말 기능
- 시스템 사용 예시 비디오 또는 이미지
- 자주 묻는 질문(FAQ) 섹션

## 8. 보안 및 개인정보 보호

- 학생 개인정보 보호를 위한 익명화 옵션
- 데이터 로컬 처리 우선 (가능한 서버에 저장하지 않음)
- 구글 시트 접근은 읽기 전용으로 제한
- 교사 인증 옵션 제공 (선택적)

## 9. 파일 구조

```
Class-SNA/
├── .github/                    # GitHub 관련 설정
│   └── workflows/              # GitHub Actions 워크플로우
│       └── deploy.yml          # Streamlit Cloud 자동 배포 설정
├── .gitignore                  # Git 무시 파일 목록
├── README.md                   # 프로젝트 소개 및 사용 방법
├── requirements.txt            # 필요한 Python 패키지 목록
├── PRD.md                      # 제품 요구사항 문서
├── LICENSE                     # 라이센스 정보
├── app.py                      # 메인 Streamlit 애플리케이션
├── config.py                   # 설정 파일 (API 키 관리 등)
├── assets/                     # 정적 파일 (이미지, CSS 등)
│   ├── logo.png                # 애플리케이션 로고
│   └── styles.css              # 커스텀 CSS 스타일
└── src/                        # 소스 코드
    ├── __init__.py             # Python 패키지 초기화
    ├── api_manager.py          # API 키 관리 및 Gemini API 호출 모듈
    ├── data_processor.py       # 데이터 처리 및 변환 모듈
    ├── network_analyzer.py     # 네트워크 분석 기능 모듈
    ├── visualizer.py           # 네트워크 시각화 모듈
    ├── report_generator.py     # 분석 보고서 생성 모듈
    └── utils.py                # 유틸리티 함수 모듈
```

## 10. 배포 및 유지보수 계획

- GitHub 저장소를 통한 코드 관리 및 버전 관리
- Streamlit Cloud를 통한 자동 배포
- 월간 유지보수 일정 수립
- 사용자 피드백 수집 및 개선사항 적용 프로세스

## 11. 향후 개선사항

- 시계열 데이터 지원 (학기별 변화 추적)
- 고급 분석 기능 추가 (예측 모델링, 추천 시스템)
- 여러 학급 간 비교 분석 기능
- 모바일 앱 버전 개발

## 12. 구현 일정

- **1단계** (2주): 기본 프레임워크 설정, GitHub 저장소 구성
- **2단계** (3주): 데이터 가져오기 및 AI 기반 처리 구현
- **3단계** (2주): 네트워크 분석 및 시각화 구현
- **4단계** (1주): UI/UX 개선 및 사용자 테스트
- **5단계** (1주): 최종 테스트 및 Streamlit Cloud 배포

---

이 PRD는 Class-SNA 시스템의 기본 요구사항과 구현 방향을 제시합니다. 개발 과정에서 교사 및 교육 전문가의 피드백을 반영하여 지속적으로 업데이트될 예정입니다.