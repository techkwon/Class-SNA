import google.generativeai as genai
import logging
import time
from config import get_random_api_key, APP_SETTINGS

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIManager:
    """Google Gemini API 통신을 관리하는 클래스"""
    
    def __init__(self):
        self.current_api_key = None
        self.model = APP_SETTINGS["gemini_model"]
        self.setup_api()
    
    def setup_api(self):
        """API 키 설정 및 Gemini 모델 초기화"""
        self.current_api_key = get_random_api_key()
        genai.configure(api_key=self.current_api_key)
        logger.info(f"API 설정 완료: 모델 {self.model} 사용")
    
    def switch_api_key(self):
        """다른 API 키로 전환"""
        previous_key = self.current_api_key
        while self.current_api_key == previous_key:
            self.current_api_key = get_random_api_key()
        
        genai.configure(api_key=self.current_api_key)
        logger.info("새로운 API 키로 전환 완료")
    
    def generate_response(self, prompt, max_retries=3):
        """Gemini API를 사용하여 응답 생성"""
        retries = 0
        
        while retries < max_retries:
            try:
                model = genai.GenerativeModel(self.model)
                response = model.generate_content(prompt)
                return response.text
            
            except Exception as e:
                logger.error(f"API 오류 발생: {str(e)}")
                retries += 1
                
                if retries < max_retries:
                    logger.info(f"API 키 전환 후 {retries}/{max_retries} 재시도 중...")
                    self.switch_api_key()
                    time.sleep(1)  # 재시도 전 대기
                else:
                    logger.error("최대 재시도 횟수 초과")
                    raise Exception("API 요청 실패. 잠시 후 다시 시도해주세요.")
    
    def analyze_survey_data(self, survey_data, survey_questions=None):
        """설문 데이터 구조 분석 및 관계형 데이터 변환 요청"""
        context = """
        당신은 학생 관계 설문조사 데이터를 분석하는 AI 전문가입니다.
        제공된 설문조사 데이터를 분석하여 학생 간 관계(From-To)를 식별하고 네트워크 분석에 적합한 형태로 변환해야 합니다.
        """
        
        prompt = f"""
        {context}
        
        # 설문조사 데이터:
        ```
        {survey_data}
        ```
        
        # 작업:
        1. 관계형 질문(예: "함께 일하고 싶은 친구는?", "도움을 요청할 친구는?")을 식별하세요.
        2. 응답자(From)와 선택된 학생(To) 간의 관계를 추출하세요.
        3. 학생 이름의 불일치나 오타를 수정하세요.
        4. 다음 JSON 형식으로 결과를 반환하세요:
        ```json
        {
            "relationships": [
                {"from": "학생1", "to": "학생2", "weight": 1, "type": "friendship"},
                ...
            ],
            "students": ["학생1", "학생2", "학생3", ...],
            "question_types": {
                "question1": "friendship",
                "question2": "academic",
                ...
            }
        }
        ```
        
        결과는 반드시 유효한 JSON 형식이어야 하며, 불확실한 데이터는 포함하지 마세요.
        """
        
        if survey_questions:
            prompt += f"\n\n# 설문조사 질문:\n{survey_questions}"
        
        return self.generate_response(prompt) 