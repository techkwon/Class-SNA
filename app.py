import streamlit as st
import pandas as pd
import logging
import os
import tempfile
import time

from src.api_manager import APIManager
from src.data_processor import DataProcessor
from src.network_analyzer import NetworkAnalyzer
from src.visualizer import NetworkVisualizer
from src.report_generator import ReportGenerator
from src.utils import set_streamlit_page_config, show_footer, check_and_create_assets, handle_error

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 페이지 설정
set_streamlit_page_config()

# assets 디렉토리 확인
check_and_create_assets()

# 다크모드에서 텍스트가 잘 보이도록 전역 CSS 설정
def apply_global_css():
    """다크모드에서도 텍스트가 잘 보이도록 CSS 적용"""
    dark_mode_css = """
    <style>
    /* 알림 메시지의 글씨를 항상 검은색으로 설정 */
    div[data-testid="stAlert"] p {
        color: black !important;
        font-weight: 500 !important;
    }
    
    /* 알림 메시지의 배경색을 더 밝게 설정 */
    div[data-testid="stAlert"] {
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid rgba(0, 0, 0, 0.2) !important;
    }
    
    /* HTML 태그가 그대로 보이는 문제 수정 */
    .vis-tooltip, .vis-network-tooltip {
        white-space: pre-wrap !important;
    }
    
    /* <br> 태그 처리 */
    .vis-tooltip br, .vis-network-tooltip br {
        display: block !important;
        content: " " !important;
    }
    </style>
    """
    st.markdown(dark_mode_css, unsafe_allow_html=True)

def main():
    # 전역 CSS 적용
    apply_global_css()
    
    # 페이지 헤더
    st.markdown("<div class='main-header'>학급 관계 네트워크 분석 시스템</div>", unsafe_allow_html=True)
    st.markdown("""
    학생 간 관계 설문조사 데이터를 소셜 네트워크 분석(SNA) 그래프로 자동 변환하여 시각화합니다.
    구글 시트 공유 링크를 입력하시면 AI가 데이터를 분석하여 네트워크 그래프를 생성합니다.
    """)
    
    # 사이드바
    with st.sidebar:
        st.markdown("### 데이터 입력")
        st.markdown("""
        학생 관계 설문조사 데이터가 담긴 구글 시트 링크를 입력하세요.
        시트는 '공개' 또는 '링크가 있는 사용자에게 공개' 상태여야 합니다.
        """)
        
        sheet_url = st.text_input("구글 시트 공유 링크:")
        
        # 구글 설문조사 예시 링크 추가
        st.markdown("### 설문조사 양식 예시")
        st.markdown("""
        아래 링크로 학생 관계 설문조사 양식을 복사하여 사용할 수 있습니다:
        
        [📋 설문조사 양식 복사하기](https://docs.google.com/forms/d/1OOpDNUMp3GIooYb0PgvTUHpMJqfHxY7fMGNRAM_Xez8/copy)
        
        이 링크를 통해 설문조사를 생성한 후, 응답 스프레드시트의 링크를 위에 입력하세요.
        """)
        
        st.markdown("### 예시 데이터")
        st.markdown("""
        아래 예시 데이터 중 하나를 선택하여 테스트해볼 수 있습니다:
        """)
        
        example_options = {
            "": "선택하세요",
            "https://docs.google.com/spreadsheets/d/1iBAe4rYrQ8MuQyKVlZ-awqGSiAr9pMAaLK8y5BSrIX8": "예시 1: 가상 학급 친구 관계",
            "https://docs.google.com/spreadsheets/d/1-Nv-aAQkUkS9KYJwF1VlnY6qRKEO5SnNVQfmIZLNDfQ": "예시 2: 협업 선호도"
        }
        
        example_data = st.selectbox(
            "예시 데이터 선택:",
            options=list(example_options.keys()),
            format_func=lambda x: example_options[x]
        )
        
        if example_data:
            sheet_url = example_data
            st.info(f"선택한 예시 데이터: {example_options[example_data]}")
        
        st.markdown("### 분석 실행")
        analyze_button = st.button("분석 시작", type="primary")
    
    # 메인 콘텐츠
    if analyze_button and sheet_url:
        try:
            with st.spinner("데이터를 분석 중입니다. 잠시만 기다려주세요..."):
                # 1. API 매니저 초기화
                api_manager = APIManager()
                
                # 2. 데이터 처리
                data_processor = DataProcessor(api_manager)
                
                # 진행상황 표시
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                # 2.1 데이터 로드
                progress_text.text("구글 시트에서 데이터를 가져오는 중...")
                time.sleep(1)  # UI 표시를 위한 딜레이
                
                try:
                    df = data_processor.load_from_gsheet(sheet_url)
                    progress_bar.progress(20)
                    
                    # 데이터 미리보기
                    st.markdown("<div class='sub-header'>설문조사 데이터 미리보기</div>", unsafe_allow_html=True)
                    st.dataframe(df.head())
                    
                    # 2.2 데이터 구조 분석
                    progress_text.text("AI가 데이터 구조를 분석하는 중...")
                    time.sleep(1)
                    
                    analysis_result = data_processor.analyze_data_structure(df)
                    progress_bar.progress(50)
                    
                    # 2.3 네트워크 데이터로 변환
                    progress_text.text("관계 네트워크 데이터 생성 중...")
                    time.sleep(1)
                    
                    network_data = data_processor.convert_to_network_data(analysis_result)
                    progress_bar.progress(70)
                    
                    # 3. 네트워크 분석
                    progress_text.text("네트워크 분석 및 시각화 준비 중...")
                    
                    analyzer = NetworkAnalyzer(network_data)
                    metrics = analyzer.calculate_centrality()
                    communities = analyzer.detect_communities()
                    progress_bar.progress(85)
                    
                    # 4. 네트워크 시각화
                    visualizer = NetworkVisualizer(analyzer)
                    
                    # 5. 분석 보고서 생성
                    progress_text.text("분석 보고서 생성 중...")
                    time.sleep(1)
                    
                    report_generator = ReportGenerator(analyzer, visualizer)
                    progress_bar.progress(100)
                    progress_text.text("분석 완료!")
                    
                    # 보고서 표시
                    st.markdown("---")
                    report_generator.generate_full_report(network_data)
                    
                except Exception as e:
                    handle_error(e, "데이터 처리")
                
            # 푸터 표시
            show_footer()
                
        except Exception as e:
            handle_error(e, "시스템")
    
    elif analyze_button and not sheet_url:
        st.error("구글 시트 링크를 입력해주세요.")
    
    else:
        # 초기 화면
        st.markdown("<div class='sub-header'>시작하기</div>", unsafe_allow_html=True)
        
        # 설명 카드
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📊 분석 기능
            
            - 학생 간 관계 네트워크 그래프 자동 생성
            - 중심성 지표 계산 (연결, 매개, 근접 중심성)
            - 하위 그룹(커뮤니티) 자동 탐지
            - 소외 학생 식별 및 강조
            - 시각화 및 분석 결과 다운로드
            """)
        
        with col2:
            st.markdown("""
            ### 🛠️ 사용 방법
            
            1. 사이드바에 구글 시트 공유 링크 입력
            2. 또는 예시 데이터 선택
            3. '분석 시작' 버튼 클릭
            4. AI가 데이터 구조를 자동으로 파악
            5. 분석 결과 및 시각화 확인
            6. 필요한 결과 다운로드
            """)
        
        st.markdown("<div class='sub-header'>설문조사 데이터 형식</div>", unsafe_allow_html=True)
        st.markdown("""
        다양한 형식의 설문조사 데이터를 지원합니다. AI가 데이터 구조를 자동으로 분석하여 적절한 네트워크 그래프로 변환합니다.
        
        **지원 형식 예시:**
        - 학생별 선호하는 친구(들) 선택 형식
        - 협업/학습/친목 등 여러 관계 유형 질문
        - 직접 학생 이름 입력 또는 항목 선택 형식
        
        **가장 이상적인 형식:**
        - 첫 번째 열: 응답자(학생) 이름
        - 나머지 열: 관계 질문 (예: "함께 공부하고 싶은 친구는?", "도움을 청하고 싶은 친구는?" 등)
        """)
        
        # 푸터 표시
        show_footer()

if __name__ == "__main__":
    main() 