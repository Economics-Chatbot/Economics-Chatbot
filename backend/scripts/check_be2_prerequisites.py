"""Check terms table data availability and RPC function for BE2 verification."""
import os
import sys
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

url = os.getenv("SUPABASE_URL", "").strip()
key = os.getenv("SUPABASE_ANON_KEY", "").strip()

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Accept": "application/json",
    "Prefer": "count=exact",
}


def check_table(table, select="*", limit=5):
    endpoint = f"{url}/rest/v1/{table}?select={select}&limit={limit}"
    req = Request(endpoint, headers=headers)
    try:
        with urlopen(req, timeout=10) as resp:
            cr = resp.headers.get("Content-Range", "")
            data = json.loads(resp.read().decode("utf-8"))
            print(f"\n[Table: {table}] Content-Range: {cr}, fetched: {len(data)}")
            if data:
                print(f"  Columns: {list(data[0].keys())}")
                # Skip embedding fields
                sample = {k: (str(v)[:80] + "..." if isinstance(v, str) and len(str(v)) > 80 else v) for k, v in data[0].items() if "embedding" not in k}
                print(f"  Sample: {json.dumps(sample, ensure_ascii=False)}")
            return data, cr
    except HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        print(f"\n[-] Table '{table}' HTTP {e.code}: {err}")
        return [], ""


def check_rpc(rpc_name):
    """Try calling an RPC function with a dummy embedding to see if it exists."""
    endpoint = f"{url}/rest/v1/rpc/{rpc_name}"
    payload = json.dumps({
        "query_embedding": [0.0] * 1536,
        "match_count": 3,
    }).encode("utf-8")
    req = Request(endpoint, headers={
        **headers,
        "Content-Type": "application/json",
    }, data=payload, method="POST")
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"\n[RPC: {rpc_name}] SUCCESS - returned {len(data)} rows")
            if data:
                print(f"  Columns: {list(data[0].keys())}")
                sample = {k: (str(v)[:80] + "..." if isinstance(v, str) and len(str(v)) > 80 else v) for k, v in data[0].items() if "embedding" not in k}
                print(f"  Sample: {json.dumps(sample, ensure_ascii=False)}")
            return data
    except HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        print(f"\n[-] RPC '{rpc_name}' HTTP {e.code}: {err}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("BE2 Vector Search Prerequisites Check")
    print(f"Supabase URL: {url}")
    print("=" * 60)

    # 1. Check terms table
    terms_data, terms_range = check_table("terms", "term_id,term_name,official_definition")

    # 2. Check search_names table
    sn_data, sn_range = check_table("search_names", "id,term_id,search_name", limit=5)

    # 3. Check context table
    ctx_data, ctx_range = check_table("context")

    # 4. Check RPC function
    print("\n" + "=" * 60)
    print("RPC Function Check")
    print("=" * 60)
    rpc_result = check_rpc("match_economic_terms")

    # Summary
    print("\n" + "=" * 60)
    print("PREREQUISITES SUMMARY")
    print("=" * 60)

    def parse_total(cr):
        if "/" in cr:
            return cr.split("/")[-1]
        return "0"

    issues = []
    terms_total = parse_total(terms_range)
    sn_total = parse_total(sn_range)

    print(f"  terms table: {terms_total} rows")
    print(f"  search_names table: {sn_total} rows")
    print(f"  context table: {parse_total(ctx_range)} rows")
    print(f"  match_economic_terms RPC: {'✅ Available' if rpc_result is not None else '❌ Not available'}")

    if terms_total == "0":
        issues.append("terms 테이블에 데이터가 없음 (RLS 또는 데이터 미적재)")
    if rpc_result is None:
        issues.append("match_economic_terms RPC 함수가 없거나 접근 불가")

    if issues:
        print("\n⚠️  ISSUES:")
        for i in issues:
            print(f"  - {i}")
        print("\n→ BE2 벡터 검색 품질 검증을 위해서는:")
        print("  1. terms 테이블에 경제용어 데이터 적재 필요")
        print("  2. match_economic_terms RPC 함수 생성 필요 (SQL migration)")
        print("  3. SUPABASE_SERVICE_ROLE_KEY 또는 적절한 RLS 정책 필요")
    else:
        print("\n✅ All prerequisites met for BE2 quality verification")
