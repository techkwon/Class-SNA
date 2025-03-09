import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import logging
import networkx as nx
from IPython.display import HTML
import os
import tempfile
from datetime import datetime
import plotly.graph_objects as go
from src.data_processor import DataProcessor
import streamlit.components.v1 as components
import traceback  # 상단에 traceback 모듈 import 추가
from PIL import Image
# from streamlit_plotly_events import plotly_events - 모듈 없음

# streamlit_plotly_events 모듈 대체 함수
def plotly_events(fig, **kwargs):
    """streamlit_plotly_events 모듈 없이 Plotly 차트를 표시하는 대체 함수"""
    # 일반 plotly_chart로 표시하고 클릭 이벤트 처리 안함
    st.plotly_chart(fig, use_container_width=True)
    # 클릭 이벤트 데이터가 없다는 의미로 빈 리스트 반환
    return []

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportGenerator:
    """네트워크 분석 보고서 생성 클래스"""
    
    def __init__(self, analyzer, visualizer):
        self.analyzer = analyzer
        self.visualizer = visualizer
        self.metrics = analyzer.metrics
        self.communities = analyzer.communities
        self.graph = analyzer.graph
        
        # 다크모드 대응 CSS 적용
        self._apply_dark_mode_css()
    
    def _apply_dark_mode_css(self):
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
        
        /* 확장 가능한 섹션 스타일 수정 */
        .stExpander {
            color: inherit !important;
            background-color: rgba(255, 255, 255, 0.1) !important;
        }
        
        /* 기타 요소들 */
        .css-qrbaxs {
            color: inherit !important;
            background-color: rgba(255, 255, 255, 0.1) !important;
        }
        
        .stMarkdown p, .stMarkdown div, .stMarkdown code, .stMarkdown pre {
            color: inherit !important;
        }
        
        .stDataFrame {
            color: inherit !important;
        }
        
        /* 정보 메시지 배경색 조정 */
        .element-container .stAlert.st-ae.st-af.st-ag.st-ah.st-ai.st-aj.st-ak.st-al {
            background-color: rgba(28, 131, 225, 0.2) !important;
        }
        
        /* 성공 메시지 배경색 조정 */
        .element-container .stAlert.st-ae.st-af.st-ag.st-ah.st-ai.st-aj.st-am.st-al {
            background-color: rgba(45, 201, 55, 0.2) !important;
        }
        
        /* 경고 메시지 배경색 조정 */
        .element-container .stAlert.st-ae.st-af.st-ag.st-ah.st-ai.st-aj.st-an.st-al {
            background-color: rgba(255, 170, 0, 0.2) !important;
        }
        
        /* 에러 메시지 배경색 조정 */
        .element-container .stAlert.st-ae.st-af.st-ag.st-ah.st-ai.st-aj.st-ao.st-al {
            background-color: rgba(255, 70, 70, 0.2) !important;
        }
        </style>
        """
        st.markdown(dark_mode_css, unsafe_allow_html=True)
    
    def _show_network_stats(self, network_data):
        """네트워크 기본 통계 정보를 표시합니다"""
        try:
            # 기본 네트워크 통계
            st.write("**기본 네트워크 통계:**")
            
            # 노드 및 엣지 수
            col1, col2 = st.columns(2)
            with col1:
                st.metric("학생 수", len(self.graph.nodes))
            with col2:
                st.metric("관계 수", len(self.graph.edges))
            
            # 네트워크 밀도 및 평균 경로 길이
            if len(self.graph.nodes) > 1:  # 노드가 2개 이상일 때만 계산
                col1, col2 = st.columns(2)
                with col1:
                    density = nx.density(self.graph)
                    st.metric("네트워크 밀도", f"{density:.4f}")
                
                # 평균 경로 길이 (비연결 그래프면 최대 연결 컴포넌트에 대해 계산)
                with col2:
                    try:
                        if nx.is_strongly_connected(self.graph):
                            avg_path = nx.average_shortest_path_length(self.graph)
                            st.metric("평균 경로 길이", f"{avg_path:.2f}")
                        else:
                            largest_cc = max(nx.strongly_connected_components(self.graph), key=len)
                            if len(largest_cc) > 1:
                                subgraph = self.graph.subgraph(largest_cc)
                                avg_path = nx.average_shortest_path_length(subgraph)
                                st.metric("평균 경로 길이 (최대 연결 요소)", f"{avg_path:.2f}")
                            else:
                                st.metric("평균 경로 길이", "계산 불가 (연결 없음)")
                    except Exception as e:
                        st.metric("평균 경로 길이", "계산 불가")
                        logger.warning(f"평균 경로 길이 계산 중 오류: {str(e)}")
            
            # 커뮤니티(그룹) 수
            if self.communities:
                st.metric("발견된 그룹 수", len(self.communities))
        
        except Exception as e:
            logger.error(f"네트워크 통계 표시 중 오류: {str(e)}")
            st.warning("네트워크 통계 표시 중 오류가 발생했습니다.")
    
    def generate_summary_section(self):
        """요약 정보 섹션 생성"""
        try:
            # 요약 통계 계산
            total_nodes = len(self.graph.nodes())
            total_edges = len(self.graph.edges())
            
            # 요약 섹션 레이아웃
            st.markdown("## 네트워크 요약")
            st.markdown(f"이 네트워크는 **{total_nodes}명의 학생**과 **{total_edges}개의 관계**로 구성되어 있습니다.")
            
            # 기본 네트워크 메트릭 표시
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("#### 학생 수")
                st.markdown(f"<h2 style='text-align: center;'>{total_nodes}</h2>", unsafe_allow_html=True)
            
            with col2:
                st.markdown("#### 관계 수")
                st.markdown(f"<h2 style='text-align: center;'>{total_edges}</h2>", unsafe_allow_html=True)
            
            with col3:
                density = nx.density(self.graph)
                st.markdown("#### 네트워크 밀도")
                st.markdown(f"<h2 style='text-align: center;'>{density:.3f}</h2>", unsafe_allow_html=True)
            
            # 커뮤니티 정보
            st.markdown("#### 그룹 구성")
            for comm_id, members in self.communities.items():
                st.markdown(f"**그룹 {comm_id}**: {', '.join(members)}")
                
            return True
        except Exception as e:
            logger.error(f"요약 섹션 생성 오류: {str(e)}")
            st.error("요약 정보를 생성하는 중 오류가 발생했습니다.")
            return False
    
    def generate_network_summary(self):
        """네트워크 요약 정보를 생성합니다"""
        try:
            # 요약 통계 계산
            stats = self.analyzer.get_summary_statistics()
            
            # Streamlit에 표시
            st.markdown("<div class='sub-header'>네트워크 요약 정보</div>", unsafe_allow_html=True)
            
            # 두 열로 표시
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**기본 통계**")
                st.write(f"👥 **학생 수**: {stats['nodes_count']}명")
                st.write(f"🔗 **관계 연결 수**: {stats['edges_count']}개")
                st.write(f"🌐 **네트워크 밀도**: {stats['density']:.3f}")
                st.write(f"🏘️ **하위 그룹 수**: {stats['community_count']}개")
            
            with col2:
                st.write("**중심성 지표**")
                st.write(f"🥇 **연결 중심성(In) 최고 학생**: {stats['in_degree_max_node']}")
                st.write(f"📊 **연결 중심성(In) 평균**: {stats['in_degree_mean']:.3f}")
                st.write(f"🔄 **매개 중심성 최고 학생**: {stats['betweenness_max_node']}")
                st.write(f"📊 **매개 중심성 평균**: {stats['betweenness_mean']:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"요약 정보 섹션 생성 실패: {str(e)}")
            st.error(f"요약 정보 생성 중 오류가 발생했습니다: {str(e)}")
            return False
    
    def generate_visualizations(self):
        """시각화 섹션 생성"""
        try:
            st.markdown("<div class='sub-header'>네트워크 시각화</div>", unsafe_allow_html=True)
            
            # 세션 상태 초기화 (탭, 레이아웃, 중심성 지표, 상위 학생 수 유지)
            if 'active_tab' not in st.session_state:
                st.session_state.active_tab = "네트워크 그래프"
            if 'selected_layout' not in st.session_state:
                st.session_state.selected_layout = "fruchterman"
            if 'selected_metric' not in st.session_state:
                st.session_state.selected_metric = "in_degree"
            if 'top_n' not in st.session_state:
                st.session_state.top_n = 10
                
            # 탭 상태 변경 콜백 함수
            def on_tab_change(tab_name):
                st.session_state.active_tab = tab_name
                
            # 레이아웃 변경 콜백 함수
            def on_layout_change(layout):
                st.session_state.selected_layout = layout
                
            # 중심성 지표 변경 콜백 함수
            def on_metric_change(metric):
                st.session_state.selected_metric = metric
                
            # 상위 학생 수 변경 콜백 함수
            def on_top_n_change(value):
                st.session_state.top_n = value
                
            # 탭 생성
            tabs = ["네트워크 그래프", "중심성 지표", "커뮤니티 분석"]
            active_tab_index = tabs.index(st.session_state.active_tab)
            tab1, tab2, tab3 = st.tabs(tabs)
            
            with tab1:
                # 활성 탭 설정
                on_tab_change("네트워크 그래프")
                
                # 네트워크 그래프 시각화
                st.write("#### 학급 관계 네트워크 그래프")
                st.write("""
                **📊 그래프 해석 가이드:**
                - **원(노드)** : 각 학생을 나타냅니다
                - **원의 크기** : 인기도(다른 학생들에게 선택된 횟수)에 비례합니다
                - **원의 색상** : 같은 색상은 같은 그룹(커뮤니티)에 속한 학생들입니다
                - **연결선** : 학생 간의 관계를 나타냅니다
                """)
                
                # 레이아웃 선택 옵션
                layout_options = {
                    "fruchterman": "균형적 배치",
                    "spring": "자연스러운 연결",
                    "circular": "원형 배치",
                    "kamada": "최적 거리 배치"
                }
                
                selected_layout = st.selectbox(
                    "레이아웃 선택:",
                    options=list(layout_options.keys()),
                    format_func=lambda x: layout_options[x],
                    index=list(layout_options.keys()).index(st.session_state.selected_layout),
                    key="layout_selectbox",
                    on_change=on_layout_change,
                    args=(st.session_state.get("layout_selectbox"),)
                )
                
                # 선택된 레이아웃 저장
                st.session_state.selected_layout = selected_layout
                
                # Plotly 그래프 생성
                fig = self.visualizer.create_plotly_network(layout=selected_layout)
                st.plotly_chart(fig, use_container_width=True)
                
                # PyVis 네트워크 생성 (인터랙티브)
                st.write("#### 인터랙티브 네트워크")
                st.write("""
                아래 그래프는 마우스로 조작할 수 있습니다:
                - **드래그**: 학생(노드)을 끌어서 이동할 수 있습니다
                - **확대/축소**: 마우스 휠로 확대하거나 축소할 수 있습니다
                - **호버**: 마우스를 올리면 학생 정보가 표시됩니다
                """)
                
                # HTML 코드를 직접 받아옴 (파일 사용하지 않음)
                html_data = self.visualizer.create_pyvis_network()
                
                if html_data:
                    try:
                        import streamlit.components.v1 as components
                        components.html(html_data, height=500)
                    except Exception as e:
                        # 오류 메시지에서 "File name too long" 오류를 특별 처리
                        error_str = str(e)
                        if "File name too long" in error_str:
                            # 다른 방식으로 HTML 표시 시도 (iframe 사용)
                            try:
                                from IPython.display import HTML
                                # HTML을 문자열 단축 처리
                                html_short = html_data
                                if len(html_short) > 1000000:  # 1MB 이상이면 요약
                                    html_short = html_short[:500000] + "<!-- 내용 생략 -->" + html_short[-500000:]
                                # HTML base64 인코딩 후 데이터 URL로 표시
                                import base64
                                html_bytes = html_short.encode('utf-8')
                                encoded = base64.b64encode(html_bytes).decode()
                                data_url = f"data:text/html;base64,{encoded}"
                                st.markdown(f'<iframe src="{data_url}" width="100%" height="500px"></iframe>', unsafe_allow_html=True)
                                
                                # 다운로드 링크도 제공
                                html_download = html_data.encode("utf-8")
                                b64 = base64.b64encode(html_download).decode()
                                href = f'<a href="data:text/html;base64,{b64}" download="network_graph.html">📥 네트워크 그래프 다운로드</a>'
                                st.markdown(href, unsafe_allow_html=True)
                            except Exception as iframe_e:
                                st.error(f"대체 표시 방법도 실패했습니다: {str(iframe_e)}")
                                st.info("그래프를 표시할 수 없습니다. 다른 탭의 정적 그래프를 참고하세요.")
                        else:
                            st.error(f"인터랙티브 네트워크 표시 중 오류 발생: {error_str}")
                else:
                    st.warning("인터랙티브 네트워크 생성에 실패했습니다.")
            
            with tab2:
                # 활성 탭 설정
                on_tab_change("중심성 지표")
                
                # 중심성 지표 시각화
                st.write("#### 중심성 지표 분석")
                st.write("""
                **📈 중심성 지표 의미:**
                - **인기도(연결 중심성-In)**: 다른 학생들에게 선택된 횟수입니다. 높을수록 더 인기가 많습니다.
                - **친밀도(연결 중심성-Out)**: 학생이 다른 학생들을 선택한 횟수입니다. 높을수록 더 적극적으로 관계를 맺습니다.
                - **중재자 역할(매개 중심성)**: 서로 다른 그룹을 연결하는 다리 역할입니다. 높을수록 정보 전달자 역할을 합니다.
                - **정보 접근성(근접 중심성)**: 다른 모든 학생들과의 근접도입니다. 높을수록 전체 네트워크에서 정보를 빠르게 얻을 수 있습니다.
                """)
                
                # 지표 선택 옵션
                metric_options = {
                    "in_degree": "인기도 (선택받은 횟수)",
                    "out_degree": "친밀도 (선택한 횟수)",
                    "betweenness": "중재자 역할",
                    "closeness": "정보 접근성"
                }
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    selected_metric = st.selectbox(
                        "중심성 지표 선택:",
                        options=list(metric_options.keys()),
                        format_func=lambda x: metric_options[x],
                        index=list(metric_options.keys()).index(st.session_state.selected_metric),
                        key="metric_selectbox",
                        on_change=on_metric_change,
                        args=(st.session_state.get("metric_selectbox"),)
                    )
                
                # 선택된 중심성 지표 저장
                st.session_state.selected_metric = selected_metric
                
                with col2:
                    # 상위 학생 수 선택
                    top_n = st.slider(
                        "상위 학생 수:", 
                        min_value=5, 
                        max_value=20, 
                        value=st.session_state.top_n,
                        key="top_n_slider",
                        on_change=on_top_n_change,
                        args=(st.session_state.get("top_n_slider"),)
                    )
                
                # 선택된 상위 학생 수 저장
                st.session_state.top_n = top_n
                
                # 중심성 그래프 생성
                fig = self.visualizer.create_centrality_plot(metric=selected_metric, top_n=top_n)
                
                # fig 객체가 있는지 확인 후 표시
                if fig is not None:
                    st.pyplot(fig)  # fig 객체를 명시적으로 전달
                else:
                    st.warning(f"선택한 중심성 지표 ({selected_metric})에 대한 시각화를 생성할 수 없습니다. 데이터가 부족하거나 형식이 맞지 않을 수 있습니다.")
                
                # 중심성 데이터 표시 전에 metrics가 있는지 확인
                if hasattr(self, 'metrics') and self.metrics:
                    try:
                        metrics_df = pd.DataFrame()
                        for name, values in self.metrics.items():
                            # 딕셔너리 형태인지 확인하고 시리즈로 변환
                            if isinstance(values, dict):
                                metrics_df[centrality_explanation.get(name, name)] = pd.Series(values)
                        
                        if not metrics_df.empty:
                            st.write("#### 전체 중심성 지표 데이터")
                            st.dataframe(metrics_df)
                            
                            # CSV 다운로드 버튼
                            csv = metrics_df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label="CSV로 다운로드",
                                data=csv,
                                file_name=f'중심성_{selected_metric}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                                mime='text/csv',
                            )
                        else:
                            st.warning("중심성 지표 데이터가 비어있습니다.")
                    except Exception as e:
                        st.error(f"중심성 지표 데이터 표시 중 오류: {str(e)}")
                else:
                    st.warning("중심성 지표 데이터가 없습니다.")
            
            with tab3:
                # 활성 탭 설정
                on_tab_change("커뮤니티 분석")
                
                # 커뮤니티 분석
                st.write("#### 하위 그룹(커뮤니티) 분석")
                st.write("""
                **👨‍👩‍👧‍👦 하위 그룹 분석 가이드:**
                - 하위 그룹은 서로 밀접하게 연결된 학생들의 집단입니다
                - 같은 그룹에 속한 학생들은 서로 더 자주 교류하는 경향이 있습니다
                - 그룹 간 연결이 적은 경우 학급 내 분리 현상이 있을 수 있습니다
                - 특정 그룹이 지나치게 고립되어 있는지 확인해보세요
                """)
                
                # 커뮤니티 테이블 생성
                community_df = self.visualizer.create_community_table()
                st.dataframe(community_df, use_container_width=True)
                
                # 커뮤니티 시각화
                st.markdown("### 하위 그룹 시각화")
                group_viz = self.visualizer.create_plotly_network(layout="kamada")
                if group_viz is not None:
                    st.plotly_chart(group_viz, use_container_width=True)
                    
        except Exception as e:
            st.error(f"시각화 섹션 생성 중 오류가 발생했습니다: {str(e)}")
            return False
    
    def generate_export_options(self, network_data):
        """데이터 내보내기 옵션 생성"""
        try:
            st.markdown("<div class='sub-header'>결과 내보내기</div>", unsafe_allow_html=True)
            
            # 내보내기 옵션 컬럼
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**데이터 내보내기**")
                
                # 노드 데이터 (학생) 다운로드
                nodes_df = self.analyzer.get_node_attributes()
                nodes_csv = nodes_df.to_csv(index=False)
                nodes_b64 = base64.b64encode(nodes_csv.encode()).decode()
                st.markdown(f'<a href="data:file/csv;base64,{nodes_b64}" download="students_data.csv">학생 데이터 CSV 다운로드</a>', unsafe_allow_html=True)
                
                # 관계 데이터 다운로드
                edges_csv = network_data["edges"].to_csv(index=False)
                edges_b64 = base64.b64encode(edges_csv.encode()).decode()
                st.markdown(f'<a href="data:file/csv;base64,{edges_b64}" download="relationships_data.csv">관계 데이터 CSV 다운로드</a>', unsafe_allow_html=True)
                
                # 전체 Excel 내보내기
                analysis_results = {
                    "centrality": self.metrics,
                    "communities": self.visualizer.create_community_table(),
                    "summary": self.analyzer.get_summary_statistics()
                }
                
                from src.utils import export_to_excel
                excel_link = export_to_excel(network_data, analysis_results)
                st.markdown(excel_link, unsafe_allow_html=True)
            
            with col2:
                st.write("**시각화 내보내기**")
                
                # Plotly 그래프 내보내기
                fig = self.visualizer.create_plotly_network()
                
                try:
                    # kaleido 패키지 필요
                    import kaleido
                    
                    # 이미지 버퍼에 저장
                    img_bytes = BytesIO()
                    fig.write_image(img_bytes, format='png', width=1200, height=800)
                    img_bytes.seek(0)
                    
                    # 다운로드 링크 생성
                    img_b64 = base64.b64encode(img_bytes.getvalue()).decode()
                    st.markdown(f'<a href="data:image/png;base64,{img_b64}" download="network_graph.png">네트워크 그래프 PNG 다운로드</a>', unsafe_allow_html=True)
                except Exception as e:
                    st.warning(f"PNG 내보내기에 실패했습니다. kaleido 패키지가 필요합니다: {str(e)}")
                
                # 인터랙티브 네트워크 다운로드 링크
                try:
                    # HTML 코드를 직접 생성하여 다운로드 링크 제공 (파일 저장 없이)
                    html_content = self.visualizer.create_pyvis_network()
                    if html_content:
                        html_b64 = base64.b64encode(html_content.encode()).decode()
                        st.markdown(f'<a href="data:text/html;base64,{html_b64}" download="interactive_network.html">인터랙티브 네트워크 HTML 다운로드</a>', unsafe_allow_html=True)
                    else:
                        st.warning("인터랙티브 네트워크 HTML 생성에 실패했습니다.")
                except Exception as e:
                    logger.error(f"인터랙티브 HTML 생성 실패: {str(e)}")
                    st.warning("인터랙티브 네트워크 HTML 생성에 실패했습니다.")
            
            return True
            
        except Exception as e:
            logger.error(f"내보내기 옵션 생성 실패: {str(e)}")
            st.error(f"내보내기 옵션 생성 중 오류가 발생했습니다: {str(e)}")
            return False
    
    def generate_full_report(self, network_data):
        """종합 보고서 생성 및 표시"""
        try:
            # 헤더 표시
            st.markdown("<div class='main-header'>📊 분석 결과 대시보드</div>", unsafe_allow_html=True)
            
            # 요약 정보 카드 표시
            self._display_summary_cards()
            
            # 세션 상태 초기화 (없는 경우)
            if 'active_tab' not in st.session_state:
                st.session_state.active_tab = 0
            
            # 탭 생성 - 학생별 분석 탭 추가
            tab_names = ["🏠 네트워크 개요", "📈 중심성 분석", "👥 하위 그룹 분석", "💫 대화형 시각화", "⚠️ 소외 학생 분석", "👤 학생별 분석"]
            tabs = st.tabs(tab_names)
            
            # 각 탭에 내용 채우기
            with tabs[0]:  # 네트워크 개요
                self._display_overview_tab(network_data)
            
            with tabs[1]:  # 중심성 분석
                st.markdown("## 중심성 분석")
                self.show_centrality_analysis(network_data)
            
            with tabs[2]:  # 하위 그룹 분석
                st.markdown("## 하위 그룹 (커뮤니티) 분석")
                self.show_communities(network_data)
            
            with tabs[3]:  # 대화형 시각화
                st.markdown("## 대화형 관계망 시각화")
                self.show_interactive_network(network_data)
            
            with tabs[4]:  # 소외 학생 분석
                st.markdown("## 관계망 주의 학생 분석")
                self.show_isolated_students(network_data)
                
            with tabs[5]:  # 학생별 분석 (새로 추가)
                self.show_student_analysis(network_data)
            
            # 내보내기 옵션
            self.generate_export_options(network_data)
            
            # 분석 완료 표시
            logger.info("보고서 생성 완료")
            
            return True
            
        except Exception as e:
            logger.error(f"보고서 생성 중 오류: {str(e)}")
            logger.error(traceback.format_exc())
            st.error(f"보고서 생성 중 오류가 발생했습니다: {str(e)}")
            return False
            
    def _display_summary_cards(self):
        """주요 분석 지표를 카드 형태로 표시"""
        try:
            # 그래프가 있는지 확인
            if not hasattr(self, 'graph') or not self.graph:
                return
                
            # 주요 지표 계산
            num_students = self.graph.number_of_nodes()
            num_relationships = self.graph.number_of_edges()
            density = nx.density(self.graph)
            num_communities = len(self.communities) if self.communities else 0
            
            # 가장 활발한 학생과 가장 중요한 중재자 찾기
            top_student = "없음"
            top_mediator = "없음"
            
            if 'in_degree' in self.metrics and self.metrics['in_degree']:
                top_student_id = max(self.metrics['in_degree'], key=self.metrics['in_degree'].get)
                # 한글 이름으로 변환
                if 'romanized_names' in st.session_state and top_student_id in st.session_state.romanized_names:
                    top_student = st.session_state.romanized_names[top_student_id]
                else:
                    top_student = str(top_student_id)
            
            if 'betweenness' in self.metrics and self.metrics['betweenness']:
                top_mediator_id = max(self.metrics['betweenness'], key=self.metrics['betweenness'].get)
                # 한글 이름으로 변환
                if 'romanized_names' in st.session_state and top_mediator_id in st.session_state.romanized_names:
                    top_mediator = st.session_state.romanized_names[top_mediator_id]
                else:
                    top_mediator = str(top_mediator_id)
            
            # 고립 학생 수 계산
            isolated_count = 0
            if hasattr(self.analyzer, 'identify_isolated_nodes'):
                isolated_students = self.analyzer.identify_isolated_nodes(threshold=0.1)
                isolated_count = len(isolated_students)
            
            # 카드 스타일 CSS
            st.markdown("""
            <style>
            .metric-card {
                background-color: #f0f2f6;
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #4b7bec;
            }
            .metric-label {
                margin-top: 5px;
                font-size: 14px;
                color: #576574;
            }
            .metric-important {
                color: #ff6b6b;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # 4개 열로 된 카드 레이아웃
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{num_students}</div>
                    <div class="metric-label">학생 수</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{top_student}</div>
                    <div class="metric-label">가장 인기 많은 학생</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{num_relationships}</div>
                    <div class="metric-label">관계 수</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{top_mediator}</div>
                    <div class="metric-label">핵심 매개자</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{num_communities}</div>
                    <div class="metric-label">그룹 수</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{density:.3f}</div>
                    <div class="metric-label">네트워크 밀도</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value {'metric-important' if isolated_count > 0 else ''}">{isolated_count}</div>
                    <div class="metric-label">관심이 필요한 학생 수</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 현재 날짜 기준 보고서 정보
                from datetime import datetime
                today = datetime.now().strftime("%Y-%m-%d")
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">보고서 생성일</div>
                    <div class="metric-value" style="font-size: 16px;">{today}</div>
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            logger.error(f"요약 카드 표시 중 오류: {str(e)}")
            # 오류가 발생해도 보고서 생성 계속 진행
            
    def _display_overview_tab(self, network_data):
        """네트워크 개요 탭 내용 표시"""
        try:
            st.markdown("## 네트워크 분석 개요")
            
            # 네트워크 기본 통계
            self._show_network_stats(network_data)
            
            # 요약 보고서
            st.markdown("### 네트워크 요약")
            summary = self.analyzer.generate_summary()
            st.markdown(summary)
            
            # 설명 추가
            with st.expander("🔍 네트워크 분석 해석 방법", expanded=False):
                st.markdown("""
                ### 네트워크 분석 이해하기
                
                #### 네트워크 밀도
                밀도는 가능한 모든 관계 중 실제로 존재하는 관계의 비율입니다. 높을수록 학생들 간의 연결이 많다는 의미입니다.
                
                #### 평균 경로 길이
                평균적으로 한 학생에서 다른 학생까지 도달하는데 필요한 단계 수입니다. 낮을수록 정보가 빠르게 퍼질 수 있는 구조입니다.
                
                #### 그룹(커뮤니티)
                서로 밀접하게 연결된 학생들의 하위 그룹입니다. 교우 관계의 자연스러운 패턴을 보여줍니다.
                """)
            
            # 요약 시각화
            st.markdown("### 전체 네트워크 시각화")
            summary_viz = self.visualizer.create_plotly_network()
            if summary_viz is not None:
                st.plotly_chart(summary_viz, use_container_width=True)
            else:
                st.warning("네트워크 시각화 생성에 실패했습니다.")
                
        except Exception as e:
            logger.error(f"개요 탭 표시 중 오류: {str(e)}")
            st.error("네트워크 개요 표시 중 오류가 발생했습니다.")
            
    def show_student_analysis(self, network_data):
        """학생별 관계망 및 중심성 분석"""
        try:
            st.markdown("## 👤 학생별 관계망 분석")
            st.markdown("""
            이 분석은 개별 학생의 관계 형태와 특성을 보여줍니다. 각 학생이 학급 내에서 어떤 위치에 있는지, 
            누구와 관계를 맺고 있는지 파악할 수 있습니다.
            """)
            
            # 선택 가능한 학생 목록 (실제 이름 표시)
            student_ids = list(self.graph.nodes())
            
            if not student_ids:
                st.warning("분석할 학생 데이터가 없습니다.")
                return
            
            # 학생 ID를 실제 이름으로 표시하기 위한 변환
            romanized_to_korean = {}
            
            # 원본 이름 매핑 확인
            if hasattr(self.analyzer, 'name_mapping') and self.analyzer.name_mapping:
                # 애널라이저의 name_mapping 사용 (ID -> 이름)
                for node_id in student_ids:
                    if node_id in self.analyzer.name_mapping:
                        romanized_to_korean[node_id] = self.analyzer.name_mapping[node_id]
                    else:
                        romanized_to_korean[node_id] = str(node_id)
            # 역 로마자화 매핑 확인
            elif hasattr(self.analyzer, 'reverse_romanized') and self.analyzer.reverse_romanized:
                # 애널라이저의 reverse_romanized 사용 (로마자 -> 한글)
                for node_id in student_ids:
                    if node_id in self.analyzer.reverse_romanized:
                        romanized_to_korean[node_id] = self.analyzer.reverse_romanized[node_id]
                    else:
                        romanized_to_korean[node_id] = str(node_id)
            # id_to_name 매핑 확인
            elif hasattr(self.analyzer, 'id_to_name') and self.analyzer.id_to_name:
                # 애널라이저의 id_to_name 사용
                for node_id in student_ids:
                    if node_id in self.analyzer.id_to_name:
                        romanized_to_korean[node_id] = self.analyzer.id_to_name[node_id]
                    else:
                        romanized_to_korean[node_id] = str(node_id)
            else:
                # 기본 변환 (ID를 문자열로)
                for node_id in student_ids:
                    romanized_to_korean[node_id] = str(node_id)
            
            # 학생 선택 드롭다운 메뉴
            selected_student = st.selectbox(
                "분석할 학생 선택:",
                options=student_ids,
                format_func=lambda x: romanized_to_korean.get(x, str(x))
            )
            
            # 선택된 학생 ID
            selected_student_id = selected_student
            selected_student_name = romanized_to_korean.get(selected_student_id, str(selected_student_id))
            
            # 선택된 학생의 중심성 지표
            in_degree = 0
            out_degree = 0
            betweenness = 0
            eigenvector = 0
            closeness = 0
            
            if 'in_degree' in self.metrics and selected_student_id in self.metrics['in_degree']:
                in_degree = self.metrics['in_degree'][selected_student_id]
            if 'out_degree' in self.metrics and selected_student_id in self.metrics['out_degree']:
                out_degree = self.metrics['out_degree'][selected_student_id]
            if 'betweenness' in self.metrics and selected_student_id in self.metrics['betweenness']:
                betweenness = self.metrics['betweenness'][selected_student_id]
            if 'eigenvector' in self.metrics and selected_student_id in self.metrics['eigenvector']:
                eigenvector = self.metrics['eigenvector'][selected_student_id]
            if 'closeness' in self.metrics and selected_student_id in self.metrics['closeness']:
                closeness = self.metrics['closeness'][selected_student_id]
            
            # 학생 분석 정보 표시
            st.markdown(f"### 📊 {selected_student_name}님의 관계망 분석", unsafe_allow_html=True)
            
            # 학생 정보를 두 컬럼으로 나누어 표시
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### 👑 학생 중심성 지표")
                
                # 입력 및 출력 차수
                in_degree_actual = self.graph.in_degree(selected_student_id)
                out_degree_actual = self.graph.out_degree(selected_student_id)
                
                # 커뮤니티 찾기
                community_id = "없음"
                if self.communities is not None:
                    for comm_id, members in self.communities.items():
                        if selected_student_id in members:
                            community_id = comm_id
                            break
                
                # 데이터 테이블
                metrics_data = {
                    "지표": ["받은 선택 수", "한 선택 수", "매개 중심성", "근접 중심성", "영향력", "소속 그룹"],
                    "값": [
                        f"{in_degree_actual}",
                        f"{out_degree_actual}",
                        f"{betweenness:.3f}" if isinstance(betweenness, (int, float)) else str(betweenness),
                        f"{closeness:.3f}" if isinstance(closeness, (int, float)) else str(closeness),
                        f"{eigenvector:.3f}" if isinstance(eigenvector, (int, float)) else str(eigenvector),
                        f"{community_id}"
                    ]
                }
                
                metrics_df = pd.DataFrame(metrics_data)
                st.table(metrics_df)
                
                # 학생 위치 해석
                st.markdown("#### 🧠 학생 역할 분석")
                
                # 역할 결정
                role = self._determine_student_role(in_degree, betweenness, in_degree_actual, out_degree_actual)
                
                st.markdown(f"**역할:** {role['title']}")
                st.markdown(f"{role['description']}")
                
                # 중심성 지표 설명 추가
                with st.expander("📌 중심성 지표 설명"):
                    st.markdown("""
                    - **받은 선택 수**: 다른 학생들로부터 받은 선택의 수입니다. 높을수록 인기가 많은 학생입니다.
                    - **한 선택 수**: 학생이 다른 학생들을 선택한 수입니다. 높을수록 활동적인 학생입니다.
                    - **매개 중심성**: 학생이 다른 학생들 사이의 관계를 연결하는 정도입니다. 높을수록 중재자 역할을 합니다.
                    - **근접 중심성**: 학생이 다른 모든 학생들과 얼마나 가까운지를 나타냅니다. 높을수록 정보를 빠르게 얻고 전달합니다.
                    - **영향력**: 학생의 영향력을 나타냅니다. 높을수록 영향력이 큰 학생들과 연결되어 있습니다.
                    - **소속 그룹**: 학생이 속한 그룹(커뮤니티) 번호입니다.
                    """)
            
            with col2:
                # 관계 네트워크 시각화
                st.markdown("#### 🌐 학생 관계 네트워크")
                
                # 1촌 네트워크 추출 (직접 연결된 학생들)
                successors = list(self.graph.successors(selected_student_id))  # 학생이 선택한 학생들
                predecessors = list(self.graph.predecessors(selected_student_id))  # 학생을 선택한 학생들
                neighbors = list(set(successors + predecessors))  # 중복 제거
                
                # 선택된 학생을 포함한 서브그래프 생성
                subgraph_nodes = neighbors + [selected_student_id]
                subgraph = self.graph.subgraph(subgraph_nodes)
                
                # 네트워크 시각화 생성
                try:
                    # PyVis 네트워크 시각화
                    from pyvis.network import Network
                    import random
                    
                    # 네트워크 생성
                    net = Network(height="400px", width="100%", directed=True, notebook=False)
                    
                    # 노드 추가
                    for node in subgraph_nodes:
                        # 선택된 학생은 크게 표시
                        size = 25 if node == selected_student_id else 15
                        
                        # 노드 색상
                        if node == selected_student_id:
                            color = "#E53935"  # 선택된 학생
                        elif node in successors and node in predecessors:
                            color = "#43A047"  # 상호 선택
                        elif node in successors:
                            color = "#1E88E5"  # 학생이 선택한 학생
                        elif node in predecessors:
                            color = "#FB8C00"  # 학생을 선택한 학생
                        else:
                            color = "#9E9E9E"  # 기타 
                        
                        # 노드 추가 (실제 이름으로 표시)
                        label = romanized_to_korean.get(node, str(node))
                        net.add_node(node, label=label, size=size, color=color, title=f"학생: {label}")
                    
                    # 엣지 추가
                    for u, v in subgraph.edges():
                        # 엣지 색상 및 두께
                        if u == selected_student_id:
                            color = "#1E88E5"  # 학생이 선택한 관계
                            title = f"{romanized_to_korean.get(u, u)}님이 {romanized_to_korean.get(v, v)}님을 선택함"
                        elif v == selected_student_id:
                            color = "#FB8C00"  # 학생을 선택한 관계
                            title = f"{romanized_to_korean.get(u, u)}님이 {romanized_to_korean.get(v, v)}님을 선택함"
                        else:
                            color = "#9E9E9E"  # 기타 관계
                            title = f"{romanized_to_korean.get(u, u)}님이 {romanized_to_korean.get(v, v)}님을 선택함"
                        
                        net.add_edge(u, v, color=color, title=title)
                    
                    # 물리 엔진 설정
                    net.barnes_hut(spring_length=200)
                    
                    # HTML 생성 및 표시
                    html = net.generate_html()
                    components.html(html, height=410)
                    
                except Exception as e:
                    # 오류 시 기본 네트워크 표시
                    st.warning(f"네트워크 시각화 생성 중 오류: {str(e)}")
                    
                    # Plotly로 기본 네트워크 표시
                    if hasattr(self.visualizer, 'create_plotly_network'):
                        fig = self.visualizer.create_plotly_network(focus_node=selected_student_id, neighbor_depth=1)
                        st.plotly_chart(fig, use_container_width=True)
                
                # 분석 내용 추가
                st.markdown("#### 📊 관계 분석")
                incoming = len(predecessors)
                outgoing = len(successors)
                mutual = len(set(predecessors).intersection(set(successors)))
                
                st.markdown(f"**총 관계 수:** {len(neighbors)}명의 학생과 연결")
                st.markdown(f"**받은 선택:** {incoming}명의 학생이 {selected_student_name}님을 선택")
                st.markdown(f"**한 선택:** {selected_student_name}님이 {outgoing}명의 학생을 선택")
                st.markdown(f"**상호 선택:** {mutual}명의 학생과 상호 선택 관계")
                
                # 관계 목록 추가
                with st.expander("🔍 상세 관계 목록 보기"):
                    # 학생을 선택한 학생 목록
                    if predecessors:
                        st.markdown("**나를 선택한 학생:**")
                        for student in predecessors:
                            st.markdown(f"- {romanized_to_korean.get(student, str(student))}")
                    else:
                        st.markdown("**나를 선택한 학생: 없음**")
                    
                    # 학생이 선택한 학생 목록
                    if successors:
                        st.markdown("**내가 선택한 학생:**")
                        for student in successors:
                            st.markdown(f"- {romanized_to_korean.get(student, str(student))}")
                    else:
                        st.markdown("**내가 선택한 학생: 없음**")
            
            # 권장 전략/개입 제안
            st.markdown("### 교사 권장 사항")
            
            # 권장 사항 결정 (학생 역할 및 지표 기반)
            recommendations = self._generate_recommendations(
                role['type'], 
                in_degree_actual, 
                out_degree_actual,
                len(neighbors)
            )
            
            for i, rec in enumerate(recommendations):
                st.markdown(f"**{i+1}. {rec['title']}**")
                st.markdown(f"{rec['description']}")
            
        except Exception as e:
            logger.error(f"학생별 분석 표시 중 오류: {str(e)}")
            logger.error(traceback.format_exc())
            st.error("학생별 분석 결과를 표시하는 중 오류가 발생했습니다.")
    
    def _determine_student_role(self, in_degree, betweenness, in_count, out_count):
        """학생의 역할 결정"""
        # 각 지표값을 0-1 사이로 정규화 (단순 연산 목적)
        # 실제로는 그래프 전체 통계를 고려해야 함
        try:
            # 최대값 찾기
            max_in_degree = max(self.metrics.get('in_degree', {}).values() or [0.001])
            max_betweenness = max(self.metrics.get('betweenness', {}).values() or [0.001])
            
            # 0으로 나누기 방지
            if max_in_degree == 0:
                max_in_degree = 0.001
            if max_betweenness == 0:
                max_betweenness = 0.001
            
            # 정규화
            in_degree_norm = min(in_degree / max_in_degree, 1.0)
            betweenness_norm = min(betweenness / max_betweenness, 1.0)
            
            # 역할 결정
            role_type = ""
            if in_degree_norm > 0.7 and betweenness_norm > 0.7:
                role_type = "leader"
                return {
                    "type": role_type,
                    "title": "리더",
                    "description": "학급 내에서 높은 인기도와 매개 중심성을 지니고 있어 여러 그룹 간의 연결점 역할을 합니다. 많은 학생들에게 선택을 받으며, 학급의 다양한 구성원들과 연결되어 있습니다."
                }
            elif in_degree_norm > 0.7 and betweenness_norm <= 0.7:
                role_type = "popular"
                return {
                    "type": role_type,
                    "title": "인기 있는 학생",
                    "description": "많은 학생들에게 선택을 받지만, 특정 그룹 내에서 주로 활동합니다. 자신의 그룹에서 중심적인 역할을 하지만, 다른 그룹과의 연결은 상대적으로 적습니다."
                }
            elif in_degree_norm <= 0.7 and betweenness_norm > 0.7:
                role_type = "bridge"
                return {
                    "type": role_type,
                    "title": "연결자",
                    "description": "특별히 많은 선택을 받지는 않지만, 서로 다른 그룹 간의 중요한 연결 역할을 합니다. 다양한 그룹과 연결되어 있어 정보와 영향력이 학급 전체에 흐르는 데 중요한 역할을 합니다."
                }
            elif in_degree_norm > 0.3 and betweenness_norm > 0.3:
                role_type = "connector"
                return {
                    "type": role_type,
                    "title": "친화형 학생",
                    "description": "적정 수준의 인기도와 중개 역할을 가지고 있습니다. 특정 그룹 내에서 안정적인 관계를 형성하고 있으며, 때로는 다른 그룹과도 교류합니다."
                }
            elif in_degree_norm <= 0.3 and out_count >= 2:
                role_type = "peripheral"
                return {
                    "type": role_type,
                    "title": "주변부 학생",
                    "description": "다른 학생들에게 많이 선택되지는 않지만, 스스로는 적극적으로 다른 학생들을 선택합니다. 관계망에 참여하고자 하는 의지는 있으나, 아직 충분한 상호작용이 이루어지지 않고 있습니다."
                }
            elif in_count == 0 and out_count == 0:
                role_type = "isolated"
                return {
                    "type": role_type,
                    "title": "고립된 학생",
                    "description": "현재 관계망에서 다른 학생들과의 연결이 없습니다. 적극적인 교사의 개입과 지원이 필요할 수 있습니다."
                }
            else:
                role_type = "regular"
                return {
                    "type": role_type,
                    "title": "일반 학생",
                    "description": "학급 내에서 평균적인 관계를 유지하고 있습니다. 특별히 두드러진 특성은 없으나, 자신의 소규모 관계망 내에서 안정적으로 활동하고 있습니다."
                }
                
        except Exception as e:
            logger.error(f"학생 역할 결정 중 오류: {str(e)}")
            return {
                "type": "unknown",
                "title": "분석 불가",
                "description": "데이터 부족으로 인해 역할을 정확히 분석할 수 없습니다."
            }
    
    def _generate_recommendations(self, role_type, in_count, out_count, neighbor_count):
        """학생 역할에 따른 교사 권장사항 생성"""
        recommendations = []
        
        if role_type == "leader":
            recommendations.append({
                "title": "리더십 역할 부여",
                "description": "이 학생에게 학급 활동에서 리더십 역할을 부여하세요. 다른 학생들을 돕고 포용하는 책임감을 기르도록 격려합니다."
            })
            recommendations.append({
                "title": "영향력 긍정적 활용 유도",
                "description": "이 학생의 영향력을 학급 분위기 개선과 소외된 학생 포용에 활용할 수 있도록 개인적으로 대화하고 격려하세요."
            })
            
        elif role_type == "popular":
            recommendations.append({
                "title": "사회적 책임감 함양",
                "description": "인기가 많은 위치에서 다른 학생들을 배려하고 포용하는 태도를 가질 수 있도록 지도하세요."
            })
            recommendations.append({
                "title": "다양한 학생과의 협업 기회 제공",
                "description": "다양한 학생들과 함께 일할 수 있는 프로젝트를 구성하여 더 넓은 교우관계를 형성하도록 돕습니다."
            })
            
        elif role_type == "bridge":
            recommendations.append({
                "title": "연결자 역할 강화",
                "description": "이 학생의 '다리' 역할을 강화하는 활동을 제공하세요. 서로 다른 그룹의 학생들이 함께하는 활동에서 중재자 역할을 부여해보세요."
            })
            recommendations.append({
                "title": "소통 능력 개발 지원",
                "description": "다양한 성격과 배경을 가진 학생들 사이에서 효과적으로 소통하는 능력을 개발할 수 있도록 지원하세요."
            })
            
        elif role_type == "balanced":
            recommendations.append({
                "title": "균형 잡힌 관계 유지 격려",
                "description": "현재의 균형 잡힌 교우관계를 유지하면서, 필요에 따라 다른 학생들과도 관계를 확장할 수 있도록 격려하세요."
            })
            recommendations.append({
                "title": "팀워크 활동 참여 권장",
                "description": "다양한 팀 활동에 참여하도록 권장하여 사회적 기술과 협력 능력을 더욱 발전시키세요."
            })
            
        elif role_type == "seeking":
            recommendations.append({
                "title": "상호적 관계 형성 지원",
                "description": "이 학생이 선택한 친구들과 더 깊고 상호적인 관계를 형성할 수 있도록 소그룹 활동을 구성하세요."
            })
            recommendations.append({
                "title": "사회적 기술 개발 지원",
                "description": "친구 관계에서 필요한 경청, 공감, 대화 등의 사회적 기술을 발전시킬 수 있는 활동이나 지도를 제공하세요."
            })
            
        elif role_type == "isolated":
            recommendations.append({
                "title": "점진적 사회적 통합",
                "description": "이 학생을 위한 점진적인 사회적 통합 계획을 세우세요. 먼저 소규모 그룹에서 시작하여 성공 경험을 쌓도록 합니다."
            })
            recommendations.append({
                "title": "강점 기반 참여 기회 제공",
                "description": "이 학생의 강점이나 관심사를 파악하여, 그것을 바탕으로 다른 학생들과 자연스럽게 교류할 수 있는 기회를 만들어주세요."
            })
            recommendations.append({
                "title": "정서적 지원 및 상담",
                "description": "정기적인 대화와 상담을 통해 이 학생의 정서적 필요를 지원하고, 필요한 경우 전문적인 도움을 연결해주세요."
            })
            
        elif role_type == "average":
            recommendations.append({
                "title": "관심사 기반 활동 참여 권장",
                "description": "이 학생의 관심사와 강점을 파악하여 관련된 활동에 참여하도록 권장하세요. 이를 통해 비슷한 관심사를 가진 학생들과 더 깊은 관계를 형성할 수 있습니다."
            })
            recommendations.append({
                "title": "리더십 기회 제공",
                "description": "작은 그룹 활동에서 리더십 역할을 경험할 수 있는 기회를 제공하여 자신감과 사회적 위치를 강화하도록 돕습니다."
            })
            
        else:  # unknown
            recommendations.append({
                "title": "개별 관찰 및 평가",
                "description": "이 학생의 교우관계와 사회적 상호작용을 면밀히 관찰하여 더 정확한 평가를 진행하세요."
            })
            recommendations.append({
                "title": "개인 면담 진행",
                "description": "학교에서의 관계와 경험에 대해 개인 면담을 통해 직접 대화하여 필요한 지원을 파악하세요."
            })
            
        # 공통 권장사항 (필요한 경우)
        if neighbor_count < 2:
            recommendations.append({
                "title": "사회적 연결 촉진",
                "description": "이 학생이 더 다양한 교우관계를 형성할 수 있도록 협력 활동과 그룹 프로젝트에 전략적으로 배치하세요."
            })
            
        return recommendations
    
    def show_communities(self, network_data):
        """커뮤니티(하위 그룹) 분석 표시"""
        try:
            st.markdown("## 👥 학급 내 하위 그룹 분석")
            
            # 설명 추가
            st.markdown("""
            이 분석은 학급 내에서 자연스럽게 형성된 하위 그룹(커뮤니티)을 보여줍니다.
            같은 색상의 학생들은 서로 더 긴밀하게 연결된 하나의 그룹을 형성하고 있습니다.
            이러한 그룹 파악은 학급 활동 구성, 모둠 편성, 또는 학생 관계 개선에 활용할 수 있습니다.
            """)
            
            # 커뮤니티 테이블 생성
            community_table = self.visualizer.create_community_table()
            st.dataframe(community_table, use_container_width=True)
            
            # 커뮤니티 시각화
            st.markdown("### 하위 그룹 시각화")
            group_viz = self.visualizer.create_plotly_network(layout="kamada")
            if group_viz is not None:
                st.plotly_chart(group_viz, use_container_width=True)
                
        except Exception as e:
            logger.error(f"커뮤니티 분석 표시 중 오류: {str(e)}")
            st.error("커뮤니티 분석 결과를 표시하는 중 오류가 발생했습니다.")
    
    def show_centrality_analysis(self, network_data):
        """중심성 분석 결과 표시"""
        try:
            st.markdown("## 📊 중심성 지표 분석")
            
            # 설명 추가
            st.markdown("""
            이 분석은 각 학생이 네트워크에서 얼마나 중요한 위치를 차지하는지 보여줍니다.
            중심성 지표는 학생들의 영향력, 인기도, 매개 역할 등 다양한 관점에서의 중요도를 측정합니다.
            다양한 지표를 통해 학급 내 주요 학생들의 역할을 파악할 수 있습니다.
            """)
            
            # 중심성 선택 및 설명
            st.markdown("### 중심성 지표 선택")
            
            # 중심성 유형 설명
            centrality_explanation = {
                "in_degree": "**인기도 (In-Degree)**: 다른 학생들로부터 받은 선택의 수입니다. 높을수록 많은 학생들에게 선택받은 인기 있는 학생입니다.",
                "out_degree": "**활동성 (Out-Degree)**: 다른 학생들을 선택한 수입니다. 높을수록 적극적으로 관계를 형성하는 활동적인 학생입니다.",
                "betweenness": "**매개 중심성 (Betweenness)**: 서로 다른 학생들 사이의 관계를 연결하는 중재자 역할을 얼마나 하는지 측정합니다. 높을수록 다양한 그룹 간 소통을 돕는 '다리' 역할을 합니다.",
                "closeness": "**근접 중심성 (Closeness)**: 한 학생이 다른 모든 학생들과 얼마나 가까운지 측정합니다. 높을수록 정보를 빠르게 얻고 전달할 수 있는 위치에 있습니다.",
                "eigenvector": "**영향력 중심성 (Eigenvector)**: 학생의 영향력을 측정합니다. 높을수록 중요한(영향력 있는) 학생들과 연결되어 있어 간접적 영향력이 큰 학생입니다."
            }
            
            # 중심성 지표 선택 옵션
            metric_options = list(centrality_explanation.keys())
            selected_metric = st.selectbox("중심성 지표 선택:", options=metric_options)
            
            # 상위 학생 수 선택
            top_n = st.slider("상위 학생 수:", min_value=5, max_value=20, value=10)
            
            # 중심성 그래프 생성
            fig = self.visualizer.create_centrality_plot(metric=selected_metric, top_n=top_n)
            
            # fig 객체가 있는지 확인 후 표시
            if fig is not None:
                st.pyplot(fig)  # fig 객체를 명시적으로 전달
            else:
                st.warning(f"선택한 중심성 지표 ({selected_metric})에 대한 시각화를 생성할 수 없습니다. 데이터가 부족하거나 형식이 맞지 않을 수 있습니다.")
            
            # 중심성 데이터 표시 전에 metrics가 있는지 확인
            if hasattr(self, 'metrics') and self.metrics:
                try:
                    metrics_df = pd.DataFrame()
                    for name, values in self.metrics.items():
                        # 딕셔너리 형태인지 확인하고 시리즈로 변환
                        if isinstance(values, dict):
                            metrics_df[centrality_explanation.get(name, name)] = pd.Series(values)
                    
                    if not metrics_df.empty:
                        st.write("#### 전체 중심성 지표 데이터")
                        st.dataframe(metrics_df)
                        
                        # CSV 다운로드 버튼
                        csv = metrics_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="CSV로 다운로드",
                            data=csv,
                            file_name=f'중심성_{selected_metric}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                            mime='text/csv',
                        )
                    else:
                        st.warning("중심성 지표 데이터가 비어있습니다.")
                except Exception as e:
                    st.error(f"중심성 지표 데이터 표시 중 오류: {str(e)}")
            else:
                st.warning("중심성 지표 데이터가 없습니다.")
            
        except Exception as e:
            st.error(f"중심성 분석 섹션 생성 중 오류: {str(e)}")
            logger.error(f"중심성 분석 섹션 생성 중 오류: {str(e)}")
    
    def show_isolated_students(self, network_data):
        """고립(소외) 학생 분석 표시"""
        try:
            st.markdown("## ⚠️ 관계망 주의 학생 분석")
            
            # 설명 추가
            st.markdown("""
            이 분석은 학급 내에서 상대적으로 적은 선택을 받거나 관계가 적은 학생들을 식별합니다.
            이러한 학생들에게 특별한 관심을 기울이면 학급 내 모든 학생들이 건강한 관계를 형성하도록 도울 수 있습니다.
            그러나 모든 학생의 성향이 다르므로, 이 결과만으로 학생의 사회성을 판단하지 않도록 주의해야 합니다.
            """)
            
            # 고립 학생 검출
            isolated = []
            peripheral = []
            for node in self.graph.nodes():
                in_degree = self.graph.in_degree(node)
                out_degree = self.graph.out_degree(node)
                
                # 완전 고립(in+out = 0) 또는 외곽(in = 0)
                if in_degree + out_degree == 0:
                    isolated.append(node)
                elif in_degree == 0:
                    peripheral.append(node)
            
            if isolated or peripheral:
                # 고립 학생이 있는 경우
                st.markdown("""
                아래 학생들이 관계망에서 고립되어 있거나 외곽에 위치하고 있습니다. 
                이들에게 특별한 관심이 필요할 수 있습니다.
                """)
                
                # 데이터 준비
                isolation_data = []
                
                # 완전 고립 학생
                for student in isolated:
                    # 학생 실명 표시 개선
                    student_name = self._get_student_real_name(student)
                    isolation_data.append({
                        "학생명": student_name,
                        "상태": "완전 고립",
                        "받은 선택": 0,
                        "한 선택": 0,
                        "설명": "어떤 관계도 형성되지 않음"
                    })
                
                # 외곽 학생 (선택받지 못함)
                for student in peripheral:
                    # 학생 실명 표시 개선
                    student_name = self._get_student_real_name(student)
                    # 나가는 엣지 수
                    out_count = self.graph.out_degree(student)
                    
                    isolation_data.append({
                        "학생명": student_name,
                        "상태": "외곽",
                        "받은 선택": 0, 
                        "한 선택": out_count,
                        "설명": "다른 학생을 선택했으나 선택받지 못함"
                    })
                
                # 데이터프레임 변환 및 표시
                df_isolation = pd.DataFrame(isolation_data)
                st.dataframe(df_isolation, use_container_width=True)
                
                # 권장 개입 전략
                st.markdown("### 교사 개입 권장 사항")
                st.markdown("""
                고립 학생에 대한 교사의 적절한 개입이 필요합니다. 아래 전략을 고려해보세요:
                
                1. **점진적 통합 접근**: 고립 학생을 소그룹 활동에 단계적으로 통합
                2. **장점 기반 역할 부여**: 학생의 강점을 활용할 수 있는 특별 역할 부여
                3. **또래 멘토링 시스템**: 사회성이 좋은 학생과 짝 활동 기회 제공
                4. **관심사 기반 연결**: 공통 관심사를 가진 학생들과 연결 기회 마련
                5. **일대일 상담**: 고립 원인 파악을 위한 정기적 상담 및 지원
                """)
                
            else:
                # 고립 학생이 없는 경우
                st.success("분석 결과, 완전히 고립되거나 외곽에 위치한 학생이 없습니다!")
                st.markdown("""
                모든 학생들이 최소한 한 명 이상의 다른 학생과 관계를 맺고 있습니다.
                이는 학급 전체의 관계망이 건강하게 형성되어 있음을 의미합니다.
                """)
            
        except Exception as e:
            import traceback  # 명시적 임포트 추가
            logger.error(f"고립 학생 분석 표시 중 오류: {str(e)}")
            logger.error(traceback.format_exc())
            st.error("고립 학생 분석 결과를 표시하는 중 오류가 발생했습니다.")
    
    def show_interactive_network(self, network_data=None):
        """대화형 네트워크 시각화 표시"""
        try:
            st.markdown("## 🌐 대화형 관계망 시각화")
            
            # 설명 추가
            st.markdown("""
            이 시각화는 학급 전체의 관계망을 보여줍니다. 네트워크에서:
            
            * **노드(원)**: 각 학생을 나타냅니다. 크기가 클수록 많은 선택을 받은 학생입니다.
            * **색상**: 같은 색상의 학생들은 같은 그룹(커뮤니티)에 속합니다.
            * **화살표**: 한 학생이 다른 학생을 선택한 방향을 나타냅니다.
            * **노드 위치**: 서로 많이 연결된 학생들이 더 가깝게 배치됩니다.
            
            마우스로 노드를 드래그하여 위치를 조정하거나, 노드를 클릭하여 해당 학생의 관계를 자세히 볼 수 있습니다.
            확대/축소와 화면 이동도 가능합니다.
            """)
            
            # 레이아웃 선택 (PyVis 호환 레이아웃으로 변경)
            layout_options = {
                'fruchterman': '표준 레이아웃',
                'force': '힘 기반 레이아웃',
                'circular': '원형 레이아웃'
            }
            
            selected_layout = st.selectbox("레이아웃 선택:", options=list(layout_options.keys()))
            
            # 선택된 레이아웃 저장
            st.session_state.current_layout = selected_layout
            
            # PyVis 네트워크 생성
            visualizer = self.visualizer  # 직접 visualizer 속성 사용
            pyvis_net = visualizer.create_pyvis_network(
                layout=selected_layout,
                height="600px",
                width="100%"
            )
            
            if pyvis_net:
                # 임시 HTML 파일 생성
                html_path = "temp_network.html"
                pyvis_net.save_graph(html_path)
                
                # HTML 파일 읽기
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # HTML 내용에 실제 학생 이름이 표시되도록 추가 스크립트 삽입
                html_with_names = html_content.replace('</head>', '''
                <style>
                .node-label {
                    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif !important;
                    font-size: 14px;
                }
                </style>
                </head>
                ''')
                
                # iframe 높이 설정
                iframe_height = 700
                
                # HTML 컴포넌트 표시
                components.html(html_with_names, height=iframe_height, scrolling=True)
                
                # 설명 텍스트
                st.info("""
                **사용 방법:**
                - 노드를 드래그하여 위치 조정
                - 마우스 휠로 확대/축소
                - 노드에 마우스를 올리면 상세 정보 표시
                - 네트워크 여백을 드래그하면 전체 화면 이동
                """)
            else:
                st.error("네트워크 시각화를 생성할 수 없습니다. 데이터를 확인해 주세요.")
                
        except Exception as e:
            st.error(f"네트워크 시각화 생성 중 오류가 발생했습니다: {str(e)}")
            logger.error(f"네트워크 시각화 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    # 실제 학생 이름을 가져오는 새로운 헬퍼 함수 추가
    def _get_student_real_name(self, student_id):
        """학생 ID를 실제 이름으로 변환
        
        Arguments:
            student_id: 학생 ID (로마자 또는 숫자)
            
        Returns:
            str: 실제 학생 이름, 변환 실패 시 원래 ID를 문자열로 반환
        """
        # analyzer가 있는지 확인
        if not hasattr(self, 'analyzer') or not self.analyzer:
            return str(student_id)
        
        # 1. name_mapping 확인 (ID -> 이름)
        if hasattr(self.analyzer, 'name_mapping') and self.analyzer.name_mapping:
            if student_id in self.analyzer.name_mapping:
                return self.analyzer.name_mapping[student_id]
                
        # 2. reverse_romanized 확인 (로마자 -> 한글)
        if hasattr(self.analyzer, 'reverse_romanized') and self.analyzer.reverse_romanized:
            if student_id in self.analyzer.reverse_romanized:
                return self.analyzer.reverse_romanized[student_id]
                
        # 3. id_to_name 확인
        if hasattr(self.analyzer, 'id_to_name') and hasattr(self.analyzer.id_to_name, 'get'):
            name = self.analyzer.id_to_name.get(student_id)
            if name:
                return name
        
        # 4. visualizer의 _get_original_name 메서드 사용 시도
        if hasattr(self, 'visualizer') and hasattr(self.visualizer, '_get_original_name'):
            try:
                name = self.visualizer._get_original_name(student_id)
                if name:
                    return name
            except:
                pass
        
        # 변환 실패 시 원래 ID 반환
        return str(student_id)