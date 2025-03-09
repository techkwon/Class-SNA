# 학급 관계 네트워크 분석 시스템 (Class-SNA) v1.0

학급 관계 네트워크 분석 시스템(Class-SNA)은 교사가 수집한 학생 간 관계 설문조사 데이터를 소셜 네트워크 분석(SNA) 그래프로 자동 변환하여 시각화하는 웹 애플리케이션입니다.

## 주요 기능

- 구글 시트 공유 링크를 통한 설문 데이터 가져오기
- Google Gemini AI를 활용한 자동 데이터 구조 분석 및 변환
- 향상된 물리 엔진을 활용한 대화형 네트워크 그래프 시각화
- 노드 클릭 시 시각적 효과 강화로 관계망 탐색 용이성 개선
- 중심성 지표 계산 및 하위 그룹(커뮤니티) 자동 식별
- 한글 이름 지원 및 최적화된 레이아웃 알고리즘
- 고립 학생 자동 감지 및 통계 분석

## 설치 및 실행 방법

### 로컬 환경에서 실행하기

1. 저장소 클론:
   ```
   git clone https://github.com/techkwon/Class-SNA.git
   cd Class-SNA
   ```

2. 필요한 패키지 설치:
   ```
   pip install -r requirements.txt
   ```

3. API 키 설정:
   - `.streamlit/secrets.example.toml` 파일을 복사하여 `.streamlit/secrets.toml` 파일을 생성합니다.
   - 파일을 열고 `google_api_keys` 변수에 Google Gemini API 키를 입력합니다(쉼표로 구분).
   ```toml
   google_api_keys = "키1,키2,키3,..."
   ```

4. 앱 실행:
   ```
   streamlit run app.py
   ```

### Streamlit Cloud에서 사용하기

1. GitHub 저장소를 Streamlit Cloud에 연결합니다.
2. API 키 설정:
   - Streamlit Cloud 대시보드에서 앱 설정으로 이동합니다.
   - 'Secrets' 섹션에서 다음 내용을 추가합니다:
   ```toml
   google_api_keys = "키1,키2,키3,..."
   ```
   또는
   ```toml
   google_api_keys = ["키1", "키2", "키3", ...]
   ```
3. 앱을 배포하면 자동으로 설정된 API 키를 사용합니다.

[https://class-sna.streamlit.app](https://class-sna.streamlit.app) 링크를 통해 직접 접속하여 사용할 수 있습니다.

## 사용 방법

1. 구글 시트 공유 링크 입력 또는 샘플 데이터 사용
2. AI가 자동으로 데이터 구조 분석 및 매핑 제안
3. 네트워크 그래프 생성 및 인터랙티브 시각화 확인
4. 다양한 탭에서 분석 결과 탐색:
   - 📊 학생 분석: 개별 학생의 관계 통계
   - 🌐 대화형 네트워크: 인터랙티브 그래프 
   - 📈 중심성 분석: 학생 영향력 및 역할 분석
   - 👥 그룹 분석: 커뮤니티 구성 확인
   - ⚠️ 고립 학생: 관계망에서 소외된 학생 식별
5. '새 분석 시작하기' 버튼으로 다른 데이터 분석

## 최근 업데이트 (v1.0)

- 🎨 **향상된 시각화**: 개선된 물리 엔진과 색상 대비로 그래프 가시성 향상
- 🖱️ **강화된 인터랙션**: 노드 클릭 시 연결된 관계만 하이라이트 표시
- 🔍 **커뮤니티 탐색 용이성**: 색상 코딩 및 그룹 식별 기능 개선
- 🌏 **한글 폰트 최적화**: 한글 이름이 깔끔하게 표시되도록 개선
- 🧮 **통계 분석 강화**: 더 정확한 중심성 지표 계산 및 시각화
- 🚀 **성능 최적화**: 대용량 데이터 처리 시 성능 개선
- 🔄 **UI 개선**: 더 직관적이고 깔끔한 사용자 인터페이스

## 기여하기

프로젝트에 기여하고 싶으시다면 다음 단계를 따라주세요:

1. 이 저장소를 포크합니다
2. 새로운 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

---

*Made by TechKwon* 