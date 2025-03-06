import os
import random
import streamlit as st

# Streamlit secrets에서 API 키 가져오기
def get_api_keys():
    """Streamlit secrets에서 API 키 목록 가져오기"""
    try:
        # Streamlit Cloud/로컬 환경에서 secrets에서 API 키 가져오기
        if "google_api_keys" in st.secrets:
            # 문자열로 저장된 경우 쉼표로 구분하여 리스트로 변환
            if isinstance(st.secrets["google_api_keys"], str):
                return st.secrets["google_api_keys"].split(",")
            # 리스트로 저장된 경우 그대로 반환
            elif isinstance(st.secrets["google_api_keys"], list):
                return st.secrets["google_api_keys"]
            else:
                return []
        else:
            # 개발 환경에서는 환경 변수에서 가져오기 (fallback)
            env_api_keys = os.getenv("GOOGLE_API_KEYS")
            if env_api_keys:
                return env_api_keys.split(",")
            return []
    except Exception as e:
        print(f"API 키 로드 중 오류 발생: {str(e)}")
        return []

def get_random_api_key():
    """사용 가능한 API 키 중 하나를 랜덤으로 반환"""
    api_keys = get_api_keys()
    if not api_keys:
        raise ValueError("사용 가능한 API 키가 없습니다. Streamlit secrets에 'google_api_keys' 설정이 필요합니다.")
    return random.choice(api_keys)

# Streamlit Cloud 환경 확인
def is_streamlit_cloud():
    """현재 Streamlit Cloud 환경에서 실행 중인지 확인"""
    return os.getenv("STREAMLIT_RUNTIME") is not None

# 앱 설정
APP_SETTINGS = {
    "title": "학급 관계 네트워크 분석 시스템 (Class-SNA)",
    "description": "학생 간 관계 설문조사 데이터를 소셜 네트워크 분석 그래프로 변환합니다.",
    "logo_path": "assets/logo.png",
    "max_file_size_mb": 10,
    "gemini_model": "gemini-2.0-flash",
    "debug_mode": False
} 