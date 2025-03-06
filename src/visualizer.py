import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from pyvis.network import Network
import tempfile
import os
import logging
import streamlit as st
import base64
from io import BytesIO

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkVisualizer:
    """네트워크 그래프 시각화 클래스"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.graph = analyzer.graph
        self.communities = analyzer.communities
        self.metrics = analyzer.metrics
    
    def create_plotly_network(self, layout="fruchterman", width=800, height=600):
        """Plotly를 사용한 인터랙티브 네트워크 그래프 생성"""
        try:
            # 레이아웃 알고리즘 선택
            if layout == "fruchterman":
                pos = nx.fruchterman_reingold_layout(self.graph)
            elif layout == "spring":
                pos = nx.spring_layout(self.graph)
            elif layout == "circular":
                pos = nx.circular_layout(self.graph)
            elif layout == "shell":
                pos = nx.shell_layout(self.graph)
            else:
                pos = nx.kamada_kawai_layout(self.graph)
            
            # 중심성 지표가 계산되어 있는지 확인
            if not self.metrics:
                self.analyzer.calculate_centrality()
            
            # 노드 크기 계산 (in_degree 기준)
            node_size = {node: (self.metrics["in_degree"][node] * 50) + 10 for node in self.graph.nodes()}
            
            # 커뮤니티 정보가 없으면 탐지
            if not self.communities:
                self.analyzer.detect_communities()
            
            # 커뮤니티별 색상 할당
            community_colors = {}
            color_palette = list(mcolors.TABLEAU_COLORS.values())
            unique_communities = set(self.communities.values())
            
            for i, comm_id in enumerate(unique_communities):
                color_idx = i % len(color_palette)
                community_colors[comm_id] = color_palette[color_idx]
            
            # Plotly용 그래프 데이터 준비
            edge_x = []
            edge_y = []
            edge_text = []
            edge_width = []
            
            for edge in self.graph.edges(data=True):
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                
                # 곡선형 엣지 그리기
                edge_x.append(x0)
                edge_x.append(x1)
                edge_x.append(None)
                edge_y.append(y0)
                edge_y.append(y1)
                edge_y.append(None)
                
                # 엣지 텍스트 및 두께
                weight = edge[2].get('weight', 1)
                edge_text.append(f"{edge[0]} → {edge[1]}, Weight: {weight}")
                edge_width.append(weight)
            
            node_x = []
            node_y = []
            node_text = []
            node_sizes = []
            node_colors = []
            
            for node in self.graph.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                
                # 노드 텍스트: 학생 이름과 중심성 정보 포함
                text = f"{node}<br>"
                text += f"연결 중심성(In): {self.metrics['in_degree'][node]:.3f}<br>"
                text += f"연결 중심성(Out): {self.metrics['out_degree'][node]:.3f}<br>"
                text += f"매개 중심성: {self.metrics['betweenness'][node]:.3f}"
                node_text.append(text)
                
                # 노드 크기 및 색상
                node_sizes.append(node_size[node])
                
                comm_id = self.communities.get(node, 0)
                node_colors.append(community_colors.get(comm_id, '#CCCCCC'))
            
            # 엣지 트레이스
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=0.5, color='#888'),
                hoverinfo='text',
                text=edge_text,
                mode='lines')
            
            # 노드 트레이스
            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                hoverinfo='text',
                text=node_text,
                marker=dict(
                    showscale=False,
                    color=node_colors,
                    size=node_sizes,
                    line=dict(width=1, color='#888')
                ))
            
            # 그래프 레이아웃
            fig = go.Figure(
                data=[edge_trace, node_trace],
                layout=go.Layout(
                    title="학급 관계 네트워크",
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20, l=5, r=5, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    width=width,
                    height=height
                ))
            
            return fig
            
        except Exception as e:
            logger.error(f"Plotly 네트워크 그래프 생성 실패: {str(e)}")
            raise Exception(f"네트워크 그래프 생성 중 오류가 발생했습니다: {str(e)}")
    
    def create_pyvis_network(self, height="500px", width="100%"):
        """PyVis를 사용한 인터랙티브 네트워크 그래프 생성 (HTML)"""
        try:
            # PyVis 네트워크 객체 생성
            net = Network(height=height, width=width, directed=True, notebook=False)
            
            # 중심성 지표가 계산되어 있는지 확인
            if not self.metrics:
                self.analyzer.calculate_centrality()
            
            # 커뮤니티 정보가 없으면 탐지
            if not self.communities:
                self.analyzer.detect_communities()
            
            # 커뮤니티별 색상 할당
            community_colors = {}
            color_palette = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33", "#a65628", "#f781bf"]
            unique_communities = set(self.communities.values())
            
            for i, comm_id in enumerate(unique_communities):
                color_idx = i % len(color_palette)
                community_colors[comm_id] = color_palette[color_idx]
            
            # 노드 추가
            for node in self.graph.nodes():
                # 노드 크기 계산 (in_degree 기준)
                size = (self.metrics["in_degree"][node] * 30) + 15
                
                # 커뮤니티 색상
                comm_id = self.communities.get(node, 0)
                color = community_colors.get(comm_id, '#CCCCCC')
                
                # 툴팁 텍스트
                title = f"{node}\n"
                title += f"연결 중심성(In): {self.metrics['in_degree'][node]:.3f}\n"
                title += f"연결 중심성(Out): {self.metrics['out_degree'][node]:.3f}\n"
                title += f"매개 중심성: {self.metrics['betweenness'][node]:.3f}\n"
                title += f"커뮤니티: {comm_id}"
                
                # 노드 추가
                net.add_node(node, label=node, title=title, size=size, color=color)
            
            # 엣지 추가
            for edge in self.graph.edges(data=True):
                from_node, to_node, attr = edge
                weight = attr.get('weight', 1)
                
                # 엣지 너비 계산
                width = min(weight * 2, 10)  # 너비 상한선 10
                
                # 엣지 추가
                net.add_edge(from_node, to_node, title=f"Weight: {weight}", width=width)
            
            # 물리적 레이아웃 설정
            net.set_options("""
            var options = {
                "physics": {
                    "barnesHut": {
                        "gravitationalConstant": -10000,
                        "centralGravity": 0.3,
                        "springLength": 150,
                        "springConstant": 0.05,
                        "damping": 0.09
                    },
                    "maxVelocity": 50,
                    "minVelocity": 0.75,
                    "solver": "barnesHut"
                },
                "interaction": {
                    "hover": true,
                    "navigationButtons": true
                }
            }
            """)
            
            # 임시 HTML 파일 생성
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmpfile:
                net.save_graph(tmpfile.name)
                
                # HTML 파일을 읽어 데이터 URI로 변환
                with open(tmpfile.name, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 워크어라운드: streamlit.components.v1이 없을 경우, iframe을 사용하여 표시
                try:
                    # streamlit.components.v1이 있으면 사용
                    import streamlit.components.v1 as components
                    return tmpfile.name
                except (ImportError, AttributeError):
                    # 없으면 임시 방편으로 iframe으로 처리
                    logger.warning("streamlit.components.v1 모듈을 가져올 수 없습니다. 대체 방법을 사용합니다.")
                    
                    # HTML 내용을 base64로 인코딩
                    encoded_html = base64.b64encode(html_content.encode()).decode()
                    
                    # iframe 방식으로 데이터 URI 생성
                    st.markdown(f"### 인터랙티브 네트워크 그래프")
                    st.warning("시각화 컴포넌트가 제한된 환경에서 실행 중입니다. HTML 다운로드 기능을 이용해 네트워크 그래프를 확인하세요.")
                    
                    # 다운로드 링크 제공
                    st.markdown(f'<a href="data:text/html;base64,{encoded_html}" download="network_graph.html">인터랙티브 네트워크 HTML 다운로드</a>', unsafe_allow_html=True)
                    
                    return tmpfile.name
            
        except Exception as e:
            logger.error(f"PyVis 네트워크 그래프 생성 실패: {str(e)}")
            st.error(f"인터랙티브 네트워크 그래프 생성 중 오류가 발생했습니다: {str(e)}")
            return None
    
    def create_centrality_plot(self, metric="in_degree", top_n=10):
        """중심성 지표 막대 그래프 생성"""
        try:
            if not self.metrics:
                self.analyzer.calculate_centrality()
            
            # 지표 선택
            if metric not in self.metrics:
                raise ValueError(f"지원하지 않는 중심성 지표입니다: {metric}")
            
            # 중심성 값 정렬 및 상위 N개 선택
            metric_values = self.metrics[metric]
            sorted_values = sorted(metric_values.items(), key=lambda x: x[1], reverse=True)
            top_items = sorted_values[:top_n]
            
            # 데이터 준비
            nodes = [item[0] for item in top_items]
            values = [item[1] for item in top_items]
            
            # matplotlib 그래프 생성
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(nodes, values, color='lightblue')
            
            # 그래프 스타일 설정
            ax.set_xlabel(f'{metric} 중심성 지표')
            ax.set_ylabel('학생')
            
            metric_names = {
                "in_degree": "연결 중심성(In)",
                "out_degree": "연결 중심성(Out)",
                "closeness": "근접 중심성",
                "betweenness": "매개 중심성",
                "eigenvector": "아이겐벡터 중심성"
            }
            
            ax.set_title(f'상위 {top_n}명 학생의 {metric_names.get(metric, metric)} 지표')
            
            # 값 레이블 추가
            for bar in bars:
                width = bar.get_width()
                ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, f'{width:.3f}', 
                        ha='left', va='center')
            
            # 그리드 추가
            ax.grid(True, axis='x', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"중심성 지표 그래프 생성 실패: {str(e)}")
            raise Exception(f"중심성 지표 그래프 생성 중 오류가 발생했습니다: {str(e)}")
    
    def create_community_table(self):
        """커뮤니티별 학생 목록 생성"""
        try:
            if not self.communities:
                self.analyzer.detect_communities()
            
            # 커뮤니티별 학생 그룹화
            community_groups = {}
            for node, community_id in self.communities.items():
                if community_id not in community_groups:
                    community_groups[community_id] = []
                community_groups[community_id].append(node)
            
            # 커뮤니티별 데이터 준비
            data = []
            for comm_id, members in community_groups.items():
                # 중심성 지표가 높은 학생 식별
                if self.metrics:
                    # in_degree 기준 중심 학생 식별
                    central_student = max(members, key=lambda x: self.metrics["in_degree"].get(x, 0))
                    central_value = self.metrics["in_degree"].get(central_student, 0)
                else:
                    central_student = ""
                    central_value = 0
                
                data.append({
                    "커뮤니티 ID": comm_id,
                    "학생 수": len(members),
                    "소속 학생": ", ".join(members),
                    "중심 학생": central_student,
                    "중심 학생 연결성": f"{central_value:.3f}"
                })
            
            # 데이터프레임 생성
            df = pd.DataFrame(data)
            
            return df
            
        except Exception as e:
            logger.error(f"커뮤니티 테이블 생성 실패: {str(e)}")
            raise Exception(f"커뮤니티 테이블 생성 중 오류가 발생했습니다: {str(e)}") 