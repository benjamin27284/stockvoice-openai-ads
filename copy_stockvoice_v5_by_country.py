"""Copy live STOCKVOICE_US_CONTEXT_CLICK_V5 into two paused campaigns: US only and CA only.

Everything (budget, conversion events, UTM templates, ad groups, context hints, ads, images)
is copied from the live snapshot; only the country targeting differs.

Usage:
  python copy_stockvoice_v5_by_country.py          # dry run (writes snapshot + plan)
  python copy_stockvoice_v5_by_country.py --push   # create everything (paused)

Never calls any /activate endpoint.
"""
import csv, json, sys, time
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
BASE = "https://api.ads.openai.com/v1"
SOURCE = "cmpn_36b27a64ff4881999bb5b283b33e94db"
RUN = "r1"
TARGETS = {"US": "STOCKVOICE_US_CONTEXT_CLICK_V5_US", "CA": "STOCKVOICE_US_CONTEXT_CLICK_V5_CA"}
SNAP_FILE = HERE / "sv_v5_country_copy_snapshot.json"
RESULT_FILE = HERE / "sv_v5_country_copy_result.json"
MAPPING_CSV = HERE / "sv_v5_country_copy_ad_id_mapping.csv"

s = requests.Session()
s.headers["Authorization"] = "Bearer " + (HERE / "ads-manager-api-key.txt").read_text().strip()


def get(path, **params):
    r = s.get(f"{BASE}/{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def post(path, body, idem):
    r = s.post(f"{BASE}/{path}", json=body, headers={"Idempotency-Key": idem}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"POST /{path} {r.status_code}: {r.text[:800]}")
    return r.json()


def snapshot():
    c = get(f"campaigns/{SOURCE}")
    c["ad_groups"] = sorted(get("ad_groups", campaign_id=SOURCE, limit=100)["data"], key=lambda g: g["name"])
    for g in c["ad_groups"]:
        g["ads"] = sorted(get("ads", ad_group_id=g["id"], limit=100)["data"], key=lambda a: a["name"])
    return c


def push(src):
    result = []
    try:
        for cc, name in TARGETS.items():
            camp = post("campaigns", {
                "name": name, "status": "paused",
                "objective": src["objective"], "bidding_type": src["bidding_type"],
                "billing_event_type": src["billing_event_type"],
                "conversion_event_setting_ids": src["conversion_event_setting_ids"],
                "budget": src["budget"],
                "targeting": {"locations": {"countries": [cc]}},
                "landing_page_configuration": src["landing_page_configuration"],
            }, f"{name}-{RUN}-campaign")
            rc = {"country": cc, "id": camp["id"], "name": name, "status": camp.get("status"), "ad_groups": []}
            result.append(rc)
            print(f"campaign {camp['id']} {name} {camp.get('status')}")
            for g in src["ad_groups"]:
                ag = post("ad_groups", {
                    "campaign_id": camp["id"], "name": g["name"], "status": "paused",
                    "context_hints": g["context_hints"], "bidding_config": g["bidding_config"],
                    "landing_page_configuration": g["landing_page_configuration"],
                }, f"{name}-{RUN}-{g['name']}")
                rg = {"id": ag["id"], "name": g["name"], "source_id": g["id"], "ads": []}
                rc["ad_groups"].append(rg)
                print(f"  ad_group {ag['id']} {g['name']} {ag.get('status')}")
                for a in g["ads"]:
                    cr = a["creative"]
                    ad = post("ads", {
                        "ad_group_id": ag["id"], "name": a["name"], "status": "paused",
                        "creative": {k: cr[k] for k in ("type", "title", "body", "target_url", "file_id", "image_crop") if cr.get(k) is not None},
                        "landing_page_configuration": a["landing_page_configuration"],
                    }, f"{name}-{RUN}-{a['name']}")
                    rg["ads"].append({"id": ad["id"], "name": a["name"], "source_id": a["id"], "title": cr["title"]})
                    print(f"    ad {ad['id']} {a['name']} {ad.get('status')}")
                    time.sleep(0.15)
    finally:
        RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        with MAPPING_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["country", "campaign", "campaign_id", "ad_group", "ad_group_id", "ad_name", "ad_id", "source_ad_id", "title"])
            for c in result:
                for g in c["ad_groups"]:
                    for a in g["ads"]:
                        w.writerow([c["country"], c["name"], c["id"], g["name"], g["id"], a["name"], a["id"], a["source_id"], a["title"]])


if __name__ == "__main__":
    src = snapshot()
    SNAP_FILE.write_text(json.dumps(src, ensure_ascii=False, indent=1), encoding="utf-8")
    n_ads = sum(len(g["ads"]) for g in src["ad_groups"])
    print(f"source {src['name']} {src['status']} / {len(src['ad_groups'])} ad groups / {n_ads} ads; "
          f"budget {src['budget']}; events {len(src['conversion_event_setting_ids'])}")
    missing = [a["name"] for g in src["ad_groups"] for a in g["ads"] if not a["creative"].get("file_id")]
    if missing:
        sys.exit(f"ads without file_id: {missing}")
    for cc, name in TARGETS.items():
        print(f"  -> {name}: countries [{cc}], paused")
    if "--push" in sys.argv:
        push(src)
