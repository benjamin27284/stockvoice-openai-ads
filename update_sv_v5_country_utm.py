"""Split utm_campaign for the StockVoice V5 country copies: ..._click -> ..._click_us / ..._click_ca.

Only the utm_campaign value changes; every other UTM param and the param order stay as they are.
Touches campaign, ad group and ad landing_page_configuration of the two copies only (never the source).

Usage:
  python update_sv_v5_country_utm.py          # dry run
  python update_sv_v5_country_utm.py --push
"""
import json, sys, time
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
BASE = "https://api.ads.openai.com/v1"
OLD = "stockvoice_us_context_click"
SOURCE = "cmpn_36b27a64ff4881999bb5b283b33e94db"
BACKUP = HERE / "sv_v5_country_utm_backup.json"
s = requests.Session()
s.headers["Authorization"] = "Bearer " + (HERE / "ads-manager-api-key.txt").read_text().strip()


def get(path, **params):
    r = s.get(f"{BASE}/{path}", params=params, timeout=60); r.raise_for_status(); return r.json()


def retag(qs, new):
    parts = qs.split("&")
    hits = [i for i, p in enumerate(parts) if p.split("=", 1)[0] == "utm_campaign"]
    if len(hits) != 1 or parts[hits[0]] != f"utm_campaign={OLD}":
        raise ValueError(f"unexpected utm_campaign in {qs}")
    parts[hits[0]] = f"utm_campaign={new}"
    return "&".join(parts)


updates, backup = [], []
for rc in json.loads((HERE / "sv_v5_country_copy_result.json").read_text(encoding="utf-8")):
    assert rc["id"] != SOURCE
    new = f"{OLD}_{rc['country'].lower()}"
    objs = [("campaigns", get(f"campaigns/{rc['id']}"))]
    for g in get("ad_groups", campaign_id=rc["id"], limit=100)["data"]:
        objs.append(("ad_groups", g))
        objs += [("ads", a) for a in get("ads", ad_group_id=g["id"], limit=100)["data"]]
    for kind, o in objs:
        qs = o["landing_page_configuration"]["query_string_template"]
        backup.append({"kind": kind, "id": o["id"], "name": o["name"], "query_string_template": qs})
        updates.append((kind, o["id"], o["name"], qs, retag(qs, new)))

print(f"{len(updates)} objects to update")
for kind, oid, name, old, newqs in updates:
    print(f"{kind:9} {name:32} {newqs}")

if "--push" in sys.argv:
    BACKUP.write_text(json.dumps(backup, ensure_ascii=False, indent=1), encoding="utf-8")
    for kind, oid, name, old, newqs in updates:
        r = s.post(f"{BASE}/{kind}/{oid}", json={"landing_page_configuration": {"query_string_template": newqs}},
                   headers={"Idempotency-Key": f"sv-v5-utm-split-{oid}"}, timeout=60)
        if r.status_code != 200:
            sys.exit(f"{kind} {oid} {r.status_code}: {r.text[:500]}")
        got = r.json()["landing_page_configuration"]["query_string_template"]
        print("ok" if got == newqs else "MISMATCH", kind, name, got if got != newqs else "")
        time.sleep(0.15)
