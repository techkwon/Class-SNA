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
            
            # 탭 생성
            tab1, tab2, tab3 = st.tabs(["네트워크 그래프", "중심성 지표", "커뮤니티 분석"])
            
            with tab1:
                # 네트워크 그래프 시각화
                st.write("#### 학급 관계 네트워크 그래프")
                st.write("노드(원)는 학생을 나타내며, 크기는 연결 중심성(In)에 비례합니다. 색상은 같은 커뮤니티(그룹)에 속한 학생들을 나타냅니다.")
                
                # 레이아웃 선택 옵션
                layout_options = {
                    "fruchterman": "Fruchterman-Reingold",
                    "spring": "Spring",
                    "circular": "Circular",
                    "kamada": "Kamada-Kawai"
                }
                
                selected_layout = st.selectbox(
                    "레이아웃 선택:",
                    options=list(layout_options.keys()),
                    format_func=lambda x: layout_options[x],
                    index=0
                )
                
                # Plotly 그래프 생성
                fig = self.visualizer.create_plotly_network(layout=selected_layout)
                st.plotly_chart(fig, use_container_width=True)
                
                # PyVis 네트워크 생성 (인터랙티브)
                st.write("#### 인터랙티브 네트워크 (드래그하여 조작 가능)")
                pyvis_path = self.visualizer.create_pyvis_network()
                
                if pyvis_path:
                    # components.v1 모듈 사용 시도
                    try:
                        # HTML 파일 표시
                        with open(pyvis_path, 'r', encoding='utf-8') as f:
                            html_data = f.read()
                        
                        import streamlit.components.v1 as components
                        components.html(html_data, height=500)
                    except (ImportError, AttributeError):
                        # 대체 방법: 이미 visualizer에서 링크가 제공되었을 것입니다
                        st.info("인터랙티브 네트워크를 보려면 위의 다운로드 링크를 사용하세요.")
                else:
                    st.warning("인터랙티브 네트워크 생성에 실패했습니다.")
            
            with tab2:
                # 중심성 지표 시각화
                st.write("#### 중심성 지표 분석")
                st.write("중심성 지표는 학생들의 관계망 내 위치와 역할을 수치화합니다.")
                
                # 지표 선택 옵션
                metric_options = {
                    "in_degree": "연결 중심성(In) - 선호도",
                    "out_degree": "연결 중심성(Out) - 친밀도",
                    "betweenness": "매개 중심성 - 중재자 역할",
                    "closeness": "근접 중심성 - 정보 접근성"
                }
                
                selected_metric = st.selectbox(
                    "중심성 지표 선택:",
                    options=list(metric_options.keys()),
                    format_func=lambda x: metric_options[x],
                    index=0
                )
                
                # 상위 학생 수 선택
                top_n = st.slider("상위 학생 수:", min_value=5, max_value=20, value=10)
                
                # 중심성 그래프 생성
                fig = self.visualizer.create_centrality_plot(metric=selected_metric, top_n=top_n)
                st.pyplot(fig)
                
                # 중심성 데이터 표시
                metrics_df = pd.DataFrame()
                for name, values in self.metrics.items():
                    metrics_df[metric_options.get(name, name)] = pd.Series(values)
                
                st.write("#### 중심성 지표 데이터")
                st.dataframe(metrics_df)
            
            with tab3:
                # 커뮤니티 분석
                st.write("#### 하위 그룹(커뮤니티) 분석")
                st.write("하위 그룹은 서로 밀접하게 연결된 학생들의 집단을 나타냅니다.")
                
                # 커뮤니티 테이블 생성
                community_df = self.visualizer.create_community_table()
                st.dataframe(community_df)
                
                # 소외 학생 식별
                isolated_students = self.analyzer.identify_isolated_nodes()
                
                if isolated_students:
                    st.write("#### 관심이 필요한 학생")
                    st.write("연결 중심성(In)이 낮은 학생들입니다. 학급 내에서 상대적으로 적은 선택을 받았습니다.")
                    st.write(", ".join(isolated_students))
            
            return True
            
        except Exception as e:
            logger.error(f"시각화 섹션 생성 실패: {str(e)}")
            st.error(f"시각화 생성 중 오류가 발생했습니다: {str(e)}")
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
                    b64 = base64.b64encode(img_bytes.read()).decode()
                    st.markdown(f'<a href="data:image/png;base64,{b64}" download="network_graph.png">네트워크 그래프 PNG 다운로드</a>', unsafe_allow_html=True)
                except ImportError:
                    # kaleido가 없으면 안내 메시지 표시
                    st.warning("이미지 내보내기를 위해 kaleido 패키지가 필요합니다. `pip install kaleido` 명령으로 설치할 수 있습니다.")
                    # 대안으로 JSON 형식 제공
                    json_str = fig.to_json()
                    json_b64 = base64.b64encode(json_str.encode()).decode()
                    st.markdown(f'<a href="data:application/json;base64,{json_b64}" download="network_graph.json">네트워크 그래프 JSON 다운로드</a>', unsafe_allow_html=True)
                
                # PyVis HTML 다운로드
                pyvis_path = self.visualizer.create_pyvis_network()
                if pyvis_path:
                    try:
                        with open(pyvis_path, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        
                        html_b64 = base64.b64encode(html_content.encode()).decode()
                        st.markdown(f'<a href="data:text/html;base64,{html_b64}" download="interactive_network.html">인터랙티브 네트워크 HTML 다운로드</a>', unsafe_allow_html=True)
                    except Exception as e:
                        logger.error(f"HTML 파일 읽기 실패: {str(e)}")
                        st.warning("인터랙티브 네트워크 HTML 생성에 실패했습니다.")
                else:
                    st.warning("인터랙티브 네트워크 생성에 실패했습니다.")
            
            return True
            
        except Exception as e:
            logger.error(f"내보내기 옵션 생성 실패: {str(e)}")
            st.error(f"내보내기 옵션 생성 중 오류가 발생했습니다: {str(e)}")
            return False
    
    def generate_full_report(self, network_data):
        """전체 보고서 생성"""
        try:
            # 타이틀
            st.markdown("<div class='main-header'>학급 관계 네트워크 분석 결과</div>", unsafe_allow_html=True)
            
            # 요약 정보
            self.generate_summary_section()
            
            # 네트워크 시각화
            self.generate_visualizations()
            
            # 내보내기 옵션
            self.generate_export_options(network_data)
            
            # 푸터
            from src.utils import show_footer
            show_footer()
            
            logger.info("보고서 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"보고서 생성 실패: {str(e)}")
            st.error(f"보고서 생성 중 오류가 발생했습니다: {str(e)}")
            return False 