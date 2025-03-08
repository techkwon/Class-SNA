import streamlit as st
import pandas as pd
import logging
import os
import tempfile
import time
import glob
from datetime import datetime

from src.api_manager import APIManager
from src.data_processor import DataProcessor
from src.network_analyzer import NetworkAnalyzer
from src.visualizer import NetworkVisualizer, set_korean_font
from src.report_generator import ReportGenerator
from src.utils import set_streamlit_page_config, show_footer, check_and_create_assets, handle_error

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 페이지 설정
set_streamlit_page_config()

# assets 디렉토리 확인
check_and_create_assets()

# 글로벌 CSS 적용
def apply_global_css():
    """전역 CSS 스타일을 적용합니다"""
    css = """
    <style>
    /* 헤더 스타일 */
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #1E88E5;
    }
    
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin: 1rem 0;
        padding-top: 1rem;
        border-top: 1px solid #f0f0f0;
        color: #0D47A1;
    }

    /* 카드 스타일 */
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
    }
    
    /* 알림 스타일 */
    .alert {
        padding: 0.75rem 1.25rem;
        border: 1px solid transparent;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    
    .alert-info {
        color: #0c5460;
        background-color: #d1ecf1;
        border-color: #bee5eb;
    }
    
    .alert-warning {
        color: #856404;
        background-color: #fff3cd;
        border-color: #ffeeba;
    }
    
    /* 다크 모드 지원 */
    @media (prefers-color-scheme: dark) {
        .card {
            background-color: #1e1e1e;
            border-color: #333333;
        }
        
        .alert-info {
            color: #d1ecf1;
            background-color: #0c5460;
            border-color: #0c5460;
        }
        
        .alert-warning {
            color: #fff3cd;
            background-color: #856404;
            border-color: #856404;
        }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def init_session_state():
    """세션 상태 초기화 (없는 경우에만)"""
    # 기본 상태 초기화
    if 'initialized' not in st.session_state:
        # 분석 관련 상태
        if 'analyzed' not in st.session_state:
            st.session_state.analyzed = False
        if 'network_data' not in st.session_state:
            st.session_state.network_data = None
        if 'sheet_url' not in st.session_state:
            st.session_state.sheet_url = ""
        if 'example_selected' not in st.session_state:
            st.session_state.example_selected = ""
        if 'button_clicked' not in st.session_state:
            st.session_state.button_clicked = False
            
        # 시각화 관련 상태
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0
        if 'centrality_metric' not in st.session_state:
            st.session_state.centrality_metric = 'in_degree'
        if 'layout_option' not in st.session_state:
            st.session_state.layout_option = 'fruchterman'
            
        # 이미 초기화되었음을 표시
        st.session_state.initialized = True
        logger.info("세션 상태 초기화 완료")

def reset_session():
    """모든 세션 상태를 초기화합니다"""
    # 세션 상태의 모든 키 삭제
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # 초기화 플래그 설정
    st.session_state.initialized = False
    
    # 다시 초기화 실행
    init_session_state()
    
    logger.info("세션 상태 초기화됨")

def get_example_data_files():
    """data 디렉토리에서 예시 데이터 파일 목록을 가져옵니다"""
    try:
        # 앱 디렉토리 경로
        app_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(app_dir, 'data')
        
        # data 디렉토리가 없으면 생성
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.info(f"데이터 디렉토리 생성: {data_dir}")
            return []  # 디렉토리가 없었으면 빈 목록 반환
        
        # CSV 파일 검색
        csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
        
        # 파일명만 추출하고 확장자 제거
        example_files = [os.path.splitext(os.path.basename(file))[0] for file in csv_files]
        
        logger.info(f"예시 데이터 파일 {len(example_files)}개 발견: {example_files}")
        return sorted(example_files)
    except Exception as e:
        logger.error(f"예시 데이터 파일 목록 조회 중 오류: {str(e)}")
        return ["example1", "example2"]  # 오류 발생 시 기본값 반환

# 예시 데이터 설명 및 제목 함수
def get_example_data_info(example_name):
    """예시 데이터에 대한 제목과 설명을 반환합니다"""
    # 예시 데이터 제목과 설명 매핑
    example_info = {
        "example1": {
            "title": "가상 학급 친구 관계 데이터",
            "description": """
            이 데이터는 중학교 3학년 가상 학급의 친구 관계를 표현한 예시입니다.
            각 학생은 '함께 공부하고 싶은 친구'와 '여가 시간을 보내고 싶은 친구'를 각각 3명씩 선택했습니다.
            """
        },
        "example2": {
            "title": "협업 선호도 데이터",
            "description": """
            이 데이터는 회사 내 프로젝트 팀원들의 협업 선호도를 조사한 결과입니다.
            각 팀원은 '함께 프로젝트를 진행하고 싶은 동료'를 5명씩 선택했습니다.
            """
        }
    }
    
    # 기본 설명 형식
    default_info = {
        "title": f"예시 데이터: {example_name}",
        "description": f"""
        이 데이터는 학급 관계 네트워크 분석을 위한 예시 데이터입니다.
        """
    }
    
    # 해당 예시 데이터의 정보 반환 (없으면 기본 정보)
    return example_info.get(example_name, default_info)

# 예시 데이터 제목 얻기 함수
def get_example_title(example_name):
    """예시 데이터의 제목만 반환합니다"""
    info = get_example_data_info(example_name)
    return info["title"]

# 예시 데이터 설명 얻기 함수
def get_example_description(example_name):
    """예시 데이터의 설명만 반환합니다"""
    info = get_example_data_info(example_name)
    return info["description"]

def upload_page():
    """데이터 업로드 및 분석 시작 페이지"""
    # 사이드바
    with st.sidebar:
        st.markdown("### 데이터 입력")
        st.markdown("구글 시트 공유 링크를 입력하세요.")
        
        # URL 입력 필드 - 고유 키 부여
        sheet_url = st.text_input("구글 시트 공유 링크:", 
                                value=st.session_state.get('sheet_url', ''),
                                key="url_input")
        
        # URL 변경 시 세션 상태 업데이트
        if sheet_url != st.session_state.get('sheet_url', ''):
            st.session_state.sheet_url = sheet_url
            # URL 변경 시 example_selected 초기화
            st.session_state.example_selected = ""
        
        # 예시 데이터 섹션
        st.markdown("### 예시 데이터")
        st.markdown("테스트용 예시 데이터를 선택하세요:")
        
        # 예시 목록 추출
        example_options = get_example_data_files()
        
        # 예시 데이터와 제목 매핑 생성 (드롭다운 표시용)
        example_titles = {ex: get_example_title(ex) for ex in example_options}
        
        # 빈 선택지 추가
        all_options = [""] + example_options
        format_func = lambda x: "선택하세요" if x == "" else f"{x}: {example_titles.get(x, x)}"
        
        # 예시 선택 드롭다운
        example_selection = st.selectbox(
            "예시 데이터 선택:", 
            options=all_options,
            index=0,
            format_func=format_func,
            key="example_selectbox"
        )
        
        # 예시 선택 시 처리
        if example_selection != st.session_state.get('example_selected', ''):
            st.session_state.example_selected = example_selection
            if example_selection:
                # 예시 파일 경로 구성
                example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f"{example_selection}.csv")
                if os.path.exists(example_path):
                    st.session_state.sheet_url = example_selection
                    
                    # 예시 데이터 설명 표시
                    st.success(f"'{example_titles.get(example_selection, example_selection)}' 예시 데이터가 선택되었습니다.")
                    st.markdown(get_example_description(example_selection))
                else:
                    st.error(f"예시 데이터 파일을 찾을 수 없습니다: {example_path}")
                    st.session_state.example_selected = ""
        
        # 분석 버튼
        analyzer_button = st.button(
            "분석 시작", 
            disabled=not bool(st.session_state.get('sheet_url', '')),
            use_container_width=True,
            key="analyze_button"
        )
        
        # 상태 유지와 무관하게 버튼이 작동하도록 조건 수정
        if analyzer_button:
            with st.spinner("데이터 분석 중입니다..."):
                try:
                    # 간소화된 진행 표시
                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                    
                    # API 초기화 및 데이터 로드
                    progress_text.text("데이터 로드 중...")
                    progress_bar.progress(25)
                    
                    # API 매니저 초기화
                    api_manager = APIManager()
                    data_processor = DataProcessor(api_manager)
                    
                    # 데이터 처리
                    progress_text.text("데이터 처리 중...")
                    progress_bar.progress(50)
                    
                    sheet_url = st.session_state.get('sheet_url', '')
                    
                    # 파일 또는 URL에서 데이터 로드
                    if sheet_url.startswith("example"):
                        # 예시 파일 로드
                        example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f"{sheet_url}.csv")
                        if os.path.exists(example_path):
                            df = pd.read_csv(example_path)
                            network_data = data_processor.process_network_data(df)
                        else:
                            st.error(f"예시 파일을 찾을 수 없습니다: {example_path}")
                            progress_bar.empty()
                            progress_text.empty()
                            return
                    else:
                        # 구글 시트에서 데이터 로드
                        network_data = data_processor.process_survey_data(sheet_url)
                    
                    if not network_data:
                        st.error("데이터 처리에 실패했습니다.")
                        progress_bar.empty()
                        progress_text.empty()
                        return
                    
                    # 네트워크 분석 수행
                    progress_text.text("네트워크 분석 중...")
                    progress_bar.progress(75)
                    
                    # 네트워크 분석기 생성
                    network_analyzer = NetworkAnalyzer(network_data)
                    
                    # 세션 상태에 저장
                    st.session_state.network_analyzer = network_analyzer
                    st.session_state.network_data = network_data
                    
                    # 진행 완료
                    progress_bar.progress(100)
                    progress_text.text("분석 완료!")
                    time.sleep(0.5)
                    progress_bar.empty()
                    progress_text.empty()
                    
                    # 분석 결과 페이지로 전환
                    st.session_state.page = 'analysis'
                    st.experimental_rerun()
                    
                except Exception as e:
                    import traceback
                    logger.error(f"데이터 분석 중 오류: {str(e)}")
                    logger.error(traceback.format_exc())
                    if 'progress_bar' in locals():
                        progress_bar.empty()
                    if 'progress_text' in locals():
                        progress_text.empty()
                    st.error(f"데이터 분석 중 오류가 발생했습니다: {str(e)}")
        
        # 세션 초기화 버튼
        if st.button("🗑️ 초기화", use_container_width=True, key="reset_button"):
            reset_session()
            st.experimental_rerun()
    
    # 메인 컨텐츠
    st.markdown("## 데이터 업로드")
    
    st.info("""
    **데이터 형식 안내**
    - 구글 시트 또는 CSV 파일로 데이터를 준비하세요
    - 첫 번째 열: 학생 ID 또는 이름
    - 두 번째 열부터: 학생들이 선택한 다른 학생들
    """)
    
    upload_container = st.container()
    
    with upload_container:
        # 파일 업로드 기능
        uploaded_file = st.file_uploader("Excel 또는 CSV 파일 업로드", type=["xlsx", "csv"])
        
        if uploaded_file is not None:
            try:
                # 파일 형식에 따라 다른 방식으로 로드
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # 데이터 미리보기
                st.subheader("데이터 미리보기")
                st.dataframe(df.head())
                
                # 분석 버튼
                if st.button("이 데이터로 분석 시작", key="analyze_uploaded_file"):
                    with st.spinner("데이터 분석 중입니다..."):
                        try:
                            # API 및 데이터 처리기 초기화
                            api_manager = APIManager()
                            data_processor = DataProcessor(api_manager)
                            
                            # 데이터 처리
                            network_data = data_processor.process_network_data(df)
                            
                            if not network_data:
                                st.error("데이터 처리에 실패했습니다.")
                                return
                            
                            # 네트워크 분석기 생성
                            network_analyzer = NetworkAnalyzer(network_data)
                            
                            # 세션 상태에 저장
                            st.session_state.network_analyzer = network_analyzer
                            st.session_state.network_data = network_data
                            
                            # 분석 결과 페이지로 전환
                            st.session_state.page = 'analysis'
                            st.experimental_rerun()
                            
                        except Exception as e:
                            import traceback
                            logger.error(f"업로드 파일 분석 중 오류: {str(e)}")
                            logger.error(traceback.format_exc())
                            st.error(f"데이터 분석 중 오류가 발생했습니다: {str(e)}")
            
            except Exception as e:
                st.error(f"파일 로드 중 오류가 발생했습니다: {str(e)}")
    
    # 사용 가이드
    st.markdown("""
    ## 간단 사용 가이드
    
    1. **데이터 입력**: 구글 시트 링크를 입력하거나 파일 업로드 또는 예시 데이터 선택
    2. **분석 시작**: 버튼을 클릭하여 네트워크 분석 실행
    3. **결과 확인**: 생성된 네트워크 그래프와 분석 결과 확인
    """)

def main():
    # 전역 CSS 적용
    apply_global_css()
    
    # 필수 디렉토리 확인
    check_and_create_assets()
    
    # 세션 상태 초기화
    init_session_state()
    
    # 페이지 제목
    st.title("학급 관계 네트워크 분석 시스템")
    
    # 설명 텍스트
    st.markdown("학생 간 관계 설문조사 데이터를 소셜 네트워크 분석(SNA) 그래프로 변환하여 시각화합니다. 구글 시트 공유 링크를 입력하거나 엑셀 데이터를 선택하세요.")
    
    # 페이지 라우팅
    if st.session_state.page == 'upload':
        upload_page()
    elif st.session_state.page == 'analysis':
        show_analysis_results()
    else:
        st.session_state.page = 'upload'
        st.experimental_rerun()
        
    # 푸터
    st.markdown("""
    <div style="text-align: center; margin-top: 40px; color: #888;">
        <p>© 2023 학급 관계 네트워크 분석 시스템 | 소셜 네트워크 분석 도구</p>
    </div>
    """, unsafe_allow_html=True)

# 분석 결과 표시 함수
def show_analysis_results():
    """분석 결과 표시 페이지"""
    try:
        # 사이드바 제거
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
                width: 0px;
            }
            [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
                width: 0px;
                margin-left: -500px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        # 결과가 있는지 확인
        if 'network_analyzer' not in st.session_state or not st.session_state.network_analyzer:
            st.error("분석 결과가 없습니다. 먼저 데이터를 업로드하고 분석을 실행해주세요.")
            # 버튼 클릭 처리 방식 변경
            if st.button("데이터 업로드 화면으로 돌아가기", key="go_to_upload"):
                # 세션 상태 초기화를 먼저 수행
                for key in list(st.session_state.keys()):
                    if key not in ['page', 'go_to_upload']:
                        del st.session_state[key]
                # 페이지 상태 변경
                st.session_state.page = 'upload'
                st.experimental_rerun()
            return

        # 분석기 가져오기
        analyzer = st.session_state.network_analyzer

        # 보고서 생성기 초기화
        if 'report_generator' not in st.session_state:
            st.session_state.report_generator = ReportGenerator(analyzer)
        report_generator = st.session_state.report_generator

        # 상단 메뉴 탭
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 기본 분석", 
            "🌐 대화형 네트워크", 
            "📈 중심성 분석", 
            "👥 그룹 분석",
            "⚠️ 고립 학생"
        ])

        # 탭 1: 기본 분석
        with tab1:
            report_generator.show_basic_analysis()

        # 탭 2: 대화형 네트워크 시각화 (Plotly 사용)
        with tab2:
            report_generator.show_interactive_network()

        # 탭 3: 중심성 분석
        with tab3:
            report_generator.show_centrality_analysis()

        # 탭 4: 그룹 분석
        with tab4:
            report_generator.show_community_analysis()

        # 탭 5: 고립 학생 분석
        with tab5:
            report_generator.show_isolated_students()

        # CSV 내보내기 버튼
        st.sidebar.header("데이터 내보내기")
        if st.sidebar.button("분석 결과 CSV 내보내기"):
            csv_data = report_generator.export_to_csv()
            st.sidebar.download_button(
                label="CSV 파일 다운로드",
                data=csv_data,
                file_name="social_network_analysis_results.csv",
                mime="text/csv",
            )

        # 보고서 생성 버튼
        if st.sidebar.button("전체 보고서 생성"):
            report_pdf = report_generator.generate_pdf_report()
            st.sidebar.download_button(
                label="PDF 보고서 다운로드",
                data=report_pdf,
                file_name="social_network_analysis_report.pdf",
                mime="application/pdf",
            )

        # 홈으로 돌아가기 버튼
        if st.sidebar.button("새 분석 시작하기"):
            # 세션 상태 초기화
            for key in list(st.session_state.keys()):
                if key != 'page':
                    del st.session_state[key]
            st.session_state.page = 'upload'
            st.rerun()

    except Exception as e:
        st.error(f"결과 표시 중 오류가 발생했습니다: {str(e)}")
        logger.error(f"결과 표시 중 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 