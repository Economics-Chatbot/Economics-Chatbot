import os
import sys
import json
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.services.vector_retrieval import vector_retrieve, SUGGESTION_THRESHOLD, ANSWERABLE_THRESHOLD

TEST_QUESTIONS = [
    {"id": 1, "query": "GDP가 뭐야?", "type": "직접 용어 약어 질문", "target": "GDP"},
    {"id": 2, "query": "기준금리가 무슨 뜻인가요?", "type": "직접 용어 한글 질문", "target": "기준금리"},
    {"id": 3, "query": "ICO", "type": "단일 키워드 검색", "target": "ICO"},
    {"id": 4, "query": "스프레드에 대해 설명해줘", "type": "용어 서술 요청", "target": "스프레드"},
    {"id": 5, "query": "물가가 지속적으로 상승하는 현상", "type": "개념 설명 질문 (인플레이션)", "target": "인플레이션 / CPI"},
    {"id": 6, "query": "중앙은행에서 결정하는 정책 금리", "type": "개념 설명 질문 (기준금리)", "target": "기준금리"},
    {"id": 7, "query": "주식 거래 시장 지수", "type": "유사 금융 관련 질문", "target": "주가지수 / CI"},
    {"id": 8, "query": "돈과 금융", "type": "모호하고 광범위한 질문", "target": "금융 / 화폐"},
    {"id": 9, "query": "오늘 내일 날씨 어때?", "type": "경제와 무관한 질문", "target": "없음"},
    {"id": 10, "query": "맛있는 점심 메뉴 추천해줘", "type": "일상적 무관한 질문", "target": "없음"},
]

def check_env():
    settings = get_settings()
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required in .env")
    if not settings.supabase_service_role_key and not os.getenv("SUPABASE_ANON_KEY"):
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY is required in .env")
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required in .env for actual pipeline testing")
    return settings

def main():
    settings = check_env()
    supabase = get_supabase_client()
    
    print("[*] Running 10 real pipeline test cases...")
    test_results = []
    
    for t in TEST_QUESTIONS:
        query = t["query"]
        try:
            res = vector_retrieve(query, supabase=supabase)
            status = res.status.value
            term_dict = res.term.model_dump() if res.term else None
            sugs_dict = [s.model_dump() for s in res.suggestions] if res.suggestions else []
            
            res_entry = {
                "id": t["id"],
                "query": query,
                "type": t["type"],
                "target": t["target"],
                "status": status,
                "term": term_dict,
                "suggestions": sugs_dict,
            }
            test_results.append(res_entry)
            print(f"[+] [{t['id']}] '{query}' -> status: {status}")
        except Exception as e:
            print(f"[-] Error processing '{query}': {e}")

    out_file = "test_10_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
        
    print(f"\n[+] Completed 10 real pipeline tests. Results saved to {out_file}")

if __name__ == "__main__":
    main()
