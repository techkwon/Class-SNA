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
    
    /* 버튼 스타일 개선 */
    .reset-button {
        background-color: #f44336;
        color: white;
        border: none;
        padding: 8px 16px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 14px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 4px;
    }
    </style>
    """
    st.markdown(dark_mode_css, unsafe_allow_html=True)

def init_session_state():
    """세션 상태 초기화"""
    # 기본 UI 상태
    if 'analyzed' not in st.session_state:
        st.session_state.analyzed = False
    if 'example_selected' not in st.session_state:
        st.session_state.example_selected = ""
    if 'sheet_url' not in st.session_state:
        st.session_state.sheet_url = ""
        
    # 레이아웃 상태 관리
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0  # 기본 탭 인덱스
    if 'selected_layout' not in st.session_state:
        st.session_state.selected_layout = "fruchterman"  # 기본 레이아웃
    if 'selected_metric' not in st.session_state:
        st.session_state.selected_metric = "in_degree"  # 기본 중심성 지표
    if 'top_n' not in st.session_state:
        st.session_state.top_n = 10  # 기본 상위 학생 수

def reset_session():
    """세션 상태를 완전히 초기화"""
    # 모든 세션 상태를 삭제
    for key in list(st.session_state.keys()):
        del st.session_state[key]
        
    # 기본값 설정
    st.session_state.analyzed = False
    st.session_state.example_selected = ""
    st.session_state.sheet_url = ""
    st.session_state.network_data = None
    st.session_state.selected_layout = "fruchterman"
    st.session_state.selected_metric = "in_degree"
    st.session_state.top_n = 10
    st.session_state.active_tab = 0
    
    # 캐시 디렉토리 정리
    try:
        import shutil
        cache_dirs = ['.streamlit', '.cache']
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                for item in os.listdir(cache_dir):
                    item_path = os.path.join(cache_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
    except Exception as e:
        logger.warning(f"캐시 정리 중 오류: {str(e)}")
    
    # 중복 요소 방지를 위한 페이지 새로고침
    st.rerun()

def main():
    # 전역 CSS 적용
    apply_global_css()
    
    # 필수 디렉토리 확인
    check_and_create_assets()
    
    # 세션 상태 초기화
    init_session_state()
    
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
        
        # URL 입력 필드
        sheet_url = st.text_input("구글 시트 공유 링크:", value=st.session_state.sheet_url)
        
        # URL 변경 시 세션 상태 업데이트
        if sheet_url != st.session_state.sheet_url:
            st.session_state.sheet_url = sheet_url
            # URL 변경 시 example_selected 초기화
            st.session_state.example_selected = ""
        
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
            "example1": "예시 1: 가상 학급 친구 관계",
            "example2": "예시 2: 협업 선호도"
        }
        
        # 예시 데이터 선택 - 세션 상태 사용
        example_data = st.selectbox(
            "예시 데이터 선택:",
            options=list(example_options.keys()),
            format_func=lambda x: example_options[x],
            index=list(example_options.keys()).index(st.session_state.example_selected) if st.session_state.example_selected in example_options else 0,
            key="example_selector"
        )
        
        # 예시 데이터 선택 시 처리
        if example_data != st.session_state.example_selected:
            st.session_state.example_selected = example_data
            if example_data:  # 예시 데이터 선택 시 URL 설정
                st.session_state.sheet_url = example_data  # 예시 식별자를 그대로 URL로 사용
                sheet_url = st.session_state.sheet_url
                st.info(f"선택한 예시 데이터: {example_options[example_data]}")
        
        st.markdown("### 분석 실행")
        
        # 분석 및 초기화 버튼
        col1, col2 = st.columns(2)
        
        with col1:
            # 분석 시작 버튼 추가
            analyze_button = st.button("분석 시작", type="primary", key="analyze_button")
        
        with col2:
            # 초기화 버튼
            reset_button = st.button("데이터 초기화", key="reset_button")
    
    # 초기화 버튼 클릭 시
    if reset_button:
        reset_session()
    
    # 메인 영역
    if analyze_button or st.session_state.analyzed:
        # URL이 비어있는지 확인
        if not sheet_url:
            st.error("구글 시트 공유 링크를 입력하거나 예시 데이터를 선택해주세요.")
            st.stop()
        
        # 분석 상태 설정
        st.session_state.analyzed = True
        
        # 동일한 URL인 경우 이전 분석 결과 재사용
        if 'last_analyzed_url' in st.session_state and 'network_data' in st.session_state:
            if sheet_url == st.session_state.last_analyzed_url and st.session_state.network_data:
                show_analysis_results()
                st.stop()
        
        # 새로운 URL 분석
        with st.spinner("데이터를 분석 중입니다. 잠시만 기다려주세요..."):
            try:
                # 1. API 매니저 초기화
                api_manager = APIManager()
                
                # 2. 데이터 처리
                data_processor = DataProcessor(api_manager)
                
                # 진행상황 표시
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                # 2.1 데이터 로드
                progress_text.text("구글 시트에서 데이터를 가져오는 중...")
                time.sleep(0.5)  # UI 표시를 위한 딜레이
                
                # 예시 데이터인 경우 내장 데이터 사용
                if sheet_url.startswith("example"):
                    # 파일 경로 구성
                    example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f"{sheet_url}.csv")
                    
                    # 파일 존재 확인
                    if os.path.exists(example_path):
                        df = pd.read_csv(example_path)
                    else:
                        st.error(f"예시 데이터 파일이 존재하지 않습니다: {example_path}")
                        st.stop()
                else:
                    # 실제 구글 시트에서 데이터 로드
                    df = data_processor.load_from_gsheet(sheet_url)
                
                progress_bar.progress(20)
                
                # 데이터 미리보기
                st.markdown("<div class='sub-header'>설문조사 데이터 미리보기</div>", unsafe_allow_html=True)
                st.dataframe(df.head())
                
                # 2.2 데이터 구조 분석
                progress_text.text("AI가 데이터 구조를 분석하는 중...")
                time.sleep(0.5)
                
                # 데이터 구조 분석
                analysis_result = data_processor.analyze_data_structure(df)
                analysis_result['dataframe'] = df  # 데이터프레임 추가
                progress_bar.progress(50)
                
                # 2.3 네트워크 데이터로 변환
                progress_text.text("관계 네트워크 데이터 생성 중...")
                time.sleep(0.5)
                
                # 네트워크 데이터 변환
                network_data = data_processor.convert_to_network_data(analysis_result)
                progress_bar.progress(70)
                
                # 세션 상태에 저장
                st.session_state.network_data = network_data
                st.session_state.last_analyzed_url = sheet_url
                
                # 2.4 네트워크 분석
                progress_text.text("네트워크 분석 및 시각화 생성 중...")
                
                # 세션에서 network_data가 변경되었는지 확인
                network_data = st.session_state.network_data
                
                # 3. 네트워크 분석
                analyzer = NetworkAnalyzer(network_data)
                
                # 분석 지표 계산
                analyzer.calculate_centrality()
                progress_bar.progress(80)
                
                # 커뮤니티 탐지
                communities = analyzer.detect_communities()
                progress_bar.progress(90)
                
                # 4. 시각화
                visualizer = NetworkVisualizer(analyzer)
                
                # 한글 폰트 설정
                set_korean_font()
                
                # 5. 보고서 생성
                report_generator = ReportGenerator(analyzer, visualizer)
                
                # 진행 완료
                progress_bar.progress(100)
                progress_text.empty()
                
                # 분석 결과 표시
                st.markdown("<div class='sub-header'>분석 결과</div>", unsafe_allow_html=True)
                report_generator.generate_full_report(network_data)
                
                # 푸터 표시
                show_footer()
                
            except Exception as e:
                # 오류 처리
                handle_error(e, error_type="데이터 처리")
    
    # 초기 화면
    elif not st.session_state.analyzed:
        # 시작 안내
        st.info("👈 왼쪽 사이드바에서 데이터를 입력하고 '분석 시작' 버튼을 클릭하세요.")
        
        # 설명 추가
        st.markdown("""
        ### 📊 이 앱으로 무엇을 할 수 있나요?
        
        이 앱은 학급 내 학생들 간의 관계를 분석하여 다음과 같은 정보를 제공합니다:
        
        1. **학생 간 관계 시각화**: 누가 누구와 연결되어 있는지 직관적으로 확인할 수 있습니다.
        2. **중심성 분석**: 학급 내에서 인기가 많거나 영향력이 큰 학생을 식별합니다.
        3. **그룹 분석**: 자연스럽게 형성된 소그룹(커뮤니티)을 탐지합니다.
        4. **소외 학생 식별**: 관계망에서 소외된 학생을 찾아내 개입이 필요한 경우를 알려줍니다.
        5. **관계 패턴 분석**: 학급 전체의 관계 패턴을 요약하여 보여줍니다.
        
        ### 🔍 사용 방법
        
        1. 구글 폼으로 학생들의 관계 설문조사를 실시합니다 (예: "함께 일하고 싶은 친구는?")
        2. 구글 시트로 응답을 수집하고 시트의 공유 링크를 복사합니다
        3. 이 앱에 링크를 붙여넣고 '분석 시작' 버튼을 클릭합니다
        
        ### 🛠️ 필요한 데이터 형식
        
        - 응답자 이름/ID를 포함하는 열 1개 이상
        - 관계를 나타내는 질문(누구와 함께 하고 싶은지 등)을 포함하는 열 1개 이상
        
        ### 📝 예시 질문
        
        - "함께 공부하고 싶은 친구는 누구인가요?"
        - "어려운 일이 있을 때 도움을 청하고 싶은 친구는?"
        - "여가 시간을 함께 보내고 싶은 친구는?"
        """)
        
        # 푸터 표시
        show_footer()

# 분석 결과 표시 함수
def show_analysis_results():
    """저장된 분석 결과 표시"""
    try:
        # 세션에서 network_data 가져오기
        network_data = st.session_state.network_data
        
        # 분석 객체 생성
        analyzer = NetworkAnalyzer(network_data)
        
        # 분석 지표 계산 (이미 계산되어 있을 수 있음)
        if not hasattr(analyzer, 'metrics') or not analyzer.metrics:
            analyzer.calculate_centrality()
        
        # 커뮤니티 탐지 (이미 탐지되어 있을 수 있음)
        if not hasattr(analyzer, 'communities') or not analyzer.communities:
            analyzer.detect_communities()
        
        # 시각화 객체 생성
        visualizer = NetworkVisualizer(analyzer)
        
        # 한글 폰트 설정
        set_korean_font()
        
        # 보고서 생성기 생성
        report_generator = ReportGenerator(analyzer, visualizer)
        
        # 분석 결과 표시
        st.markdown("<div class='sub-header'>분석 결과</div>", unsafe_allow_html=True)
        report_generator.generate_full_report(network_data)
        
        # 푸터 표시
        show_footer()
    
    except Exception as e:
        # 오류 처리
        handle_error(e, error_type="분석 결과 표시")

if __name__ == "__main__":
    main() 