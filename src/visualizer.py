import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.font_manager as fm
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
import platform
import re
import warnings

# 한글 폰트 관련 경고 메시지 필터링
warnings.filterwarnings("ignore", "Glyph .* missing from current font")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit Cloud 환경인지 확인하는 함수 - 전역 함수로 정의
def is_streamlit_cloud():
    """Streamlit Cloud 환경인지 확인"""
    return os.getenv("STREAMLIT_RUNTIME") is not None or os.getenv("STREAMLIT_RUN_ON_SAVE") is not None

# 한글 폰트 설정 함수
def set_korean_font():
    """matplotlib에서 한글 폰트를 사용하도록 설정"""
    try:
        # Streamlit Cloud 환경 확인 - 전역 함수 사용
        if is_streamlit_cloud():
            logger.info("Streamlit Cloud 환경이 감지되었습니다. 기본 폰트를 사용합니다.")
            # 클라우드 환경에서는 폰트 설치를 시도하지 않음
            
            # 일반 폰트 중 한글 지원 가능성이 있는 폰트 시도
            for font in ['Noto Sans', 'DejaVu Sans', 'Arial Unicode MS', 'Roboto']:
                try:
                    plt.rc('font', family=font)
                    logger.info(f"{font} 폰트를 사용합니다.")
                    break
                except Exception as font_e:
                    logger.debug(f"{font} 폰트 사용 실패: {str(font_e)}")
                    continue
                    
            # 영문 폰트 사용 알림
            logger.warning("Streamlit Cloud 환경에서는 한글 폰트가 제한될 수 있습니다. 영문 표기로 대체합니다.")
            return
            
        # 운영체제별 폰트 설정 (로컬 환경)
        system = platform.system()
        if system == 'Darwin':  # macOS
            plt.rc('font', family='AppleGothic')
            logger.info("macOS 환경에서 AppleGothic 폰트를 사용합니다.")
        elif system == 'Windows':  # Windows
            plt.rc('font', family='Malgun Gothic')
            logger.info("Windows 환경에서 Malgun Gothic 폰트를 사용합니다.")
        else:  # Linux 등 (로컬에서만 설치 시도)
            # 로컬 리눅스 환경인 경우에만 폰트 설치 시도
            logger.info("로컬 Linux 환경이 감지되었습니다.")
            
            # 이미 설치된 폰트 먼저 확인
            font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
            nanum_fonts = [f for f in font_list if 'Nanum' in f]
            
            if nanum_fonts:
                # 나눔 폰트가 이미 설치되어 있는 경우
                plt.rc('font', family='NanumGothic')
                logger.info("나눔 폰트가 이미 설치되어 있습니다.")
            else:
                # 일반 폰트 시도
                for font in ['Noto Sans', 'DejaVu Sans', 'Ubuntu']:
                    try:
                        plt.rc('font', family=font)
                        logger.info(f"{font} 폰트를 사용합니다.")
                        break
                    except Exception as font_e:
                        logger.debug(f"{font} 폰트 사용 실패: {str(font_e)}")
                        continue
        
        # 폰트 설정 확인
        plt.rc('axes', unicode_minus=False)  # 마이너스 기호 깨짐 방지
        logger.info(f"폰트 설정 완료: {plt.rcParams['font.family']}")
        
    except Exception as e:
        logger.warning(f"한글 폰트 설정 실패: {str(e)}")
        logger.warning("기본 폰트를 사용합니다. 영문 표기로 대체합니다.")

# 한글 폰트 설정 시도
set_korean_font()

# 한글을 영문으로 변환하는 함수 (폰트 문제 대비)
def romanize_korean(text):
    """한글 이름을 로마자로 변환 (폰트 문제 대비용)"""
    # 성씨 음역 매핑 확장
    surname_mapping = {
        '김': 'Kim', '이': 'Lee', '박': 'Park', '정': 'Jung', '최': 'Choi', '장': 'Jang', 
        '조': 'Jo', '강': 'Kang', '윤': 'Yoon', '한': 'Han', '송': 'Song', '황': 'Hwang',
        '민': 'Min', '서': 'Seo', '도': 'Do', '신': 'Shin', '우': 'Woo', '유': 'Yoo', 
        '성': 'Sung', '지': 'Ji', '예': 'Ye', '준': 'Jun', '진': 'Jin', '현': 'Hyun',
        '승': 'Seung', '은': 'Eun', '하': 'Ha', '명': 'Myung', '고': 'Ko', '권': 'Kwon',
        '전': 'Jeon', '오': 'Oh', '손': 'Son', '안': 'Ahn', '홍': 'Hong', '백': 'Baek',
        '임': 'Lim', '양': 'Yang', '변': 'Byun', '배': 'Bae', '허': 'Heo', '남': 'Nam',
        '구': 'Ku', '노': 'Noh', '원': 'Won', '문': 'Moon', '천': 'Chun', '심': 'Shim',
        '방': 'Bang', '라': 'Ra', '차': 'Cha', '국': 'Kook', '채': 'Chae', '길': 'Gil'
    }
    
    # 1글자 이름에 대한 처리
    if len(text) == 1 and '\uAC00' <= text <= '\uD7A3':  # 한글 유니코드 범위 확인
        return f"Student-{text}"
    
    # 이름을 영문으로 변환
    if len(text) >= 2:
        # 성과 이름 분리 (김민준 -> 김 + 민준)
        surname = text[0]
        given_name = text[1:]
        
        # 성은 매핑 테이블에서 찾기
        if surname in surname_mapping:
            romanized_surname = surname_mapping[surname]
            
            # 이름 첫 글자에 대한 간단한 음역 처리 (완전하지 않음)
            if len(given_name) > 0:
                # 원래 한글 이름 유지하면서 로마자 표기 추가
                return f"{romanized_surname}.{given_name}"
            else:
                return romanized_surname
    
    # 매핑이 없거나 특별한 경우, 원래 텍스트 반환하되 학생 번호 부여
    if re.search(r'[가-힣]', text):
        # 한글이 포함된 텍스트에 번호 부여
        student_id = sum(ord(c) for c in text) % 100  # 간단한 해시
        return f"Student-{student_id}"
    
    # 매핑이 없으면 원래 이름 사용
    return text

class NetworkVisualizer:
    """네트워크 그래프 시각화 클래스"""
    
    def __init__(self, analyzer):
        """NetworkAnalyzer 객체를 받아 초기화"""
        self.analyzer = analyzer
        self.graph = analyzer.graph
        
        # 한글 폰트 설정 및 확인
        set_korean_font()
        self.has_korean_font = self._check_korean_font()
        
        # Streamlit Cloud 환경에서는 자동으로 로마자화 사용
        if is_streamlit_cloud():
            self.has_korean_font = False
            logger.info("Streamlit Cloud 환경에서는 로마자화를 기본으로 사용합니다.")
            
        # 노드 이름 매핑 (원래 이름 -> 로마자화된 이름)
        self.name_mapping = {}
        if not self.has_korean_font:
            for node in self.graph.nodes():
                self.name_mapping[node] = romanize_korean(node)
        
        self.communities = analyzer.communities
        self.metrics = analyzer.metrics
    
    def _check_korean_font(self):
        """한글 폰트 사용 가능 여부 확인"""
        # Streamlit Cloud 환경에서는 자동으로 False 반환
        if is_streamlit_cloud():
            logger.info("Streamlit Cloud 환경에서는 한글 폰트 체크를 건너뜁니다.")
            return False
            
        try:
            # 간단한 한글 텍스트로 시험해보기
            fig, ax = plt.subplots(figsize=(1, 1))
            ax.text(0.5, 0.5, "한글", fontsize=9)
            
            # 경고 없이 생성되면 한글 폰트 지원으로 간주
            plt.close(fig)
            logger.info("한글 폰트 사용 가능 확인됨")
            return True
            
        except Exception as e:
            logger.warning(f"한글 폰트 확인 실패: {str(e)}")
            logger.warning("한글 폰트를 찾을 수 없습니다. 노드 레이블을 영문으로 변환합니다.")
            return False
    
    def _get_display_label(self, node_name, use_romanized=False):
        """표시할 노드 레이블 생성 (한글 폰트 문제시 로마자 변환)"""
        if use_romanized and re.search(r'[가-힣]', node_name):
            return romanize_korean(node_name)
        return node_name
    
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
            
            # 한글 폰트 문제 확인 및 대응
            use_romanized = not self.has_korean_font
            
            if use_romanized:
                # 영문 변환된 노드 이름 표시 안내
                st.info("한글 폰트 문제로 인해 학생 이름이 영문으로 표시됩니다.")
                
                # 매핑 테이블 생성
                original_names = list(self.graph.nodes())
                romanized_names = [self._get_display_label(node, use_romanized=True) for node in original_names]
                name_map = dict(zip(romanized_names, original_names))
                
                # 매핑 테이블 표시
                with st.expander("학생 이름 매핑 테이블", expanded=False):
                    mapping_df = pd.DataFrame({
                        "영문 표시": romanized_names,
                        "원래 이름": original_names
                    })
                    st.dataframe(mapping_df)
            
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
                
                # 한글 폰트 문제가 있으면 로마자 변환
                if use_romanized:
                    from_node = self._get_display_label(edge[0], use_romanized=True)
                    to_node = self._get_display_label(edge[1], use_romanized=True)
                    # 원래 이름도 보여주기 (괄호 안에)
                    edge_text.append(f"{from_node} → {to_node}, 가중치: {weight}")
                else:
                    edge_text.append(f"{edge[0]} → {edge[1]}, 가중치: {weight}")
                    
                edge_width.append(weight)
            
            node_x = []
            node_y = []
            node_text = []
            node_sizes = []
            node_colors = []
            node_labels = []  # 표시할 레이블
            
            for node in self.graph.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                
                # 로마자 변환 여부에 따라 표시 레이블 결정
                if use_romanized:
                    display_name = self._get_display_label(node, use_romanized=True)
                    node_labels.append(display_name)
                else:
                    display_name = node
                    node_labels.append(node)
                
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
                mode='markers+text',  # 텍스트 추가
                hoverinfo='text',
                text=node_text,
                textposition="top center",  # 텍스트 위치
                textfont=dict(size=10),  # 텍스트 크기
                marker=dict(
                    showscale=False,
                    color=node_colors,
                    size=node_sizes,
                    line=dict(width=1, color='#888')
                ))
            
            # 노드 레이블 트레이스 추가
            label_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='text',
                text=node_labels,
                textposition="top center",
                textfont=dict(
                    family="Arial, sans-serif",  # 범용 폰트 사용
                    size=12,
                    color="black"
                ),
                hoverinfo='none'
            )
            
            # 그래프 레이아웃
            fig = go.Figure(
                data=[edge_trace, node_trace, label_trace],  # 레이블 트레이스 추가
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
            st.error(f"네트워크 그래프 생성 중 오류가 발생했습니다: {str(e)}")
            
            # 오류 발생 시 네트워크 데이터 표시
            st.write("### 네트워크 데이터")
            
            if hasattr(self, 'graph') and self.graph:
                # 노드 정보 표시
                nodes_df = pd.DataFrame({
                    "학생": list(self.graph.nodes()),
                    "연결 중심성(In)": [self.metrics["in_degree"].get(node, 0) for node in self.graph.nodes()],
                    "연결 중심성(Out)": [self.metrics["out_degree"].get(node, 0) for node in self.graph.nodes()],
                    "매개 중심성": [self.metrics["betweenness"].get(node, 0) for node in self.graph.nodes()],
                    "커뮤니티": [self.communities.get(node, -1) for node in self.graph.nodes()]
                })
                st.write("#### 노드 (학생) 정보")
                st.dataframe(nodes_df)
            
            return None
    
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
            
            # 한글 폰트 문제 확인 및 대응
            use_romanized = not self.has_korean_font
            
            if use_romanized:
                st.info("한글 폰트 문제로 인해 PyVis 네트워크에서 학생 이름이 영문으로 표시됩니다.")
            
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
                
                # 한글 폰트 문제가 있는 경우 로마자 변환
                if use_romanized:
                    display_label = self._get_display_label(node, use_romanized=True)
                else:
                    display_label = node
                
                # 노드 추가
                net.add_node(node, label=display_label, title=title, size=size, color=color)
            
            # 엣지 추가
            for edge in self.graph.edges(data=True):
                from_node, to_node, attr = edge
                weight = attr.get('weight', 1)
                
                # 엣지 너비 계산
                width = min(weight * 2, 10)  # 너비 상한선 10
                
                # 엣지 툴팁 텍스트
                if use_romanized:
                    from_label = self._get_display_label(from_node, use_romanized=True)
                    to_label = self._get_display_label(to_node, use_romanized=True)
                    title = f"{from_label} → {to_label}, 가중치: {weight}"
                else:
                    title = f"{from_node} → {to_node}, 가중치: {weight}"
                
                # 엣지 추가
                net.add_edge(from_node, to_node, title=title, width=width)
            
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
                },
                "edges": {
                    "smooth": {
                        "type": "continuous",
                        "forceDirection": "none"
                    }
                },
                "nodes": {
                    "font": {
                        "face": "arial",
                        "size": 14
                    }
                }
            }
            """)
            
            # 맵핑 테이블 표시 (한글 폰트 문제가 있는 경우)
            if use_romanized:
                # 매핑 테이블 생성
                node_names = list(self.graph.nodes())
                romanized_names = [self._get_display_label(node, use_romanized=True) for node in node_names]
                
                # 매핑 테이블 표시
                with st.expander("학생 이름 매핑 테이블 (PyVis)", expanded=False):
                    mapping_df = pd.DataFrame({
                        "영문 표시": romanized_names,
                        "원래 이름": node_names
                    })
                    st.dataframe(mapping_df)
            
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
            
            # 오류 발생 시 간단한 안내 메시지
            st.warning("인터랙티브 네트워크 그래프를 생성할 수 없습니다. 대신 Plotly 그래프를 사용해주세요.")
            
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
            
            # 한글 폰트 문제 확인 및 대응
            use_romanized = not self.has_korean_font
            
            if use_romanized:
                # 영문 변환된 노드 이름 사용
                display_nodes = [self._get_display_label(node, use_romanized=True) for node in nodes]
                # 원래 이름을 표시하기 위한 매핑 테이블
                name_map = {self._get_display_label(node, use_romanized=True): node for node in nodes}
                
                st.info("한글 폰트 문제로 인해 학생 이름이 영문으로 표시됩니다.")
                
                # 매핑 테이블 표시
                with st.expander("학생 이름 매핑 테이블", expanded=False):
                    mapping_df = pd.DataFrame({
                        "영문 표시": list(name_map.keys()),
                        "원래 이름": list(name_map.values())
                    })
                    st.dataframe(mapping_df)
            else:
                # 한글 폰트 사용 가능하면 원래 이름 사용
                display_nodes = nodes
            
            # matplotlib 그래프 생성
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(display_nodes, values, color='lightblue')
            
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
            
            # Plotly로 대체 그래프 생성 (한글 폰트 문제가 있는 경우)
            if use_romanized:
                # 원본 노드 이름 데이터
                original_nodes = nodes
                values_dict = {node: value for node, value in zip(original_nodes, values)}
                
                # 한글과 로마자 모두 표시하는 Plotly 그래프 생성
                fig_plotly = go.Figure()
                
                # 막대 그래프 추가
                fig_plotly.add_trace(go.Bar(
                    y=display_nodes,
                    x=values,
                    orientation='h',
                    marker_color='lightblue',
                    text=[f"{values_dict[original_node]:.3f}" for original_node in original_nodes],
                    textposition='outside',
                    hovertext=[f"{original_node}: {values_dict[original_node]:.3f}" for original_node in original_nodes]
                ))
                
                # 레이아웃 설정
                fig_plotly.update_layout(
                    title=f'상위 {top_n}명 학생의 {metric_names.get(metric, metric)} 지표',
                    xaxis_title=f'{metric} 중심성 지표',
                    yaxis_title='학생',
                    height=500,
                    width=700
                )
                
                # 플롯리 그래프 표시 (대체 방법)
                st.write("### Plotly로 생성한 대체 그래프")
                st.plotly_chart(fig_plotly)
            
            return fig
            
        except Exception as e:
            logger.error(f"중심성 지표 그래프 생성 실패: {str(e)}")
            # 대체 방법으로 데이터 테이블 표시
            st.error(f"그래프 생성 중 오류가 발생했습니다: {str(e)}")
            
            # 값 테이블로 대체 표시
            if 'metric_values' in locals() and 'sorted_values' in locals() and 'top_items' in locals():
                st.write("### 중심성 지표 데이터 (테이블)")
                
                # 상위 N개 항목 데이터프레임 생성
                df = pd.DataFrame({
                    "학생": [item[0] for item in top_items],
                    f"{metric} 값": [item[1] for item in top_items]
                })
                st.dataframe(df)
            
            return None
    
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
            
            # 한글 폰트 문제 확인 및 대응
            use_romanized = not self.has_korean_font
            
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
                
                # 한글 폰트 문제가 있으면 로마자 변환
                if use_romanized:
                    # 중심 학생 이름 변환
                    central_student_display = self._get_display_label(central_student, use_romanized=True)
                    
                    # 소속 학생 목록 변환
                    members_display = [self._get_display_label(m, use_romanized=True) for m in members]
                    members_str = ", ".join(members_display)
                    
                    # 원본 이름과 로마자 매핑 정보 표시
                    member_mapping = {self._get_display_label(m, use_romanized=True): m for m in members}
                    
                    data.append({
                        "커뮤니티 ID": comm_id,
                        "학생 수": len(members),
                        "소속 학생": members_str,
                        "중심 학생": central_student_display,
                        "중심 학생 연결성": f"{central_value:.3f}",
                        # 원본 이름 정보 저장
                        "학생 매핑": member_mapping
                    })
                else:
                    data.append({
                        "커뮤니티 ID": comm_id,
                        "학생 수": len(members),
                        "소속 학생": ", ".join(members),
                        "중심 학생": central_student,
                        "중심 학생 연결성": f"{central_value:.3f}"
                    })
            
            # 데이터프레임 생성
            df = pd.DataFrame(data)
            
            # 한글 폰트 문제가 있는 경우 매핑 테이블 표시
            if use_romanized:
                st.info("한글 폰트 문제로 인해 학생 이름이 영문으로 표시됩니다.")
                
                # 매핑 정보 표시
                with st.expander("학생 이름 매핑 테이블", expanded=False):
                    all_mappings = {}
                    for row in data:
                        all_mappings.update(row.get("학생 매핑", {}))
                    
                    mapping_df = pd.DataFrame({
                        "영문 표시": list(all_mappings.keys()),
                        "원래 이름": list(all_mappings.values())
                    })
                    st.dataframe(mapping_df)
                
                # 매핑 정보는 테이블에서 제거
                if "학생 매핑" in df.columns:
                    df = df.drop(columns=["학생 매핑"])
            
            return df
            
        except Exception as e:
            logger.error(f"커뮤니티 테이블 생성 실패: {str(e)}")
            st.error(f"커뮤니티 테이블 생성 중 오류가 발생했습니다: {str(e)}")
            return pd.DataFrame(columns=["커뮤니티 ID", "학생 수", "소속 학생", "중심 학생", "중심 학생 연결성"]) 