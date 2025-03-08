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
import json

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
    # HTML <style> 요소 대신 직접 CSS를 주입하는 방식으로 변경
    # 이전 코드가 항상 작동하지 않는 경우가 있었음
    custom_css = """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic&family=Noto+Sans+KR&display=swap');
      
      .node text {
        font-family: 'Noto Sans KR', 'Nanum Gothic', sans-serif !important;
      }
      
      .tooltip {
        font-family: 'Noto Sans KR', 'Nanum Gothic', sans-serif !important;
      }
    </style>
    """
    
    # 기존 options 딕셔너리에 직접 덮어쓰기
    net.html = net.html.replace("<head>", f"<head>\n{custom_css}")
    
    # 종합적인 수정사항 - 네트워크 자체의 옵션도 조정
    net.options.physics.enabled = True
    net.options.physics.solver = "forceAtlas2Based"
    
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
    """한글 텍스트를 로마자로 변환하는 함수
    
    내부 처리용으로만 사용하고, 표시할 때는 원래 한글을 사용
    """
    if not text or not isinstance(text, str):
        return "Unknown"
        
    # 한글이 아닌 경우 그대로 반환
    if not any(c for c in text if ord('가') <= ord(c) <= ord('힣')):
        return text
        
    # 간단한 로마자 변환 (더 복잡한 규칙이 필요하면 hangul-romanize 등의 라이브러리 사용 권장)
    korean_to_roman = {
        '가': 'ga', '나': 'na', '다': 'da', '라': 'ra', '마': 'ma', '바': 'ba', '사': 'sa', 
        '아': 'a', '자': 'ja', '차': 'cha', '카': 'ka', '타': 'ta', '파': 'pa', '하': 'ha',
        '김': 'Kim', '이': 'Lee', '박': 'Park', '최': 'Choi', '정': 'Jung', '강': 'Kang',
        '조': 'Jo', '윤': 'Yoon', '장': 'Jang', '임': 'Lim', '한': 'Han', '오': 'Oh',
        '서': 'Seo', '신': 'Shin', '권': 'Kwon', '황': 'Hwang', '안': 'Ahn', '송': 'Song',
        '유': 'Yoo', '홍': 'Hong', '전': 'Jeon', '고': 'Go', '문': 'Moon', '양': 'Yang',
        '손': 'Son', '배': 'Bae', '조': 'Cho', '백': 'Baek', '허': 'Heo', '남': 'Nam'
    }
    
    result = ""
    for char in text:
        if '가' <= char <= '힣':
            if char in korean_to_roman:
                result += korean_to_roman[char]
            else:
                # 매핑되지 않은 한글 문자는 'x'로 대체
                result += 'x'
        else:
            result += char
    
    # 로마자 변환 결과 로깅
    logging.debug(f"로마자 변환: {text} -> {result}")
    return result

class NetworkVisualizer:
    """네트워크 그래프 시각화 클래스"""
    
    def __init__(self, analyzer):
        """NetworkAnalyzer 객체를 받아 초기화"""
        self.analyzer = analyzer
        self.G = analyzer.G.copy()
        
        # 항상 로마자 이름 사용
        self.has_korean_font = False
        
        # 원래 이름 매핑 저장
        self.original_names = {}
        for node in self.G.nodes():
            # 노드가 문자열이 아닌 경우 처리
            if isinstance(node, str):
                # 한글 이름 저장
                self.original_names[romanize_korean(node)] = node
            else:
                self.original_names[str(node)] = str(node)
        
        # 한글 폰트 확인 (결과에 상관없이 로마자화된 이름 사용)
        self._check_korean_font()
        
        # 그래프 복사본 생성 (로마자 이름 사용)
        self.G_roman = nx.DiGraph()
        
        # 노드 복사 (이름 로마자화)
        for node, data in self.G.nodes(data=True):
            # 노드 이름 로마자화
            roman_name = romanize_korean(str(node))
            self.G_roman.add_node(roman_name, **data)
            
        # 엣지 복사 (이름 로마자화)
        for u, v, data in self.G.edges(data=True):
            u_roman = romanize_korean(str(u))
            v_roman = romanize_korean(str(v))
            self.G_roman.add_edge(u_roman, v_roman, **data)
            
        # 로마자 이름 매핑 저장
        logging.info(f"로마자 이름 매핑 생성 완료: {len(self.original_names)}개")
        
        self.communities = analyzer.communities
        self.metrics = analyzer.metrics
    
    def _check_korean_font(self):
        """한글 폰트 사용 가능 여부 확인"""
        # 글로벌 변수 사용
        global HAS_KOREAN_FONT
        
        # 항상 False로 설정 (로마자 사용)
        self.has_korean_font = False
        
    def _get_display_label(self, node_name, use_romanized=True):
        """노드 표시 레이블 생성
        
        내부 처리용으로는 로마자화된 이름을 사용하고,
        사용자 표시용으로는 원래 한글 이름을 사용합니다.
        """
        if not node_name:
            return "Unknown"
            
        # 로마자화된 이름
        romanized_name = romanize_korean(str(node_name))
        
        # 항상 원래 이름 반환 (한글)
        if romanized_name in self.original_names:
            return self.original_names[romanized_name]
        
        # 없으면 원래 이름 그대로 반환
        return str(node_name)
    
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
                        
                        # 커뮤니티 ID가 리스트인 경우 첫 번째 값 사용
                        if isinstance(comm_id, list):
                            if len(comm_id) > 0:
                                comm_id = comm_id[0]
                            else:
                                comm_id = 0
                        
                        # 커뮤니티 ID가 정수로 변환 가능한지 확인
                        try:
                            if not isinstance(comm_id, int):
                                comm_id = int(comm_id)
                        except (ValueError, TypeError):
                            comm_id = 0
                            
                        color_idx = comm_id % len(color_palette)
                        node_color.append(color_palette[color_idx])
                    except Exception as e:
                        # 오류 발생 시 기본 색상 사용
                        logger.warning(f"노드 {node}의 색상 설정 중 오류: {str(e)}")
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
    
    def create_pyvis_network(self, height="600px", width="100%", layout="fruchterman"):
        """PyVis 네트워크 시각화 생성
        
        Arguments:
            height (str): 네트워크 높이 (기본값: 600px)
            width (str): 네트워크 너비 (기본값: 100%)
            layout (str): 레이아웃 알고리즘 (기본값: fruchterman)
            
        Returns:
            pyvis.network.Network: 시각화된 네트워크 객체
        """
        try:
            # 로마자 이름으로 변환된 그래프 사용
            G = self.G_roman.copy()
            
            # 빈 그래프 확인
            if len(G.nodes()) == 0:
                logging.error("빈 그래프로 PyVis 네트워크를 생성할 수 없습니다.")
                return None
            
            # 정점 레이블 매핑 (원래 한글 이름으로 표시)
            node_labels = {}
            for node in G.nodes():
                # 실제 원래 이름 가져오기
                node_labels[node] = self._get_original_name(node)
            
            # 중심성 데이터 가져오기
            centrality_metrics = self.analyzer.get_centrality_metrics()
            
            # 정규화 함수 정의
            def normalize(values, min_size=10, max_size=30):
                if not values:
                    return {}
                min_val, max_val = min(values), max(values)
                if min_val == max_val:
                    return {k: (max_size + min_size) / 2 for k in values.keys()}
                return {k: min_size + (v - min_val) * (max_size - min_size) / (max_val - min_val) 
                        for k, v in values.items()}
                    
            # 기본 중심성 (크기, 색상용)
            in_degree = nx.in_degree_centrality(G)
            bet_cent = nx.betweenness_centrality(G)
            
            # 정규화
            node_sizes = normalize(in_degree)
            node_colors = normalize(bet_cent, 0, 1)
            
            # 커뮤니티 탐지 (색상 다양화용)
            community_data = self.analyzer.get_communities()
            
            # 색상 매핑
            color_map = {}
            if community_data:
                unique_communities = set(community_data.values())
                colors = plt.cm.tab20(np.linspace(0, 1, len(unique_communities)))
                community_colors = {comm: f"rgba({int(r*255)},{int(g*255)},{int(b*255)},{a})" 
                                    for comm, (r, g, b, a) in zip(unique_communities, colors)}
                
                for node, comm in community_data.items():
                    # 로마자화된 이름으로 변환
                    roman_node = romanize_korean(str(node))
                    if roman_node in G.nodes():
                        color_map[roman_node] = community_colors[comm]
            
            # PyVis 네트워크 초기화
            net = Network(height=height, width=width, directed=True, notebook=False)
            
            # 한글 폰트 적용
            net = apply_korean_font_to_pyvis(net)
            
            # 레이아웃 설정
            layout_options = {
                "fruchterman": {"springLength": 250, "springConstant": 0.01, "damping": 0.09},
                "force": {"springLength": 100, "springConstant": 0.05, "damping": 0.09, "centralGravity": 0.1},
                "circular": {}
            }
            
            # 레이아웃 설정
            if layout in layout_options:
                # 선택된 레이아웃으로 물리 옵션 설정
                physics_options = layout_options[layout]
                
                if layout == "circular":
                    # 원형 레이아웃은 물리 비활성화하고 원형으로 배치
                    net.set_options("""
                    {
                        "physics": {
                            "enabled": false
                        },
                        "layout": {
                            "circular": {
                                "enabled": true
                            }
                        }
                    }
                    """)
                else:
                    # 물리 기반 레이아웃
                    physics_json = json.dumps(physics_options)
                    net.set_options(f"""
                    {{
                        "physics": {{
                            "enabled": true,
                            "forceAtlas2Based": {physics_json},
                            "solver": "forceAtlas2Based"
                        }}
                    }}
                    """)
            
            # 노드 추가
            for node in G.nodes():
                # 원래 이름 가져오기
                original_name = self._get_original_name(node)
                
                # 노드 크기 및 색상
                size = node_sizes.get(node, 15)
                color = color_map.get(node, "#97C2FC")
                
                # 중심성 지표 가져오기
                in_degree_val = centrality_metrics.get("in_degree", {}).get(original_name, 0)
                out_degree_val = centrality_metrics.get("out_degree", {}).get(original_name, 0)
                betweenness_val = centrality_metrics.get("betweenness", {}).get(original_name, 0)
                
                # 소수점 둘째자리로 반올림
                in_degree_val = round(in_degree_val, 2)
                out_degree_val = round(out_degree_val, 2)
                betweenness_val = round(betweenness_val, 2)
                
                # 네트워크에 화살표가 향하는 수 (인기도)
                in_arrows = len([u for u, v in G.edges() if v == node])
                
                # 네트워크에서 나가는 화살표 수 (활동성)
                out_arrows = len([u for u, v in G.edges() if u == node])
                
                # 툴팁 텍스트 (HTML 태그 제거, 일반 텍스트로 변환)
                tooltip_text = f"{original_name}\n인기도(In): {in_degree_val}\n활동성(Out): {out_degree_val}\n매개성: {betweenness_val}\n받은 선택: {in_arrows}개\n한 선택: {out_arrows}개"
                
                # 정점 추가
                net.add_node(
                    node, 
                    label=original_name,
                    title=tooltip_text,
                    size=size, 
                    color=color
                )
            
            # 엣지 추가
            for u, v, data in G.edges(data=True):
                # 가중치 (기본값 1)
                weight = data.get('weight', 1)
                
                # 엣지 설명 
                title = f"{self._get_original_name(u)} → {self._get_original_name(v)}"
                if weight > 1:
                    title += f" (가중치: {weight})"
                
                # 엣지 색상 및 폭 설정
                edge_color = "#848484"  # 기본 회색
                width = 1 + weight * 0.5  # 가중치에 비례
                
                # 엣지 추가
                net.add_edge(u, v, title=title, width=width, color=edge_color)
            
            # 네트워크 옵션 설정
            net.set_options("""
            {
                "nodes": {
                    "font": {
                        "size": 16,
                        "face": "Noto Sans KR"
                    },
                    "shape": "dot",
                    "borderWidth": 2,
                    "borderWidthSelected": 4
                },
                "edges": {
                    "arrows": {
                        "to": {
                            "enabled": true,
                            "scaleFactor": 0.5
                        }
                    },
                    "color": {
                        "inherit": false
                    },
                    "smooth": {
                        "enabled": true,
                        "type": "continuous"
                    }
                },
                "interaction": {
                    "hover": true,
                    "navigationButtons": true,
                    "keyboard": {
                        "enabled": true
                    }
                }
            }
            """)
            
            # 툴팁이 HTML 태그를 그대로 보여주는 문제 해결
            # 자바스크립트를 이용해 툴팁 텍스트를 적절히 포맷팅
            net.html = net.html.replace('</head>', '''
            <style>
            div.vis-tooltip {
                position: absolute;
                visibility: hidden;
                padding: 10px;
                white-space: pre-wrap;
                font-family: 'Noto Sans KR', sans-serif;
                font-size: 14px;
                color: #000000;
                background-color: #f5f5f5;
                border-radius: 4px;
                border: 1px solid #d3d3d3;
                box-shadow: 3px 3px 10px rgba(0, 0, 0, 0.2);
                pointer-events: none;
                z-index: 5;
            }
            </style>
            <script>
            // 커스텀 툴팁 기능
            document.addEventListener("DOMContentLoaded", function() {
                setTimeout(function() {
                    try {
                        // 노드 호버 이벤트에 연결
                        network.on("hoverNode", function(params) {
                            // 노드의 title 속성 가져오기
                            var node = network.body.nodes[params.node];
                            if (node && node.options.title) {
                                var content = node.options.title;
                                // 줄바꿈을 <br>로 변환
                                content = content.replace(/\\n/g, '<br>');
                                // 툴팁 요소 스타일 지정
                                var tooltip = document.querySelector('.vis-tooltip');
                                if (tooltip) {
                                    tooltip.innerHTML = content;
                                    tooltip.style.visibility = 'visible';
                                }
                            }
                        });
                        
                        // 호버 상태 벗어날 때 툴팁 숨기기
                        network.on("blurNode", function() {
                            var tooltip = document.querySelector('.vis-tooltip');
                            if (tooltip) {
                                tooltip.style.visibility = 'hidden';
                            }
                        });
                        
                        // 마우스 움직임에 따라 툴팁 위치 조정
                        document.addEventListener('mousemove', function(e) {
                            var tooltip = document.querySelector('.vis-tooltip');
                            if (tooltip && tooltip.style.visibility === 'visible') {
                                tooltip.style.top = (e.pageY + 15) + 'px';
                                tooltip.style.left = (e.pageX + 15) + 'px';
                            }
                        });
                    } catch (err) {
                        console.error("툴팁 설정 중 오류 발생:", err);
                    }
                }, 500); // 네트워크가 로드될 시간을 주기 위한 지연
            });
            </script>
            </head>
            ''')
            
            return net
        except Exception as e:
            logging.error(f"PyVis 네트워크 생성 중 오류 발생: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return None
    
    def create_centrality_plot(self, metric="in_degree", top_n=10):
        """중심성 지표 시각화 (내부 처리는 영문, 표시는 한글)"""
        try:
            # 지표 선택
            if metric not in self.metrics:
                st.error(f"요청한 중심성 지표({metric})가 존재하지 않습니다.")
                return None
            
            # 선택된 지표 값 가져오기
            metric_values = self.metrics[metric]
            
            # 리스트 타입의 값을 처리하기 위한 정제 과정
            processed_values = {}
            for k, v in metric_values.items():
                # 값이 리스트인 경우 첫 번째 값 사용
                if isinstance(v, list):
                    if len(v) > 0:
                        processed_values[k] = v[0]
                    else:
                        processed_values[k] = 0
                # 숫자가 아닌 경우 변환 시도
                elif not isinstance(v, (int, float)):
                    try:
                        processed_values[k] = float(v)
                    except (ValueError, TypeError):
                        processed_values[k] = 0
                else:
                    processed_values[k] = v
            
            # 데이터프레임 변환 및 정렬
            df = pd.DataFrame(processed_values.items(), columns=['name', 'value'])
            
            # 이름이 문자열이 아닌 경우 문자열로 변환
            df['name'] = df['name'].apply(lambda x: str(x) if not isinstance(x, str) else x)
            
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
            
            # Y축 레이블이 카테고리형 데이터가 아닌 숫자로 처리되는 문제 해결
            y_pos = np.arange(len(df))  # 숫자 위치값 생성
            
            # 반전된 순서로 그래프 생성 (위에서 아래로 내림차순)
            bars = ax.barh(y_pos, df['value'], 
                         color=[colors[i % len(colors)] for i in range(len(df))])
            
            # Y축 레이블 설정 (위치에 표시 이름 매핑)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(df['display_name'])
            
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
                    self.communities = self.analyzer.get_communities()
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
                # 커뮤니티 데이터 형식 검사
                is_nodeid_to_community = True
                for key in list(self.communities.keys())[:5]:  # 처음 몇 개만 확인
                    if not isinstance(key, (str, int)):
                        is_nodeid_to_community = False
                        break
                
                if is_nodeid_to_community:
                    # 구조: {노드ID: 커뮤니티ID, ...}
                    for node, community_id in self.communities.items():
                        # community_id가 리스트인 경우 (1개 이상의 커뮤니티에 속한 경우)
                        if isinstance(community_id, list):
                            # 첫 번째 커뮤니티만 사용
                            comm_id = str(community_id[0])
                        else:
                            comm_id = str(community_id)
                        
                        if comm_id not in community_groups:
                            community_groups[comm_id] = []
                        
                        # 노드가 문자열이 아닌 경우 문자열로 변환
                        node_str = str(node) if not isinstance(node, str) else node
                        community_groups[comm_id].append(node_str)
                else:
                    # 구조: {커뮤니티ID: [노드ID, ...], ...}
                    for community_id, members in self.communities.items():
                        comm_id = str(community_id)
                        
                        if comm_id not in community_groups:
                            community_groups[comm_id] = []
                        
                        # members가 리스트가 아닌 경우 리스트로 변환
                        if not isinstance(members, list):
                            members = [members]
                        
                        # 멤버를 문자열로 변환하여 추가
                        for member in members:
                            member_str = str(member) if not isinstance(member, str) else member
                            community_groups[comm_id].append(member_str)
            except Exception as e:
                logger.error(f"커뮤니티 그룹화 중 오류: {str(e)}")
                return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
            
            # 결과 데이터 생성
            result_data = []
            for comm_id, members in community_groups.items():
                # 학생 수
                student_count = len(members)
                
                # 주요 학생 (최대 5명)
                top_students = ', '.join(members[:5])
                if student_count > 5:
                    top_students += ', ...'
                
                result_data.append({
                    "그룹 ID": comm_id,
                    "학생 수": student_count,
                    "주요 학생": top_students
                })
            
            # 데이터프레임 생성
            result_df = pd.DataFrame(result_data)
            
            # 그룹 크기에 따라 정렬
            if not result_df.empty:
                result_df = result_df.sort_values(by="학생 수", ascending=False)
            
            return result_df
        
        except Exception as e:
            logger.error(f"커뮤니티 테이블 생성 실패: {str(e)}")
            return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
    
    def get_centrality_metrics(self):
        """중심성 지표 반환 - analyzer의 지표를 사용"""
        if not self.metrics:
            # 중심성 지표가 계산되지 않았다면 계산
            self.metrics = self.analyzer.metrics
        return self.metrics

    # 원본 이름 가져오기 위한 도우미 메서드 추가
    def _get_original_name(self, node_id):
        """로마자화된 노드 ID에서 원래 이름 조회"""
        if node_id in self.original_names:
            return self.original_names[node_id]
        return str(node_id) 