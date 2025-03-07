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

# 시스템에 설치된 한글 폰트 목록 확인
def get_korean_fonts():
    """시스템에 설치된 한글 폰트 목록 확인"""
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
                        
                # 나눔 폰트 목록 확인
                result = subprocess.run(['fc-list', '|', 'grep', 'Nanum'], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    font_name = line.split(':')[1].strip().split(',')[0] if ':' in line else ''
                    if font_name and font_name not in korean_fonts:
                        korean_fonts.append(font_name)
            except:
                pass
                
        # matplotlib 폰트 매니저 사용
        for font in fm.fontManager.ttflist:
            if font.name not in korean_fonts:
                # 한글 관련 키워드 확인
                korean_keywords = ['nanum', 'gothic', 'gulim', 'batang', 'dotum', 'malgun', '나눔', '고딕', '굴림', '바탕', '돋움', '맑은']
                if any(keyword in font.name.lower() for keyword in korean_keywords):
                    korean_fonts.append(font.name)
        
        # 기본 시스템 폰트도 추가 (한글 지원 가능성이 있는 폰트)
        system_fonts = ['Arial Unicode MS', 'Segoe UI', 'Microsoft Sans Serif', 'Tahoma']
        for font in system_fonts:
            if font not in korean_fonts:
                korean_fonts.append(font)
                
    except Exception as e:
        logger.warning(f"한글 폰트 목록 확인 중 오류 발생: {str(e)}")
    
    return korean_fonts

# 한글 폰트 설치 안내
def show_korean_font_installation_guide():
    """한글 폰트 설치 안내 메시지 표시"""
    # 이미 안내가 표시되었는지 확인
    if 'font_guide_shown' in st.session_state and st.session_state['font_guide_shown']:
        return
        
    st.session_state['font_guide_shown'] = True
    
    st.sidebar.markdown("""
    ### 💡 한글 폰트 안내
    
    **Linux 환경에서 한글 폰트 설치:**
    ```bash
    # 나눔 폰트 설치
    sudo apt-get update
    sudo apt-get install fonts-nanum fonts-nanum-coding
    
    # 폰트 캐시 갱신
    sudo fc-cache -fv
    
    # 설치된 폰트 확인
    fc-list | grep -i nanum
    ```
    
    **웹 폰트를 사용 중입니다:**
    로컬 폰트가 없어도 웹 폰트를 통해 한글이 표시됩니다.
    """)

# 한글 폰트 설정 함수
def set_korean_font():
    """matplotlib에서 한글 폰트를 사용하도록 설정"""
    try:
        # 이미 캐시된 한글 폰트 확인 (세션 상태 활용)
        if 'korean_font_set' in st.session_state and st.session_state['korean_font_set']:
            return
            
        # 시스템에 설치된 한글 폰트 목록 확인
        korean_fonts = get_korean_fonts()
        
        # 폰트 설정 상태 저장
        st.session_state['korean_font_set'] = True
        
        # 한글 폰트가 부족하면 설치 안내 표시 (경고는 로그에만 남기고 UI에는 표시하지 않음)
        if len(korean_fonts) < 2:  # 기본 폰트 외에 한글 폰트가 없으면
            logger.warning("한글 폰트가 부족합니다.")
            show_korean_font_installation_guide()
        
        # 나눔 폰트 우선 순위 설정
        prioritized_fonts = [f for f in korean_fonts if 'nanum' in f.lower()]
        prioritized_fonts += [f for f in korean_fonts if 'nanum' not in f.lower()]
        
        # 한글 지원 가능한 폰트 후보 목록 (우선순위 순서)
        default_korean_fonts = [
            'NanumGothicCoding', 'NanumGothic', 'Nanum Gothic', 'Nanum Gothic Coding',
            'NanumBarunGothic', 'Nanum Barun Gothic', 'Malgun Gothic', 'Gulim', 'Batang',
            'AppleGothic', 'Noto Sans KR', 'Noto Sans CJK KR', 'UnDotum', 'Dotum'
        ]
        
        # 찾은 한글 폰트 + 기본 폰트 목록 결합
        all_fonts = prioritized_fonts + [f for f in default_korean_fonts if f not in prioritized_fonts]
        
        # 적용 가능한 폰트 찾기
        font_list = [f.name for f in fm.fontManager.ttflist]
        
        # 시스템에 설치된 한글 폰트 찾기
        found_font = None
        for font in all_fonts:
            if any(font.lower() == f.lower() for f in font_list):
                found_font = font
                break
            
        # 정확한 이름 매칭이 안 되면 일부 매칭 시도
        if not found_font:
            for font in all_fonts:
                matching_fonts = [f for f in font_list if font.lower() in f.lower()]
                if matching_fonts:
                    found_font = matching_fonts[0]
                    break
        
        # 폰트 설정
        if found_font:
            plt.rc('font', family=found_font)
            logger.info(f"한글 폰트 설정 완료: {found_font}")
        else:
            # 한글 폰트 못 찾았을 때 sans-serif 설정
            plt.rc('font', family='sans-serif')
            
            # 경고 메시지는 로그에만 남기고 UI에는 표시하지 않음
            logger.warning("한글 폰트를 찾을 수 없습니다.")
            
            # 가이드 표시 대신 웹 폰트로 대체 안내
            show_korean_font_installation_guide()
        
        # 폰트 설정 확인
        plt.rc('axes', unicode_minus=False)  # 마이너스 기호 깨짐 방지
        
    except Exception as e:
        # 오류 발생 시 기본 폰트 설정 (오류 메시지는 로그에만 남김)
        plt.rc('font', family='sans-serif')
        logger.warning(f"폰트 설정 중 오류 발생: {str(e)}")

# PyVis에 한글 폰트 적용 함수
def apply_korean_font_to_pyvis(net):
    """PyVis 네트워크에 기본 스타일을 적용합니다 (한글 지원 X)"""
    try:
        # 스타일 개선만 적용 (한글 폰트 설정 시도 없음)
        net.html = net.html.replace("<head>", """<head>
        <style>
        body, html, .vis-network, .vis-label {
            font-family: Arial, sans-serif !important;
        }
        .vis-network div.vis-network-tooltip {
            background-color: rgba(255, 255, 255, 0.9) !important;
            border: 1px solid #ccc !important;
            border-radius: 4px !important;
            padding: 8px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        }
        </style>
        """)
        
        # 기본 옵션 설정 (영문 폰트만 사용)
        try:
            net.set_options("""
            {
                "nodes": {
                    "font": {
                        "face": "Arial, sans-serif",
                        "size": 14
                    }
                },
                "edges": {
                    "font": {
                        "face": "Arial, sans-serif",
                        "size": 12
                    }
                }
            }
            """)
        except:
            pass  # 조용히 실패 처리
            
        return net
    except Exception:
        return net  # 오류 무시

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
            # 노드 정보 준비
            node_x = []
            node_y = []
            node_text = []  # 노드 텍스트 (한글 이름 또는 로마자화된 이름)
            node_size = []  # 노드 크기
            node_color = []  # 노드 색상
            
            # 그래프 레이아웃 계산 - 파라미터 조정하여 노드 간격 최적화
            if layout == "spring":
                pos = nx.spring_layout(self.graph, k=0.5, iterations=50)
            elif layout == "circular":
                pos = nx.circular_layout(self.graph)
            elif layout == "kamada":
                pos = nx.kamada_kawai_layout(self.graph)
            else:  # fruchterman
                pos = nx.fruchterman_reingold_layout(self.graph, k=0.3)
            
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
                degree_in = in_degree.get(node, 0)
                degree_out = self.metrics.get('out_degree', {}).get(node, 0)
                betweenness = self.metrics.get('betweenness', {}).get(node, 0)
                
                node_text.append(f"이름: {display_name}<br>인기도: {degree_in}<br>친밀도: {degree_out}<br>중재자 역할: {betweenness:.3f}")
                
                # 노드 크기 설정: 연결 중심성(In)에 비례
                size = in_degree.get(node, 0) * 15 + 15  # 크기 증가하여 더 잘 보이게 함
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
                line=dict(width=1.5, color='#888'),
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
                    line=dict(width=1.5, color='#444')
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
    
    def create_pyvis_network(self, height="600px", width="100%"):
        """PyVis를 사용하여 인터랙티브 네트워크 시각화를 생성합니다 (영문 이름 표시)"""
        # 네트워크 초기화
        net = Network(height=height, width=width, directed=True, notebook=False)
        net.toggle_hide_edges_on_drag(True)
        net.barnes_hut(gravity=-10000, central_gravity=0.3, spring_length=250)
        
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
        
        # 컬러 매핑 설정
        colors = self.analyzer.get_community_colors()
        
        # 중심성 계산
        centrality = self.analyzer.get_centrality_metrics()
        
        # 커뮤니티 정보 가져오기
        communities = self.analyzer.get_communities()
        
        # 노드 정보 설정
        for i, node_name in enumerate(nodes):
            # 항상 로마자 이름으로 표시
            romanized_name = romanize_korean(node_name)
            
            # 크기 설정 (정규화된 중심성 기반)
            size = 25 + centrality['in_degree'][node_name] * 50
            if size > 50:
                size = 50
            
            # 커뮤니티 색상 가져오기
            if node_name in colors:
                color = colors[node_name]
            else:
                color = "#97c2fc"  # 기본 파란색
            
            # 커뮤니티 정보 가져오기
            community_id = None
            for comm_id, members in communities.items():
                if node_name in members:
                    community_id = comm_id
                    break
            
            # 툴팁 정보 구성 (한글로 표시, 내부는 영문 사용)
            tooltip = f"이름: {node_name}<br>"
            tooltip += f"그룹: {community_id}<br>"
            tooltip += f"인기도(In): {self.analyzer.graph.in_degree(node_name)}<br>"
            tooltip += f"친밀도(Out): {self.analyzer.graph.out_degree(node_name)}"
            
            # 노드 추가 (로마자 이름으로 내부 처리)
            net.add_node(romanized_name, label=romanized_name, title=tooltip, 
                        size=size, color=color)
        
        # 엣지 추가 (원래 이름이 로마자 이름으로 변경된 것 반영)
        for source, target, weight in edges:
            romanized_source = romanize_korean(source)
            romanized_target = romanize_korean(target)
            
            # 툴팁 한글로 표시
            edge_tooltip = f"관계: {source} → {target}<br>강도: {weight}"
            
            net.add_edge(romanized_source, romanized_target, value=weight, 
                         title=edge_tooltip)
        
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
                    
                    // 클릭 이벤트 리스너 추가
                    network.on("click", function(params) {
                        if (params.nodes.length > 0) {
                            var nodeId = params.nodes[0];
                            if (nodeId) {
                                try {
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
            padding: 5px;
            white-space: nowrap;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: black;
            background-color: white;
            border-radius: 3px;
            border: 1px solid #808074;
            box-shadow: 3px 3px 10px rgba(0, 0, 0, 0.2);
            pointer-events: none;
            z-index: 5;
        }
        """)
        
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
            
            # 원본 한글 이름 및 영문 표시 이름 컬럼 추가
            df['original_name'] = df['name']  # 원본 한글 이름 저장
            df['display_name'] = df['name'].apply(lambda x: romanize_korean(x))  # 영문 표시 이름
            
            # 그래프 생성 (영문 이름으로 그래프 생성)
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(df['display_name'], df['value'], color='skyblue')
            
            # 그래프 스타일링 (한글 레이블)
            ax.set_xlabel('중심성 지표 값')
            
            # 중심성 지표별 적절한 제목 설정 (한글)
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
            
            # 매핑 테이블 스트림릿으로 표시 (한글 UI)
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**👉 그래프에 표시된 이름**")
                for name in df['display_name']:
                    st.write(name)
                    
            with col2:
                st.write("**👉 실제 한글 이름**")
                for name in df['original_name']:
                    st.write(name)
            
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
    
    def get_centrality_metrics(self):
        """중심성 지표 반환 - analyzer의 지표를 사용"""
        if not self.metrics:
            # 중심성 지표가 계산되지 않았다면 계산
            self.metrics = self.analyzer.metrics
        return self.metrics 