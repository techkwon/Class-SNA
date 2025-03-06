import pandas as pd
import json
import logging
import gspread
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
            
            # JSON 문자열에서 실제 JSON 부분만 추출
            json_start = analysis_result.find('{')
            json_end = analysis_result.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("API 응답에서 유효한 JSON을 찾을 수 없습니다.")
                
            json_str = analysis_result[json_start:json_end]
            
            # JSON 파싱
            result = json.loads(json_str)
            return result
            
        except Exception as e:
            logger.error(f"데이터 구조 분석 실패: {str(e)}")
            raise Exception(f"데이터 분석 중 오류가 발생했습니다: {str(e)}")
    
    def convert_to_network_data(self, analysis_result):
        """분석 결과를 네트워크 데이터로 변환"""
        try:
            # 관계 데이터 추출
            relationships = analysis_result.get("relationships", [])
            
            # 노드(학생) 목록 추출
            nodes = analysis_result.get("students", [])
            
            # 엣지(관계) 데이터프레임 생성
            edges_df = pd.DataFrame(relationships)
            
            # 노드 데이터프레임 생성
            nodes_df = pd.DataFrame({"id": nodes, "label": nodes})
            
            return {
                "nodes": nodes_df,
                "edges": edges_df,
                "question_types": analysis_result.get("question_types", {})
            }
            
        except Exception as e:
            logger.error(f"네트워크 데이터 변환 실패: {str(e)}")
            raise Exception(f"네트워크 데이터 변환 중 오류가 발생했습니다: {str(e)}")
    
    def process_survey_data(self, sheet_url):
        """전체 데이터 처리 과정 실행"""
        try:
            # 데이터 로드
            df = self.load_from_gsheet(sheet_url)
            
            # 데이터 구조 분석
            analysis_result = self.analyze_data_structure(df)
            
            # 네트워크 데이터로 변환
            network_data = self.convert_to_network_data(analysis_result)
            
            return network_data
            
        except Exception as e:
            logger.error(f"설문조사 데이터 처리 실패: {str(e)}")
            raise Exception(f"데이터 처리 중 오류가 발생했습니다: {str(e)}") 