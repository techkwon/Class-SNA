import pandas as pd
import json
import base64
import streamlit as st
from io import BytesIO
import matplotlib.pyplot as plt
import logging
import os
import traceback

# 로깅 설정
logging.basicConfig(level=logging.ERROR)  # 로그 레벨을 ERROR로 설정
logger = logging.getLogger(__name__)

def get_table_download_link(df, filename="data.csv", text="CSV 다운로드"):
    """데이터프레임을 CSV 다운로드 링크로 변환"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def get_image_download_link(fig, filename="plot.png", text="이미지 다운로드"):
    """Matplotlib 그림을 PNG 다운로드 링크로 변환"""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">{text}</a>'
    return href

def get_html_download_link(html_path, filename="network.html", text="HTML 다운로드"):
    """HTML 파일 다운로드 링크 생성"""
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">{text}</a>'
    return href

def export_to_excel(network_data, analysis_results, filename="network_analysis.xlsx"):
    """분석 결과를 Excel 파일로 내보내기"""
    try:
        # 인자 검증
        if not isinstance(network_data, dict):
            logger.warning(f"유효하지 않은 network_data 형식: {type(network_data)}")
            return f'<div style="color:red;">유효하지 않은 데이터 형식입니다.</div>'
        
        if not isinstance(analysis_results, dict):
            logger.warning(f"유효하지 않은 analysis_results 형식: {type(analysis_results)}")
            return f'<div style="color:red;">유효하지 않은 분석 결과 형식입니다.</div>'
            
        # BytesIO 객체 생성
        output = BytesIO()
        
        # 엔진 선택 (openpyxl 또는 xlsxwriter)
        try:
            import openpyxl
            engine = 'openpyxl'
            logger.info("openpyxl 엔진을 사용하여 Excel 내보내기를 진행합니다.")
        except ImportError:
            try:
                import xlsxwriter
                engine = 'xlsxwriter'
                logger.info("xlsxwriter 엔진을 사용하여 Excel 내보내기를 진행합니다.")
            except ImportError:
                logger.error("Excel 내보내기에 필요한 패키지가 설치되지 않았습니다.")
                return f'<div style="color:red;">Excel 내보내기를 위해 openpyxl 또는 xlsxwriter 패키지가 필요합니다.</div>'
        
        # Excel 작성기 생성
        with pd.ExcelWriter(output, engine=engine) as writer:
            try:
                # 노드 데이터 저장
                if "nodes" in network_data and isinstance(network_data["nodes"], pd.DataFrame) and not network_data["nodes"].empty:
                    network_data["nodes"].to_excel(writer, sheet_name="Nodes", index=False)
                elif "students" in network_data and isinstance(network_data["students"], list) and network_data["students"]:
                    # students 목록이 있다면 DataFrame으로 변환
                    nodes_df = pd.DataFrame(network_data["students"])
                    nodes_df.to_excel(writer, sheet_name="Nodes", index=False)
            except Exception as e:
                logger.warning(f"노드 데이터 저장 실패: {str(e)}")
                traceback.print_exc()
            
            try:
                # 엣지 데이터 저장
                if "edges" in network_data and isinstance(network_data["edges"], pd.DataFrame) and not network_data["edges"].empty:
                    network_data["edges"].to_excel(writer, sheet_name="Edges", index=False)
                elif "relationships" in network_data and isinstance(network_data["relationships"], list) and network_data["relationships"]:
                    # relationships 목록이 있다면 DataFrame으로 변환
                    edges_df = pd.DataFrame(network_data["relationships"])
                    edges_df.to_excel(writer, sheet_name="Edges", index=False)
            except Exception as e:
                logger.warning(f"엣지 데이터 저장 실패: {str(e)}")
            
            # 중심성 지표 저장
            try:
                if "centrality" in analysis_results and analysis_results["centrality"]:
                    centrality_data = analysis_results["centrality"]
                    # 다양한 형태의 centrality 데이터 처리
                    if isinstance(centrality_data, pd.DataFrame):
                        # 이미 DataFrame인 경우
                        centrality_data.to_excel(writer, sheet_name="Centrality", index=True)
                    elif isinstance(centrality_data, dict):
                        # 딕셔너리가 중첩된 경우 (`metric_name: {node: value}`)
                        centrality_df = pd.DataFrame()
                        for metric_name, values in centrality_data.items():
                            if isinstance(values, dict):
                                centrality_df[metric_name] = pd.Series(values)
                        if not centrality_df.empty:
                            centrality_df.to_excel(writer, sheet_name="Centrality", index=True)
                    else:
                        logger.warning(f"지원되지 않는 centrality 데이터 형식: {type(centrality_data)}")
            except Exception as e:
                logger.warning(f"중심성 지표 저장 실패: {str(e)}")
            
            # 커뮤니티 정보 저장
            try:
                if "communities" in analysis_results:
                    communities_data = analysis_results["communities"]
                    
                    # 데이터 형식 확인 및 변환
                    community_rows = []
                    
                    if isinstance(communities_data, pd.DataFrame):
                        # 이미 DataFrame인 경우
                        communities_data.to_excel(writer, sheet_name="Communities", index=False)
                    elif isinstance(communities_data, dict):
                        # 딕셔너리 형태 처리 {community_id: members, ...} 또는 {node: community_id, ...}
                        
                        # 첫 번째 값 확인하여 형식 추정
                        first_value = next(iter(communities_data.values())) if communities_data else None
                        
                        if isinstance(first_value, (list, tuple, set)):
                            # {community_id: [members]} 형식
                            for comm_id, members in communities_data.items():
                                if isinstance(members, (list, tuple, set)):
                                    for member in members:
                                        community_rows.append({"Community_ID": comm_id, "Member": member})
                                else:
                                    # 단일 값인 경우
                                    community_rows.append({"Community_ID": comm_id, "Member": members})
                        elif isinstance(first_value, (int, str, float)):
                            # {node: community_id} 형식
                            for node, comm_id in communities_data.items():
                                community_rows.append({"Node": node, "Community_ID": comm_id})
                        else:
                            # 알 수 없는 형식
                            logger.warning(f"알 수 없는 community 데이터 형식: {type(first_value)}")
                            
                        # 데이터프레임으로 변환하여 저장
                        if community_rows:
                            pd.DataFrame(community_rows).to_excel(writer, sheet_name="Communities", index=False)
                    elif isinstance(communities_data, (list, tuple)):
                        # 리스트 형식
                        if all(isinstance(item, dict) for item in communities_data):
                            # 딕셔너리 리스트
                            pd.DataFrame(communities_data).to_excel(writer, sheet_name="Communities", index=False)
                        else:
                            # 단순 리스트
                            pd.DataFrame({"Community_Member": communities_data}).to_excel(writer, sheet_name="Communities", index=False)
                    elif isinstance(communities_data, (int, float, str)):
                        # 단일 값 - 리스트로 감싸서 저장
                        pd.DataFrame({"Community_Single_Value": [communities_data]}).to_excel(writer, sheet_name="Communities", index=False)
                    else:
                        logger.warning(f"지원되지 않는 communities 데이터 형식: {type(communities_data)}")
            except Exception as e:
                logger.warning(f"커뮤니티 정보 저장 실패: {str(e)}")
                traceback.print_exc()
            
            # 요약 통계 저장
            try:
                if "summary" in analysis_results and analysis_results["summary"]:
                    summary_data = analysis_results["summary"]
                    
                    if isinstance(summary_data, dict):
                        # 딕셔너리를 DataFrame으로 변환하여 저장
                        summary_df = pd.DataFrame([summary_data])
                        summary_df.to_excel(writer, sheet_name="Summary", index=False)
                    elif isinstance(summary_data, pd.DataFrame):
                        # 이미 DataFrame인 경우
                        summary_data.to_excel(writer, sheet_name="Summary", index=False)
                    else:
                        logger.warning(f"지원되지 않는 summary 데이터 형식: {type(summary_data)}")
            except Exception as e:
                logger.warning(f"요약 통계 저장 실패: {str(e)}")
        
        # BytesIO 데이터 가져오기
        data = output.getvalue()
        
        # 다운로드 링크 생성
        b64 = base64.b64encode(data).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{filename} 다운로드</a>'
        
        return href
        
    except Exception as e:
        logger.error(f"Excel 내보내기 실패: {str(e)}")
        traceback.print_exc()
        return f'<div style="color:red;">Excel 내보내기 실패: {str(e)}</div>'

def set_streamlit_page_config():
    """Streamlit 페이지 설정"""
    st.set_page_config(
        page_title="학급 관계 네트워크 분석 시스템",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 커스텀 CSS 적용
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
    }
    .footer {
        font-size: 0.8rem;
        color: #666;
        text-align: center;
        margin-top: 2rem;
        border-top: 1px solid #eee;
        padding-top: 1rem;
    }
    .stAlert {
        background-color: #E3F2FD;
        border-left: 5px solid #1E88E5;
        padding: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

def show_footer():
    """페이지 하단 푸터 표시"""
    st.markdown("""
    <div class="footer">
        학급 관계 네트워크 분석 시스템 (Class-SNA) | 
        데이터 분석 및 시각화: NetworkX, Plotly |
        AI 분석: Google Gemini
    </div>
    """, unsafe_allow_html=True)

def check_and_create_assets():
    """assets 디렉토리 확인 및 필요한 파일 생성"""
    # assets 디렉토리가 없으면 생성
    if not os.path.exists("assets"):
        os.makedirs("assets")
        logger.info("assets 디렉토리 생성 완료")

def handle_error(e, error_type="처리"):
    """오류 처리 및 표시"""
    error_msg = f"{error_type} 오류: {str(e)}"
    logger.error(error_msg)
    logger.error(traceback.format_exc())  # 자세한 오류 트레이스백 기록
    st.error(error_msg)
    st.stop() 