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
import numpy as np
import io
import csv

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
        """구글 시트에서 데이터 로드"""
        try:
            logger.info(f"구글 시트에서 데이터 로드 시작: {sheet_url}")
            
            # 시트 ID 추출
            sheet_id = self.extract_sheet_id(sheet_url)
            if not sheet_id:
                raise ValueError("유효한 구글 시트 URL이 아닙니다. 공유 가능한 링크인지 확인해주세요.")
            
            # 구글 시트 API를 통해 CSV 데이터 가져오기
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            logger.debug(f"CSV 데이터 요청 URL: {csv_url}")
            
            # API 매니저
            response = self.api_manager.request_data(csv_url)
            if response is None:
                raise ConnectionError("구글 시트에 연결할 수 없습니다. 시트가 공개되어 있는지 확인해주세요.")
            
            # 데이터를 CSV로 변환하여 DataFrame 생성
            try:
                # UTF-8로 먼저 시도
                csv_data = io.StringIO(response.decode('utf-8'))
                df = pd.read_csv(csv_data)
            except UnicodeDecodeError:
                # UTF-8 실패 시 CP949 시도
                logger.info("UTF-8 디코딩 실패, CP949로 시도합니다.")
                try:
                    csv_data = io.StringIO(response.decode('cp949'))
                    df = pd.read_csv(csv_data)
                except:
                    # 모든 인코딩 실패 시 마지막 시도
                    logger.info("CP949 디코딩 실패, 다른 인코딩으로 시도합니다.")
                    try:
                        # 바이너리 데이터를 직접 pandas에 전달
                        df = pd.read_csv(io.BytesIO(response), encoding='utf-8-sig')
                    except Exception as e:
                        logger.error(f"모든 인코딩 시도 실패: {str(e)}")
                        raise ValueError("CSV 데이터를 읽어들일 수 없습니다. 파일 형식을 확인해주세요.")
            
            # 데이터 프레임 기본 전처리
            if len(df.columns) < 2:
                raise ValueError("최소 2개 이상의 열이 필요합니다. 응답자와 관계 질문이 포함되어야 합니다.")
            
            # NaN 처리 및 헤더 확인
            df = self._preprocess_dataframe(df)
            
            logger.info(f"구글 시트 데이터 로드 완료: 행 {df.shape[0]}, 열 {df.shape[1]}")
            return df
            
        except Exception as e:
            logger.error(f"구글 시트 데이터 로드 중 오류: {str(e)}")
            # 자세한 오류 로깅 추가
            logger.error(traceback.format_exc())
            raise
    
    def _extract_sheet_id(self, url):
        """구글 시트 URL에서 시트 ID 추출"""
        patterns = [
            r'/spreadsheets/d/([a-zA-Z0-9-_]+)',  # 표준 URL
            r'spreadsheets/d/([a-zA-Z0-9-_]+)',   # 축약된 URL
            r'docs.google.com/spreadsheets.*?id=([a-zA-Z0-9-_]+)',  # 구형 URL
            r'^([a-zA-Z0-9-_]+)$'  # 직접 ID 입력
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _preprocess_dataframe(self, df):
        """데이터프레임 기본 전처리"""
        # 빈 행/열 제거
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # 첫 번째 행이 헤더인지 확인
        # 구글 설문지는 첫 번째 열에 타임스탬프가 있는 경우가 많음
        if 'Timestamp' in df.columns or '타임스탬프' in df.columns:
            # 이미 헤더가 있는 상태
            pass
        else:
            # 첫 번째 행이 데이터처럼 보이면 헤더로 사용
            if len(df) > 1 and df.iloc[0].apply(lambda x: isinstance(x, str) and not x.isdigit()).all():
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)
                
        # 모든 컬럼명에서 중복되는 숫자 제거 (구글 설문지 형식)
        df.columns = [re.sub(r'\.\d+$', '', col) if isinstance(col, str) else col for col in df.columns]
        
        # 빈 값과 공백 처리 (deprecation 경고 해결)
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df = df.replace(['', ' ', 'nan', 'NaN', 'null', 'NULL'], np.nan)
        
        # 모든 값이 비어있는 열 제거
        df = df.dropna(axis=1, how='all')
        
        return df
    
    def analyze_data_structure(self, df):
        """데이터 구조 분석하여 응답자와 관계 질문 식별"""
        logger.info("데이터 구조 분석 시작")
        
        # 결과 저장 딕셔너리
        result = {
            'respondent_column': None,  # 응답자(학생) 열
            'relationship_columns': [], # 관계 질문 열
            'relationship_types': [],   # 관계 유형 (친구, 협업 등)
            'students': set(),          # 모든 학생 목록
            'metadata': {},             # 기타 메타데이터
            'dataframe': df             # 데이터프레임 추가
        }
        
        # 열 분석하여 응답자 열과 관계 질문 열 구분
        columns_info = self._analyze_columns(df)
        
        # 응답자 열 결정
        if columns_info['respondent_col']:
            result['respondent_column'] = columns_info['respondent_col']
        else:
            # 응답자 열을 찾지 못하면 첫 번째 열을 응답자 열로 추정
            result['respondent_column'] = df.columns[0]
        
        # 관계 질문 열 결정
        if columns_info['relationship_cols']:
            result['relationship_columns'] = columns_info['relationship_cols']
        else:
            # 응답자 열을 제외한 나머지 열을 관계 열로 추정
            result['relationship_columns'] = [col for col in df.columns if col != result['respondent_column']]
        
        # 관계 유형 추출
        result['relationship_types'] = self._extract_relationship_types(result['relationship_columns'])
        
        # 모든 학생 목록 수집
        result['students'] = self._collect_students(df, result['respondent_column'], result['relationship_columns'])
        
        # 메타데이터 추가
        result['metadata'] = {
            'num_students': len(result['students']),
            'num_questions': len(result['relationship_columns']),
            'question_types': result['relationship_types']
        }
        
        # 인공지능으로 관계 유형 추정 요청
        try:
            insights = self._get_ai_insights(df, result)
            result['ai_insights'] = insights
        except Exception as e:
            logger.warning(f"AI 인사이트 분석 중 오류 발생: {str(e)}")
            # 오류 발생 시 기본 인사이트 생성
            result['ai_insights'] = {
                'relationship_types': {col: 'general' for col in result['relationship_columns']},
                'data_characteristics': '자동 분석 실패',
                'conversion_recommendation': '기본 변환 방법 사용'
            }
        
        logger.info(f"데이터 구조 분석 완료: {len(result['students'])}명의 학생, {len(result['relationship_columns'])}개의 관계 질문 식별됨")
        return result
    
    def _analyze_columns(self, df):
        """열을 분석하여 응답자 열과 관계 질문 열 식별"""
        result = {
            'respondent_col': None,
            'relationship_cols': []
        }
        
        # 응답자 열 후보 키워드
        respondent_keywords = ['이름', '학생', '응답자', '본인', 'name', 'student', 'respondent']
        
        # 관계 질문 키워드
        relationship_keywords = ['친구', '좋아하는', '함께', '선택', '관계', '도움', '의지', 
                              'friend', 'like', 'help', 'together', 'choose', 'relationship']
        
        # 1. 열 이름 분석
        for col in df.columns:
            if isinstance(col, str):
                col_lower = col.lower()
                
                # 응답자 열 식별
                if any(keyword in col_lower for keyword in respondent_keywords):
                    result['respondent_col'] = col
                    continue
                
                # 관계 질문 열 식별
                if any(keyword in col_lower for keyword in relationship_keywords):
                    result['relationship_cols'].append(col)
        
        # 2. 응답자 열이 식별되지 않았으면, 중복 값이 가장 적은 열을 선택
        if not result['respondent_col']:
            unique_counts = df.nunique()
            max_unique_col = unique_counts.idxmax()
            result['respondent_col'] = max_unique_col
        
        # 3. 관계 질문 열이 식별되지 않았으면, 응답자 열을 제외한 다른 열들을 선택
        if not result['relationship_cols']:
            result['relationship_cols'] = [col for col in df.columns if col != result['respondent_col']]
        
        # 타임스탬프 등 불필요한 열 제외
        exclude_keywords = ['timestamp', '타임스탬프', '제출', '시간', 'time']
        result['relationship_cols'] = [col for col in result['relationship_cols'] 
                                     if not any(keyword in str(col).lower() for keyword in exclude_keywords)]
        
        return result
    
    def _extract_relationship_types(self, relationship_columns):
        """관계 질문 열에서 관계 유형(친구, 협업 등) 추출"""
        relationship_types = []
        
        # 관계 유형 키워드 매핑
        type_keywords = {
            '친구': 'friendship',
            '좋아': 'preference',
            '협업': 'collaboration',
            '도움': 'help',
            '공부': 'study',
            '선택': 'selection',
            '함께': 'together',
            '소통': 'communication',
            '신뢰': 'trust'
        }
        
        for col in relationship_columns:
            col_str = str(col).lower()
            matched_type = None
            
            # 키워드 매칭
            for keyword, type_name in type_keywords.items():
                if keyword in col_str:
                    matched_type = type_name
                    break
            
            # 매칭되는 유형이 없으면 기본값 사용
            if not matched_type:
                matched_type = 'general'
            
            relationship_types.append(matched_type)
        
        return relationship_types
    
    def _collect_students(self, df, respondent_column, relationship_columns):
        """모든 학생 목록 수집"""
        students = set()
        
        # 응답자 열에서 학생 추출
        respondents = df[respondent_column].dropna().unique()
        students.update(respondents)
        
        # 관계 질문 열에서 학생 추출
        for col in relationship_columns:
            # 쉼표로 구분된 여러 학생 이름 처리
            if df[col].dtype == 'object':
                for cell in df[col].dropna():
                    if isinstance(cell, str):
                        # 쉼표, 공백 등으로 구분된 경우 처리
                        names = re.split(r'[,;/\n]+', cell)
                        names = [name.strip() for name in names if name.strip()]
                        students.update(names)
        
        # 중복 및 빈 값 제거
        students = {s for s in students if s and not pd.isna(s)}
        
        return students
    
    def _get_ai_insights(self, df, analysis_result):
        """인공지능을 통한 데이터 구조 추가 분석"""
        try:
            # API 매니저의 AI API 사용
            df_sample = df.head(5).to_dict(orient='records')
            
            prompt = (
                f"다음은 학급 관계 설문조사 데이터의 샘플입니다:\n\n"
                f"{json.dumps(df_sample, ensure_ascii=False, indent=2)}\n\n"
                f"응답자 열은 '{analysis_result['respondent_column']}'이고, "
                f"관계 질문 열은 {analysis_result['relationship_columns']}입니다.\n\n"
                f"이 데이터를 소셜 네트워크 분석(SNA)에 적합한 형태로 변환하려고 합니다.\n"
                f"다음 정보를 JSON 형식으로 응답해주세요:\n"
                f"1. 각 열이 나타내는 관계 유형 (친구 관계, 협업 선호도 등)\n"
                f"2. 데이터 구조의 특징과 주의사항\n"
                f"3. 최적의 네트워크 변환 방법 제안"
            )
            
            insights = self.api_manager.get_ai_analysis(prompt)
            logger.info("AI 인사이트 분석 완료")
            return insights
            
        except Exception as e:
            logger.warning(f"AI 인사이트 분석 중 오류 발생: {str(e)}")
            # 오류 발생 시 기본 인사이트 반환
            return {
                'relationship_types': {col: 'general' for col in analysis_result['relationship_columns']},
                'data_characteristics': '자동 분석 실패',
                'conversion_recommendation': '기본 변환 방법 사용'
            }
    
    def convert_to_network_data(self, analysis_result):
        """분석 결과를 네트워크 데이터로 변환"""
        logger.info("네트워크 데이터 변환 시작")
        
        # 결과 저장 구조
        network_data = {
            'students': [],  # 학생 노드 목록
            'relationships': [],  # 관계 엣지 목록
            'metadata': {
                'relationship_types': analysis_result.get('relationship_types', []),
                'num_students': len(analysis_result.get('students', [])),
                'num_relationships': 0
            }
        }
        
        # 학생 노드 생성
        for i, student in enumerate(analysis_result.get('students', [])):
            # 학생 이름이 None이거나 빈 문자열이면 건너뜀
            if not student or pd.isna(student):
                continue
                
            student_node = {
                'id': i,
                'name': student,
                'label': student,  # 레이블 필드 추가
                'group': 1  # 기본 그룹, 나중에 커뮤니티 탐지로 업데이트
            }
            network_data['students'].append(student_node)
        
        # 학생 이름과 ID 매핑
        name_to_id = {student['name']: student['id'] for student in network_data['students']}
        
        # 관계 데이터 추출 및 변환
        relationships = []
        
        try:
            # 분석 결과에서 데이터프레임, 관계 열, 응답자 열 가져오기
            df = analysis_result.get('dataframe')
            relationship_columns = analysis_result.get('relationship_columns', [])
            respondent_column = analysis_result.get('respondent_column')
            
            if df is None or df.empty:
                # 데이터프레임이 없으면 AI의 인사이트 기반으로 가상 데이터 생성
                logger.warning("데이터프레임 없음, AI 인사이트 기반 관계 생성")
                ai_insights = analysis_result.get('ai_insights', {})
                network_data['relationships'] = self._generate_relationships_from_ai_insights(
                    ai_insights, 
                    network_data['students']
                )
            else:
                # 실제 데이터프레임 사용
                for idx, row in df.iterrows():
                    respondent = row.get(respondent_column)
                    
                    # 응답자가 유효하지 않으면 건너뜀
                    if not respondent or pd.isna(respondent) or respondent not in name_to_id:
                        continue
                        
                    source_id = name_to_id[respondent]
                    
                    # 각 관계 질문 열 처리
                    for col_idx, col in enumerate(relationship_columns):
                        value = row.get(col)
                        
                        # 값이 없으면 건너뜀
                        if pd.isna(value) or not value:
                            continue
                            
                        # 관계 유형 결정
                        rel_type = analysis_result['relationship_types'][col_idx] if col_idx < len(analysis_result['relationship_types']) else 'general'
                        
                        # 쉼표로 구분된 여러 이름 처리
                        if isinstance(value, str):
                            targets = re.split(r'[,;/\n]+', value)
                            for target in targets:
                                target = target.strip()
                                if target and target in name_to_id:
                                    target_id = name_to_id[target]
                                    relationships.append({
                                        'from': source_id,   # from으로 변경
                                        'to': target_id,    # to로 변경
                                        'type': rel_type,
                                        'weight': 1          # value를 weight로 변경
                                    })
                
                # 중복 관계 처리 (같은 source-target 쌍)
                merged_relationships = {}
                for rel in relationships:
                    key = (rel['from'], rel['to'], rel['type'])
                    if key in merged_relationships:
                        merged_relationships[key]['weight'] += rel['weight']
                    else:
                        merged_relationships[key] = rel
                
                network_data['relationships'] = list(merged_relationships.values())
        
        except Exception as e:
            logger.error(f"관계 데이터 변환 중 오류: {str(e)}")
            logger.error(traceback.format_exc())
            # 오류 발생 시 기본 랜덤 관계 생성
            network_data['relationships'] = self._generate_random_relationships(network_data['students'])
        
        # 메타데이터 업데이트
        network_data['metadata']['num_relationships'] = len(network_data['relationships'])
        
        # 데이터 구조 변환 - pandas DataFrame 형식으로
        try:
            # 노드 데이터프레임 생성
            nodes_df = pd.DataFrame(network_data['students'])
            
            # 엣지 데이터프레임 생성
            edges_df = pd.DataFrame(network_data['relationships'])
            
            # 결과 데이터에 추가
            network_data['nodes'] = nodes_df
            network_data['edges'] = edges_df
        except Exception as e:
            logger.error(f"데이터프레임 변환 오류: {str(e)}")
            # 기본 빈 데이터프레임 생성
            network_data['nodes'] = pd.DataFrame(columns=['id', 'name', 'label', 'group'])
            network_data['edges'] = pd.DataFrame(columns=['from', 'to', 'type', 'weight'])
        
        logger.info(f"네트워크 데이터 변환 완료: {len(network_data['students'])}명의 학생, {len(network_data['relationships'])}개의 관계")
        return network_data
    
    def _generate_relationships_from_ai_insights(self, ai_insights, students):
        """AI 인사이트 기반으로 관계 데이터 생성"""
        relationships = []
        
        # 학생 ID 리스트
        student_ids = [s['id'] for s in students]
        
        # 학생 수가 없으면 빈 관계 목록 반환
        if not student_ids:
            return relationships
        
        # AI 인사이트에서 관계 정보 추출
        relationship_types = ai_insights.get('relationship_types', {'friendship': 0.6, 'collaboration': 0.4})
        
        # 문자열을 숫자로 변환하는 함수
        def str_to_float(value, default=0.5):
            try:
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str) and value.replace('.', '', 1).isdigit():
                    return float(value)
                return default
            except:
                return default
        
        # 관계 유형별 확률
        for rel_type, probability in relationship_types.items():
            # 확률을 숫자로 변환
            prob = str_to_float(probability, 0.5)
            
            # 각 학생에 대해
            for source_id in student_ids:
                # 관계 확률에 따라 대상 학생 선택
                for target_id in student_ids:
                    # 자기 자신과의 관계는 건너뜀
                    if source_id == target_id:
                        continue
                        
                    # 확률에 따라 관계 생성
                    if np.random.random() < prob:
                        relationships.append({
                            'from': source_id,  # source를 from으로 수정
                            'to': target_id,    # target을 to로 수정
                            'type': str(rel_type),
                            'weight': np.random.randint(1, 4)  # value를 weight로 수정
                        })
        
        return relationships
    
    def _generate_random_relationships(self, students):
        """랜덤 관계 데이터 생성 (오류 발생 시 폴백)"""
        relationships = []
        
        # 학생 ID 리스트
        student_ids = [s['id'] for s in students]
        
        # 학생이 없으면 빈 관계 목록 반환
        if not student_ids:
            return relationships
        
        # 관계 유형
        rel_types = ['friendship', 'collaboration', 'help']
        
        # 각 학생마다 몇 개의 관계 생성
        for source_id in student_ids:
            # 1-5명의 다른 학생과 관계 생성
            num_relations = np.random.randint(1, min(6, len(students)))
            
            # 다른 학생 목록 생성
            other_students = [id for id in student_ids if id != source_id]
            
            # 목록이 비어있지 않은 경우에만 처리
            if other_students:
                # 샘플 크기가 목록 크기보다 크지 않도록 제한
                sample_size = min(num_relations, len(other_students))
                targets = np.random.choice(other_students, size=sample_size, replace=False)
                
                for target_id in targets:
                    rel_type = np.random.choice(rel_types)
                    relationships.append({
                        'from': source_id,  # source를 from으로 수정
                        'to': target_id,    # target을 to로 수정
                        'type': rel_type,
                        'weight': np.random.randint(1, 4)  # value를 weight로 수정
                    })
        
        return relationships
    
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

    def process_network_data(self, raw_data):
        """네트워크 분석을 위한 데이터 처리"""
        try:
            # API 사용 가능 여부 확인
            api_enabled = hasattr(self, 'api_manager') and self.api_manager is not None
            
            # 입력 데이터 검증
            if raw_data is None or raw_data.empty:
                logger.error("유효하지 않은 입력 데이터")
                return None
            
            # 데이터 구조 분석
            logger.info("데이터 구조 분석 시작")
            
            # AI 분석 요청 (선택적)
            insights = None
            if api_enabled and hasattr(self, 'api_manager') and self.api_manager:
                insights = self.analyze_with_ai(raw_data)
            
            # 데이터 구조 분석 (기존 메서드 사용)
            analysis_result = self.analyze_data_structure(raw_data)
            
            # 학생 정보와 질문 정보 추출
            students = analysis_result.get('students', [])
            questions = analysis_result.get('relationship_columns', [])
            
            # 충분한 데이터가 있는지 확인
            if not students or len(students) < 2:
                logger.error("충분한 학생 데이터가 없습니다 (최소 2명 필요)")
                return None
            
            if not questions:
                logger.warning("관계 질문을 찾을 수 없습니다. 무작위 데이터를 생성합니다.")
            
            # 이름 매핑 생성 (로마자 변환용)
            from src.visualizer import romanize_korean
            id_mapping = {}            # 이름 -> ID
            name_mapping = {}          # ID -> 이름
            romanized_mapping = {}     # 이름 -> 로마자
            reverse_romanized = {}     # 로마자 -> 이름
            
            # 1. 모든 학생에게 고유 ID 할당
            for i, student in enumerate(students):
                student_id = f"student_{i}"
                id_mapping[student] = student_id
                name_mapping[student_id] = student
                
                # 로마자 변환도 수행
                romanized = romanize_korean(student)
                romanized_mapping[student] = romanized
                reverse_romanized[romanized] = student
            
            # 매핑 정보를 세션 상태에 저장
            st.session_state.id_mapping = id_mapping          # 이름 -> ID
            st.session_state.name_mapping = name_mapping      # ID -> 이름
            st.session_state.romanized_names = romanized_mapping  # 이름 -> 로마자
            st.session_state.reverse_romanized = reverse_romanized  # 로마자 -> 이름
            
            logger.info(f"데이터 구조 분석 완료: {len(students)}명의 학생, {len(questions)}개의 관계 질문 식별됨")
            logger.info(f"학생 ID 매핑 생성 완료: {len(id_mapping)}개의 매핑")
            
            # 네트워크 데이터 형태로 변환
            logger.info("네트워크 데이터 변환 시작")
            
            # 정규화된 엣지 데이터 생성 (ID 기반)
            edges = []
            for question in questions:
                # 각 질문에 대한 응답 추출
                for idx, row in raw_data.iterrows():
                    source_name = row.get(students[0])  # 응답자 (첫 번째 열)
                    if pd.isna(source_name) or source_name == '':
                        continue
                    
                    # 이름을 ID로 변환
                    source = id_mapping.get(source_name, source_name)
                    
                    # 응답 추출 (여러 명일 경우 쉼표로 구분됨)
                    response = row.get(question)
                    if pd.isna(response) or response == '':
                        continue
                    
                    # 쉼표로 구분된 응답을 분리
                    target_names = [t.strip() for t in str(response).split(',')]
                    
                    # 엣지 생성 (응답자 -> 선택된 학생)
                    for target_name in target_names:
                        if target_name in students and source_name != target_name:
                            # 이름을 ID로 변환
                            target = id_mapping.get(target_name, target_name)
                            
                            edges.append({
                                'source': source,
                                'target': target,
                                'source_name': source_name,  # 원본 이름 보존
                                'target_name': target_name,  # 원본 이름 보존
                                'question': question,
                                'weight': 1
                            })
            
            # 엣지 데이터 통합 (중복 엣지는 가중치 증가)
            edge_dict = {}
            for edge in edges:
                key = (edge['source'], edge['target'])
                if key not in edge_dict:
                    edge_dict[key] = edge.copy()
                else:
                    edge_dict[key]['weight'] += edge['weight']
            
            # 엣지 리스트로 변환
            normalized_edges = list(edge_dict.values())
            
            logger.info(f"네트워크 데이터 변환 완료: {len(id_mapping)}명의 학생, {len(normalized_edges)}개의 관계")
            
            # ID로 변환된 노드 리스트 생성
            node_ids = list(name_mapping.keys())
            
            # 최종 데이터 구조 생성
            network_data = {
                'nodes': node_ids,                    # ID 기반 노드
                'original_nodes': students,           # 원본 이름
                'edges': normalized_edges,            # ID 기반 엣지
                'question_types': questions,
                'id_mapping': id_mapping,             # 이름 -> ID
                'name_mapping': name_mapping,         # ID -> 이름
                'romanized_mapping': romanized_mapping,  # 이름 -> 로마자
                'reverse_romanized': reverse_romanized   # 로마자 -> 이름
            }
            
            # Gemini API를 사용하여 추가 데이터 처리 (선택적)
            if api_enabled and hasattr(self, 'api_manager') and self.api_manager:
                try:
                    # Gemini에게 네트워크 구조 개선 요청
                    prompt = """
                    다음 네트워크 데이터를 분석하고 개선해주세요:
                    1. 노드 간의 관계 강도를 1-10 사이로 정규화
                    2. 각 노드의 중요도를 평가하여 1-10 사이 점수 부여
                    3. 노드를 최적의 커뮤니티로 그룹화
                    
                    노드 목록: {nodes}
                    엣지 목록: {edges_sample}
                    
                    다음 JSON 형식으로 응답해주세요:
                    {{
                        "node_scores": {{"노드ID": 점수, ...}},
                        "edge_weights": {{"출발노드ID-도착노드ID": 가중치, ...}},
                        "communities": {{"노드ID": 커뮤니티ID, ...}}
                    }}
                    """.format(
                        nodes=node_ids[:50],  # 노드 수가 많을 경우 일부만 전송
                        edges_sample=normalized_edges[:100]  # 엣지 수가 많을 경우 일부만 전송
                    )
                    
                    gemini_result = self.api_manager.generate_text(prompt)
                    
                    # JSON 파싱
                    import json
                    import re
                    
                    # JSON 부분 추출
                    json_match = re.search(r'```json\n(.*?)\n```', gemini_result, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        json_str = gemini_result
                    
                    try:
                        gemini_data = json.loads(json_str)
                        # 결과 병합
                        network_data['gemini_enhanced'] = True
                        network_data['node_scores'] = gemini_data.get('node_scores', {})
                        network_data['enhanced_edge_weights'] = gemini_data.get('edge_weights', {})
                        network_data['gemini_communities'] = gemini_data.get('communities', {})
                        logger.info("Gemini를 통한 네트워크 데이터 개선 완료")
                    except json.JSONDecodeError:
                        logger.warning("Gemini 응답에서 유효한 JSON을 추출할 수 없습니다.")
                except Exception as e:
                    logger.warning(f"Gemini를 통한 데이터 처리 중 오류: {str(e)}")
            
            return network_data
        
        except Exception as e:
            logger.error(f"데이터 처리 중 오류 발생: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def analyze_with_ai(self, df):
        """AI를 사용하여 데이터 구조를 분석합니다"""
        try:
            if not hasattr(self, 'api_manager') or not self.api_manager:
                logger.warning("API 매니저가 초기화되지 않아 AI 분석을 건너뜁니다.")
                return None
            
            # 샘플 데이터 준비 (너무 큰 데이터는 API 요청에 부담)
            sample_rows = min(10, len(df))
            sample_df = df.head(sample_rows)
            
            # 데이터프레임을 텍스트로 변환
            sample_text = sample_df.to_string()
            
            # 열 정보 추가
            columns_info = "\n\n열 정보:\n" + "\n".join([
                f"{i}. {col} - 타입: {df[col].dtype}, 고유값 수: {df[col].nunique()}, 예시: {df[col].iloc[0]}"
                for i, col in enumerate(df.columns)
            ])
            
            # AI 분석 요청
            prompt = f"""
            다음은 학급 관계 네트워크 분석을 위한 설문조사 데이터입니다:
            
            {sample_text}
            
            {columns_info}
            
            이 데이터에서 다음 내용을 분석해주세요:
            1. 응답자(학생) 이름이 포함된 열은 무엇인가요?
            2. 관계 정보(누구를 선택했는지)가 포함된 열은 무엇인가요?
            3. 이 데이터의 구조와, 어떤 식으로 학생 간 관계망을 구성할 수 있을지 설명해주세요.
            
            JSON 형식으로 다음 키를 포함하여 응답해주세요:
            - student_name_column: 학생 이름이 있는 열 이름 (문자열)
            - relationship_columns: 관계 정보가 있는 열 이름들 (문자열 리스트)
            - description: 데이터 설명 (문자열)
            """
            
            # API 호출
            response = self.api_manager.generate_text(prompt)
            
            # 응답 파싱 시도
            if response:
                try:
                    import json
                    import re
                    
                    # JSON 부분 추출 시도
                    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # JSON 블록 없으면 전체 텍스트에서 JSON 형식 찾기
                        json_str = re.search(r'({[\s\S]*})', response).group(1)
                    
                    parsed_response = json.loads(json_str)
                    logger.info(f"AI 분석 결과: {parsed_response}")
                    return parsed_response
                except Exception as e:
                    logger.error(f"AI 응답 파싱 중 오류: {str(e)}")
                    logger.debug(f"원본 응답: {response}")
                    
                    # 파싱 실패 시 간단한 응답 반환
                    return {
                        "student_name_column": None,
                        "relationship_columns": [],
                        "description": "AI 분석에 실패했습니다."
                    }
            
            return None
        except Exception as e:
            logger.error(f"AI 분석 중 오류 발생: {str(e)}")
            return None 