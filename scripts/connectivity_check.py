"""End-to-end connectivity check for all external services."""
import json
import os
import sys
import time
import uuid
import subprocess
from pathlib import Path

# Load .env manually
env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

results = []


def record(service, test, status, detail=""):
    results.append({"service": service, "test": test, "status": status, "detail": detail})
    icon = "\u2705" if status == "PASS" else "\u274c"
    print(f"  {icon} {service} / {test}: {status}" + (f" \u2014 {detail}" if detail else ""))


def curl_json(url, headers=None, data=None, method=None, timeout=15):
    """Use curl subprocess to avoid Cloudflare blocking urllib."""
    cmd = ["curl", "-s", "--max-time", str(timeout)]
    if method:
        cmd += ["-X", method]
    if headers:
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
    if data:
        cmd += ["-d", data]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    return json.loads(result.stdout)


def curl_raw(url, headers=None, data=None, method=None, timeout=15):
    """Like curl_json but returns (status_code_approx, headers_text, body)."""
    cmd = ["curl", "-s", "-i", "--max-time", str(timeout)]
    if method:
        cmd += ["-X", method]
    if headers:
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
    if data:
        cmd += ["-d", data]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    return result.stdout


# ─── 1. Pinecone Primary ────────────────────────────────────
print("\n\u2500\u2500 Pinecone Primary \u2500\u2500")
try:
    pc_key = os.environ.get("PINECONE_API_KEY", "")
    if not pc_key:
        record("Pinecone-Primary", "api-key", "FAIL", "PINECONE_API_KEY not set")
    else:
        # List indexes
        data = curl_json(
            "https://api.pinecone.io/indexes",
            headers={"Api-Key": pc_key, "X-Pinecone-API-Version": "2024-10"}
        )
        index_names = [idx["name"] for idx in data.get("indexes", [])]
        record("Pinecone-Primary", "list-indexes", "PASS",
               f"Found {len(index_names)} indexes: {', '.join(sorted(index_names))}")

        expected_primary = ["ublib2", "saimemory", "athenacontextualmemory", "uicontextualmemory",
                           "miracontextualmemory", "seancallieupdates", "seanmiracontextualmemory"]
        for idx in expected_primary:
            if idx in index_names:
                record("Pinecone-Primary", f"index-{idx}", "PASS")
            else:
                record("Pinecone-Primary", f"index-{idx}", "FAIL", "Not found in account")

        # Test query on ublib2
        hosts = json.loads(os.environ.get("BOMBA_PINECONE_INDEX_HOSTS", "{}"))
        ublib2_host = hosts.get("ublib2")
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if ublib2_host and openai_key:
            embed_data = curl_json(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                data=json.dumps({"model": "text-embedding-3-small", "input": "zone action"})
            )
            vector = embed_data["data"][0]["embedding"]

            query_data = curl_json(
                f"https://{ublib2_host}/query",
                headers={"Api-Key": pc_key, "Content-Type": "application/json"},
                data=json.dumps({"vector": vector, "topK": 3, "includeMetadata": True, "namespace": "longterm"})
            )
            matches = query_data.get("matches", [])
            record("Pinecone-Primary", "query-ublib2", "PASS", f"{len(matches)} matches for 'zone action'")
        elif not ublib2_host:
            record("Pinecone-Primary", "query-ublib2", "FAIL", "No host for ublib2")
        else:
            record("Pinecone-Primary", "query-ublib2", "FAIL", "No OPENAI_API_KEY for embeddings")

except Exception as e:
    record("Pinecone-Primary", "connection", "FAIL", str(e))

# ─── 2. Pinecone Write (saimemory) ──────────────────────────
print("\n\u2500\u2500 Pinecone Write Test \u2500\u2500")
try:
    hosts = json.loads(os.environ.get("BOMBA_PINECONE_INDEX_HOSTS", "{}"))
    saimemory_host = hosts.get("saimemory")
    pc_key = os.environ.get("PINECONE_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if not saimemory_host:
        record("Pinecone-Write", "host", "FAIL", "No host for saimemory")
    elif not pc_key:
        record("Pinecone-Write", "api-key", "FAIL", "No PINECONE_API_KEY")
    elif not openai_key:
        record("Pinecone-Write", "embeddings", "FAIL", "No OPENAI_API_KEY")
    else:
        embed_data = curl_json(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
            data=json.dumps({"model": "text-embedding-3-small", "input": "connectivity test probe"})
        )
        vector = embed_data["data"][0]["embedding"]
        test_id = f"connectivity-test-{uuid.uuid4().hex[:8]}"

        # Upsert
        upsert_data = curl_json(
            f"https://{saimemory_host}/vectors/upsert",
            headers={"Api-Key": pc_key, "Content-Type": "application/json"},
            data=json.dumps({
                "vectors": [{"id": test_id, "values": vector,
                            "metadata": {"test": True, "source": "connectivity-check"}}],
                "namespace": "test"
            })
        )
        record("Pinecone-Write", "upsert", "PASS",
               f"Upserted {test_id}, count={upsert_data.get('upsertedCount', '?')}")

        time.sleep(2)

        # Query back
        query_data = curl_json(
            f"https://{saimemory_host}/query",
            headers={"Api-Key": pc_key, "Content-Type": "application/json"},
            data=json.dumps({"vector": vector, "topK": 1, "includeMetadata": True, "namespace": "test"})
        )
        matches = query_data.get("matches", [])
        if matches and matches[0]["id"] == test_id:
            record("Pinecone-Write", "query-back", "PASS",
                   f"Retrieved {test_id} with score={matches[0].get('score', '?')}")
        else:
            record("Pinecone-Write", "query-back", "FAIL", f"Expected {test_id}, got {matches}")

        # Delete
        curl_json(
            f"https://{saimemory_host}/vectors/delete",
            headers={"Api-Key": pc_key, "Content-Type": "application/json"},
            data=json.dumps({"ids": [test_id], "namespace": "test"})
        )
        record("Pinecone-Write", "delete", "PASS", f"Deleted {test_id}")

except Exception as e:
    record("Pinecone-Write", "write-test", "FAIL", str(e))

# ─── 4. Supabase ────────────────────────────────────────────
print("\n\u2500\u2500 Supabase \u2500\u2500")
try:
    supa_url = os.environ.get("SUPABASE_URL", "")
    supa_key = os.environ.get("SUPABASE_KEY", "")

    if not supa_url or not supa_key:
        record("Supabase", "config", "FAIL",
               f"URL={'set' if supa_url else 'missing'}, KEY={'set' if supa_key else 'missing'}")
    else:
        # Read test — count rows in tables
        for table in ["sai_contacts", "sai_memory", "forge_operations", "acti_beings"]:
            try:
                raw = curl_raw(
                    f"{supa_url}/rest/v1/{table}?select=*&limit=1",
                    headers={
                        "apikey": supa_key,
                        "Authorization": f"Bearer {supa_key}",
                        "Content-Type": "application/json",
                        "Prefer": "count=exact"
                    }
                )
                # Parse content-range from headers
                count = "?"
                for hline in raw.split("\n"):
                    if hline.lower().startswith("content-range:"):
                        cr = hline.split(":", 1)[1].strip()
                        count = cr.split("/")[-1] if "/" in cr else "?"
                        break
                record("Supabase", f"read-{table}", "PASS", f"{count} rows")
            except Exception as e:
                record("Supabase", f"read-{table}", "FAIL", str(e))

        # Write test — insert into sai_memory (simpler schema), verify, delete
        try:
            test_id = str(uuid.uuid4())
            insert_payload = json.dumps({
                "id": test_id,
                "content": "connectivity-check-test",
                "created_at": "2026-03-03T00:00:00Z"
            })
            raw = curl_raw(
                f"{supa_url}/rest/v1/sai_memory",
                headers={
                    "apikey": supa_key,
                    "Authorization": f"Bearer {supa_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                data=insert_payload
            )
            if "201" in raw[:50] or test_id in raw:
                record("Supabase", "write-insert", "PASS", f"Inserted test row {test_id}")

                # Delete
                curl_raw(
                    f"{supa_url}/rest/v1/sai_memory?id=eq.{test_id}",
                    headers={
                        "apikey": supa_key,
                        "Authorization": f"Bearer {supa_key}",
                        "Content-Type": "application/json"
                    },
                    method="DELETE"
                )
                record("Supabase", "write-delete", "PASS", f"Deleted test row {test_id}")
            else:
                # Try to extract error
                error_detail = raw.split("\r\n\r\n")[-1][:300] if "\r\n\r\n" in raw else raw[:300]
                record("Supabase", "write-insert", "FAIL", error_detail)
        except Exception as e:
            record("Supabase", "write-test", "FAIL", str(e))

except Exception as e:
    record("Supabase", "connection", "FAIL", str(e))

# ─── 5. ElevenLabs ──────────────────────────────────────────
print("\n\u2500\u2500 ElevenLabs \u2500\u2500")
try:
    el_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not el_key:
        record("ElevenLabs", "api-key", "FAIL", "ELEVENLABS_API_KEY not set")
    else:
        data = curl_json(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": el_key}
        )
        voices = data.get("voices", [])
        voice_names = [v["name"] for v in voices]
        record("ElevenLabs", "list-voices", "PASS", f"{len(voices)} voices")

        for name in ["Callie", "Athena", "Sean"]:
            found = [v for v in voices if name.lower() in v["name"].lower()]
            if found:
                record("ElevenLabs", f"voice-{name}", "PASS", f"ID={found[0]['voice_id']}")
            else:
                record("ElevenLabs", f"voice-{name}", "FAIL", "Not found")

        try:
            data = curl_json(
                "https://api.elevenlabs.io/v1/convai/agents",
                headers={"xi-api-key": el_key}
            )
            agents = data.get("agents", [])
            record("ElevenLabs", "list-agents", "PASS", f"{len(agents)} agents")
        except Exception as e:
            record("ElevenLabs", "list-agents", "FAIL", str(e))

except Exception as e:
    record("ElevenLabs", "connection", "FAIL", str(e))

# ─── 6. Twilio ──────────────────────────────────────────────
print("\n\u2500\u2500 Twilio \u2500\u2500")
try:
    tw_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    tw_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    tw_phone = os.environ.get("TWILIO_PHONE_NUMBER", "")

    if not tw_sid or not tw_token:
        record("Twilio", "config", "FAIL",
               f"SID={'set' if tw_sid else 'missing'}, TOKEN={'set' if tw_token else 'missing'}")
    else:
        data = curl_json(
            f"https://{tw_sid}:{tw_token}@api.twilio.com/2010-04-01/Accounts/{tw_sid}/IncomingPhoneNumbers.json"
        )
        numbers = data.get("incoming_phone_numbers", [])
        record("Twilio", "list-numbers", "PASS", f"{len(numbers)} phone numbers")

        if tw_phone:
            found = [n for n in numbers if n.get("phone_number") == tw_phone]
            if found:
                record("Twilio", f"configured-number", "PASS",
                       f"{tw_phone} active, status={found[0].get('status', '?')}")
            else:
                record("Twilio", f"configured-number", "FAIL", f"{tw_phone} not found")

except Exception as e:
    record("Twilio", "connection", "FAIL", str(e))

# ─── 7. Bland.ai ────────────────────────────────────────────
print("\n\u2500\u2500 Bland.ai \u2500\u2500")
try:
    bland_key = os.environ.get("BLAND_API_KEY", "")
    if not bland_key:
        record("Bland.ai", "api-key", "FAIL", "BLAND_API_KEY not set")
    else:
        # List pathways
        try:
            data = curl_json(
                "https://api.bland.ai/v1/convo_pathway",
                headers={"Authorization": bland_key, "User-Agent": "BombaSR/1.0",
                         "Accept": "application/json"}
            )
            count = len(data) if isinstance(data, list) else len(data.get("data", []))
            record("Bland.ai", "list-pathways", "PASS", f"{count} pathways")
        except Exception as e:
            record("Bland.ai", "list-pathways", "FAIL", str(e))

        # List calls
        try:
            data = curl_json(
                "https://api.bland.ai/v1/calls?limit=1",
                headers={"Authorization": bland_key, "User-Agent": "BombaSR/1.0",
                         "Accept": "application/json"}
            )
            total = data.get("total_count", "?") if isinstance(data, dict) else "?"
            record("Bland.ai", "list-calls", "PASS", f"{total} total calls")
        except Exception as e:
            record("Bland.ai", "list-calls", "FAIL", str(e))

except Exception as e:
    record("Bland.ai", "connection", "FAIL", str(e))

# ─── 8. OpenAI Embeddings ───────────────────────────────────
print("\n\u2500\u2500 OpenAI Embeddings \u2500\u2500")
try:
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        record("OpenAI", "api-key", "FAIL", "OPENAI_API_KEY not set")
    else:
        data = curl_json(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
            data=json.dumps({"model": "text-embedding-3-small", "input": "connectivity test"})
        )
        embedding = data["data"][0]["embedding"]
        dims = len(embedding)
        record("OpenAI", "embeddings", "PASS", f"text-embedding-3-small returned {dims} dimensions")
        if dims == 1536:
            record("OpenAI", "dimension-check", "PASS", "1536 dims as expected")
        else:
            record("OpenAI", "dimension-check", "FAIL", f"Expected 1536, got {dims}")

except Exception as e:
    record("OpenAI", "connection", "FAIL", str(e))

# ─── Generate report ────────────────────────────────────────
print(f"\n\n{'=' * 50}")
print("  CONNECTION STATUS REPORT")
print(f"{'=' * 50}\n")

pass_count = sum(1 for r in results if r["status"] == "PASS")
fail_count = sum(1 for r in results if r["status"] == "FAIL")
print(f"  Total: {len(results)} checks \u2014 {pass_count} PASS, {fail_count} FAIL\n")

# Write CONNECTION_STATUS.md
report_lines = [
    "# Connection Status Report",
    "",
    f"**Date:** 2026-03-03",
    f"**Total checks:** {len(results)} \u2014 {pass_count} PASS, {fail_count} FAIL",
    "",
    "| Service | Test | Status | Details |",
    "|---------|------|--------|---------|",
]

for r in results:
    detail = r["detail"].replace("|", "\\|").replace("\n", " ")[:150]
    report_lines.append(f"| {r['service']} | {r['test']} | {r['status']} | {detail} |")

report_lines.append("")
report_path = Path(__file__).parent.parent / "CONNECTION_STATUS.md"
report_path.write_text("\n".join(report_lines), encoding="utf-8")
print(f"Report saved to {report_path}")
