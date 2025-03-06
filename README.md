# 학급 관계 네트워크 분석 시스템 (Class-SNA)

학급 관계 네트워크 분석 시스템(Class-SNA)은 교사가 수집한 학생 간 관계 설문조사 데이터를 소셜 네트워크 분석(SNA) 그래프로 자동 변환하여 시각화하는 웹 애플리케이션입니다.

## 주요 기능

- 구글 시트 공유 링크를 통한 설문 데이터 가져오기
- Google Gemini AI를 활용한 자동 데이터 구조 분석 및 변환
- 학생 간 관계를 시각화하는 네트워크 그래프 생성
- 중심성 지표 계산 및 하위 그룹 자동 식별
- 분석 결과 및 그래프 내보내기

## 설치 및 실행 방법

### 로컬 환경에서 실행하기

1. 저장소 클론:
   ```
   git clone https://github.com/yourusername/Class-SNA.git
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

1. 구글 시트 공유 링크 입력
2. 데이터 매핑 설정 확인 (AI가 자동으로 제안)
3. 네트워크 그래프 시각화 옵션 선택
4. 분석 결과 확인 및 내보내기

## 기여하기

프로젝트에 기여하고 싶으시다면 다음 단계를 따라주세요:

1. 이 저장소를 포크합니다
2. 새로운 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요. 