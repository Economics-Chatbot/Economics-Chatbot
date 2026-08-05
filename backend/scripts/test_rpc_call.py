"""Test if match_economic_terms RPC works by disambiguating the overload."""
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
    "Content-Type": "application/json",
}

# Try with min_similarity to disambiguate overload
payload = json.dumps({
    "query_embedding": [0.01] * 1536,
    "match_count": 5,
    "min_similarity": 0.0,
}).encode("utf-8")

endpoint = f"{url}/rest/v1/rpc/match_economic_terms"
req = Request(endpoint, headers=headers, data=payload, method="POST")

try:
    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"[+] RPC SUCCESS! Returned {len(data)} rows")
        if data:
            print(f"Columns: {list(data[0].keys())}")
            for i, row in enumerate(data[:3]):
                clean = {k: (str(v)[:60] + "..." if isinstance(v, str) and len(str(v)) > 60 else v) for k, v in row.items() if "embedding" not in k}
                print(f"  Row {i}: {json.dumps(clean, ensure_ascii=False)}")
        else:
            print("  (No rows returned - terms table may be empty or RPC returns nothing at similarity 0)")
except HTTPError as e:
    err = e.read().decode("utf-8", errors="ignore")
    print(f"[-] RPC FAILED HTTP {e.code}: {err}")
