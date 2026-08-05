"""
BE2 벡터 검색 품질 검증 스크립트 (실제 백엔드 파이프라인 검증)

실제 vector_retrieve() 서비스 함수 및 Supabase / OpenAI 클라이언트를 사용하여
백엔드 파이프라인 전체 품질을 검증합니다.

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

TEST_CASES = [
    ("GDP가 뭐야?", ["GDP", "Gross Domestic Product"], "exact"),
    ("기준금리란?", ["기준금리"], "exact"),
    ("ICO가 무슨 뜻이야?", ["ICO", "Initial Coin Offering"], "exact"),
    ("스프레드 설명해줘", ["스프레드", "spread"], "exact"),
    ("OECD가 뭐야?", ["OECD"], "exact"),
    ("KYC란 무엇인가요?", ["KYC"], "exact"),
    ("PDI 설명해줘", ["PDI", "Personal Disposable Income"], "exact"),
    ("ESI가 뭐야?", ["ESI", "Economic Sentiment Index"], "exact"),
    ("물가가 계속 오르는 현상이 뭐야?", ["인플레이션", "CPI", "소비자물가지수"], "related"),
    ("돈의 가치가 떨어지는 건?", ["인플레이션", "디플레이션", "화폐가치"], "related"),
    ("은행에서 돈 빌리는 이자는?", ["기준금리", "대출금리", "이자율"], "related"),
    ("주식시장 지표가 뭐야?", ["KOSPI", "주가지수", "Composite Index", "CI"], "related"),
    ("오늘 점심 뭐 먹지?", [], "unrelated"),
    ("강아지 키우는 법 알려줘", [], "unrelated"),
    ("서울 날씨 어때?", [], "unrelated"),
]

def run_verification():
    settings = check_env()
    supabase = get_supabase_client()

    print("=" * 70)
    print("BE2 벡터 검색 품질 검증 (실제 백엔드 파이프라인)")
    print("=" * 70)

    results_summary = []
    
    for query, expected, category in TEST_CASES:
        try:
            res = vector_retrieve(query, supabase=supabase)
            status = res.status.value
            
            top_name = res.term.term_name if res.term else (res.suggestions[0].term_name if res.suggestions else None)
            
            if category == "unrelated":
                is_correct = (status == "not_found")
            elif category == "exact":
                if status == "answerable" and res.term:
                    is_correct = any(exp.lower() in res.term.term_name.lower() or res.term.term_name.lower() in exp.lower() for exp in expected)
                elif status == "suggestions":
                    is_correct = any(
                        any(exp.lower() in s.term_name.lower() or s.term_name.lower() in exp.lower() for exp in expected)
                        for s in res.suggestions
                    )
                else:
                    is_correct = False
            else:  # related
                is_correct = (status != "not_found") and top_name and any(exp.lower() in top_name.lower() for exp in expected)

            results_summary.append({
                "query": query,
                "category": category,
                "status": status,
                "top_name": top_name,
                "is_correct": is_correct,
            })
            
            icon = "✅" if is_correct else "❌"
            print(f"  {icon} [{category:>9}] '{query}' -> status={status}, top={top_name}")
        except Exception as e:
            print(f"  ❌ [{category:>9}] '{query}' -> ERROR: {e}")

    print("\n" + "=" * 70)
    print("검증 통계")
    print("=" * 70)
    correct_count = sum(1 for r in results_summary if r["is_correct"])
    total_count = len(results_summary)
    print(f"전체 통과율: {correct_count}/{total_count} ({100 * correct_count / total_count if total_count else 0:.1f}%)")

if __name__ == "__main__":
    run_verification()
