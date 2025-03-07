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
import requests
from io import StringIO

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
            
            # 예시 데이터 처리 (하드코딩된 예시 데이터 처리)
            if sheet_id in ["1iBAe4rYrQ8MuQyKVlZ-awqGSiAr9pMAaLK8y5BSrIX8", "1-Nv-aAQkUkS9KYJwF1VlnY6qRKEO5SnNVQfmIZLNDfQ"]:
                # 예시 1: 가상 학급 친구 관계
                if sheet_id == "1iBAe4rYrQ8MuQyKVlZ-awqGSiAr9pMAaLK8y5BSrIX8":
                    # 가상의 학급 친구 관계 데이터 생성
                    data = {
                        '학생 이름': ['김민준', '이지훈', '박서준', '정도윤', '최예준', '강현우', '윤우진', '장민호', '임지용', '조승현'],
                        '함께 공부하고 싶은 친구 (1순위)': ['이지훈', '최예준', '김민준', '최예준', '정도윤', '윤우진', '장민호', '임지용', '조승현', '김민준'],
                        '함께 공부하고 싶은 친구 (2순위)': ['박서준', '박서준', '장우진', '김민준', '김민준', '장민호', '강현우', '윤우진', '장민호', '이지훈'],
                        '도움을 청하고 싶은 친구 (1순위)': ['정도윤', '김민준', '이지훈', '박서준', '이지훈', '임지용', '강현우', '조승현', '윤우진', '임지용']
                    }
                # 예시 2: 협업 선호도
                else:
                    # 가상의 협업 선호도 데이터 생성
                    data = {
                        '응답자': ['김민준', '이지훈', '박서준', '정도윤', '최예준', '강현우', '윤우진', '장민호', '임지용', '조승현'],
                        '프로젝트에서 함께 일하고 싶은 사람': ['이지훈,박서준,정도윤', '김민준,최예준,박서준', '김민준,이지훈,장우진', 
                                         '최예준,박서준,김민준', '정도윤,김민준,이지훈', '윤우진,장민호,임지용',
                                         '장민호,강현우,조승현', '임지용,윤우진,조승현', '조승현,장민호,윤우진', '임지용,장민호,김민준'],
                        '일하는 스타일이 비슷한 사람': ['정도윤,최예준', '박서준,최예준', '이지훈,김민준', '최예준,김민준', '정도윤,박서준',
                                      '임지용,장민호', '강현우,장민호', '윤우진,임지용', '조승현,윤우진', '장민호,임지용']
                    }
                
                # 데이터프레임 생성
                df = pd.DataFrame(data)
                return df
            
            # 일반 데이터 처리 (일반적인 구글 시트 URL 처리)
            try:
                # 설문조사 데이터는 공개 시트라고 가정
                # 공개 시트의 경우 인증 없이 CSV로 직접 다운로드 가능
                csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                
                # pandas로 CSV 데이터 로드 (타임아웃 및 오류 처리 개선)
                # HTTP 요청 설정 개선
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # 타임아웃 및 인증 오류 처리 개선
                response = requests.get(csv_export_url, headers=headers, timeout=30)
                response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
                
                # CSV 데이터를 StringIO 객체로 변환
                csv_data = StringIO(response.text)
                
                # pandas로 CSV 데이터 로드
                df = pd.read_csv(csv_data)
                
                # 처리 완료
                return df
                
            except requests.exceptions.HTTPError as e:
                # Google API 오류 처리
                logger.error(f"구글 시트 접근 오류: {str(e)}")
                if "404" in str(e):
                    raise ValueError("해당 구글 시트를 찾을 수 없습니다. 공유 설정을 확인해주세요.")
                elif "403" in str(e):
                    raise ValueError("구글 시트에 접근 권한이 없습니다. 공유 설정을 확인해주세요.")
                elif "400" in str(e):
                    raise ValueError("잘못된 요청입니다. 구글 시트 ID가 유효한지 확인해주세요.")
                else:
                    raise ValueError(f"구글 시트 데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")
            except Exception as e:
                logger.error(f"구글 시트 데이터 로드 중 일반 오류: {str(e)}")
                raise ValueError(f"구글 시트 데이터를 로드하는 중 오류가 발생했습니다: {str(e)}")
                
        except Exception as e:
            logger.error(f"구글 시트 데이터 로드 실패: {str(e)}")
            raise Exception(f"구글 시트 데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")
    
    def extract_json_from_text(self, text):
        """텍스트에서 JSON 부분 추출 및 정제"""
        try:
            original_text = text  # 원본 텍스트 저장
            
            # 디버그를 위해 원본 응답 저장
            st.session_state["original_api_response"] = text
            
            # 마크다운 코드 블록(```json) 처리
            if "```json" in text or "```" in text:
                # 코드 블록 내용 추출
                code_block_pattern = r'```(?:json)?\s*\n([\s\S]*?)\n\s*```'
                code_blocks = re.findall(code_block_pattern, text)
                
                if code_blocks:
                    # 가장 큰 코드 블록 선택 (일반적으로 전체 JSON)
                    text = max(code_blocks, key=len)
                    logger.info(f"마크다운 코드 블록에서 JSON 추출 성공 (길이: {len(text)})")
                    st.session_state["extracted_code_block"] = text
            
            # JSON 시작과 끝 찾기 (중괄호로 둘러싸인 부분)
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            # 유효한 JSON 범위가 있는 경우
            if json_start >= 0 and json_end > json_start:
                json_text = text[json_start:json_end]
                logger.info(f"중괄호로 둘러싸인 JSON 추출 (길이: {len(json_text)})")
                
                # JSON 문자열 정제
                # 1. 후행 쉼표 제거
                cleaned_json = re.sub(r',\s*}', '}', json_text)
                cleaned_json = re.sub(r',\s*]', ']', cleaned_json)
                
                # 2. 누락된 쌍따옴표 처리
                cleaned_json = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', cleaned_json)
                
                # 3. 홑따옴표를 쌍따옴표로 변환
                cleaned_json = cleaned_json.replace("'", '"')
                
                # 4. 불완전한 JSON 처리 - 마지막 객체가 불완전한 경우
                # 마지막 객체가 완전하지 않은 경우 (닫는 중괄호 누락)
                if cleaned_json.count('{') > cleaned_json.count('}'):
                    # 마지막 완전한 객체까지만 유지
                    last_complete_obj = cleaned_json.rfind('},')
                    if last_complete_obj > 0:
                        cleaned_json = cleaned_json[:last_complete_obj+1] + ']}'
                        logger.warning("불완전한 JSON 감지: 마지막 객체를 제거하고 JSON을 닫았습니다.")
                
                # 5. 불완전한 JSON 처리 - 마지막 배열이 불완전한 경우
                # 마지막 배열이 완전하지 않은 경우 (닫는 대괄호 누락)
                if cleaned_json.count('[') > cleaned_json.count(']'):
                    # 마지막 완전한 배열까지만 유지하거나 닫는 대괄호 추가
                    cleaned_json = cleaned_json + ']' * (cleaned_json.count('[') - cleaned_json.count(']'))
                    logger.warning("불완전한 JSON 감지: 닫는 대괄호를 추가했습니다.")
                
                # 6. 이스케이프되지 않은 따옴표 처리
                cleaned_json = re.sub(r'(?<!\\)"([^"]*?)(?<!\\)"', r'"\1"', cleaned_json)
                
                # 정제된 JSON 저장
                st.session_state["cleaned_json"] = cleaned_json
                
                # 파싱 테스트
                try:
                    json.loads(cleaned_json)
                    logger.info("정제된 JSON이 유효합니다")
                    return cleaned_json
                except json.JSONDecodeError as e:
                    logger.warning(f"정제된 JSON이 여전히 유효하지 않습니다: {str(e)}")
                    
                    # 7. 추가 정제 시도 - 특정 위치의 오류 수정
                    error_msg = str(e)
                    if "Expecting ',' delimiter" in error_msg:
                        # 오류 위치 추출
                        match = re.search(r'line (\d+) column (\d+)', error_msg)
                        if match:
                            line, col = int(match.group(1)), int(match.group(2))
                            # 줄 단위로 분할
                            json_lines = cleaned_json.split('\n')
                            if 0 < line <= len(json_lines):
                                # 문제가 있는 줄 수정 시도
                                problem_line = json_lines[line-1]
                                if col < len(problem_line):
                                    # 콤마 누락 추정 위치에 콤마 추가
                                    fixed_line = problem_line[:col] + ',' + problem_line[col:]
                                    json_lines[line-1] = fixed_line
                                    fixed_json = '\n'.join(json_lines)
                                    
                                    # 수정된 JSON 테스트
                                    try:
                                        json.loads(fixed_json)
                                        logger.info("콤마 추가 후 JSON이 유효해졌습니다")
                                        return fixed_json
                                    except json.JSONDecodeError:
                                        logger.warning("콤마 추가 시도 후에도 JSON이 유효하지 않습니다")
                    
                    # 8. 마지막 시도 - 관계 배열만 추출하여 새 JSON 구성
                    relationships_pattern = r'"relationships"\s*:\s*\[([\s\S]*?)\]'
                    rel_match = re.search(relationships_pattern, cleaned_json)
                    if rel_match:
                        rel_content = rel_match.group(1)
                        # 불완전한 마지막 객체 제거
                        if rel_content.strip().endswith(','):
                            rel_content = rel_content.rstrip(',')
                        
                        # 새 JSON 구성
                        minimal_json = '{"relationships": [' + rel_content + ']}'
                        try:
                            json.loads(minimal_json)
                            logger.info("관계 배열만 추출하여 유효한 JSON 생성")
                            return minimal_json
                        except json.JSONDecodeError:
                            logger.warning("관계 배열 추출 후에도 JSON이 유효하지 않습니다")
                    
                    # 오류가 있지만 일단 정제된 JSON 반환 (이후 백업 로직 활용)
                    return cleaned_json
            
            # JSON 객체를 찾을 수 없는 경우, 원본 텍스트에서 직접 관계 추출 시도
            logger.warning("정규 JSON 객체를 찾지 못했습니다. 원본 응답에서 직접 관계 추출을 시도합니다.")
            
            # 원본 텍스트를 그대로 반환 (이후 백업 로직에서 처리)
            return original_text
            
        except Exception as e:
            logger.error(f"JSON 추출 실패: {str(e)}")
            logger.error(traceback.format_exc())
            st.error(f"JSON 추출 중 오류가 발생했습니다: {str(e)}")
            st.code(text[:1000] + "..." if len(text) > 1000 else text, language="text")
            
            # 오류가 발생해도 원본 텍스트 반환 (이후 백업 로직에서 처리)
            return text
    
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
            
            # API 응답 전체를 디버깅 목적으로 로깅 (UI에는 표시하지 않음)
            logger.info(f"Gemini API 응답: {analysis_result[:1000]}...")
            
            # 디버그 정보를 UI에 표시하지 않음
            # with st.expander("디버그: API 응답 (개발자용)", expanded=False):
            #     st.text_area("원본 응답:", value=analysis_result, height=200)
            
            # JSON 문자열 추출 및 정제
            json_str = self.extract_json_from_text(analysis_result)
            
            # 디버그 정보를 UI에 표시하지 않음
            # with st.expander("디버그: 추출된 JSON (개발자용)", expanded=False):
            #     st.text_area("정제된 JSON:", value=json_str, height=200)
            
            # 결과 객체 변수 초기화
            result = {"relationships": [], "students": []}
            
            # JSON 파싱 시도
            try:
                # 정제된 JSON 파싱 시도
                parsed_json = json.loads(json_str)
                logger.info("JSON 파싱 성공")
                
                # 파싱된 JSON에 필요한 키가 있는지 확인
                if "relationships" in parsed_json and parsed_json["relationships"]:
                    result = parsed_json  # 파싱 결과 사용
                    logger.info(f"유효한 relationships 키가 발견되었습니다. {len(parsed_json['relationships'])}개의 관계가 있습니다.")
                else:
                    logger.warning("파싱된 JSON에 유효한 relationships 키가 없습니다. 직접 관계 추출을 시도합니다.")
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {str(e)}")
                st.info("데이터 구조를 자동으로 분석하고 있습니다. 잠시만 기다려주세요.")
            
            # 백업 로직: API 응답에서 직접 관계 추출
            if not result.get("relationships"):
                # 사용자에게 진행 상황만 간략히 알림
                st.info("관계 데이터를 추출하고 있습니다. 잠시만 기다려주세요.")
                
                # 정규식 패턴 - 다양한 형식 지원
                patterns = [
                    # 기본 {"from": "학생명", "to": "학생명"} 패턴
                    r'{"from":\s*"([^"]+)",\s*"to":\s*"([^"]+)"',
                    # 확장 패턴 - 쉼표와 콜론 주변 공백 다양하게 처리
                    r'{\s*"from"\s*:\s*"([^"]+)"\s*,\s*"to"\s*:\s*"([^"]+)"',
                    # 속성 순서가 다른 경우 처리
                    r'{\s*"to"\s*:\s*"([^"]+)"\s*,\s*"from"\s*:\s*"([^"]+)"',
                ]
                
                relationships = []
                for pattern in patterns:
                    matches = re.finditer(pattern, analysis_result)
                    for match in matches:
                        if pattern.startswith(r'{\s*"to"'):
                            # to, from 순서로 그룹이 있는 패턴
                            to_student, from_student = match.groups()
                        else:
                            # from, to 순서로 그룹이 있는 패턴
                            from_student, to_student = match.groups()
                        
                        # 중복 제거를 위한 키 생성
                        rel_key = f"{from_student}-{to_student}"
                        
                        # 이미 추가된 관계인지 확인
                        existing_keys = [f"{r['from']}-{r['to']}" for r in relationships]
                        if rel_key not in existing_keys:
                            relationships.append({
                                "from": from_student,
                                "to": to_student,
                                "weight": 1,
                                "type": "relationship"
                            })
                
                # 추출된 관계가 있으면 result 업데이트
                if relationships:
                    logger.info(f"직접 추출로 {len(relationships)}개의 관계를 찾았습니다.")
                    result["relationships"] = relationships
                    
                    # 학생 목록도 관계에서 추출
                    students = set()
                    for rel in relationships:
                        students.add(rel["from"])
                        students.add(rel["to"])
                    result["students"] = list(students)
                    logger.info(f"관계에서 {len(students)}명의 학생을 추출했습니다.")
                else:
                    logger.warning("API 응답에서 관계를 추출할 수 없습니다.")
            
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
            
            # 최종 결과 확인
            if not result["relationships"]:
                st.error("모든 방법을 시도했지만 관계 데이터를 추출할 수 없습니다.")
                raise ValueError("관계 데이터를 추출할 수 없습니다. API 응답을 확인해주세요.")
            
            # 디버그 정보 표시하지 않음
            # with st.expander("디버그: 최종 데이터 구조 (개발자용)", expanded=False):
            #     st.write("관계 수:", len(result["relationships"]))
            #     st.write("학생 수:", len(result["students"]))
            #     st.json({"relationships_sample": result["relationships"][:5], "students_sample": result["students"][:5]})
            
            # 대신 사용자에게 간략한 성공 메시지 표시
            st.success(f"{len(result['students'])}명의 학생과 {len(result['relationships'])}개의 관계를 성공적으로 추출했습니다.")
            
            return result
            
        except Exception as e:
            logger.error(f"데이터 구조 분석 실패: {str(e)}")
            # 사용자에게 이해하기 쉬운 오류 메시지 제공
            st.error(f"데이터 분석 중 오류가 발생했습니다: {str(e)}")
            
            # 디버그 정보 표시하지 않음
            # if "original_api_response" in st.session_state:
            #     with st.expander("디버그: 원본 API 응답", expanded=True):
            #         st.text_area("원본 응답:", value=st.session_state["original_api_response"], height=200)
            
            raise Exception(f"데이터 분석 중 오류가 발생했습니다: {str(e)}")
    
    def convert_to_network_data(self, analysis_result):
        """분석 결과를 네트워크 데이터로 변환"""
        try:
            # 관계 데이터 추출
            relationships = analysis_result.get("relationships", [])
            
            # 관계 데이터 확인 - 디버그 출력 제거
            # st.write("### 디버그: 관계 데이터 확인")
            # st.write("이 정보는 문제 해결을 위한 것입니다.")
            # st.json(relationships[:10] if len(relationships) > 10 else relationships)
            
            # 간략한 메시지로 대체
            st.info("관계 데이터를 네트워크 형식으로 변환하고 있습니다.")
            
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
            # st.write("### 표준화된 관계 데이터")
            # st.json(standardized_relationships[:10] if len(standardized_relationships) > 10 else standardized_relationships)
            
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
            # st.write(f"### 추출된 노드 목록 ({len(nodes)}개)")
            # st.write(nodes[:20] if len(nodes) > 20 else nodes)
            
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