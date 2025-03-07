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

# matplotlib 경고 메시지 필터링 강화 - 모든 폰트 관련 경고 필터링
warnings.filterwarnings("ignore", "Glyph .* missing from current font")
warnings.filterwarnings("ignore", "findfont: Font family .* not found")
warnings.filterwarnings("ignore", category=UserWarning, module='matplotlib')
warnings.filterwarnings("ignore", category=UserWarning, module='plotly')
warnings.filterwarnings("ignore", category=UserWarning, module='pyvis')

# 로깅 설정 - 파일 핸들러 추가하여 로그를 화면에 출력하지 않고 파일로 저장
logging.basicConfig(level=logging.INFO, filename='network_analysis.log', filemode='w')
logger = logging.getLogger(__name__)
# 스트림 핸들러를 제거하여 콘솔에 출력되지 않도록 설정
logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.StreamHandler)]

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
            # 폰트 설정 없이 바로 리턴
            return
            
        # 운영체제별 폰트 설정 (로컬 환경)
        system = platform.system()
        if system == 'Darwin':  # macOS
            plt.rc('font', family='AppleGothic')
        elif system == 'Windows':  # Windows
            plt.rc('font', family='Malgun Gothic')
        else:  # Linux 등 (로컬에서만 설치 시도)
            # 로컬 리눅스인지 Streamlit Cloud인지 추가 확인
            if "STREAMLIT" in os.environ:
                return
                
            # 로컬 Linux 환경으로 판단
            # 이미 설치된 폰트 확인
            try:
                # 사용 가능한 시스템 폰트 확인
                font_list = [f.name for f in fm.fontManager.ttflist]
                
                # 한글 지원 가능한 폰트 후보
                korean_fonts = ['NanumGothic', 'NanumBarunGothic', 'Noto Sans CJK KR', 
                               'Noto Sans KR', 'Malgun Gothic', 'AppleGothic', 
                               'Dotum', 'Batang', 'UnDotum', 'Gulim']
                
                # 설치된 한글 폰트 찾기
                found_font = None
                for font in korean_fonts:
                    if any(font.lower() in f.lower() for f in font_list):
                        found_font = font
                        break
                
                if found_font:
                    plt.rc('font', family=found_font)
            except Exception:
                pass
        
        # 폰트 설정 확인
        plt.rc('axes', unicode_minus=False)  # 마이너스 기호 깨짐 방지
        
    except Exception:
        pass

# 한글 폰트 설정 시도
set_korean_font()

# 한글을 영문으로 변환하는 함수 (폰트 문제 대비)
def romanize_korean(text):
    """한글 이름을 영문으로 변환. 매핑 테이블은 가장 일반적인 발음 변환 규칙 사용"""
    # 한글 문자가 포함되지 않은 경우 원본 그대로 반환
    if not any(ord('가') <= ord(char) <= ord('힣') for char in text):
        return text
        
    # 공백으로 나누어진 경우(이름과 정보가 함께 있는 경우)
    if ' ' in text:
        parts = text.split(' ', 1)
        name = parts[0]
        info = ' ' + parts[1] if len(parts) > 1 else ''
        return romanize_korean(name) + info
        
    # 성씨 딕셔너리 - 한글 성씨를 로마자 표기로 변환 (대표적인 성씨만 포함)
    surnames = {
        '김': 'Kim', '이': 'Lee', '박': 'Park', '최': 'Choi', '정': 'Jung', 
        '강': 'Kang', '조': 'Jo', '윤': 'Yoon', '장': 'Jang', '임': 'Lim',
        '오': 'Oh', '한': 'Han', '신': 'Shin', '서': 'Seo', '권': 'Kwon',
        '황': 'Hwang', '안': 'Ahn', '송': 'Song', '전': 'Jeon', '홍': 'Hong',
        '유': 'Yoo', '고': 'Ko', '문': 'Moon', '양': 'Yang', '손': 'Son',
        '배': 'Bae', '백': 'Baek', '허': 'Heo', '노': 'Noh', '심': 'Shim',
        '하': 'Ha', '전': 'Jeon', '곽': 'Kwak', '성': 'Sung', '차': 'Cha',
        '주': 'Joo', '우': 'Woo', '구': 'Koo', '나': 'Na', '민': 'Min',
        '유': 'Yoo', '진': 'Jin', '지': 'Ji', '엄': 'Uhm', '편': 'Pyeon'
    }
    
    # 이름이 1글자인 경우 (특수한 처리가 필요한 경우)
    if len(text) == 1:
        return f"Student-{hash(text) % 1000:03d}"
    
    # 2글자 이상인 이름 처리
    surname = text[0]  # 성씨는 첫 글자로 가정
    given_name = text[1:]  # 이름은 나머지 부분
    
    # 매핑 테이블에 있는 성씨면 변환, 없으면 첫 글자를 'S'로 표현
    if surname in surnames:
        romanized = f"{surnames[surname]} {given_name}"
    else:
        # 매핑되지 않은 성씨는 간단한 해시값으로 학생 ID 생성
        romanized = f"Student-{hash(text) % 1000:03d}"
    
    return romanized

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
        if is_streamlit_cloud() or "STREAMLIT" in os.environ:
            logger.warning("Streamlit 환경에서는 한글 폰트를 사용할 수 없습니다. 영문 표기로 대체합니다.")
            return False
        
        try:
            # 한글 문자로 실제 렌더링 테스트
            test_str = "한글"
            fig, ax = plt.subplots(figsize=(1, 1))
            
            # 경고 캡처를 위한 설정
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                ax.text(0.5, 0.5, test_str, fontsize=12)
                plt.savefig(BytesIO())  # 실제 렌더링 강제
                plt.close(fig)
                
                # 폰트 관련 경고가 있는지 확인
                for warning in w:
                    warning_msg = str(warning.message)
                    if "missing from current font" in warning_msg or "not found" in warning_msg:
                        logger.warning("한글 폰트 렌더링 중 문제 발생: 한글 폰트를 찾을 수 없습니다.")
                        logger.warning("노드 레이블을 영문으로 변환합니다.")
                        return False
            
            # 경고가 없으면 한글 폰트 사용 가능으로 판단
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
            # 노드 정보 준비
            node_x = []
            node_y = []
            node_text = []  # 노드 텍스트 (한글 이름 또는 로마자화된 이름)
            node_size = []  # 노드 크기
            node_color = []  # 노드 색상
            
            # 그래프 레이아웃 계산
            if layout == "spring":
                pos = nx.spring_layout(self.graph)
            elif layout == "circular":
                pos = nx.circular_layout(self.graph)
            elif layout == "kamada":
                pos = nx.kamada_kawai_layout(self.graph)
            else:  # fruchterman
                pos = nx.fruchterman_reingold_layout(self.graph)
            
            # 노드 중심성 및 커뮤니티 값 가져오기
            in_degree = self.metrics.get('in_degree', {})
            communities = self.communities
            
            # 노드 색상 팔레트 설정 (색약자를 위한 색상)
            color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                             '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            # 노드 데이터 구성
            for node in self.graph.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                
                # 노드 텍스트 (이름) 설정
                display_name = self._get_display_label(node)
                node_text.append(f"이름: {display_name}")
                
                # 노드 크기 설정: 연결 중심성(In)에 비례
                size = in_degree.get(node, 0) * 10 + 10  # 기본 크기 10, 연결 중심성에 따라 증가
                node_size.append(size)
                
                # 노드 색상 설정: 커뮤니티에 따라
                if node in communities:
                    node_color.append(color_palette[communities[node] % len(color_palette)])
                else:
                    node_color.append('#7f7f7f')  # 기본 회색
            
            # 에지(연결선) 정보 준비
            edge_x = []
            edge_y = []
            edge_width = []
            
            # 에지 데이터 구성
            for edge in self.graph.edges(data=True):
                source, target = edge[0], edge[1]
                x0, y0 = pos[source]
                x1, y1 = pos[target]
                
                # 곡선 에지를 위한 중간점 계산
                edge_x.append(x0)
                edge_x.append(x1)
                edge_x.append(None)  # 선 구분을 위한 None
                edge_y.append(y0)
                edge_y.append(y1)
                edge_y.append(None)  # 선 구분을 위한 None
                
                # 에지 두께 설정: 가중치에 비례
                weight = edge[2].get('weight', 1)
                edge_width.append(weight)
            
            # 에지 트레이스 생성
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1, color='#888'),
                hoverinfo='none',
                mode='lines',
                showlegend=False
            )
            
            # 노드 트레이스 생성
            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                hoverinfo='text',
                text=node_text,
                marker=dict(
                    color=node_color,
                    size=node_size,
                    line=dict(width=1, color='#888')
                ),
                showlegend=False
            )
            
            # 레이아웃 및 그래프 생성
            layout_config = dict(
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=60),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                width=width,
                height=height,
                title='학급 관계 네트워크 그래프<br><span style="font-size:12px;">크기: 인기도(선택받은 횟수) | 색상: 같은 그룹</span>'
            )
            
            fig = go.Figure(data=[edge_trace, node_trace], layout=layout_config)
            
            return fig
            
        except Exception as e:
            st.error(f"네트워크 그래프 생성 중 오류가 발생했습니다: {str(e)}")
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
        """중심성 지표 시각화"""
        try:
            # 지표 선택
            if metric not in self.metrics:
                st.error(f"요청한 중심성 지표({metric})가 존재하지 않습니다.")
                return None
            
            # 선택된 지표 값 가져오기
            metric_values = self.metrics[metric]
            
            # 데이터프레임 변환 및 정렬
            df = pd.DataFrame(metric_values.items(), columns=['이름', '값'])
            df = df.sort_values('값', ascending=False).head(top_n)
            
            # 표시 이름 변환
            if not self.has_korean_font:
                df['표시이름'] = df['이름'].apply(lambda x: self._get_display_label(x))
            else:
                df['표시이름'] = df['이름']
            
            # 그래프 생성
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(df['표시이름'], df['값'], color='skyblue')
            
            # 그래프 스타일링
            ax.set_xlabel('중심성 지표 값')
            
            # 중심성 지표별 적절한 제목 설정
            metric_titles = {
                'in_degree': '인기도 (선택받은 횟수)',
                'out_degree': '친밀도 (선택한 횟수)',
                'betweenness': '중재자 역할',
                'closeness': '정보 접근성'
            }
            title = metric_titles.get(metric, metric)
            ax.set_title(f'상위 {top_n}명 학생의 {title}')
            
            # 값 주석 추가
            for bar in bars:
                width = bar.get_width()
                ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                        f'{width:.2f}', va='center')
            
            # 범례 추가 - 원본 이름과 표시 이름을 표시
            if not self.has_korean_font and len(df) > 0:
                legend_text = "학생 이름 참조표:\n"
                for _, row in df.iterrows():
                    orig_name = row['이름']
                    disp_name = row['표시이름']
                    if orig_name != disp_name:
                        legend_text += f"{disp_name} = {orig_name}\n"
                plt.figtext(0.5, 0.01, legend_text, ha="center", fontsize=9, 
                           bbox={"facecolor":"lightgrey", "alpha":0.5, "pad":5})
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            st.error(f"중심성 지표 시각화 중 오류가 발생했습니다: {str(e)}")
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