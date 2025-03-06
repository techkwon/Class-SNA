import pandas as pd
import json
import re
import logging
import gspread
import traceback
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import streamlit as st

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    """설문조사 데이터 처리 및 변환 클래스"""
    
    def __init__(self, api_manager):
        self.api_manager = api_manager
    
    def extract_sheet_id(self, sheet_url):
        """구글 시트 URL에서 ID 추출"""
        try:
            # URL 형식: https://docs.google.com/spreadsheets/d/spreadsheetId/edit
            if '/d/' in sheet_url:
                sheet_id = sheet_url.split('/d/')[1].split('/')[0]
                return sheet_id
            else:
                return None
        except Exception as e:
            logger.error(f"시트 ID 추출 실패: {str(e)}")
            return None
    
    def load_from_gsheet(self, sheet_url):
        """구글 시트에서 데이터 로드 (읽기 전용)"""
        try:
            sheet_id = self.extract_sheet_id(sheet_url)
            if not sheet_id:
                raise ValueError("유효한 구글 시트 URL이 아닙니다.")
            
            # 설문조사 데이터는 공개 시트라고 가정
            # 공개 시트의 경우 인증 없이 CSV로 직접 다운로드 가능
            csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            
            # pandas로 CSV 데이터 로드
            df = pd.read_csv(csv_export_url)
            return df
            
        except Exception as e:
            logger.error(f"구글 시트 데이터 로드 실패: {str(e)}")
            raise Exception(f"구글 시트 데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")
    
    def extract_json_from_text(self, text):
        """텍스트에서 JSON 부분 추출 및 정제"""
        try:
            # 마크다운 코드 블록(```json) 처리
            if "```json" in text or "```" in text:
                # 코드 블록 내용 추출
                code_block_pattern = r'```(?:json)?\s*\n([\s\S]*?)\n\s*```'
                code_blocks = re.findall(code_block_pattern, text)
                
                if code_blocks:
                    # 가장 큰 코드 블록 선택 (일반적으로 전체 JSON)
                    text = max(code_blocks, key=len)
                    logger.info("마크다운 코드 블록에서 JSON 추출 성공")
            
            # 정규식을 사용하여 중괄호로 둘러싸인 유효한 JSON 객체를 찾습니다.
            json_pattern = r'(\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\})'
            matches = re.findall(json_pattern, text)
            
            if not matches:
                # JSON 객체를 찾을 수 없는 경우
                logger.error("API 응답에서 JSON 객체를 찾을 수 없습니다.")
                st.error("API 응답에서 유효한 JSON을 찾을 수 없습니다. 다시 시도해주세요.")
                
                # 원본 응답 로깅 및 UI에 표시
                logger.error(f"원본 응답: {text[:1000]}...")
                st.code(text[:1000] + "..." if len(text) > 1000 else text, language="text")
                
                raise ValueError("API 응답에서 유효한 JSON을 찾을 수 없습니다.")
                
            # 가장 큰 JSON 객체를 선택 (일반적으로 전체 응답)
            largest_match = max(matches, key=len)
            
            # 일반적인 JSON 구문 오류 수정 시도
            # 후행 쉼표 제거
            cleaned_json = re.sub(r',\s*}', '}', largest_match)
            cleaned_json = re.sub(r',\s*]', ']', cleaned_json)
            
            # 누락된 쌍따옴표 처리
            cleaned_json = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', cleaned_json)
            
            # 홑따옴표를 쌍따옴표로 변환
            cleaned_json = cleaned_json.replace("'", '"')
            
            return cleaned_json
            
        except Exception as e:
            logger.error(f"JSON 추출 실패: {str(e)}")
            logger.error(traceback.format_exc())
            st.error(f"JSON 추출 중 오류가 발생했습니다: {str(e)}")
            st.code(text[:1000] + "..." if len(text) > 1000 else text, language="text")
            raise ValueError(f"JSON 추출 중 오류가 발생했습니다: {str(e)}")
    
    def analyze_data_structure(self, df):
        """설문조사 데이터 구조 분석"""
        try:
            # 데이터프레임을 문자열로 변환
            data_str = df.to_string(index=False)
            
            # 질문 목록 추출 (컬럼명)
            questions = df.columns.tolist()
            questions_str = "\n".join(questions)
            
            # Gemini API를 사용하여 데이터 구조 분석
            analysis_result = self.api_manager.analyze_survey_data(data_str, questions_str)
            
            # API 응답 전체를 디버깅 목적으로 로깅
            logger.info(f"Gemini API 응답: {analysis_result[:1000]}...")
            
            # 디버그 정보를 UI에 표시
            with st.expander("디버그: Gemini API 응답 (개발자용)", expanded=False):
                st.text_area("원본 응답:", value=analysis_result, height=200)
            
            # JSON 문자열 추출 및 정제
            json_str = self.extract_json_from_text(analysis_result)
            
            # 디버그 정보를 UI에 표시
            with st.expander("디버그: 추출된 JSON (개발자용)", expanded=False):
                st.text_area("정제된 JSON:", value=json_str, height=200)
            
            try:
                # JSON 파싱 시도
                result = json.loads(json_str)
                logger.info("JSON 파싱 성공")
            except json.JSONDecodeError as e:
                # JSON 파싱 실패 시 오류 표시 및 디버깅 정보 제공
                logger.error(f"JSON 파싱 실패: {str(e)}")
                st.error(f"""
                AI 응답에서 유효한 JSON을 파싱하지 못했습니다.
                다시 시도해보세요. 오류 메시지: {str(e)}
                """)
                st.code(json_str[:500] + "..." if len(json_str) > 500 else json_str, language="json")
                
                # 백업 로직: 예제 구조 생성
                if "relationships" in analysis_result and "from" in analysis_result and "to" in analysis_result:
                    st.warning("JSON 파싱은 실패했지만, API 응답에서 관계 데이터를 추출하려고 시도합니다.")
                    
                    # 간단한 패턴 매칭으로 관계 추출 시도
                    rel_pattern = r'{"from":\s*"([^"]+)",\s*"to":\s*"([^"]+)"'
                    relationships = []
                    
                    for match in re.finditer(rel_pattern, analysis_result):
                        from_student, to_student = match.groups()
                        relationships.append({
                            "from": from_student,
                            "to": to_student,
                            "weight": 1,
                            "type": "relationship"
                        })
                    
                    if relationships:
                        logger.info(f"백업 로직으로 {len(relationships)}개의 관계를 추출했습니다.")
                        result = {
                            "relationships": relationships,
                            "students": list(set([r["from"] for r in relationships] + [r["to"] for r in relationships]))
                        }
                    else:
                        raise
                else:
                    raise
            
            # 필수 키 확인 및 추가
            required_keys = ["relationships", "students"]
            for key in required_keys:
                if key not in result:
                    logger.warning(f"결과에 필수 키 '{key}'가 없습니다.")
                    if key == "relationships":
                        result[key] = []
                    elif key == "students" and "relationships" in result and result["relationships"]:
                        # relationships에서 학생 목록 추출
                        students = set()
                        for rel in result["relationships"]:
                            if "from" in rel:
                                students.add(rel["from"])
                            if "to" in rel:
                                students.add(rel["to"])
                        result[key] = list(students)
                        logger.info(f"관계 데이터에서 {len(students)}명의 학생을 추출했습니다.")
                    else:
                        result[key] = []
            
            return result
            
        except Exception as e:
            logger.error(f"데이터 구조 분석 실패: {str(e)}")
            # 사용자에게 이해하기 쉬운 오류 메시지 제공
            st.error(f"데이터 분석 중 오류가 발생했습니다: {str(e)}")
            raise Exception(f"데이터 분석 중 오류가 발생했습니다: {str(e)}")
    
    def convert_to_network_data(self, analysis_result):
        """분석 결과를 네트워크 데이터로 변환"""
        try:
            # 관계 데이터 추출
            relationships = analysis_result.get("relationships", [])
            
            # 관계 데이터 확인 및 디버그 출력
            st.write("### 디버그: 관계 데이터 확인")
            st.write("이 정보는 문제 해결을 위한 것입니다.")
            st.json(relationships[:10] if len(relationships) > 10 else relationships)
            
            # 데이터 형식 확인
            if not relationships:
                st.error("관계 데이터가 비어 있습니다. API 응답을 확인해주세요.")
                raise ValueError("관계 데이터가 비어 있습니다.")
            
            # 관계 데이터 형식 확인 및 변환
            standardized_relationships = []
            
            # 다양한 키 이름에 대응
            key_mappings = {
                'from': ['from', 'source', 'student', 'student_from', 'from_student', 'sender', 'respondent'],
                'to': ['to', 'target', 'friend', 'student_to', 'to_student', 'receiver', 'selected'],
                'weight': ['weight', 'value', 'strength', 'count', 'frequency'],
                'type': ['type', 'relationship_type', 'relation', 'category']
            }
            
            for rel in relationships:
                if isinstance(rel, dict):
                    # 표준화된 관계 레코드 생성
                    std_rel = {}
                    
                    # from 필드 매핑
                    for key in key_mappings['from']:
                        if key in rel and rel[key]:
                            std_rel['from'] = rel[key]
                            break
                    
                    # to 필드 매핑
                    for key in key_mappings['to']:
                        if key in rel and rel[key]:
                            std_rel['to'] = rel[key]
                            break
                    
                    # weight 필드 매핑 (기본값 1)
                    std_rel['weight'] = 1
                    for key in key_mappings['weight']:
                        if key in rel and rel[key]:
                            try:
                                std_rel['weight'] = float(rel[key])
                            except (ValueError, TypeError):
                                # 숫자로 변환할 수 없는 경우 기본값 사용
                                pass
                            break
                    
                    # type 필드 매핑 (기본값 'relationship')
                    std_rel['type'] = 'relationship'
                    for key in key_mappings['type']:
                        if key in rel and rel[key]:
                            std_rel['type'] = rel[key]
                            break
                    
                    # 필수 필드가 있는 경우만 추가
                    if 'from' in std_rel and 'to' in std_rel:
                        standardized_relationships.append(std_rel)
                elif isinstance(rel, list) and len(rel) >= 2:
                    # 리스트 형태로 제공된 경우 ([from, to, weight?] 형식)
                    std_rel = {
                        'from': rel[0],
                        'to': rel[1],
                        'weight': float(rel[2]) if len(rel) > 2 and rel[2] is not None else 1,
                        'type': 'relationship'
                    }
                    standardized_relationships.append(std_rel)
            
            # 표준화된 관계 데이터 디버그 출력
            st.write("### 표준화된 관계 데이터")
            st.json(standardized_relationships[:10] if len(standardized_relationships) > 10 else standardized_relationships)
            
            if not standardized_relationships:
                st.error("관계 데이터 변환 실패. 필수 필드('from', 'to')가 없습니다.")
                raise ValueError("관계 데이터에 필수 필드가 없습니다.")
            
            # 표준화된 관계 데이터프레임 생성
            edges_df = pd.DataFrame(standardized_relationships)
            
            # 노드(학생) 목록 추출
            nodes_from_api = analysis_result.get("students", [])
            
            # 관계 데이터에서 노드 추출 (API에서 제공한 노드 목록이 없거나 불완전한 경우)
            nodes_from_relationships = set()
            for rel in standardized_relationships:
                if 'from' in rel:
                    nodes_from_relationships.add(rel['from'])
                if 'to' in rel:
                    nodes_from_relationships.add(rel['to'])
            
            # 두 소스에서 노드 통합
            if nodes_from_api:
                # API에서 제공한 노드 목록 사용하되, 관계 데이터에 있는 노드 추가
                nodes = list(set(nodes_from_api) | nodes_from_relationships)
            else:
                # API에서 노드 목록을 제공하지 않은 경우 관계 데이터에서 추출
                nodes = list(nodes_from_relationships)
            
            # 노드 목록 디버그 출력
            st.write(f"### 추출된 노드 목록 ({len(nodes)}개)")
            st.write(nodes[:20] if len(nodes) > 20 else nodes)
            
            if not nodes:
                st.error("노드 데이터가 비어 있습니다. 학생 목록을 추출할 수 없습니다.")
                raise ValueError("노드 데이터가 비어 있습니다.")
            
            # 노드 데이터프레임 생성
            nodes_df = pd.DataFrame({"id": nodes, "label": nodes})
            
            return {
                "nodes": nodes_df,
                "edges": edges_df,
                "question_types": analysis_result.get("question_types", {})
            }
            
        except Exception as e:
            logger.error(f"네트워크 데이터 변환 실패: {str(e)}")
            st.error(f"네트워크 데이터 변환에 실패했습니다: {str(e)}")
            st.error("API가 반환한 관계 데이터 형식이 예상과 다릅니다. 다시 시도해주세요.")
            raise Exception(f"네트워크 데이터 변환 중 오류가 발생했습니다: {str(e)}")
    
    def process_survey_data(self, sheet_url):
        """전체 데이터 처리 과정 실행"""
        try:
            # 데이터 로드
            df = self.load_from_gsheet(sheet_url)
            
            # 데이터 미리보기 표시
            st.write("### 로드된 설문조사 데이터 (일부)")
            st.dataframe(df.head())
            
            # 데이터 구조 분석
            with st.spinner("AI가 데이터 구조를 분석 중입니다..."):
                analysis_result = self.analyze_data_structure(df)
            
            # 네트워크 데이터로 변환
            with st.spinner("네트워크 데이터 생성 중..."):
                network_data = self.convert_to_network_data(analysis_result)
            
            return network_data
            
        except Exception as e:
            logger.error(f"설문조사 데이터 처리 실패: {str(e)}")
            raise Exception(f"데이터 처리 중 오류가 발생했습니다: {str(e)}") 