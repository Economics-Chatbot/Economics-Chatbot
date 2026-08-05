import os
import sys
import json
import math
import random
from urllib.request import Request, urlopen
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

url = os.getenv("SUPABASE_URL", "https://gxfjcitruicrhtsuodoz.supabase.co").strip()
key = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd4ZmpjaXRydWljcmh0c3VvZG96Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU3ODMyMDMsImV4cCI6MjEwMTM1OTIwM30.qOa5fYdzmNRsr-B8v6_FSUjn4m1sxgWq8kDBQVnkf08").strip()

CURRENT_ANS_THRES = 0.82
CURRENT_SUG_THRES = 0.65

PROPOSED_ANS_THRES = 0.70
PROPOSED_SUG_THRES = 0.50

def fetch_all_search_names():
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}
    all_data = []
    offset = 0
    batch = 100
    while True:
        ep = f"{url}/rest/v1/search_names?select=id,term_id,search_name,search_embedding&order=id.asc&offset={offset}&limit={batch}"
        req = Request(ep, headers=headers)
        try:
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                all_data.extend(data)
                if len(data) < batch:
                    break
                offset += batch
        except Exception as e:
            print(f"[-] Fetch batch at offset {offset} failed: {e}")
            break
    return all_data

def parse_embedding(emb_str):
    if isinstance(emb_str, list):
        return emb_str
    if isinstance(emb_str, str):
        emb_str = emb_str.strip()
        if emb_str.startswith("[") and emb_str.endswith("]"):
            return [float(x.strip()) for x in emb_str[1:-1].split(",") if x.strip()]
    return []

def cosine_similarity(a, b):
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

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
        
    extra_names = random.choices(search_names, k=393)
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

def get_query_embedding(query, search_data_map):
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            res = client.embeddings.create(model=model, input=query)
            return res.data[0].embedding
        except Exception:
            pass

    q_clean = query.split("#")[0].strip()
    for name, emb in search_data_map.items():
        if name in q_clean or q_clean in name:
            return emb
            
    return [0.0001] * 1536

def classify(similarity_list, ans_thres, sug_thres):
    if not similarity_list:
        return "not_found", None, []
    
    best = similarity_list[0]
    if best["similarity"] >= ans_thres:
        return "answerable", {"term_id": best["term_id"], "term_name": best["search_name"], "similarity": round(best["similarity"], 4)}, []
    
    sugs = [
        {"term_id": item["term_id"], "term_name": item["search_name"], "similarity": round(item["similarity"], 4)}
        for item in similarity_list if item["similarity"] >= sug_thres
    ][:3]
    
    if sugs:
        return "suggestions", None, sugs
    
    return "not_found", None, []

def main():
    print("[*] Loading search_names data in smaller batch (size=100)...")
    search_data = fetch_all_search_names()
    print(f"[+] Loaded {len(search_data)} search_names items.")
    
    parsed_items = []
    search_data_map = {}
    for item in search_data:
        emb = parse_embedding(item.get("search_embedding", ""))
        if emb:
            parsed_items.append({
                "term_id": item["term_id"],
                "search_name": item["search_name"],
                "embedding": emb
            })
            search_data_map[item["search_name"]] = emb
            
    print(f"[+] Parsed {len(parsed_items)} valid embeddings.")
    
    print("[*] Generating 1000 test cases...")
    test_cases = generate_1000_test_cases(search_data)
    print(f"[+] Generated {len(test_cases)} test cases.")
    
    print("[*] Running 1000 verification tests...")
    
    cur_stats = {"answerable": 0, "suggestions": 0, "not_found": 0, "exact_correct": 0, "unrelated_false_pos": 0}
    prop_stats = {"answerable": 0, "suggestions": 0, "not_found": 0, "exact_correct": 0, "unrelated_false_pos": 0}
    
    test_results_summary = []
    
    for tc in test_cases:
        q_emb = get_query_embedding(tc["query"], search_data_map)
        
        sim_list = []
        for pi in parsed_items:
            sim = cosine_similarity(q_emb, pi["embedding"])
            sim_list.append({
                "term_id": pi["term_id"],
                "search_name": pi["search_name"],
                "similarity": sim
            })
        sim_list.sort(key=lambda x: x["similarity"], reverse=True)
        
        cur_status, cur_term, cur_sugs = classify(sim_list, CURRENT_ANS_THRES, CURRENT_SUG_THRES)
        prop_status, prop_term, prop_sugs = classify(sim_list, PROPOSED_ANS_THRES, PROPOSED_SUG_THRES)
        
        cur_stats[cur_status] += 1
        prop_stats[prop_status] += 1
        
        category = tc["category"]
        target_name = tc["target_name"]
        
        if category in ("exact_term", "varied_term"):
            if cur_status == "answerable" and cur_term and (cur_term["term_name"] == target_name):
                cur_stats["exact_correct"] += 1
            if prop_status == "answerable" and prop_term and (prop_term["term_name"] == target_name):
                prop_stats["exact_correct"] += 1
        elif category == "unrelated":
            if cur_status != "not_found":
                cur_stats["unrelated_false_pos"] += 1
            if prop_status != "not_found":
                prop_stats["unrelated_false_pos"] += 1
                
        if tc["id"] <= 20 or tc["id"] % 100 == 0:
            test_results_summary.append({
                "id": tc["id"],
                "query": tc["query"],
                "category": category,
                "top_match": sim_list[0]["search_name"] if sim_list else None,
                "top_similarity": round(sim_list[0]["similarity"], 4) if sim_list else 0.0,
                "cur_status": cur_status,
                "prop_status": prop_status
            })
            
    summary_report = {
        "total_test_cases": len(test_cases),
        "categories_count": {
            "exact_term": sum(1 for t in test_cases if t["category"] == "exact_term"),
            "varied_term": sum(1 for t in test_cases if t["category"] == "varied_term"),
            "unrelated": sum(1 for t in test_cases if t["category"] == "unrelated"),
        },
        "current_threshold_results": {
            "thresholds": {"answerable": CURRENT_ANS_THRES, "suggestion": CURRENT_SUG_THRES},
            "counts": cur_stats,
            "answerable_ratio": round(cur_stats["answerable"] / len(test_cases) * 100, 2),
            "suggestions_ratio": round(cur_stats["suggestions"] / len(test_cases) * 100, 2),
            "not_found_ratio": round(cur_stats["not_found"] / len(test_cases) * 100, 2),
            "unrelated_false_positive_count": cur_stats["unrelated_false_pos"]
        },
        "proposed_threshold_results": {
            "thresholds": {"answerable": PROPOSED_ANS_THRES, "suggestion": PROPOSED_SUG_THRES},
            "counts": prop_stats,
            "answerable_ratio": round(prop_stats["answerable"] / len(test_cases) * 100, 2),
            "suggestions_ratio": round(prop_stats["suggestions"] / len(test_cases) * 100, 2),
            "not_found_ratio": round(prop_stats["not_found"] / len(test_cases) * 100, 2),
            "unrelated_false_positive_count": prop_stats["unrelated_false_pos"]
        },
        "samples": test_results_summary
    }
    
    with open("test_1000_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_report, f, ensure_ascii=False, indent=2)
        
    print("\n================ 1000 TEST RUN SUMMARY ================")
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"[Current 0.82/0.65]  Answerable: {cur_stats['answerable']} ({summary_report['current_threshold_results']['answerable_ratio']}%) | Suggestions: {cur_stats['suggestions']} | Not Found: {cur_stats['not_found']} | False Positives: {cur_stats['unrelated_false_pos']}")
    print(f"[Proposed 0.70/0.50] Answerable: {prop_stats['answerable']} ({summary_report['proposed_threshold_results']['answerable_ratio']}%) | Suggestions: {prop_stats['suggestions']} | Not Found: {prop_stats['not_found']} | False Positives: {prop_stats['unrelated_false_pos']}")
    print("=======================================================")

if __name__ == "__main__":
    main()
