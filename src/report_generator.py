import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import logging

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
    
    def generate_summary_section(self):
        """요약 정보 섹션 생성"""
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
        """전체 분석 보고서 생성"""
        try:
            # 요약 섹션
            self.generate_summary_section()
            
            # 시각화 섹션
            self.generate_visualizations()
            
            # 내보내기 옵션 섹션
            self.generate_export_options(network_data)
            
            # 주의: 메인 앱에서 이미 푸터를 표시하므로 여기서는 표시하지 않음
            # 단일 푸터 표시만 하려면 아래 마크다운 코드를 주석 처리하세요
            # st.markdown("---")
            # st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>학급 관계 네트워크 분석 시스템 (Class-SNA) | 데이터 분석 및 시각화: NetworkX, Plotly | AI 분석: Google Gemini</div>", unsafe_allow_html=True)
            
            logger.info("보고서 생성 완료")
            return True
            
        except Exception as e:
            st.error(f"보고서 생성 중 오류가 발생했습니다: {str(e)}")
            logger.error(f"보고서 생성 실패: {str(e)}")
            return False 