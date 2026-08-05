"""
BE2 벡터 검색 품질 검증 스크립트

RPC 함수의 테이블 참조 불일치를 우회하여,
search_names 테이블의 임베딩을 직접 사용하여 품질을 검증한다.

검증 지표:
  1. Threshold - answerable/suggestions/not_found 분기 적절성
  2. Precision - 반환 결과 중 정답 비율
  3. Recall - 정답 용어를 찾아내는 비율
  4. nDCG - 검색 순위 품질
"""
import os
import sys
import json
import math
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

url = os.getenv("SUPABASE_URL", "").strip()
key = os.getenv("SUPABASE_ANON_KEY", "").strip()

ANSWERABLE_THRESHOLD = 0.82
SUGGESTION_THRESHOLD = 0.65
MAX_SUGGESTIONS = 3

# ── Test Cases ──────────────────────────────────────────────
# (query, expected_term_names, category)
# category: "exact" = 정확한 용어 질문, "related" = 관련 질문, "unrelated" = 무관한 질문
TEST_CASES = [
    # ─ exact: 정확한 용어명 또는 약어 질문
    ("GDP가 뭐야?", ["GDP", "Gross Domestic Product"], "exact"),
    ("기준금리란?", ["기준금리"], "exact"),
    ("ICO가 무슨 뜻이야?", ["ICO", "Initial Coin Offering"], "exact"),
    ("스프레드 설명해줘", ["스프레드", "spread"], "exact"),
    ("OECD가 뭐야?", ["OECD"], "exact"),
    ("KYC란 무엇인가요?", ["KYC"], "exact"),
    ("PDI 설명해줘", ["PDI", "Personal Disposable Income"], "exact"),
    ("ESI가 뭐야?", ["ESI", "Economic Sentiment Index"], "exact"),

    # ─ related: 관련된 경제 질문 (용어명 직접 언급 안함)
    ("물가가 계속 오르는 현상이 뭐야?", ["인플레이션", "CPI", "소비자물가지수"], "related"),
    ("돈의 가치가 떨어지는 건?", ["인플레이션", "디플레이션", "화폐가치"], "related"),
    ("은행에서 돈 빌리는 이자는?", ["기준금리", "대출금리", "이자율"], "related"),
    ("주식시장 지표가 뭐야?", ["KOSPI", "주가지수", "Composite Index", "CI"], "related"),

    # ─ unrelated: 경제와 무관한 질문
    ("오늘 점심 뭐 먹지?", [], "unrelated"),
    ("강아지 키우는 법 알려줘", [], "unrelated"),
    ("서울 날씨 어때?", [], "unrelated"),
]

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Accept": "application/json",
}


def fetch_all_search_names():
    """search_names 테이블에서 전체 데이터 (id, term_id, search_name, search_embedding) 가져오기"""
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
    """search_embedding 문자열을 float 리스트로 파싱"""
    if isinstance(emb_str, list):
        return emb_str
    if isinstance(emb_str, str):
        emb_str = emb_str.strip()
        if emb_str.startswith("[") and emb_str.endswith("]"):
            return [float(x.strip()) for x in emb_str[1:-1].split(",") if x.strip()]
    return []


def cosine_similarity(a, b):
    """코사인 유사도 계산"""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_query_embedding(query):
    """OpenAI API로 query 임베딩 생성 (openai 패키지 사용)"""
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    response = client.embeddings.create(model=model, input=query)
    return response.data[0].embedding


def search_by_embedding(query_embedding, search_data, top_k=8):
    """search_names 임베딩과 코사인 유사도 비교하여 상위 결과 반환"""
    results = []
    for item in search_data:
        emb = parse_embedding(item.get("search_embedding", ""))
        if not emb:
            continue
        sim = cosine_similarity(query_embedding, emb)
        results.append({
            "id": item["id"],
            "term_id": item["term_id"],
            "search_name": item["search_name"],
            "similarity": sim,
        })
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def classify_result(results):
    """BE2 로직과 동일한 분류: answerable / suggestions / not_found"""
    if not results:
        return "not_found", None, []

    best = results[0]
    if best["similarity"] >= ANSWERABLE_THRESHOLD:
        return "answerable", best, []

    suggestions = [r for r in results if r["similarity"] >= SUGGESTION_THRESHOLD][:MAX_SUGGESTIONS]
    if suggestions:
        return "suggestions", None, suggestions

    return "not_found", None, []


def dcg(relevances, k=None):
    """Discounted Cumulative Gain"""
    if k:
        relevances = relevances[:k]
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))


def ndcg(relevances, k=None):
    """Normalized DCG"""
    actual = dcg(relevances, k)
    ideal = dcg(sorted(relevances, reverse=True), k)
    return actual / ideal if ideal > 0 else 0.0


def run_verification():
    print("=" * 70)
    print("BE2 벡터 검색 품질 검증")
    print("=" * 70)

    # 1. search_names 전체 로드
    print("\n[1/4] search_names 전체 데이터 로드 중...")
    search_data = fetch_all_search_names()
    print(f"  → {len(search_data)}건 로드 완료")

    # 임베딩 파싱 가능 여부 확인
    valid_count = sum(1 for d in search_data if parse_embedding(d.get("search_embedding", "")))
    print(f"  → 유효 임베딩: {valid_count}/{len(search_data)}")

    if valid_count == 0:
        print("\n❌ 유효한 임베딩이 없어 검증 불가")
        return

    # 2. OpenAI API 키 확인
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_key:
        print("\n⚠️  OPENAI_API_KEY가 없습니다. .env 파일에 설정해주세요.")
        print("  OpenAI 임베딩 없이 search_names 간 유사도 분포만 분석합니다.\n")

        # 임베딩 간 유사도 분포 분석
        analyze_embedding_distribution(search_data)
        return

    # 3. 테스트 케이스 실행
    print(f"\n[2/4] {len(TEST_CASES)}개 테스트 케이스 실행 중...\n")

    all_results = []
    for query, expected, category in TEST_CASES:
        try:
            q_emb = get_query_embedding(query)
        except Exception as e:
            print(f"  [SKIP] '{query}' 임베딩 실패: {e}")
            continue

        results = search_by_embedding(q_emb, search_data)
        status, term, suggestions = classify_result(results)

        top_names = [r["search_name"] for r in results[:5]]
        top_sims = [round(r["similarity"], 4) for r in results[:5]]

        # 정답 여부 판정
        if category == "unrelated":
            is_correct = (status == "not_found")
        elif category == "exact":
            if status == "answerable" and term:
                is_correct = any(exp.lower() in term["search_name"].lower() or term["search_name"].lower() in exp.lower() for exp in expected)
            elif status == "suggestions":
                is_correct = any(
                    any(exp.lower() in s["search_name"].lower() or s["search_name"].lower() in exp.lower() for exp in expected)
                    for s in suggestions
                )
            else:
                is_correct = False
        else:  # related
            found_any = any(
                any(exp.lower() in r["search_name"].lower() or r["search_name"].lower() in exp.lower() for exp in expected)
                for r in results[:5]
            )
            is_correct = found_any and status != "not_found"

        # Relevance scores for nDCG
        relevances = []
        for r in results[:5]:
            rel = 1.0 if any(exp.lower() in r["search_name"].lower() or r["search_name"].lower() in exp.lower() for exp in expected) else 0.0
            relevances.append(rel)

        record = {
            "query": query,
            "category": category,
            "status": status,
            "is_correct": is_correct,
            "top_similarity": results[0]["similarity"] if results else 0,
            "top_names": top_names,
            "top_sims": top_sims,
            "relevances": relevances,
            "expected": expected,
        }
        all_results.append(record)

        icon = "✅" if is_correct else "❌"
        print(f"  {icon} [{category:>9}] '{query}'")
        print(f"     → status={status}, top_sim={record['top_similarity']:.4f}")
        print(f"     → top results: {top_names[:3]}")

    if not all_results:
        print("\n❌ 실행된 테스트가 없습니다.")
        return

    # 4. 지표 계산
    print(f"\n[3/4] 검증 지표 계산 중...\n")
    compute_metrics(all_results)

    # 5. Threshold 분석
    print(f"\n[4/4] Threshold 분석\n")
    analyze_thresholds(all_results)


def analyze_embedding_distribution(search_data):
    """임베딩 간 유사도 분포를 분석하여 threshold 적절성 평가"""
    import random
    print("=" * 50)
    print("임베딩 유사도 분포 분석 (샘플)")
    print("=" * 50)

    embeddings = []
    for d in search_data:
        emb = parse_embedding(d.get("search_embedding", ""))
        if emb:
            embeddings.append((d["search_name"], emb))

    if len(embeddings) < 10:
        print("유효 임베딩이 부족합니다.")
        return

    # 같은 term_id 간 유사도 (관련 용어)
    term_groups = {}
    for d in search_data:
        emb = parse_embedding(d.get("search_embedding", ""))
        if emb:
            term_groups.setdefault(d["term_id"], []).append((d["search_name"], emb))

    related_sims = []
    for tid, items in term_groups.items():
        if len(items) >= 2:
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    sim = cosine_similarity(items[i][1], items[j][1])
                    related_sims.append((items[i][0], items[j][0], sim))

    # 랜덤 쌍 유사도 (무관한 용어)
    random.seed(42)
    sample_indices = random.sample(range(len(embeddings)), min(50, len(embeddings)))
    unrelated_sims = []
    for i in range(len(sample_indices)):
        for j in range(i + 1, min(i + 5, len(sample_indices))):
            a = embeddings[sample_indices[i]]
            b = embeddings[sample_indices[j]]
            sim = cosine_similarity(a[1], b[1])
            unrelated_sims.append((a[0], b[0], sim))

    print(f"\n관련 용어 쌍 ({len(related_sims)}쌍):")
    if related_sims:
        related_vals = [s[2] for s in related_sims]
        print(f"  평균: {sum(related_vals)/len(related_vals):.4f}")
        print(f"  최소: {min(related_vals):.4f}")
        print(f"  최대: {max(related_vals):.4f}")
        related_sims.sort(key=lambda x: x[2], reverse=True)
        print("  상위 5쌍:")
        for n1, n2, s in related_sims[:5]:
            print(f"    {n1} ↔ {n2}: {s:.4f}")

    print(f"\n무관한 용어 쌍 ({len(unrelated_sims)}쌍):")
    if unrelated_sims:
        unrelated_vals = [s[2] for s in unrelated_sims]
        print(f"  평균: {sum(unrelated_vals)/len(unrelated_vals):.4f}")
        print(f"  최소: {min(unrelated_vals):.4f}")
        print(f"  최대: {max(unrelated_vals):.4f}")

    # Threshold 평가
    print(f"\n─── Threshold 평가 ───")
    print(f"  현재 ANSWERABLE_THRESHOLD = {ANSWERABLE_THRESHOLD}")
    print(f"  현재 SUGGESTION_THRESHOLD = {SUGGESTION_THRESHOLD}")
    if related_sims:
        above_ans = sum(1 for _, _, s in related_sims if s >= ANSWERABLE_THRESHOLD)
        above_sug = sum(1 for _, _, s in related_sims if s >= SUGGESTION_THRESHOLD)
        print(f"  관련 용어 중 answerable 이상: {above_ans}/{len(related_sims)} ({100*above_ans/len(related_sims):.1f}%)")
        print(f"  관련 용어 중 suggestion 이상: {above_sug}/{len(related_sims)} ({100*above_sug/len(related_sims):.1f}%)")
    if unrelated_sims:
        false_ans = sum(1 for _, _, s in unrelated_sims if s >= ANSWERABLE_THRESHOLD)
        false_sug = sum(1 for _, _, s in unrelated_sims if s >= SUGGESTION_THRESHOLD)
        print(f"  무관한 용어 중 answerable 오탐: {false_ans}/{len(unrelated_sims)}")
        print(f"  무관한 용어 중 suggestion 오탐: {false_sug}/{len(unrelated_sims)}")


def compute_metrics(results):
    """Precision, Recall, nDCG 계산"""
    categories = {"exact": [], "related": [], "unrelated": []}
    for r in results:
        categories[r["category"]].append(r)

    overall_correct = sum(1 for r in results if r["is_correct"])
    print(f"전체 정확도: {overall_correct}/{len(results)} ({100*overall_correct/len(results):.1f}%)")
    print()

    for cat, items in categories.items():
        if not items:
            continue
        correct = sum(1 for r in items if r["is_correct"])
        avg_top_sim = sum(r["top_similarity"] for r in items) / len(items)
        ndcg_scores = [ndcg(r["relevances"], k=5) for r in items if r["relevances"]]
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0

        print(f"[{cat}] ({len(items)}건)")
        print(f"  정확도 (Precision): {correct}/{len(items)} ({100*correct/len(items):.1f}%)")
        print(f"  평균 top similarity: {avg_top_sim:.4f}")
        print(f"  평균 nDCG@5: {avg_ndcg:.4f}")

        # Recall for exact/related
        if cat in ("exact", "related"):
            recall_items = [r for r in items if r["expected"]]
            if recall_items:
                found = sum(1 for r in recall_items if any(
                    any(exp.lower() in rr.lower() or rr.lower() in exp.lower()
                        for exp in r["expected"])
                    for rr in r["top_names"][:5]
                ))
                print(f"  Recall@5: {found}/{len(recall_items)} ({100*found/len(recall_items):.1f}%)")
        print()


def analyze_thresholds(results):
    """유사도 점수 분포를 기반으로 threshold 적절성 분석"""
    exact = [r for r in results if r["category"] == "exact"]
    related = [r for r in results if r["category"] == "related"]
    unrelated = [r for r in results if r["category"] == "unrelated"]

    print("유사도 점수 분포:")
    for cat, items, label in [
        ("exact", exact, "정확한 용어 질문"),
        ("related", related, "관련 질문"),
        ("unrelated", unrelated, "무관한 질문"),
    ]:
        if items:
            sims = [r["top_similarity"] for r in items]
            print(f"  {label}: min={min(sims):.4f}, max={max(sims):.4f}, avg={sum(sims)/len(sims):.4f}")

    # Threshold 적절성 판단
    print(f"\nThreshold 판정:")
    print(f"  ANSWERABLE = {ANSWERABLE_THRESHOLD}")
    print(f"  SUGGESTION = {SUGGESTION_THRESHOLD}")

    if exact:
        exact_answerable = sum(1 for r in exact if r["top_similarity"] >= ANSWERABLE_THRESHOLD)
        print(f"  exact 중 answerable 판정: {exact_answerable}/{len(exact)}")

    if unrelated:
        unrelated_false_positive = sum(1 for r in unrelated if r["top_similarity"] >= SUGGESTION_THRESHOLD)
        print(f"  unrelated 중 오탐 (suggestion 이상): {unrelated_false_positive}/{len(unrelated)}")

    # 권장 threshold
    if exact and unrelated:
        exact_min = min(r["top_similarity"] for r in exact)
        unrelated_max = max(r["top_similarity"] for r in unrelated)
        gap = exact_min - unrelated_max
        print(f"\n  exact 최소 유사도: {exact_min:.4f}")
        print(f"  unrelated 최대 유사도: {unrelated_max:.4f}")
        print(f"  분리 갭: {gap:.4f}")
        if gap > 0.1:
            print(f"  → ✅ 충분한 분리 갭. Threshold 적절")
        elif gap > 0:
            print(f"  → ⚠️ 분리 갭이 좁음. Threshold 미세 조정 권장")
        else:
            print(f"  → ❌ 분리 갭 음수. Threshold 재설정 필요")


if __name__ == "__main__":
    run_verification()
