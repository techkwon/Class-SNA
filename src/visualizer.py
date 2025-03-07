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
import subprocess

# 모든 matplotlib, plotly 경고 완전히 비활성화
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", "Glyph .* missing from current font")
warnings.filterwarnings("ignore", "findfont: Font family .* not found")
warnings.filterwarnings("ignore", "Substituting symbol .* form .* font")
warnings.filterwarnings("ignore", "No contour levels were found")
warnings.filterwarnings("ignore", "The PostScript backend does not support transparency")

# 로깅 설정 - 경고 레벨을 ERROR로 상향 조정하여 WARNING 메시지 숨김
logging.basicConfig(level=logging.ERROR, filename='network_analysis.log', filemode='w')
logger = logging.getLogger(__name__)
# 스트림 핸들러를 제거하여 콘솔에 출력되지 않도록 설정
logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.StreamHandler)]

# Streamlit Cloud 환경인지 확인하는 함수
def is_streamlit_cloud():
    """Streamlit Cloud 환경인지 확인"""
    return os.getenv("STREAMLIT_RUNTIME") is not None or os.getenv("STREAMLIT_RUN_ON_SAVE") is not None

# 전역 변수로 한글 폰트 사용 가능 여부 설정 - 기본값은 False로 설정하여 항상 로마자 사용
HAS_KOREAN_FONT = False

# 시스템에 설치된 한글 폰트 목록 확인
def get_korean_fonts():
    """시스템에 설치된 한글 폰트 목록 확인"""
    global HAS_KOREAN_FONT
    
    korean_fonts = []
    try:
        # Linux 환경에서 fc-list 명령어 사용
        if platform.system() == 'Linux':
            try:
                # 한글 폰트 목록 확인
                result = subprocess.run(['fc-list', ':lang=ko'], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    # 폰트 이름 추출
                    font_name = line.split(':')[1].strip().split(',')[0] if ':' in line else ''
                    if font_name and font_name not in korean_fonts:
                        korean_fonts.append(font_name)
            except Exception as e:
                # fc-list 명령 실패 - 명령어가 없거나 실행 권한 없음
                pass
                
        # Windows 환경에서의 한글 폰트 목록 (일반적인 한글 폰트 이름)
        elif platform.system() == 'Windows':
            common_korean_fonts = ['Malgun Gothic', '맑은 고딕', 'Gulim', '굴림', 'Batang', '바탕', 'Dotum', '돋움']
            for font in fm.findSystemFonts():
                try:
                    font_name = fm.FontProperties(fname=font).get_name()
                    if font_name in common_korean_fonts:
                        korean_fonts.append(font_name)
                except:
                    pass
                    
        # macOS 환경에서의 한글 폰트 목록
        elif platform.system() == 'Darwin':
            common_korean_fonts = ['AppleGothic', 'AppleMyungjo', 'NanumGothic', 'NanumMyungjo']
            for font in fm.findSystemFonts():
                try:
                    font_name = fm.FontProperties(fname=font).get_name()
                    if font_name in common_korean_fonts:
                        korean_fonts.append(font_name)
                except:
                    pass
        
        if korean_fonts:
            HAS_KOREAN_FONT = True
        
        return korean_fonts
    
    except Exception as e:
        # 모든 예외 처리
        return []

# 한글 폰트 설치 안내 (Streamlit UI)
def show_korean_font_installation_guide():
    """한글 폰트 설치 방법 안내"""
    with st.sidebar.expander("💡 한글 폰트 설치 안내", expanded=False):
        st.markdown("""
        ### 📋 한글 폰트 설치 방법
        
        **Ubuntu/Debian Linux**:
        ```bash
        sudo apt-get update
        sudo apt-get install fonts-nanum
        fc-cache -fv
        ```
        
        **macOS**:
        - [나눔글꼴 다운로드](https://hangeul.naver.com/font) 후 설치
        
        **Windows**:
        - 이미 기본 한글 폰트가 설치되어 있습니다.
        
        설치 후 앱을 새로고침하세요.
        """)

# 한글 폰트 설정 함수 - 항상 동작하도록 개선
def set_korean_font():
    """시스템에 설치된 한글 폰트 확인 및 설정"""
    global HAS_KOREAN_FONT
    
    # Streamlit Cloud 환경인 경우
    if is_streamlit_cloud():
        # 클라우드 환경에서는 로마자 사용
        HAS_KOREAN_FONT = False
        
        # 조용히 실패하기
        try:
            plt.rcParams['font.family'] = 'DejaVu Sans'
        except:
            pass
            
        return False
        
    # 이미 폰트를 확인한 경우
    if HAS_KOREAN_FONT:
        return True
        
    # 한글 폰트 목록 확인
    korean_fonts = get_korean_fonts()
    
    # 한글 폰트가 있는 경우
    if korean_fonts:
        font_name = korean_fonts[0]
        try:
            plt.rcParams['font.family'] = font_name
            HAS_KOREAN_FONT = True
            return True
        except:
            pass
    
    # 대체 폰트 시도
    for font in ['NanumGothic', 'Malgun Gothic', 'AppleGothic', 'Gulim', 'Arial Unicode MS']:
        try:
            plt.rcParams['font.family'] = font
            HAS_KOREAN_FONT = True
            return True
        except:
            pass
    
    # 시스템 기본 폰트 사용
    try:
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
    except:
        pass
    
    # 폰트 안내 출력하지 않음 - 사용자 경험 향상을 위해
    HAS_KOREAN_FONT = False
    return False

# PyVis 네트워크에 한글 폰트 적용 (폰트 없이도 작동하도록 개선)
def apply_korean_font_to_pyvis(net):
    """PyVis 네트워크에 한글 폰트 적용"""
    # HTML 템플릿에 웹 폰트 추가 (구글 폰트 CDN 사용)
    net.html = net.html.replace('<head>', '''<head>
        <link href="https://fonts.googleapis.com/css2?family=Nanum+Gothic&display=swap" rel="stylesheet">
    ''')
    
    # CSS에 폰트 설정 추가
    net.html = net.html.replace('</style>', '''
        body { font-family: 'Nanum Gothic', sans-serif; }
        .node text { font-family: 'Nanum Gothic', sans-serif; }
        div.tooltip { font-family: 'Nanum Gothic', sans-serif; }
    </style>''')
    
    return net

# 한글 로마자 변환 함수 - 성능 개선
SURNAMES = {
    '김': 'Kim', '이': 'Lee', '박': 'Park', '최': 'Choi', '정': 'Jung', 
    '강': 'Kang', '조': 'Jo', '윤': 'Yoon', '장': 'Jang', '임': 'Lim', 
    '한': 'Han', '오': 'Oh', '서': 'Seo', '신': 'Shin', '권': 'Kwon',
    '황': 'Hwang', '안': 'An', '송': 'Song', '전': 'Jeon', '홍': 'Hong',
    '유': 'Yoo', '고': 'Ko', '문': 'Moon', '양': 'Yang', '손': 'Son',
    '배': 'Bae', '백': 'Baek', '방': 'Bang', '노': 'No', '남': 'Nam',
    '류': 'Ryu', '심': 'Sim', '허': 'Heo', '원': 'Won', '전': 'Jeon',
    '천': 'Chun', '추': 'Chu', '동': 'Dong', '곽': 'Kwak', '금': 'Keum',
    '주': 'Joo', '선': 'Sun', '구': 'Koo', '민': 'Min', '성': 'Sung',
    '탁': 'Tak', '설': 'Seol', '길': 'Gil', '온': 'On', '경': 'Kyung',
    '연': 'Yeon', '울': 'Ul', '제': 'Je', '태': 'Tae', '빈': 'Bin',
    '라': 'Ra', '사': 'Sa', '상': 'Sang', '소': 'So', '채': 'Chae',
    '지': 'Ji', '진': 'Jin', '육': 'Yook', '필': 'Pil', '하': 'Ha',
    '감': 'Kam'
}

def romanize_korean(text):
    """한글 이름을 로마자로 변환"""
    if not text:
        return "Unknown"
        
    # 정수 또는 부동소수점 처리
    if isinstance(text, (int, float)):
        return str(text)
    
    # 이미 알파벳인 경우 그대로 반환
    if re.match(r'^[A-Za-z0-9_]+$', str(text)):
        return str(text)
    
    # 단일 문자인 경우 학생 번호로 처리
    if len(str(text)) == 1 and re.match(r'[가-힣]', str(text)):
        hash_val = hash(text) % 1000
        return f"Student-{hash_val}"
    
    try:
        # 성씨 추출 (첫 글자)
        surname = text[0]
        given_name = text[1:]
        
        # 성씨 변환
        if surname in SURNAMES:
            romanized_surname = SURNAMES[surname]
        else:
            # 알 수 없는 성씨
            hash_val = hash(text) % 1000
            return f"Student-{hash_val}"
        
        # 이름은 그대로 유지 (이름 글자별 변환은 복잡함)
        # 실제로는 각 글자별로 발음에 따라 변환해야 하지만, 여기서는 단순화
        
        return f"{romanized_surname} {given_name}"
    except:
        # 변환 실패 시
        return f"Student-{hash(str(text)) % 1000}"

class NetworkVisualizer:
    """네트워크 그래프 시각화 클래스"""
    
    def __init__(self, analyzer):
        """NetworkAnalyzer 객체를 받아 초기화"""
        self.analyzer = analyzer
        self.graph = analyzer.graph
        
        # 한글 폰트 설정 및 확인
        set_korean_font()
        
        # 폰트 확인을 한 번만 실행하고 결과를 저장 (경고 메시지 중복 방지)
        if 'has_korean_font' in st.session_state:
            self.has_korean_font = st.session_state['has_korean_font']
        else:
            self.has_korean_font = self._check_korean_font()
            st.session_state['has_korean_font'] = self.has_korean_font
        
        # Streamlit Cloud 환경에서는 자동으로 로마자화 사용 (경고 메시지 중복 방지)
        if is_streamlit_cloud() and self.has_korean_font:
            self.has_korean_font = False
            st.session_state['has_korean_font'] = False
            
        # 노드 이름 매핑 (원래 이름 -> 로마자화된 이름)
        self.name_mapping = {}
        if not self.has_korean_font:
            for node in self.graph.nodes():
                self.name_mapping[node] = romanize_korean(node)
        
        self.communities = analyzer.communities
        self.metrics = analyzer.metrics
    
    def _check_korean_font(self):
        """한글 폰트 점검 - 항상 False 반환하여 로마자화 사용"""
        # 항상 로마자 이름 사용하도록 False 반환
        return False
    
    def _get_display_label(self, node_name, use_romanized=True):
        """노드 표시 라벨 반환 - 항상 로마자화된 이름 사용"""
        # 항상 로마자화 사용
        return romanize_korean(node_name)
    
    def create_plotly_network(self, layout="fruchterman", width=900, height=700):
        """Plotly를 사용한 네트워크 그래프 생성"""
        try:
            if not hasattr(self, 'analyzer') or not self.analyzer or not hasattr(self.analyzer, 'graph'):
                # 분석기나 그래프가 없는 경우 빈 그래프 반환
                fig = go.Figure()
                fig.add_annotation(text="데이터가 없습니다", showarrow=False, font=dict(size=20))
                fig.update_layout(width=width, height=height)
                return fig
            
            G = self.analyzer.graph
            
            if G is None or G.number_of_nodes() == 0:
                # 그래프가 비어 있는 경우 빈 그래프 반환
                fig = go.Figure()
                fig.add_annotation(text="네트워크 데이터가 없습니다", showarrow=False, font=dict(size=20))
                fig.update_layout(width=width, height=height)
                return fig
            
            # 레이아웃 알고리즘 선택 및 포지션 계산
            if layout == "circular":
                pos = nx.circular_layout(G)
            elif layout == "spring":
                pos = nx.spring_layout(G, seed=42)
            elif layout == "kamada":
                pos = nx.kamada_kawai_layout(G)
            elif layout == "spectral":
                pos = nx.spectral_layout(G)
            else:
                # 기본값: fruchterman_reingold
                pos = nx.fruchterman_reingold_layout(G, seed=42)
            
            # 노드 크기 결정 (인입 연결 수 기준)
            node_size = []
            for node in G.nodes():
                try:
                    # 인입 연결 수 + 1 (0이 되지 않도록)
                    size = G.in_degree(node) + 1
                    node_size.append(size * 10)  # 크기 조정
                except:
                    # 오류 발생 시 기본 크기 사용
                    node_size.append(10)
            
            # 노드 색상 설정 (커뮤니티 기준)
            node_color = []
            
            # 커뮤니티 정보 확인
            communities = None
            if hasattr(self.analyzer, 'communities') and self.analyzer.communities:
                communities = self.analyzer.communities
            
            # 색상 팔레트 설정
            color_palette = px.colors.qualitative.Set3 if 'px' in globals() else [
                '#8dd3c7', '#ffffb3', '#bebada', '#fb8072', '#80b1d3', 
                '#fdb462', '#b3de69', '#fccde5', '#d9d9d9', '#bc80bd',
                '#ccebc5', '#ffed6f'
            ]
            
            if communities:
                # 커뮤니티 정보가 있으면 색상 설정
                for node in G.nodes():
                    try:
                        comm_id = communities.get(node, 0)
                        color_idx = comm_id % len(color_palette)
                        node_color.append(color_palette[color_idx])
                    except:
                        # 오류 발생 시 기본 색상 사용
                        node_color.append('#cccccc')
            else:
                # 커뮤니티 정보가 없으면 기본 색상 사용
                node_color = ['#1f77b4'] * G.number_of_nodes()
            
            # 엣지 데이터 준비
            edge_x = []
            edge_y = []
            
            # 엣지 그리기
            for edge in G.edges():
                try:
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                except Exception as e:
                    # 엣지 그리기 오류 무시
                    continue
            
            # 엣지 트레이스 생성
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=0.5, color='#888'),
                hoverinfo='none',
                mode='lines'
            )
            
            # 노드 데이터 준비
            node_x = []
            node_y = []
            node_text = []
            
            # 노드 좌표 및 텍스트 설정
            for i, node in enumerate(G.nodes()):
                try:
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)
                    
                    # 한글 폰트 문제 확인
                    use_romanized = not hasattr(self, 'has_korean_font') or not self.has_korean_font
                    
                    # 노드 레이블 설정
                    if 'label' in G.nodes[node]:
                        label = G.nodes[node]['label']
                    elif hasattr(self, '_get_display_label'):
                        label = self._get_display_label(node, use_romanized)
                    else:
                        label = str(node)
                    
                    # 노드 정보 생성
                    info = f"이름: {label}<br>"
                    info += f"연결 수: {G.degree(node)}<br>"
                    
                    # 중심성 정보 추가
                    if hasattr(self, 'metrics') and self.metrics:
                        if 'in_degree' in self.metrics and node in self.metrics['in_degree']:
                            in_degree = self.metrics['in_degree'][node]
                            info += f"인기도: {in_degree:.3f}<br>"
                        
                        if 'betweenness' in self.metrics and node in self.metrics['betweenness']:
                            betweenness = self.metrics['betweenness'][node]
                            info += f"매개 중심성: {betweenness:.3f}<br>"
                    
                    # 커뮤니티 정보 추가
                    if communities and node in communities:
                        comm_id = communities[node]
                        info += f"그룹: {comm_id}"
                    
                    node_text.append(info)
                except Exception as e:
                    # 노드 처리 오류 시 기본값 사용
                    node_x.append(0)
                    node_y.append(0)
                    node_text.append(f"Error: {str(e)}")
            
            # 노드 트레이스 생성 (크기와 색상 적용)
            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                hoverinfo='text',
                text=node_text,
                marker=dict(
                    showscale=False,
                    color=node_color,
                    size=node_size,
                    line=dict(width=1, color='#888')
                )
            )
            
            # 그래프 생성
            fig = go.Figure(
                data=[edge_trace, node_trace],
                layout=go.Layout(
                    title='학급 관계 네트워크',
                    titlefont=dict(size=16),
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20, l=5, r=5, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    width=width,
                    height=height
                )
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"네트워크 시각화 생성 중 오류: {str(e)}")
            # 오류 발생 시 빈 그래프 반환
            fig = go.Figure()
            fig.add_annotation(text=f"시각화 생성 오류: {str(e)}", showarrow=False, font=dict(size=12, color="red"))
            fig.update_layout(width=width, height=height)
            return fig
    
    def create_pyvis_network(self, height="600px", width="100%"):
        """PyVis를 사용하여 인터랙티브 네트워크 시각화를 생성합니다 (영문 이름 표시)"""
        # 네트워크 초기화 (물리적 레이아웃 개선)
        net = Network(height=height, width=width, directed=True, notebook=False)
        net.toggle_hide_edges_on_drag(True)
        net.barnes_hut(gravity=-10000, central_gravity=0.4, spring_length=300, spring_strength=0.08, damping=0.15)
        
        # 노드와 엣지 데이터 가져오기
        nodes = self.analyzer.get_nodes()
        edges = self.analyzer.get_edges()
        
        # 스트림릿에 안내 메시지 표시 (한글)
        st.info("⚠️ 상호작용 네트워크에서는 한글 표시 문제를 방지하기 위해 영문 이름으로 표시됩니다.")
        
        # 이름 매핑 생성 (원본 → 로마자화)
        name_mapping = {}
        for node_name in nodes:
            romanized = romanize_korean(node_name)
            name_mapping[romanized] = node_name
        
        # 매핑 테이블 생성 (펼침/접기 가능한 섹션으로) - 한글
        with st.expander("👁️ 한글 이름과 영문 표기 대응표 보기"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**원본 이름**")
                for original in sorted(name_mapping.values()):
                    st.write(original)
            
            with col2:
                st.markdown("**영문 표기**")
                for original in sorted(name_mapping.values()):
                    st.write(romanize_korean(original))
        
        # 컬러 매핑 설정 (더 선명한 색상으로 변경)
        colors = self.analyzer.get_community_colors()
        
        # 더 선명한 색상 팔레트로 업데이트
        vibrant_colors = {
            0: "#4285F4",  # 구글 블루
            1: "#EA4335",  # 구글 레드
            2: "#34A853",  # 구글 그린
            3: "#FBBC05",  # 구글 옐로우
            4: "#8E24AA",  # 퍼플
            5: "#16A085"   # 터콰이즈
        }
        
        # 중심성 계산 (노드 크기 조정에 사용)
        centrality = self.analyzer.get_centrality_metrics()
        
        # 커뮤니티 정보 가져오기
        communities = self.analyzer.get_communities()
        
        # 노드 정보 설정
        for i, node_name in enumerate(nodes):
            # 항상 로마자 이름으로 표시
            romanized_name = romanize_korean(node_name)
            
            # 크기 설정 (정규화된 중심성 기반으로 더 명확한 차이 부여)
            size = 25 + centrality['in_degree'][node_name] * 75
            if size > 65:
                size = 65
            
            # 커뮤니티 정보 가져오기
            community_id = None
            for comm_id, members in communities.items():
                if node_name in members:
                    community_id = comm_id
                    break
            
            # 선명한 색상 적용
            if community_id is not None and community_id in vibrant_colors:
                color = vibrant_colors[community_id]
            else:
                color = "#607D8B"  # 기본 색상
            
            # 툴팁 정보 구성 (한글로 표시, 내부는 영문 사용)
            tooltip = f"이름: {node_name}\n"  # <br> 대신 \n 사용
            tooltip += f"그룹: {community_id}\n"
            tooltip += f"인기도(In): {self.analyzer.graph.in_degree(node_name)}\n"
            tooltip += f"친밀도(Out): {self.analyzer.graph.out_degree(node_name)}"
            
            # 노드 추가 (로마자 이름으로 내부 처리) - 그림자 및 테두리 효과 추가
            net.add_node(romanized_name, 
                         label=romanized_name, 
                         title=tooltip, 
                         size=size, 
                         color=color,
                         borderWidth=2,
                         borderWidthSelected=4,
                         shadow=True)
        
        # 엣지 추가 (원래 이름이 로마자 이름으로 변경된 것 반영)
        for source, target, weight in edges:
            romanized_source = romanize_korean(source)
            romanized_target = romanize_korean(target)
            
            # 툴팁 한글로 표시
            edge_tooltip = f"관계: {source} → {target}\n강도: {weight}"  # <br> 대신 \n 사용
            
            # 엣지 굵기를 가중치에 따라 조정하여 더 명확하게 표시
            edge_width = 1 + weight * 2
            
            net.add_edge(romanized_source, romanized_target, 
                         value=weight, 
                         title=edge_tooltip,
                         width=edge_width,
                         arrowStrikethrough=True,
                         smooth={
                             'type': 'curvedCW',
                             'roundness': 0.2
                         })
        
        # 폰트 및 스타일 적용
        net = apply_korean_font_to_pyvis(net)
        
        # HTML 직접 반환 (파일에 저장하지 않음)
        html = net.generate_html()
        
        # 노드 클릭 이벤트 처리를 위한 JavaScript 추가
        html = html.replace("</body>", """
        <script>
        // 네트워크 모듈이 로드된 후 실행
        document.addEventListener('DOMContentLoaded', function() {
            // 네트워크 객체가 초기화될 때까지 기다림
            var checkExist = setInterval(function() {
                if (typeof network !== 'undefined') {
                    clearInterval(checkExist);
                    
                    // 네트워크 옵션 개선 (시각성 및 사용성 향상)
                    network.setOptions({
                        nodes: {
                            font: {
                                size: 16,
                                strokeWidth: 4,
                                strokeColor: 'rgba(255, 255, 255, 0.8)'
                            },
                            scaling: {
                                label: true
                            },
                            shadow: {
                                enabled: true,
                                color: 'rgba(0,0,0,0.3)',
                                size: 10,
                                x: 5,
                                y: 5
                            }
                        },
                        edges: {
                            color: {
                                inherit: false,
                                color: '#999999',
                                highlight: '#FF3333',
                                hover: '#3388FF'
                            },
                            selectionWidth: 3,
                            hoverWidth: 2,
                            arrows: {
                                to: {
                                    enabled: true,
                                    scaleFactor: 0.7,
                                    type: "arrow"
                                }
                            },
                            smooth: true
                        },
                        interaction: {
                            hover: true,
                            tooltipDelay: 100,
                            zoomView: true,
                            dragView: true,
                            navigationButtons: true,
                            keyboard: true
                        },
                        physics: {
                            stabilization: {
                                enabled: true,
                                iterations: 1000,
                                updateInterval: 50
                            }
                        }
                    });
                    
                    // 클릭 이벤트 리스너 추가
                    network.on("click", function(params) {
                        if (params.nodes.length > 0) {
                            var nodeId = params.nodes[0];
                            if (nodeId) {
                                try {
                                    // 선택한 노드 강조 표시
                                    var selectedNode = nodes.get(nodeId);
                                    selectedNode.borderWidth = 4;
                                    selectedNode.size = selectedNode.size * 1.2;
                                    nodes.update(selectedNode);
                                    
                                    // Streamlit과 통신
                                    window.parent.postMessage({
                                        type: 'streamlit:setComponentValue',
                                        value: {action: 'node_click', node: nodeId}
                                    }, '*');
                                } catch (err) {
                                    console.error("노드 클릭 처리 중 오류 발생:", err);
                                }
                            }
                        }
                    });
                    
                    // 마우스 오버 이벤트 처리 (노드 강조 효과)
                    network.on("hoverNode", function(params) {
                        network.canvas.body.container.style.cursor = 'pointer';
                        
                        // 현재 노드와 연결된 노드만 강조
                        var nodeId = params.node;
                        var connectedNodes = network.getConnectedNodes(nodeId);
                        connectedNodes.push(nodeId); // 자신도 포함
                        
                        // 연결된 노드와 엣지만 표시
                        var updateArray = [];
                        for (var i in allNodes) {
                            var isConnected = connectedNodes.indexOf(i) !== -1;
                            if (isConnected) {
                                allNodes[i].color = nodeColors[i];
                                allNodes[i].borderWidth = 3;
                                allNodes[i].shadow = true;
                                allNodes[i].font = {
                                    color: '#000000',
                                    size: 18,
                                    strokeWidth: 4,
                                    strokeColor: 'rgba(255, 255, 255, 0.8)'
                                };
                            } else {
                                allNodes[i].color = 'rgba(200,200,200,0.2)';
                                allNodes[i].borderWidth = 1;
                                allNodes[i].shadow = false;
                                allNodes[i].font = {
                                    color: '#888888',
                                    size: 14
                                };
                            }
                            updateArray.push(allNodes[i]);
                        }
                        nodes.update(updateArray);
                        
                        // 연결된 엣지 강조
                        var updateEdges = [];
                        for (var i in allEdges) {
                            var edge = allEdges[i];
                            if (edge.from === nodeId || edge.to === nodeId) {
                                edge.color = 'rgba(50, 50, 200, 1)';
                                edge.width = 3;
                                edge.shadow = true;
                            } else {
                                edge.color = 'rgba(200,200,200,0.2)';
                                edge.width = 1;
                                edge.shadow = false;
                            }
                            updateEdges.push(edge);
                        }
                        edges.update(updateEdges);
                    });
                    
                    // 마우스 오버 해제 이벤트 처리
                    network.on("blurNode", function(params) {
                        network.canvas.body.container.style.cursor = 'default';
                        
                        // 원래 상태로 복원
                        var updateArray = [];
                        for (var i in allNodes) {
                            allNodes[i].color = nodeColors[i];
                            allNodes[i].borderWidth = 2;
                            allNodes[i].shadow = true;
                            allNodes[i].font = {
                                color: '#000000',
                                size: 16,
                                strokeWidth: 4,
                                strokeColor: 'rgba(255, 255, 255, 0.8)'
                            };
                            updateArray.push(allNodes[i]);
                        }
                        nodes.update(updateArray);
                        
                        // 엣지도 원래 상태로 복원
                        var updateEdges = [];
                        for (var i in allEdges) {
                            var edge = allEdges[i];
                            edge.color = 'rgba(100,100,100,0.8)';
                            edge.width = edge.value ? 1 + edge.value * 2 : 1;
                            edge.shadow = false;
                            updateEdges.push(edge);
                        }
                        edges.update(updateEdges);
                    });
                    
                    // 레이아웃 안정화 후 살짝 확대하여 전체 그래프 보이게 함
                    network.once('stabilizationIterationsDone', function() {
                        setTimeout(function() {
                            network.fit({
                                animation: {
                                    duration: 1000,
                                    easingFunction: 'easeOutQuint'
                                }
                            });
                        }, 500);
                    });
                }
            }, 100);
        });
        </script>
        </body>""")
        
        # 커스텀 CSS 스타일 추가 (툴팁 스타일 개선)
        html = html.replace("<style>", """<style>
        .vis-tooltip {
            position: absolute;
            visibility: hidden;
            padding: 10px 12px;
            white-space: pre-wrap !important;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: black;
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 6px;
            border: 1px solid #cccccc;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
            pointer-events: none;
            z-index: 10;
            max-width: 300px;
            transition: all 0.2s ease;
        }
        
        /* 태그가 표시되지 않도록 스타일 설정 */
        .vis-tooltip br, .vis-network-tooltip br {
            display: block;
            margin-top: 5px;
        }
        
        #mynetwork {
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            border-radius: 8px !important;
            overflow: hidden;
            border: 1px solid #e0e0e0 !important;
        }
        """)
        
        # 태그를 처리하기 위한 JavaScript 추가 (tooltip 문자열 치환)
        html = html.replace('function drawGraph() {', '''function drawGraph() {
            // 툴팁 태그 처리 함수 정의
            function formatTooltip(tooltip) {
                // <br> 태그를 줄바꿈으로 변환
                if (tooltip) {
                    // \\u003c 는 < 의 유니코드 이스케이프 시퀀스
                    tooltip = tooltip.replace(/\\u003cbr\\u003e/g, "\\n");
                    tooltip = tooltip.replace(/<br>/g, "\\n");
                }
                return tooltip;
            }
            
            // 원래 vis.DataSet을 확장하여 툴팁 처리
            var originalDataSet = vis.DataSet;
            vis.DataSet = function(data, options) {
                if (data) {
                    // 노드 데이터 처리
                    for (var i = 0; i < data.length; i++) {
                        if (data[i].title) {
                            data[i].title = formatTooltip(data[i].title);
                        }
                    }
                }
                return new originalDataSet(data, options);
            };
        ''')
        
        return html
    
    def create_centrality_plot(self, metric="in_degree", top_n=10):
        """중심성 지표 시각화 (내부 처리는 영문, 표시는 한글)"""
        try:
            # 지표 선택
            if metric not in self.metrics:
                st.error(f"요청한 중심성 지표({metric})가 존재하지 않습니다.")
                return None
            
            # 선택된 지표 값 가져오기
            metric_values = self.metrics[metric]
            
            # 데이터프레임 변환 및 정렬
            df = pd.DataFrame(metric_values.items(), columns=['name', 'value'])
            df = df.sort_values('value', ascending=False).head(top_n)
            
            # 원본 이름과 영문 표시 이름 매핑
            name_mapping = {}
            for name in df['name']:
                if re.search(r'[가-힣]', name):  # 한글이 포함된 경우만 변환
                    name_mapping[name] = romanize_korean(name)
                else:
                    name_mapping[name] = name
            
            # 역방향 매핑 (로마자 -> 원본)
            reverse_mapping = {v: k for k, v in name_mapping.items()}
            
            # 영문 이름으로 데이터프레임 변환
            df['display_name'] = df['name'].map(name_mapping)
            
            # matplotlib 기본 폰트 설정 (영문 사용으로 한글 문제 우회)
            plt.rcParams['font.family'] = 'DejaVu Sans'
            
            # 그래프 생성
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # 컬러 팔레트 (구글 색상 사용)
            colors = ['#4285F4', '#EA4335', '#34A853', '#FBBC05', '#8E24AA', '#16A085']
            
            # 반전된 순서로 그래프 생성 (위에서 아래로 내림차순)
            bars = ax.barh(df['display_name'], df['value'], 
                         color=[colors[i % len(colors)] for i in range(len(df))])
            
            # 그래프 스타일링 
            ax.set_xlabel('Centrality Value', fontsize=12)
            
            # 중심성 지표별 적절한 제목 설정
            metric_titles = {
                'in_degree': 'In-Degree Centrality',
                'out_degree': 'Out-Degree Centrality',
                'betweenness': 'Betweenness Centrality',
                'closeness': 'Closeness Centrality'
            }
            title = metric_titles.get(metric, metric)
            ax.set_title(f'Top {top_n} Students - {title}', fontsize=14, pad=20)
            
            # 값 주석 추가
            for bar in bars:
                width = bar.get_width()
                ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                       f'{width:.2f}', va='center', fontsize=10)
            
            # 그리드 추가
            ax.grid(axis='x', linestyle='--', alpha=0.6)
            
            # 레이아웃 조정
            plt.tight_layout()
            
            # 한글-영문 매핑 표 표시 (UI 텍스트는 한글 사용)
            st.markdown("### 📋 학생 이름 매핑 참조표")
            st.write("그래프는 영문으로 표시되지만, 아래 표에서 원래 한글 이름을 확인하실 수 있습니다.")
            
            # 데이터프레임으로 표시
            mapping_df = pd.DataFrame({
                "그래프 표시 이름": list(name_mapping.values()),
                "원래 한글 이름": list(name_mapping.keys())
            })
            
            # name_mapping이 비어있지 않으면 표시
            if not mapping_df.empty:
                st.dataframe(mapping_df)
            
            return fig
            
        except Exception as e:
            logger.error(f"중심성 지표 시각화 중 오류 발생: {str(e)}")
            st.error(f"중심성 지표 시각화 중 오류가 발생했습니다: {str(e)}")
            return None
    
    def create_community_table(self):
        """커뮤니티별 학생 목록 생성"""
        try:
            # 커뮤니티 데이터가 없으면 가져오기
            if not hasattr(self, 'communities') or not self.communities:
                # 애널라이저가 있는지 확인
                if hasattr(self, 'analyzer') and self.analyzer:
                    self.communities = self.analyzer.detect_communities()
                else:
                    # 애널라이저가 없으면 빈 데이터 반환
                    logger.warning("커뮤니티 테이블 생성 실패: analyzer가 설정되지 않았습니다.")
                    return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
            
            if not self.communities or not isinstance(self.communities, dict):
                # 커뮤니티 데이터가 없거나 형식이 잘못된 경우 빈 데이터 반환
                logger.warning(f"커뮤니티 테이블 생성 실패: 잘못된 커뮤니티 데이터 형식 {type(self.communities)}")
                return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
            
            # 커뮤니티별 학생 그룹화
            community_groups = {}
            try:
                for node, community_id in self.communities.items():
                    if community_id not in community_groups:
                        community_groups[community_id] = []
                    community_groups[community_id].append(node)
            except AttributeError:
                # 커뮤니티 데이터 형식이 예상과 다른 경우
                logger.warning("커뮤니티 데이터 형식이 예상과 다릅니다")
                # 이미 그룹화된 형태일 수 있음
                if isinstance(self.communities, dict):
                    community_groups = self.communities
            
            if not community_groups:
                logger.warning("커뮤니티 그룹을 생성할 수 없습니다")
                return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
            
            # 한글 폰트 문제 확인 및 대응
            use_romanized = False
            if hasattr(self, 'has_korean_font'):
                use_romanized = not self.has_korean_font
            
            # 커뮤니티별 데이터 준비
            data = []
            for comm_id, members in community_groups.items():
                if not isinstance(members, (list, tuple, set)):
                    # 멤버가 리스트가 아닌 경우 (단일 값)
                    members = [members]
                
                # 중심성 지표가 높은 학생 식별
                central_student = ""
                central_value = 0
                
                if hasattr(self, 'metrics') and self.metrics:
                    # in_degree 기준 중심 학생 식별 시도
                    try:
                        if "in_degree" in self.metrics and self.metrics["in_degree"]:
                            # 중심성 값이 가장 높은 학생 찾기
                            central_student = max(members, key=lambda x: self.metrics["in_degree"].get(x, 0))
                            central_value = self.metrics["in_degree"].get(central_student, 0)
                    except Exception as e:
                        logger.warning(f"중심 학생 식별 실패: {str(e)}")
                
                # 로마자화된 이름 사용 여부 결정
                if use_romanized and hasattr(self, 'romanize_korean'):
                    # 이름 변환 시도
                    try:
                        member_names = [self.romanize_korean(str(m)) for m in members]
                        central_student_name = self.romanize_korean(str(central_student)) if central_student else ""
                    except Exception as e:
                        logger.warning(f"이름 로마자화 실패: {str(e)}")
                        member_names = [str(m) for m in members]
                        central_student_name = str(central_student)
                else:
                    member_names = [str(m) for m in members]
                    central_student_name = str(central_student)
                
                data.append({
                    "그룹 ID": comm_id,
                    "학생 수": len(members),
                    "주요 학생": central_student_name if central_student else "",
                    "중심성 값": central_value,
                    "소속 학생": ", ".join(member_names)
                })
            
            # 데이터프레임 생성 및 반환
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"커뮤니티 테이블 생성 실패: {str(e)}")
            # 오류 시 빈 데이터프레임 반환
            return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
    
    def get_centrality_metrics(self):
        """중심성 지표 반환 - analyzer의 지표를 사용"""
        if not self.metrics:
            # 중심성 지표가 계산되지 않았다면 계산
            self.metrics = self.analyzer.metrics
        return self.metrics 