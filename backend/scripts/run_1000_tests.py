import os
import sys
import json
import random
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.services.vector_retrieval import vector_retrieve, SUGGESTION_THRESHOLD, ANSWERABLE_THRESHOLD

def check_env():
    settings = get_settings()
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required in .env")
    if not settings.supabase_service_role_key and not os.getenv("SUPABASE_ANON_KEY"):
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY is required in .env")
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required in .env for actual embedding quality verification")
    return settings

def fetch_all_search_names(supabase):
    all_data = []
    offset = 0
    batch = 100
    while True:
        res = supabase.table("search_names").select("id,term_id,search_name").range(offset, offset + batch - 1).execute()
        batch_data = res.data or []
        all_data.extend(batch_data)
        if len(batch_data) < batch:
            break
        offset += batch
    return all_data

def generate_1000_test_cases(search_names):
    random.seed(2026)
    test_cases = []
    
    templates = [
        "{}가 뭐야?",
        "{}에 대해 설명해줘",
        "{}란 무슨 뜻인가요?",
        "{}의 정의가 어떻게 되나요?",
        "{}에 대해 자세히 알고 싶어요",
        "{}",
        "{} 의미",
        "{} 관련 경제 정보",
    ]
    
    tc_id = 1
    for item in search_names:
        name = item["search_name"]
        tmpl = random.choice(templates)
        query = tmpl.format(name)
        test_cases.append({
            "id": tc_id,
            "query": query,
            "category": "exact_term",
            "target_name": name,
            "target_term_id": item["term_id"]
        })
        tc_id += 1
        
    extra_names = random.choices(search_names, k=393) if search_names else []
    for item in extra_names:
        name = item["search_name"]
        prefix = random.choice(["금융용어 ", "경제용어 ", "한국은행 ", "요즘 말하는 ", ""])
        suffix = random.choice([" 개념", " 지수", " 비율", " 제도", " 정책", ""])
        query = f"{prefix}{name}{suffix}"
        test_cases.append({
            "id": tc_id,
            "query": query,
            "category": "varied_term",
            "target_name": name,
            "target_term_id": item["term_id"]
        })
        tc_id += 1
        
    unrelated_queries = [
        "오늘 점심 메뉴 추천해줘", "서울 날씨 어때?", "강아지 사료 추천", "지하철 막차 시간", "영화 추천해줘",
        "유튜브 인기 동영상", "파이썬 문법 기초", "여행지 추천", "축구 경기 결과", "스마트폰 요금제",
        "피자 배달 맛집", "감기약 복용법", "노래 추천", "게임 신작 출시일", "주말 데이트 코스"
    ]
    for i in range(150):
        base_q = random.choice(unrelated_queries)
        query = f"{base_q} #{i+1}"
        test_cases.append({
            "id": tc_id,
            "query": query,
            "category": "unrelated",
            "target_name": None,
            "target_term_id": None
        })
        tc_id += 1
        
    return test_cases[:1000]

def main():
    settings = check_env()
    supabase = get_supabase_client()
    
    print("[*] Fetching search_names from Supabase via actual client...")
    search_names = fetch_all_search_names(supabase)
    print(f"[+] Loaded {len(search_names)} search_names entries.")
    
    print("[*] Generating 1,000 test cases...")
    test_cases = generate_1000_test_cases(search_names)
    print(f"[+] Generated {len(test_cases)} test cases.")
    
    print("[*] Executing real vector_retrieve pipeline testing...")
    
    stats = {"answerable": 0, "suggestions": 0, "not_found": 0, "exact_correct": 0, "unrelated_false_pos": 0}
    test_results_summary = []
    
    for tc in test_cases:
        query = tc["query"]
        category = tc["category"]
        target_name = tc["target_name"]
        
        try:
            res = vector_retrieve(query, supabase=supabase)
            status = res.status.value
            
            stats[status] += 1
            
            if category in ("exact_term", "varied_term"):
                if status == "answerable" and res.term and (res.term.term_name == target_name):
                    stats["exact_correct"] += 1
            elif category == "unrelated":
                if status != "not_found":
                    stats["unrelated_false_pos"] += 1
                    
            if tc["id"] <= 20 or tc["id"] % 100 == 0:
                top_match = res.term.term_name if res.term else (res.suggestions[0].term_name if res.suggestions else None)
                test_results_summary.append({
                    "id": tc["id"],
                    "query": query,
                    "category": category,
                    "status": status,
                    "top_match": top_match,
                })
        except Exception as e:
            print(f"[-] Error testing query '{query}': {e}")
            stats["not_found"] += 1

    summary_report = {
        "total_test_cases": len(test_cases),
        "thresholds": {"answerable": ANSWERABLE_THRESHOLD, "suggestion": SUGGESTION_THRESHOLD},
        "counts": stats,
        "answerable_ratio": round(stats["answerable"] / len(test_cases) * 100, 2),
        "suggestions_ratio": round(stats["suggestions"] / len(test_cases) * 100, 2),
        "not_found_ratio": round(stats["not_found"] / len(test_cases) * 100, 2),
        "unrelated_false_positive_count": stats["unrelated_false_pos"],
        "samples": test_results_summary
    }
    
    out_file = "test_1000_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, ensure_ascii=False, indent=2)
        
    print("\n================ 1000 REAL PIPELINE TEST RUN SUMMARY ================")
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"Status Counts: {stats}")
    print(f"Saved summary to {out_file}")

if __name__ == "__main__":
    main()
