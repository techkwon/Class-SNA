import os
import random
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# API 키 목록
API_KEYS = [
    "AIzaSyD2UzkUP2jxjwzAc3eSZkq9CR1Rrk0szJQ",
    "AIzaSyCv3YJc4QiJtlhymRqpo0rirH3ploC0yR8",
    "AIzaSyB_KV2WIdo21usPYRAUXnlyHIrq9qV2Hzo",
    "AIzaSyDwj5tIYg8X5ASilXiqKnpxrScRdZ1QAUs",
    "AIzaSyDS8RQWjEgB_9pmLUvaAeMoxxYBduVeyJQ",
    "AIzaSyCsExDCjCLZjMHdRaIjo9wZZ_qd9SA-9Es",
    "AIzaSyBltJa9K3bDpbulMvNoWL6OlrUjvfNNIGY",
    "AIzaSyBqmvWg6HOREWX00h3udxF5HwbquF5qIEU",
    "AIzaSyD0UW-mslCxaqMBKAN_AX6C0xhofKaRoLk",
    "AIzaSyAc6I3KtFKFnVJ11JvRtVlYbtaw76siC5I"
]

# 환경 변수에서 API 키를 가져옴 (있는 경우)
env_api_keys = os.getenv("GOOGLE_API_KEYS")
if env_api_keys:
    API_KEYS = env_api_keys.split(",")

def get_random_api_key():
    """사용 가능한 API 키 중 하나를 랜덤으로 반환"""
    return random.choice(API_KEYS)

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