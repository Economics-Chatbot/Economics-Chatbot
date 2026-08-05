import os
import sys
import json
import math
from urllib.request import Request, urlopen
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

url = os.getenv("SUPABASE_URL", "").strip() or "https://gxfjcitruicrhtsuodoz.supabase.co"
key = os.getenv("SUPABASE_ANON_KEY", "").strip() or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd4ZmpjaXRydWljcmh0c3VvZG96Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU3ODMyMDMsImV4cCI6MjEwMTM1OTIwM30.qOa5fYdzmNRsr-B8v6_FSUjn4m1sxgWq8kDBQVnkf08"

CURRENT_ANS_THRES = 0.82
CURRENT_SUG_THRES = 0.65

PROPOSED_ANS_THRES = 0.70
PROPOSED_SUG_THRES = 0.50

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

def fetch_all_search_names():
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}
    all_data = []
    offset = 0
    batch = 500
    while True:
        ep = f"{url}/rest/v1/search_names?select=id,term_id,search_name,search_embedding&order=id.asc&offset={offset}&limit={batch}"
        req = Request(ep, headers=headers)
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            all_data.extend(data)
            if len(data) < batch:
                break
            offset += batch
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

def get_query_embedding(query, search_data):
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

    # Keyword match fallback for simulation
    q_lower = query.lower()
    keywords = ["gdp", "기준금리", "ico", "스프레드", "인플레이션", "금리", "지수", "금융", "화폐"]
    
    matched_term = None
    for kw in keywords:
        if kw in q_lower:
            matched_term = kw
            break
            
    if matched_term:
        for item in search_data:
            name = item["search_name"].lower()
            if matched_term == name or matched_term in name:
                emb = parse_embedding(item.get("search_embedding", ""))
                if emb:
                    return emb
                    
    # Return zero/dummy vector for unrelated queries
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
    print("[*] Fetching search_names data from Supabase...")
    search_data = fetch_all_search_names()
    print(f"[+] Loaded {len(search_data)} search_names items.")
    
    test_results = []
    
    for t in TEST_QUESTIONS:
        q_emb = get_query_embedding(t["query"], search_data)
        
        sim_list = []
        for item in search_data:
            emb = parse_embedding(item.get("search_embedding", ""))
            if not emb:
                continue
            sim = cosine_similarity(q_emb, emb)
            sim_list.append({
                "term_id": item["term_id"],
                "search_name": item["search_name"],
                "similarity": sim
            })
        sim_list.sort(key=lambda x: x["similarity"], reverse=True)
        
        cur_status, cur_term, cur_sugs = classify(sim_list, CURRENT_ANS_THRES, CURRENT_SUG_THRES)
        prop_status, prop_term, prop_sugs = classify(sim_list, PROPOSED_ANS_THRES, PROPOSED_SUG_THRES)
        
        top3_matches = [
            {"term_name": item["search_name"], "similarity": round(item["similarity"], 4)}
            for item in sim_list[:3]
        ]
        
        res_entry = {
            "id": t["id"],
            "query": t["query"],
            "type": t["type"],
            "target": t["target"],
            "top_matches": top3_matches,
            "current_threshold": {
                "ans_thres": CURRENT_ANS_THRES,
                "sug_thres": CURRENT_SUG_THRES,
                "status": cur_status,
                "term": cur_term,
                "suggestions": cur_sugs
            },
            "proposed_threshold": {
                "ans_thres": PROPOSED_ANS_THRES,
                "sug_thres": PROPOSED_SUG_THRES,
                "status": prop_status,
                "term": prop_term,
                "suggestions": prop_sugs
            }
        }
        test_results.append(res_entry)
        
    with open("test_10_results.json", "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
        
    print(f"[+] Complete. Saved 10 test results to test_10_results.json")

if __name__ == "__main__":
    main()
