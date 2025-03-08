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
        if 'top_n_slider' not in st.session_state:
            st.session_state.top_n_slider = 10
        if 'layout_option' not in st.session_state:
            st.session_state.layout_option = 'fruchterman'
            
        # 이미 초기화되었음을 표시
        st.session_state.initialized = True
        logger.info("세션 상태 초기화 완료")

def reset_session():
    """세션 상태 완전 초기화"""
    # 모든 세션 상태를 제거
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # 앱 재실행
    st.rerun()

def get_example_data_files():
    """data 디렉토리에서 예시 데이터 파일 목록을 가져옵니다."""
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
    """예시 데이터에 대한 제목과 설명을 반환합니다."""
    # 예시 데이터 제목과 설명 매핑
    example_info = {
        "example1": {
            "title": "가상 학급 친구 관계 데이터",
            "description": """
            이 데이터는 중학교 3학년 가상 학급의 친구 관계를 표현한 예시입니다.
            각 학생은 '함께 공부하고 싶은 친구'와 '여가 시간을 보내고 싶은 친구'를 각각 3명씩 선택했습니다.
            인기 있는 학생, 그룹 형성, 소외된 학생 등 학급 내 관계 구조를 파악할 수 있습니다.
            """
        },
        "example2": {
            "title": "협업 선호도 데이터",
            "description": """
            이 데이터는 회사 내 프로젝트 팀원들의 협업 선호도를 조사한 결과입니다.
            각 팀원은 '함께 프로젝트를 진행하고 싶은 동료'를 5명씩 선택했습니다.
            업무 네트워크에서의 핵심 인물과 협업 패턴을 파악할 수 있습니다.
            """
        }
    }
    
    # 기본 설명 형식
    default_info = {
        "title": f"예시 데이터: {example_name}",
        "description": f"""
        이 데이터는 학급 관계 네트워크 분석을 위한 예시 데이터입니다.
        학생들 간의 선호도와 관계 패턴을 분석하는 데 활용할 수 있습니다.
        """
    }
    
    # 해당 예시 데이터의 정보 반환 (없으면 기본 정보)
    return example_info.get(example_name, default_info)

# 예시 데이터 제목 얻기 함수
def get_example_title(example_name):
    """예시 데이터의 제목만 반환합니다."""
    info = get_example_data_info(example_name)
    return info["title"]

# 예시 데이터 설명 얻기 함수
def get_example_description(example_name):
    """예시 데이터의 설명만 반환합니다."""
    info = get_example_data_info(example_name)
    return info["description"]

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
        
        # URL 입력 필드 - 고유 키 부여
        sheet_url = st.text_input("구글 시트 공유 링크:", 
                               value=st.session_state.sheet_url,
                               key="url_input")
        
        # URL 변경 시 세션 상태 업데이트
        if sheet_url != st.session_state.sheet_url:
            st.session_state.sheet_url = sheet_url
            # URL 변경 시 example_selected 초기화
            st.session_state.example_selected = ""
        
        # 구글 설문조사 양식 링크 추가
        st.markdown("### 설문조사 양식 예시")
        st.markdown("""
        아래 링크로 학생 관계 설문조사 양식을 복사하여 사용할 수 있습니다:
        
        [📋 설문조사 양식 복사하기](https://docs.google.com/forms/d/1OOpDNUMp3GIooYb0PgvTUHpMJqfHxY7fMGNRAM_Xez8/copy)
        
        이 링크를 통해 설문조사를 생성한 후, 응답 스프레드시트의 링크를 위에 입력하세요.
        """)
        
        # 예시 데이터 섹션
        st.markdown("### 예시 데이터")
        st.markdown("아래 예시 데이터 중 하나를 선택하여 테스트해볼 수 있습니다:")
        
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
        if example_selection != st.session_state.example_selected:
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
            disabled=not bool(st.session_state.sheet_url),
            use_container_width=True,
            key="analyze_button_unique"
        )
        
        # 상태 유지와 무관하게 버튼이 작동하도록 조건 수정
        if analyzer_button:
            st.session_state.button_clicked = True
        
        # 세션 초기화 버튼
        if st.button("🗑️ 모든 데이터 초기화", use_container_width=True, key="reset_button"):
            reset_session()
            # 이 시점에서 페이지가 리로드됨
            st.rerun()
    
    # 분석 버튼이 클릭되었거나 이미 분석 결과가 있을 때
    if st.session_state.button_clicked or st.session_state.analyzed:
        sheet_url = st.session_state.sheet_url
        
        # 이미 분석되지 않았거나 URL이 변경된 경우에만 분석 실행
        if not st.session_state.analyzed or st.session_state.last_analyzed_url != sheet_url:
            with st.spinner("데이터 분석 중... 잠시만 기다려주세요."):
                try:
                    # 진행 상황 표시를 위한 컴포넌트
                    progress_container = st.container()
                    progress_bar = progress_container.progress(0, "분석 준비 중...")
                    progress_text = progress_container.empty()
                    
                    # API 관리자 초기화
                    progress_text.text("API 초기화 중...")
                    progress_bar.progress(10)
                    api_manager = APIManager()
                    
                    # 데이터 처리기 초기화
                    progress_text.text("데이터 처리기 초기화 중...")
                    progress_bar.progress(20)
                    data_processor = DataProcessor(api_manager)
                    
                    # 데이터 로드 및 처리
                    if sheet_url.startswith("example"):
                        # 파일 경로 구성
                        progress_text.text("예시 데이터 로드 중...")
                        progress_bar.progress(30)
                        example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f"{sheet_url}.csv")
                        if os.path.exists(example_path):
                            # 예시 파일 로드
                            df = pd.read_csv(example_path)
                            st.success(f"예시 데이터를 성공적으로 로드했습니다: {sheet_url}")
                            
                            # 데이터 미리보기
                            progress_text.text("데이터 미리보기 생성 중...")
                            progress_bar.progress(40)
                            st.dataframe(df.head(), use_container_width=True)
                            
                            # 데이터 처리
                            progress_text.text("네트워크 데이터 생성 중...")
                            progress_bar.progress(50)
                            network_data = data_processor.process_network_data(df)
                            if network_data:
                                # 네트워크 데이터 저장
                                st.session_state.network_data = network_data
                                st.session_state.analyzed = True
                                st.session_state.last_analyzed_url = sheet_url
                                
                                # 분석 결과 계산
                                progress_text.text("네트워크 분석 중...")
                                progress_bar.progress(70)
                                
                                # 한글 폰트 설정
                                progress_text.text("시각화 준비 중...")
                                progress_bar.progress(90)
                                set_korean_font()
                                
                                # 진행 완료
                                progress_bar.progress(100)
                                progress_text.text("분석 완료!")
                                
                                # 결과 표시 컨테이너
                                results_container = st.container()
                                with results_container:
                                    # 분석 결과 표시
                                    show_analysis_results()
                            else:
                                progress_bar.empty()
                                progress_text.empty()
                                st.error("데이터 처리에 실패했습니다.")
                        else:
                            progress_bar.empty()
                            progress_text.empty()
                            st.error(f"예시 데이터 파일을 찾을 수 없습니다: {example_path}")
                    else:
                        # 구글 시트에서 데이터 로드
                        with st.status("구글 시트에서 데이터 로드 중...") as status:
                            progress_text.text("구글 시트 데이터 로드 중...")
                            progress_bar.progress(30)
                            result = data_processor.process_survey_data(sheet_url)
                            if result:
                                status.update(label="데이터 처리 완료!", state="complete")
                                progress_text.text("네트워크 분석 중...")
                                progress_bar.progress(70)
                                
                                # 네트워크 데이터 저장
                                st.session_state.network_data = result
                                st.session_state.analyzed = True
                                st.session_state.last_analyzed_url = sheet_url
                                
                                # 분석 결과 계산
                                progress_text.text("시각화 준비 중...")
                                progress_bar.progress(90)
                                set_korean_font()
                                
                                # 진행 완료
                                progress_bar.progress(100)
                                progress_text.text("분석 완료!")
                                
                                # 분석 결과 표시
                                show_analysis_results()
                            else:
                                progress_bar.empty()
                                progress_text.empty()
                                status.update(label="데이터 처리 실패", state="error")
                                st.error("구글 시트 데이터를 처리할 수 없습니다. URL을 확인해주세요.")
                except Exception as e:
                    if 'progress_bar' in locals():
                        progress_bar.empty()
                    if 'progress_text' in locals():
                        progress_text.empty()
                    handle_error(f"데이터 분석 중 오류 발생: {str(e)}")
        else:
            # 이미 분석된 결과가 있는 경우 바로 표시
            show_analysis_results()
    else:
        # 분석 전 가이드 표시
        st.info("데이터 분석을 시작하려면 왼쪽 사이드바에서 Google 시트 URL을 입력하거나 예시 데이터를 선택한 후 '분석 시작' 버튼을 클릭하세요.")
        
        # 사용 방법 안내
        st.markdown("""
        ## 사용 방법
        
        ### 🔍 데이터 준비
        
        1. 구글 설문지에서 학생들의 관계 데이터를 수집합니다
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
        
        # 커뮤니티 분석 (이미 계산되어 있을 수 있음)
        if not hasattr(analyzer, 'communities') or not analyzer.communities:
            analyzer.detect_communities()
        
        # 시각화 객체 생성
        visualizer = NetworkVisualizer(analyzer)
        
        # 한글 폰트 설정
        set_korean_font()
        
        # 보고서 생성 객체
        report_generator = ReportGenerator(analyzer, visualizer)
        
        # 이름 매핑 테이블 표시 (미리 펼쳐서 표시)
        if hasattr(st.session_state, 'name_mapping') and st.session_state.name_mapping:
            with st.expander("📋 한글-영문 이름 변환 테이블", expanded=True):
                st.info("네트워크 분석과 시각화를 위해 한글 이름은 자동으로 영문으로 변환됩니다. 아래는 변환된 이름 목록입니다.")
                
                # 테이블 생성을 위한 데이터
                name_data = []
                for korean, roman in st.session_state.name_mapping.items():
                    name_data.append({"한글 이름": korean, "영문 변환": roman})
                
                if name_data:
                    name_df = pd.DataFrame(name_data)
                    
                    # 2개 열로 나란히 표시
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(name_df, hide_index=True, use_container_width=True)
                    
                    # 다운로드 버튼 추가
                    with col2:
                        st.markdown("### 변환 테이블 다운로드")
                        st.markdown("이름 매핑 테이블을 다운로드하여 참고할 수 있습니다.")
                        
                        # CSV 파일로 변환
                        csv = name_df.to_csv(index=False)
                        st.download_button(
                            label="📥 CSV 파일로 다운로드",
                            data=csv,
                            file_name="name_mapping.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
        
        # 메인 분석 보고서 생성
        report_generator.generate_full_report(network_data)
        
        # 보고서 생성 완료 로그
        logger.info("보고서 생성 완료")
        
    except Exception as e:
        handle_error(f"분석 결과 표시 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    main() 