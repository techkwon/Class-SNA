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
        margin-bottom: 1rem;
        border-radius: 0.25rem;
    }
    
    /* 다크모드 대응 스타일 */
    @media (prefers-color-scheme: dark) {
        .main-header, .sub-header {
            color: #90CAF9 !important;
        }
        
        .card {
            background-color: rgba(49, 51, 63, 0.4) !important;
            border-color: rgba(100, 100, 100, 0.4) !important;
        }
        
        .stTextInput, .stSelectbox, .stDateInput {
            color: #FFFFFF !important;
        }
        
        p, span, label, div {
            color: #FFFFFF !important;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #90CAF9 !important;
        }
        
        .stDataFrame {
            color: #FFFFFF !important;
        }
        
        .stTable th {
            background-color: rgba(100, 100, 100, 0.2) !important;
            color: #FFFFFF !important;
        }
        
        .stTable td {
            color: #FFFFFF !important;
        }
    }
    
    /* 이미지 및 아이콘 스타일 */
    .icon-img {
        width: 64px;
        height: 64px;
        margin-right: 1rem;
    }
    
    /* 버튼 스타일 */
    .stButton>button {
        font-weight: bold !important;
    }
    
    /* 푸터 스타일 */
    .footer {
        text-align: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #f0f0f0;
        font-size: 0.8rem;
        color: #666;
    }
    
    /* 링크 박스 스타일 */
    .link-box {
        padding: 10px;
        background-color: #f1f8ff;
        border: 1px solid #cce5ff;
        border-radius: 4px;
        margin: 10px 0;
    }
    
    /* 다크모드 링크 박스 */
    @media (prefers-color-scheme: dark) {
        .link-box {
            background-color: rgba(30, 136, 229, 0.2);
            border-color: rgba(30, 136, 229, 0.4);
        }
        
        .link-box a {
            color: #90CAF9 !important;
        }
    }
    
    /* 사용 방법 안내 박스 */
    .instruction-box {
        background-color: #e8f4f8;
        border-radius: 8px;
        padding: 15px;
        margin: 15px 0;
        border-left: 4px solid #2196F3;
    }
    
    .instruction-box h4 {
        color: #0D47A1;
        margin-top: 0;
        font-weight: 600;
    }
    
    .instruction-box p, .instruction-box li {
        color: #333 !important;
        font-weight: 500;
    }
    
    /* 다크모드 사용 방법 안내 박스 */
    @media (prefers-color-scheme: dark) {
        .instruction-box {
            background-color: rgba(33, 150, 243, 0.1);
            border-left: 4px solid #2196F3;
        }
        
        .instruction-box h4 {
            color: #90CAF9;
        }
        
        .instruction-box p, .instruction-box li {
            color: #FFFFFF !important;
            font-weight: 600;
        }
    }
    
    /* 메뉴 바로가기 버튼 */
    .menu-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin: 15px 0;
    }
    
    .menu-button {
        padding: 8px 16px;
        border-radius: 20px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s;
        font-weight: bold;
        text-decoration: none;
        background-color: #f0f7ff;
        border: 1px solid #90CAF9;
        color: #1976D2;
    }
    
    .menu-button:hover {
        background-color: #90CAF9;
        color: white;
    }
    
    /* 다크모드 메뉴 버튼 */
    @media (prefers-color-scheme: dark) {
        .menu-button {
            background-color: rgba(25, 118, 210, 0.1);
            border: 1px solid #90CAF9;
            color: #90CAF9;
        }
        
        .menu-button:hover {
            background-color: rgba(25, 118, 210, 0.3);
            color: white;
        }
    }
    
    /* 알림 메시지 컨테이너 */
    .info-container {
        background-color: #ffffff;
        color: #000000 !important;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border: 1px solid #e0e0e0;
    }
    
    .info-container p, .info-container span, .info-container div {
        color: #000000 !important;
    }
    
    /* 다크모드 알림 메시지 컨테이너 */
    @media (prefers-color-scheme: dark) {
        .info-container {
            background-color: rgba(255, 255, 255, 0.1);
            border-color: rgba(200, 200, 200, 0.2);
        }
        
        .info-container p, .info-container span, .info-container div {
            color: #FFFFFF !important;
        }
    }
    
    /* Streamlit 알림창 스타일 */
    .element-container div[data-testid="stAlert"] p {
        color: #000000 !important;
        font-weight: 500 !important;
    }
    
    /* 다크모드 Streamlit 알림창 */
    @media (prefers-color-scheme: dark) {
        .element-container div[data-testid="stAlert"] {
            background-color: rgba(255, 255, 255, 0.1) !important;
        }
        .element-container div[data-testid="stAlert"] p {
            color: #000000 !important;
        }
    }
    
    /* 성공 알림 메시지 */
    .element-container div[data-baseweb="notification"] {
        background-color: #ffffff !important;
    }
    
    .element-container div[data-baseweb="notification"] div {
        color: #000000 !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def init_session_state():
    """세션 상태 초기화 (없는 경우에만)"""
    # 가장 필수적인 page 상태 먼저 초기화 (항상 존재해야 함)
    if 'page' not in st.session_state:
        st.session_state.page = 'upload'
    
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
    """세션 상태 완전 초기화"""
    # 모든 세션 상태 키 삭제
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # 반드시 page 키는 유지 (없으면 생성)
    st.session_state.page = 'upload'
    
    # 나머지는 init_session_state에서 처리
    init_session_state()
    
    logger.info("세션 상태 완전 초기화 완료")

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
    # 메인 화면 상단 설명
    st.title("교실 소셜 네트워크 분석 도구")
    st.markdown("""
    이 도구는 학급 내 학생들 간의 관계를 시각화하고 분석하여 학급 운영에 도움을 주는 도구입니다.
    설문조사나 CSV 파일로 수집된 학생 관계 데이터를 분석하여 다양한 네트워크 시각화와 지표를 제공합니다.
    """)
    
    # 사용 방법 안내 박스
    st.markdown("""
    <div class="instruction-box">
        <h4>📌 사용 방법</h4>
        <ul>
            <li><strong>노드를 드래그하여 위치 조정</strong></li>
            <li><strong>마우스 휠로 확대/축소</strong></li>
            <li><strong>노드에 마우스를 올리면 상세 정보 표시</strong></li>
            <li><strong>네트워크 여백을 드래그하면 전체 화면 이동</strong></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 메뉴 바로가기 버튼 - 분석이 완료된 경우에만 표시
    if st.session_state.get('analyzed', False):
        st.markdown("""
        <div class="menu-buttons">
            <a href="#학생-분석" class="menu-button">📊 학생 분석</a>
            <a href="#대화형-네트워크" class="menu-button">🌐 대화형 네트워크</a>
            <a href="#중심성-분석" class="menu-button">📈 중심성 분석</a>
            <a href="#그룹-분석" class="menu-button">👥 그룹 분석</a>
            <a href="#고립-학생" class="menu-button">⚠️ 고립 학생</a>
        </div>
        """, unsafe_allow_html=True)
    
    # 구글 설문지 링크 제공
    st.markdown("### 📋 샘플 설문지 사용하기")
    st.markdown("""
    아래 링크를 클릭하면 학급 관계 분석을 위한 구글 설문지 템플릿을 복사하여 사용할 수 있습니다.
    설문지를 복사한 후 질문 내용을 수정하고, 학생들에게 공유하여 데이터를 수집할 수 있습니다.
    """)
    
    st.markdown('<div class="link-box"><b>구글 설문지 템플릿:</b> <a href="https://docs.google.com/forms/d/1OOpDNUMp3GIooYb0PgvTUHpMJqfHxY7fMGNRAM_Xez8/copy" target="_blank">복사하여 사용하기 (클릭)</a></div>', unsafe_allow_html=True)
    
    # 데이터 입력 영역
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📤 CSV 파일 업로드")
        uploaded_file = st.file_uploader("학생 관계 데이터 CSV 파일을 업로드하세요", type=["csv"], key="file_uploader")
        
        if uploaded_file is not None:
            try:
                # 파일 업로드 처리
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                # 세션 상태에 저장
                st.session_state.uploaded_file = tmp_path
                st.session_state.sheet_url = ""  # URL 초기화
                st.session_state.example_selected = ""  # 예시 선택 초기화
                
                # 파일 내용 미리보기
                df = pd.read_csv(uploaded_file)
                st.success(f"파일 '{uploaded_file.name}'이 성공적으로 업로드되었습니다.")
                
                # 데이터 미리보기
                st.subheader("데이터 미리보기")
                st.dataframe(df.head())
                
                # CSV 파일용 분석 시작 버튼
                if st.button("이 데이터로 분석 시작", key="analyze_csv_button"):
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
                            
                            progress_text.text("데이터 처리 중...")
                            progress_bar.progress(50)
                            
                            # 업로드된 CSV 파일 로드
                            network_data = data_processor.process_network_data(df)
                            
                            if not network_data:
                                st.error("데이터 처리에 실패했습니다.")
                                progress_bar.empty()
                                progress_text.empty()
                                return
                            
                            # 네트워크 분석
                            progress_text.text("네트워크 분석 중...")
                            progress_bar.progress(75)
                            
                            # 네트워크 분석기 생성
                            network_analyzer = NetworkAnalyzer(network_data)
                            
                            # 중심성 지표 계산
                            if not hasattr(network_analyzer, 'metrics') or not network_analyzer.metrics:
                                network_analyzer.calculate_centrality()
                            
                            # 커뮤니티 탐지
                            if not hasattr(network_analyzer, 'communities') or not network_analyzer.communities:
                                network_analyzer.detect_communities()
                            
                            # 세션 상태에 저장
                            st.session_state.network_analyzer = network_analyzer
                            st.session_state.network_data = network_data
                            st.session_state.analyzed = True
                            
                            # 완료 표시
                            progress_text.text("분석 완료!")
                            progress_bar.progress(100)
                            time.sleep(0.5)
                            
                            # 분석 결과 페이지로 전환
                            st.session_state.page = 'analysis'
                            st.rerun()
                            
                        except Exception as e:
                            import traceback
                            logger.error(f"CSV 분석 중 오류: {str(e)}")
                            logger.error(traceback.format_exc())
                            st.error(f"데이터 분석 중 오류가 발생했습니다: {str(e)}")
            except Exception as e:
                st.error(f"파일 로드 중 오류가 발생했습니다: {str(e)}")

    with col2:
        st.markdown("### 📚 예시 데이터 사용")
        # 예시 목록 추출
        example_options = get_example_data_files()
        
        # 예시 데이터와 제목 매핑 생성 (드롭다운 표시용)
        example_titles = {ex: get_example_title(ex) for ex in example_options}
        
        # 빈 선택지 추가
        all_options = [""] + example_options
        format_func = lambda x: "선택하세요" if x == "" else f"{example_titles.get(x, x)}"
        
        # 예시 선택 드롭다운
        example_selection = st.selectbox(
            "예시 데이터를 선택하세요:", 
            options=all_options,
            index=0,
            format_func=format_func,
            key="example_selectbox"
        )
        
        # 예시 선택 시 처리
        if example_selection != st.session_state.get('example_selected', ''):
            st.session_state.example_selected = example_selection
            if example_selection:
                try:
                    # 예시 파일 경로 구성
                    example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f"{example_selection}.csv")
                    if os.path.exists(example_path):
                        st.session_state.sheet_url = example_selection
                        
                        # 예시 데이터 로드 및 미리보기
                        df = pd.read_csv(example_path)
                        
                        # 예시 데이터 설명 표시
                        st.success(f"'{format_func(example_selection)}' 예시 데이터가 선택되었습니다.")
                        st.markdown(get_example_description(example_selection))
                        
                        # 데이터 미리보기
                        st.subheader("데이터 미리보기")
                        st.dataframe(df.head())
                        
                        # 예시 데이터용 분석 시작 버튼
                        if st.button("이 데이터로 분석 시작", key="analyze_example_button"):
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
                                    
                                    progress_text.text("데이터 처리 중...")
                                    progress_bar.progress(50)
                                    
                                    # 데이터 처리
                                    network_data = data_processor.process_network_data(df)
                                    
                                    if not network_data:
                                        st.error("데이터 처리에 실패했습니다.")
                                        progress_bar.empty()
                                        progress_text.empty()
                                        return
                                    
                                    # 네트워크 분석
                                    progress_text.text("네트워크 분석 중...")
                                    progress_bar.progress(75)
                                    
                                    # 네트워크 분석기 생성
                                    network_analyzer = NetworkAnalyzer(network_data)
                                    
                                    # 중심성 지표 계산
                                    if not hasattr(network_analyzer, 'metrics') or not network_analyzer.metrics:
                                        network_analyzer.calculate_centrality()
                                    
                                    # 커뮤니티 탐지
                                    if not hasattr(network_analyzer, 'communities') or not network_analyzer.communities:
                                        network_analyzer.detect_communities()
                                    
                                    # 세션 상태에 저장
                                    st.session_state.network_analyzer = network_analyzer
                                    st.session_state.network_data = network_data
                                    st.session_state.analyzed = True
                                    
                                    # 완료 표시
                                    progress_text.text("분석 완료!")
                                    progress_bar.progress(100)
                                    time.sleep(0.5)
                                    
                                    # 분석 결과 페이지로 전환
                                    st.session_state.page = 'analysis'
                                    st.rerun()
                                    
                                except Exception as e:
                                    import traceback
                                    logger.error(f"예시 데이터 분석 중 오류: {str(e)}")
                                    logger.error(traceback.format_exc())
                                    st.error(f"데이터 분석 중 오류가 발생했습니다: {str(e)}")
                    else:
                        st.error(f"예시 데이터 파일을 찾을 수 없습니다: {example_path}")
                        st.session_state.example_selected = ""
                except Exception as e:
                    st.error(f"예시 데이터 로드 중 오류가 발생했습니다: {str(e)}")

def check_and_create_assets():
    """필요한 디렉토리와 자산 파일들을 확인하고 생성합니다"""
    try:
        # 기본 디렉토리 확인 및 생성
        dirs = ['data', 'temp', 'assets']
        for directory in dirs:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"디렉토리 생성: {directory}")
    except Exception as e:
        logger.warning(f"자산 디렉토리 확인 중 오류: {str(e)}")

def main():
    try:
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
        
        # 페이지 라우팅 - 세션 상태 속성 접근 전에 안전하게 확인
        try:
            current_page = st.session_state.get('page', 'upload')
        except Exception:
            # 세션 상태 접근 실패 시 기본값으로 설정
            current_page = 'upload'
            st.session_state.page = current_page
            
        # 페이지 라우팅
        if current_page == 'upload':
            upload_page()
        elif current_page == 'analysis':
            show_analysis_results()
        else:
            st.session_state.page = 'upload'
            st.rerun()
            
        # 푸터
        st.markdown("""
        <div style="text-align: center; margin-top: 40px; color: #888;">
            <p>© 2025 학급 관계 네트워크 분석 시스템 | 소셜 네트워크 분석 도구</p>
        </div>
        """, unsafe_allow_html=True)
    
    except Exception as e:
        # 전역 예외 처리
        st.error(f"애플리케이션 실행 중 오류가 발생했습니다: {str(e)}")
        if 'page' not in st.session_state:
            st.session_state.page = 'upload'
        
        # 로그에 오류 기록
        import traceback
        logger.error(f"애플리케이션 오류: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 초기화 버튼 제공
        if st.button("앱 초기화"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# 분석 결과 표시 함수
def show_analysis_results():
    """분석 결과 표시 페이지"""
    try:
        # 사이드바에 컨트롤 추가
        with st.sidebar:
            st.header("분석 옵션")
            
            # 레이아웃 선택
            layout_options = ["fruchterman", "force", "circular"]
            selected_layout = st.selectbox(
                "네트워크 레이아웃:", 
                options=layout_options,
                index=layout_options.index(st.session_state.get('layout_option', 'fruchterman')),
                key="layout_selector"
            )
            
            # 레이아웃 변경 시 세션 상태 업데이트
            if selected_layout != st.session_state.get('layout_option', 'fruchterman'):
                st.session_state.layout_option = selected_layout
            
            # 중심성 지표 선택
            centrality_options = ["in_degree", "out_degree", "betweenness", "closeness", "eigenvector"]
            centrality_labels = ["인기도(In-Degree)", "활동성(Out-Degree)", "매개 중심성", "근접 중심성", "고유벡터 중심성"]
            
            centrality_dict = {opt: label for opt, label in zip(centrality_options, centrality_labels)}
            
            selected_centrality = st.selectbox(
                "중심성 지표:", 
                options=centrality_options,
                format_func=lambda x: centrality_dict.get(x, x),
                index=centrality_options.index(st.session_state.get('centrality_metric', 'in_degree')),
                key="centrality_selector"
            )
            
            # 중심성 변경 시 세션 상태 업데이트
            if selected_centrality != st.session_state.get('centrality_metric', 'in_degree'):
                st.session_state.centrality_metric = selected_centrality
            
            st.markdown("---")
            
            # 내보내기 옵션
            st.header("데이터 내보내기")
            if st.button("분석 결과 CSV 내보내기", use_container_width=True):
                csv_data = report_generator.export_to_csv()
                st.download_button(
                    label="CSV 파일 다운로드",
                    data=csv_data,
                    file_name="social_network_analysis_results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # 보고서 생성 버튼
            if st.button("전체 보고서 생성", use_container_width=True):
                report_pdf = report_generator.generate_pdf_report()
                st.download_button(
                    label="PDF 보고서 다운로드",
                    data=report_pdf,
                    file_name="social_network_analysis_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            st.markdown("---")
            
            # 홈으로 돌아가기 버튼
            if st.button("새 분석 시작하기", use_container_width=True):
                # 세션 상태 초기화
                for key in list(st.session_state.keys()):
                    if key != 'page':
                        del st.session_state[key]
                st.session_state.page = 'upload'
                st.rerun()
        
        # 결과가 있는지 안전하게 확인
        network_analyzer = st.session_state.get('network_analyzer')
        if not network_analyzer:
            st.error("분석 결과가 없습니다. 먼저 데이터를 업로드하고 분석을 실행해주세요.")
            # 버튼 클릭 처리 방식 변경
            if st.button("데이터 업로드 화면으로 돌아가기", key="go_to_upload"):
                # 세션 상태 안전하게 초기화
                for key in list(st.session_state.keys()):
                    if key not in ['page', 'go_to_upload']:
                        del st.session_state[key]
                # 페이지 상태 변경
                st.session_state.page = 'upload'
                st.rerun()
            return

        # 분석기 가져오기
        analyzer = network_analyzer
        
        # 네트워크 데이터 가져오기
        network_data = st.session_state.get('network_data')
        if not network_data:
            st.error("네트워크 데이터가 없습니다.")
            return

        # 시각화 객체 생성 또는 가져오기
        if 'visualizer' not in st.session_state or not st.session_state.visualizer:
            try:
                from src.visualizer import NetworkVisualizer
                # 시각화 객체 생성
                visualizer = NetworkVisualizer(analyzer=analyzer)
                st.session_state.visualizer = visualizer
            except Exception as e:
                logger.error(f"시각화 객체 생성 중 오류: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # 오류 발생 시 기본 시각화 객체 없이 진행 시도
                visualizer = None
        else:
            visualizer = st.session_state.visualizer

        # 보고서 생성기 초기화
        if 'report_generator' not in st.session_state:
            st.session_state.report_generator = ReportGenerator(analyzer, visualizer)
        report_generator = st.session_state.report_generator

        # 상단 메뉴 탭
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 학생 분석", 
            "🌐 대화형 네트워크", 
            "📈 중심성 분석", 
            "👥 그룹 분석",
            "⚠️ 고립 학생"
        ])

        # 탭 1: 학생 분석 (기본 분석 대체)
        with tab1:
            report_generator.show_student_analysis(network_data)

        # 탭 2: 대화형 네트워크 시각화 (Plotly 사용)
        with tab2:
            report_generator.show_interactive_network()

        # 탭 3: 중심성 분석
        with tab3:
            report_generator.show_centrality_analysis(network_data)

        # 탭 4: 그룹 분석
        with tab4:
            report_generator.show_communities(network_data)

        # 탭 5: 고립 학생 분석
        with tab5:
            report_generator.show_isolated_students(network_data)

    except Exception as e:
        st.error(f"결과 표시 중 오류가 발생했습니다: {str(e)}")
        logger.error(f"결과 표시 중 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 