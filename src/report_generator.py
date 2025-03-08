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
                st.pyplot(fig)
                
                # 중심성 데이터 표시
                metrics_df = pd.DataFrame()
                for name, values in self.metrics.items():
                    metrics_df[metric_options.get(name, name)] = pd.Series(values)
                
                st.write("#### 전체 중심성 지표 데이터")
                st.dataframe(metrics_df)
            
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
                st.dataframe(community_df)
                
                # 소외 학생 분석
                st.write("#### 소외 학생 분석")
                st.write("""
                **💡 소외 학생 분석 가이드:**
                - 소외 학생은 다른 학생들과의 연결이 적거나 없는 학생을 의미합니다
                - 인기도(In) 값이 0인 학생은 아무도 선택하지 않은 학생입니다
                - 친밀도(Out) 값이 0인 학생은 아무도 선택하지 않은 학생입니다
                - 소외 학생들에게 특별한 관심이 필요할 수 있습니다
                """)
                
                isolated_nodes = self.analyzer.find_isolated_nodes()
                if isolated_nodes:
                    isolated_df = pd.DataFrame({
                        "학생": isolated_nodes,
                        "인기도(In)": [self.metrics["in_degree"].get(node, 0) for node in isolated_nodes],
                        "친밀도(Out)": [self.metrics["out_degree"].get(node, 0) for node in isolated_nodes],
                        "소속 그룹": [self.communities.get(node, -1) for node in isolated_nodes]
                    })
                    st.dataframe(isolated_df)
                else:
                    st.success("소외된 학생이 없습니다. 모든 학생이 네트워크에 잘 연결되어 있습니다.")
            
            return True
            
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
        """학생별 개인 분석 탭"""
        try:
            st.markdown("## 👤 학생별 개인 분석")
            st.markdown("""
            이 섹션에서는 각 학생의 개인별 네트워크 특성과 관계를 분석합니다.
            학생을 선택하면 해당 학생의 직접적인 관계와 네트워크 내 위치에 대한 자세한 정보를 볼 수 있습니다.
            """)
            
            # 학생 이름 매핑 확인
            romanized_to_korean = {}
            if 'romanized_names' in st.session_state:
                romanized_to_korean = st.session_state.romanized_names
            
            # 학생 목록 가져오기 (가능하면 한글 이름으로)
            students = []
            for node in self.graph.nodes():
                if isinstance(node, str) and node in romanized_to_korean:
                    students.append((node, romanized_to_korean[node]))
                else:
                    students.append((node, str(node)))
            
            # 학생 선택 드롭다운
            student_options = [korean for _, korean in sorted(students, key=lambda x: x[1])]
            if not student_options:
                st.warning("분석할 학생 데이터가 없습니다.")
                return
                
            selected_student_name = st.selectbox(
                "분석할 학생 선택:",
                options=student_options,
                key="student_selector"
            )
            
            # 선택된 학생의 원래 ID 찾기
            selected_student_id = None
            for node_id, korean in students:
                if korean == selected_student_name:
                    selected_student_id = node_id
                    break
            
            if not selected_student_id:
                st.warning("선택한 학생의 데이터를 찾을 수 없습니다.")
                return
                
            # 학생 정보 카드
            st.markdown(f"### {selected_student_name}님의 네트워크 분석")
            
            # 학생 정보를 2개 열로 나눠서 표시
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # 기본 정보와 중심성 지표
                st.markdown("#### 네트워크 지표")
                
                # 중심성 지표 가져오기
                in_degree = self.metrics.get('in_degree', {}).get(selected_student_id, 0)
                betweenness = self.metrics.get('betweenness', {}).get(selected_student_id, 0)
                
                # 리스트 형태인 경우 첫 번째 값 사용
                if isinstance(in_degree, list):
                    in_degree = in_degree[0] if in_degree else 0
                if isinstance(betweenness, list):
                    betweenness = betweenness[0] if betweenness else 0
                
                # 입력 및 출력 차수
                in_degree_actual = self.graph.in_degree(selected_student_id)
                out_degree_actual = self.graph.out_degree(selected_student_id)
                
                # 커뮤니티 찾기
                community_id = "없음"
                for comm_id, members in self.communities.items():
                    if selected_student_id in members:
                        community_id = comm_id
                        break
                
                # 데이터 테이블
                metrics_data = {
                    "지표": ["받은 선택 수", "한 선택 수", "매개 중심성", "소속 그룹"],
                    "값": [
                        f"{in_degree_actual}",
                        f"{out_degree_actual}",
                        f"{betweenness:.3f}" if isinstance(betweenness, (int, float)) else str(betweenness),
                        f"{community_id}"
                    ]
                }
                st.table(pd.DataFrame(metrics_data))
                
                # 학생 위치 해석
                st.markdown("#### 학생 역할 분석")
                
                # 역할 결정
                role = self._determine_student_role(in_degree, betweenness, in_degree_actual, out_degree_actual)
                
                st.markdown(f"**역할:** {role['title']}")
                st.markdown(f"{role['description']}")
            
            with col2:
                # 관계 네트워크 시각화
                st.markdown("#### 학생 관계 네트워크")
                
                # 1촌 네트워크 추출 (직접 연결된 학생들)
                neighbors = list(self.graph.successors(selected_student_id)) + list(self.graph.predecessors(selected_student_id))
                neighbors = list(set(neighbors))  # 중복 제거
                
                # 선택된 학생을 포함한 서브그래프 생성
                subgraph_nodes = neighbors + [selected_student_id]
                subgraph = self.graph.subgraph(subgraph_nodes)
                
                # 각 엣지의 방향 정보 추가
                edge_info = []
                for u, v in subgraph.edges():
                    if u == selected_student_id:
                        relation = "선택함"
                    elif v == selected_student_id:
                        relation = "선택받음"
                    else:
                        relation = "기타 관계"
                    edge_info.append((u, v, relation))
                
                # 분석 내용 추가
                incoming = len(list(self.graph.predecessors(selected_student_id)))
                outgoing = len(list(self.graph.successors(selected_student_id)))
                
                st.markdown(f"**직접 관계:** {len(neighbors)}명의 학생과 연결됨")
                st.markdown(f"**받은 선택:** {incoming}명의 학생이 선택함")
                st.markdown(f"**한 선택:** {outgoing}명의 학생을 선택함")
                
                # 이 학생의 네트워크를 시각화 (미니 네트워크)
                # (여기서는 간단한 텍스트 기반 정보만 제공)
                st.markdown("#### 직접 연결된 학생들")
                
                # 선택한 학생 & 선택받은 학생 목록
                chosen_by = []
                chosen = []
                
                for u, v in self.graph.edges():
                    # 이 학생을 선택한 학생들
                    if v == selected_student_id:
                        student_name = romanized_to_korean.get(u, str(u))
                        chosen_by.append(student_name)
                    
                    # 이 학생이 선택한 학생들
                    if u == selected_student_id:
                        student_name = romanized_to_korean.get(v, str(v))
                        chosen.append(student_name)
                
                # 두 열로 나누어 표시
                col2_1, col2_2 = st.columns(2)
                
                with col2_1:
                    st.markdown("**이 학생을 선택한 학생들:**")
                    if chosen_by:
                        for name in sorted(chosen_by):
                            st.markdown(f"- {name}")
                    else:
                        st.markdown("이 학생을 선택한 학생이 없습니다.")
                        
                with col2_2:
                    st.markdown("**이 학생이 선택한 학생들:**")
                    if chosen:
                        for name in sorted(chosen):
                            st.markdown(f"- {name}")
                    else:
                        st.markdown("이 학생이 선택한 학생이 없습니다.")
            
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
            max_in_degree = max(self.metrics.get('in_degree', {}).values())
            max_betweenness = max(self.metrics.get('betweenness', {}).values())
            
            # 타입 체크 및 처리
            if isinstance(max_in_degree, list):
                max_in_degree = max_in_degree[0] if max_in_degree else 1
            if isinstance(max_betweenness, list):
                max_betweenness = max_betweenness[0] if max_betweenness else 1
                
            # 0으로 나누기 방지
            if max_in_degree == 0:
                max_in_degree = 1
            if max_betweenness == 0:
                max_betweenness = 1
                
            # 정규화 (0-1 범위)
            norm_in_degree = float(in_degree) / float(max_in_degree) if max_in_degree else 0
            norm_betweenness = float(betweenness) / float(max_betweenness) if max_betweenness else 0
            
            # 균형 지표 (선택한 수와 선택받은 수의 균형)
            balance = 0
            if (in_count + out_count) > 0:
                balance = min(in_count, out_count) / max(in_count, out_count)
                
            # 조건에 따른 역할 결정
            if norm_in_degree > 0.7:
                if norm_betweenness > 0.5:
                    return {
                        "type": "leader",
                        "title": "리더 (영향력 있는 중심 학생)",
                        "description": "이 학생은 많은 친구들로부터 선택을 받고, 서로 다른 그룹을 연결하는 중요한 위치에 있습니다. 학급에서 높은 영향력을 가지고 있으며, 여러 그룹 사이의 소통을 도울 수 있습니다."
                    }
                else:
                    return {
                        "type": "popular",
                        "title": "인기 있는 학생",
                        "description": "이 학생은 많은 친구들로부터 선택을 받았습니다. 학급에서 인기가 많고 또래들에게 긍정적인 영향을 줄 수 있는 위치에 있습니다."
                    }
            elif norm_betweenness > 0.6:
                return {
                    "type": "bridge",
                    "title": "다리 역할 학생",
                    "description": "이 학생은 서로 다른 그룹을 연결하는 중요한 '다리' 역할을 합니다. 인기가 가장 높지는 않지만, 정보 전달과 학급 화합에 중요한 위치에 있습니다."
                }
            elif balance > 0.7:
                return {
                    "type": "balanced",
                    "title": "균형 있는 관계형 학생",
                    "description": "이 학생은 다른 학생들을 선택하는 수와 선택받는 수가 균형을 이루고 있습니다. 안정적이고 상호적인 교우관계를 형성하고 있습니다."
                }
            elif out_count > in_count * 2:
                return {
                    "type": "seeking",
                    "title": "관계 추구형 학생",
                    "description": "이 학생은 다른 학생들을 많이 선택했지만, 받은 선택은 상대적으로 적습니다. 사회적 관계를 적극적으로 원하고 있으며, 더 많은 상호작용 기회가 필요할 수 있습니다."
                }
            elif in_count == 0 or norm_in_degree < 0.1:
                return {
                    "type": "isolated",
                    "title": "고립 위험 학생",
                    "description": "이 학생은 다른 학생들로부터 선택을 거의 또는 전혀 받지 못했습니다. 학급에서 사회적으로 고립될 위험이 있으며, 관심과 지원이 필요합니다."
                }
            else:
                return {
                    "type": "average",
                    "title": "일반적인 관계 학생",
                    "description": "이 학생은 학급 내에서 평균적인 사회적 관계를 유지하고 있습니다. 특별히 눈에 띄는 패턴은 없지만, 안정적인 교우관계를 형성하고 있습니다."
                }
                
        except Exception as e:
            logger.warning(f"학생 역할 결정 중 오류: {str(e)}")
            return {
                "type": "unknown",
                "title": "분석 불가",
                "description": "이 학생의 네트워크 역할을 분석하는 중 오류가 발생했습니다."
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
        """커뮤니티 분석 결과 표시"""
        try:
            if not self.communities:
                st.warning("커뮤니티 정보가 없습니다.")
                return
                
            # 커뮤니티 정보 표시
            st.markdown("### 하위 그룹 구성")
            
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
            # 중심성 지표가 있는지 확인
            if not self.metrics or not any(metric in self.metrics for metric in ['in_degree', 'betweenness']):
                st.warning("중심성 분석 데이터가 없습니다.")
                return
            
            # 중심성 설명
            st.markdown("""
            ### 중심성 지표란?
            
            중심성 지표는 네트워크에서 각 학생의 중요도를 나타내는 수치입니다:
            
            - **인기도(In-Degree)**: 다른 학생들에게 선택된 횟수입니다. 높을수록 더 인기가 많습니다.
            - **중재자 역할(매개 중심성)**: 서로 다른 그룹을 연결하는 다리 역할입니다. 높을수록 정보 전달자 역할을 합니다.
            - **정보 접근성(근접 중심성)**: 다른 모든 학생들과의 근접도입니다. 높을수록 전체 네트워크에서 정보를 빠르게 얻을 수 있습니다.
            """)
            
            # 중심성 지표 선택
            metric_options = ['in_degree', 'betweenness']
            metric_names = {'in_degree': '인기도', 'betweenness': '매개 중심성'}
            
            # 세션 상태 초기화
            if 'centrality_metric' not in st.session_state:
                st.session_state.centrality_metric = 'in_degree'
            
            if 'top_n_slider' not in st.session_state:
                st.session_state.top_n_slider = 10
                
            # 선택 변경 콜백 함수
            def on_metric_change():
                # 상태 유지를 위한 빈 콜백
                pass
                
            def on_top_n_change():
                # 상태 유지를 위한 빈 콜백
                pass
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_metric = st.selectbox(
                    "분석할 중심성 지표 선택:", 
                    options=metric_options,
                    format_func=lambda x: metric_names.get(x, x),
                    key='centrality_metric',
                    on_change=on_metric_change
                )
            
            with col2:
                top_n = st.slider(
                    "표시할 학생 수:", 
                    min_value=3, 
                    max_value=20, 
                    value=st.session_state.top_n_slider,
                    key='top_n_slider',
                    on_change=on_top_n_change
                )
            
            # 중심성 시각화
            st.markdown(f"### 상위 {top_n}명 {metric_names.get(selected_metric, selected_metric)} 분석")
            
            # 중심성 차트
            centrality_fig = self.visualizer.create_centrality_plot(metric=selected_metric, top_n=top_n)
            if centrality_fig is not None:
                st.pyplot(centrality_fig)
            
            # 중심성 데이터 표시
            metrics_df = pd.DataFrame()
            
            # 이름 매핑을 위한 준비
            name_mapping = {}
            if hasattr(self.analyzer, 'name_mapping'):
                name_mapping = self.analyzer.name_mapping
            elif 'name_mapping' in st.session_state:
                name_mapping = st.session_state.name_mapping
                
            # 원본 노드 목록
            node_ids = list(self.metrics.get('in_degree', {}).keys())
            
            # 데이터 구성
            nodes_data = []
            for node_id in node_ids:
                # 노드 이름 추출
                original_name = name_mapping.get(str(node_id), str(node_id))
                
                # 중심성 지표 값 추출
                row_data = {"학생 이름": original_name}
                
                for metric in metric_options:
                    metric_name = metric_names.get(metric, metric)
                    if metric in self.metrics and node_id in self.metrics[metric]:
                        value = self.metrics[metric][node_id]
                        
                        # 리스트 타입 처리
                        if isinstance(value, list):
                            value = value[0] if value else 0
                            
                        try:
                            row_data[metric_name] = float(value)
                        except (ValueError, TypeError):
                            row_data[metric_name] = 0
                    else:
                        row_data[metric_name] = 0
                        
                nodes_data.append(row_data)
                
            # 데이터프레임 생성 및 정렬
            if nodes_data:
                result_df = pd.DataFrame(nodes_data)
                metric_col = metric_names.get(selected_metric, selected_metric)
                result_df = result_df.sort_values(by=metric_col, ascending=False)
                
                # 소수점 자리 포맷팅
                for col in result_df.columns:
                    if col != "학생 이름":
                        result_df[col] = result_df[col].map(lambda x: f"{x:.4f}")
                
                st.write("#### 전체 중심성 지표 데이터")
                st.dataframe(result_df, use_container_width=True)
                
                # CSV 다운로드 버튼
                csv = result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 중심성 지표 CSV 다운로드",
                    data=csv,
                    file_name="centrality_metrics.csv",
                    mime="text/csv"
                )
            else:
                st.warning("중심성 지표 데이터를 표시할 수 없습니다.")
        
        except Exception as e:
            logger.error(f"중심성 분석 표시 중 오류: {str(e)}")
            st.error("중심성 분석 결과를 표시하는 중 오류가 발생했습니다.")
    
    def show_isolated_students(self, network_data):
        """고립된 학생 분석 결과 표시"""
        try:
            st.markdown("## 관계망 주의 학생 분석")
            st.markdown("""
            이 섹션에서는 관계망에서 상대적으로 고립되거나 관계가 적은 학생들을 식별합니다.
            이러한 분석은 교사가 사회적 개입이 필요한 학생들을 파악하는 데 도움이 됩니다.
            """)
            
            # 임계값 설정 슬라이더
            threshold = st.slider(
                "고립 학생 식별 임계값 (낮을수록 더 많은 학생이 '고립됨'으로 식별됨):", 
                min_value=0.0, 
                max_value=0.5, 
                value=0.1, 
                step=0.05,
                key="isolation_threshold"
            )
            
            # 고립 학생 식별
            isolated_students = self.analyzer.identify_isolated_nodes(threshold=threshold)
            
            if isolated_students:
                # 고립 학생 목록 표시
                st.markdown(f"### 관계망 주의 학생 목록 ({len(isolated_students)}명)")
                
                # 데이터프레임 생성
                isolation_data = []
                for student in isolated_students:
                    in_degree = self.metrics.get('in_degree', {}).get(student, 0)
                    out_degree = 0  # 기본값
                    
                    # 출력 차수(out degree) 계산
                    if self.graph:
                        out_degree = self.graph.out_degree(student)
                    
                    # 데이터 추가
                    isolation_data.append({
                        "학생": student,
                        "받은 선택 수": in_degree,
                        "한 선택 수": out_degree,
                        "고립도": 1.0 - in_degree  # 단순화된 고립도 지표
                    })
                
                # 데이터프레임 생성 및 정렬
                if isolation_data:
                    iso_df = pd.DataFrame(isolation_data)
                    iso_df = iso_df.sort_values("고립도", ascending=False)
                    
                    # 테이블 표시
                    st.dataframe(iso_df, use_container_width=True)
                    
                    # 시각화
                    st.markdown("### 고립 학생 관계망 시각화")
                    st.markdown("아래 그래프에서 붉은색으로 표시된 노드는 관계망에서 상대적으로 고립된 학생들입니다.")
                    
                    # 여기서 고립 학생을 강조하는 네트워크 시각화 코드를 추가할 수 있습니다
                    # 현재는 생략하고 텍스트로만 설명
                    
                    # 고립 학생 지원 전략
                    st.markdown("### 고립 학생 지원 전략")
                    st.markdown("""
                    관계망에서 고립된 학생들을 지원하기 위한 일반적인 전략:
                    
                    1. **그룹 활동 강화**: 다양한 학생들과 협력할 수 있는 그룹 활동을 구성합니다.
                    2. **멘토-멘티 시스템**: 사회성이 좋은 학생들과 고립된 학생들을 연결하는 멘토링 시스템을 구축합니다.
                    3. **관심사 기반 활동**: 공통 관심사를 중심으로 한 활동을 통해 자연스러운 관계 형성을 촉진합니다.
                    4. **사회적 기술 교육**: 고립된 학생들에게 사회적 상호작용 기술을 가르칩니다.
                    5. **학급 분위기 개선**: 포용적이고 지지적인 학급 분위기를 조성합니다.
                    """)
            else:
                st.info("현재 임계값 기준으로 고립된 학생이 없습니다. 임계값을 낮춰보세요.")
                
        except Exception as e:
            logger.error(f"고립 학생 분석 표시 중 오류: {str(e)}")
            st.error("고립 학생 분석 결과를 표시하는 중 오류가 발생했습니다.")
    
    def show_interactive_network(self, network_data):
        """인터랙티브 네트워크 시각화"""
        try:
            # 제목은 이미 탭 헤더에 있으므로 제거하고 설명만 표시
            st.write("""
            아래 그래프는 마우스로 조작할 수 있습니다:
            - **드래그**: 학생(노드)을 끌어서 이동할 수 있습니다
            - **확대/축소**: 마우스 휠로 확대하거나 축소할 수 있습니다
            - **호버**: 마우스를 올리면 학생 정보가 표시됩니다
            """)
            
            # Plotly 그래프 생성
            st.subheader("정적 네트워크 뷰")
            fig = self.visualizer.create_plotly_network()
            st.plotly_chart(fig, use_container_width=True)
            
            # PyVis 네트워크 생성 (인터랙티브)
            st.subheader("인터랙티브 네트워크")
            st.write("""
            이 네트워크는 실시간으로 상호작용이 가능합니다:
            - **노드 끌기**: 학생을 드래그하여 위치를 변경할 수 있습니다
            - **확대/축소**: 마우스 휠로 줌인/줌아웃이 가능합니다
            - **정보 보기**: 학생에게 마우스를 올리면 상세 정보가 표시됩니다
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
                            href = f'<a href="data:text/html;base64,{b64}" download="interactive_network.html">인터랙티브 네트워크 HTML 다운로드</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        except Exception as iframe_e:
                            st.error(f"대체 표시 방법도 실패했습니다: {str(iframe_e)}")
                            st.info("그래프를 표시할 수 없습니다. 다른 탭의 정적 그래프를 참고하세요.")
                    else:
                        st.error(f"인터랙티브 네트워크 표시 중 오류 발생: {error_str}")
            else:
                st.warning("인터랙티브 네트워크 생성에 실패했습니다.")
            
        except Exception as e:
            logger.error(f"인터랙티브 네트워크 표시 중 오류: {str(e)}")
            st.error("인터랙티브 네트워크 시각화에 실패했습니다.")