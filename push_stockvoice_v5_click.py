"""Push StockVoice V5 A/B ads (selected groups) to OpenAI Ads as a paused clicks campaign.

Source: StockVoice_OpenAI_Ads_V5_含非个股层12组_AB_2026-10-08.xlsx
  - 01_组总览: ad group name (= utm_term) and full Context hint
  - 02_全部广告: Ad name / Title / Description / full landing URL / image file
Images: ads_images_v6/masters/<Ad name>.png

Usage:
  python push_stockvoice_v5_click.py          # dry run: validate + write plan JSON
  python push_stockvoice_v5_click.py --push   # upload images, create everything (paused)

Never calls any /activate endpoint.
"""
import csv
import json
import sys
import time
import warnings
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import openpyxl
import requests
from PIL import Image

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
XLSX = HERE / "StockVoice_OpenAI_Ads_V5_含非个股层12组_AB_2026-10-08.xlsx"
KEY_FILE = HERE / "ads-manager-api-key.txt"
PLAN_FILE = HERE / "sv_v5_click_plan.json"
RESULT_FILE = HERE / "sv_v5_click_result.json"
MAPPING_CSV = HERE / "sv_v5_click_ad_id_mapping.csv"
BASE = "https://api.ads.openai.com/v1"

RUN = "r1"
STATUS = "paused"
GROUPS = ["G01", "G02", "G04", "G06", "G08", "G10"]
CAMPAIGN_NAME = "STOCKVOICE_US_CONTEXT_CLICK_V5"
DAILY_BUDGET_TWD = 720
COUNTRIES = ["TW", "US"]
# Custom events from the Stock_voice pixel (tracking only; clicks objective is unchanged)
CONVERSION_EVENTS = {
    "6accecae45a481a083532e54b2805a6b": "Login Completed",
    "6accec10503081a091bf9eb412253ada": "KOL Follow Completed",
    "6accec7c23c881a0a0b4df2fddf14cb9": "Stock Follow Completed",
}
BASE_URL = "https://stockvoice.cmoney.tw/"
UTM_CAMPAIGN = "stockvoice_us_context_click"
UTM_ORDER = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id"]


def build_plan():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    group_info = {}
    for r in wb["01_组总览"].iter_rows(min_row=2, values_only=True):
        if r[0]:
            group_info[r[0]] = {"name": r[4], "hint": r[10]}

    ws = wb["02_全部广告"]
    col = {c.value: i for i, c in enumerate(ws[1])}
    groups, errors = {}, []
    for r in ws.iter_rows(min_row=2, values_only=True):
        gid = r[0]
        if gid not in GROUPS:
            continue
        name, title, body = r[col["Ad name"]], r[col["Title"]], r[col["Description"]]
        term = r[col["utm_term"]]
        full_url = r[col["完整Landing URL（含UTM）"]]
        parts = urlsplit(full_url)
        params = dict(parse_qsl(parts.query, keep_blank_values=True))
        expected = {"utm_source": "openai", "utm_medium": "paid_conversation", "utm_campaign": UTM_CAMPAIGN,
                    "utm_term": term, "utm_content": "{ad_id}", "utm_id": "{campaign_id}"}
        if params != expected or list(params) != UTM_ORDER:
            errors.append(f"{name}: utm {params}")
        base = r[col["Ad destination URL"]]
        if base != BASE_URL or f"{parts.scheme}://{parts.netloc}{parts.path}" != base:
            errors.append(f"{name}: base url {base} / {full_url}")
        if term != group_info[gid]["name"]:
            errors.append(f"{name}: utm_term {term} != ad group {group_info[gid]['name']}")
        image = HERE / r[col["图片文件"]]
        if not image.exists():
            errors.append(f"{name}: image missing {image}")
        else:
            w, h = Image.open(image).size
            if min(w, h) < 640:
                errors.append(f"{name}: image too small {w}x{h}")
        if not (3 <= len(title) <= 50) or not body or len(body) > 100:
            errors.append(f"{name}: title/body length {len(title)}/{len(body or '')}")
        g = groups.setdefault(gid, {"group_id": gid, "name": group_info[gid]["name"],
                                    "context_hints": [group_info[gid]["hint"]],
                                    "query_string_template": parts.query, "ads": []})
        if g["query_string_template"] != parts.query:
            errors.append(f"{name}: A/B landing URLs differ within {gid}")
        g["ads"].append({"name": name, "title": title, "body": body, "target_url": base,
                         "image": str(image.relative_to(HERE)).replace("\\", "/")})

    for gid in GROUPS:
        if gid not in groups or len(groups[gid]["ads"]) != 2:
            errors.append(f"{gid}: expected A and B ads, got {len(groups.get(gid, {}).get('ads', []))}")

    plan = {
        "campaign": {
            "name": CAMPAIGN_NAME,
            "status": STATUS,
            "objective": "clicks",
            "bidding_type": "clicks",
            "billing_event_type": "click",
            "conversion_event_setting_ids": list(CONVERSION_EVENTS),
            "budget": {"daily_spend_limit_micros": DAILY_BUDGET_TWD * 1_000_000},
            "targeting": {"locations": {"countries": COUNTRIES}},
            "landing_page_configuration": {"query_string_template":
                f"utm_source=openai&utm_medium=paid_conversation&utm_campaign={UTM_CAMPAIGN}&utm_id={{campaign_id}}"},
        },
        "ad_groups": [groups[g] for g in GROUPS if g in groups],
    }
    return plan, errors


def push(plan):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {KEY_FILE.read_text().strip()}"})

    def post(path, body, idem):
        resp = s.post(f"{BASE}/{path}", json=body, headers={"Idempotency-Key": idem}, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"POST /{path} {resp.status_code}: {resp.text[:800]}")
        return resp.json()

    def upload(path):
        with open(HERE / path, "rb") as f:
            resp = s.post(f"{BASE}/upload", files={"file": (Path(path).name, f, "image/png")}, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"upload {path} {resp.status_code}: {resp.text[:800]}")
        return resp.json()["file_id"]

    result = {"campaign": None, "ad_groups": []}
    try:
        file_ids = {}
        for g in plan["ad_groups"]:
            for a in g["ads"]:
                file_ids[a["image"]] = upload(a["image"])
                print(f"uploaded {a['image']} -> {file_ids[a['image']]}")

        camp = post("campaigns", plan["campaign"], f"{CAMPAIGN_NAME}-{RUN}-campaign")
        result["campaign"] = {"id": camp["id"], "name": CAMPAIGN_NAME, "status": camp.get("status")}
        print(f"campaign {camp['id']} {CAMPAIGN_NAME} {camp.get('status')}")
        for g in plan["ad_groups"]:
            ag = post("ad_groups", {
                "campaign_id": camp["id"], "name": g["name"], "status": STATUS,
                "context_hints": g["context_hints"],
                "bidding_config": {"billing_event_type": "click", "strategy": "maximize_clicks"},
                "landing_page_configuration": {"query_string_template": g["query_string_template"]},
            }, f"{CAMPAIGN_NAME}-{RUN}-{g['name']}")
            rg = {"id": ag["id"], "name": g["name"], "status": ag.get("status"), "ads": []}
            result["ad_groups"].append(rg)
            print(f"  ad_group {ag['id']} {g['name']} {ag.get('status')}")
            for a in g["ads"]:
                ad = post("ads", {
                    "ad_group_id": ag["id"], "name": a["name"], "status": STATUS,
                    "creative": {"type": "chat_card", "title": a["title"], "body": a["body"],
                                 "target_url": a["target_url"], "file_id": file_ids[a["image"]]},
                    "landing_page_configuration": {"query_string_template": g["query_string_template"]},
                }, f"{CAMPAIGN_NAME}-{RUN}-{a['name']}")
                rg["ads"].append({"id": ad["id"], "name": a["name"], "title": a["title"],
                                  "image": a["image"], "status": ad.get("status")})
                print(f"    ad {ad['id']} {a['name']} {ad.get('status')}")
                time.sleep(0.15)
    finally:
        RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        with MAPPING_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["campaign", "campaign_id", "ad_group", "ad_group_id", "ad_name", "ad_id", "title", "image"])
            c = result["campaign"] or {}
            for g in result["ad_groups"]:
                for a in g["ads"]:
                    w.writerow([c.get("name"), c.get("id"), g["name"], g["id"], a["name"], a["id"], a["title"], a["image"]])


if __name__ == "__main__":
    plan, errors = build_plan()
    PLAN_FILE.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"plan: {CAMPAIGN_NAME} / {len(plan['ad_groups'])} ad groups / "
          f"{sum(len(g['ads']) for g in plan['ad_groups'])} ads")
    if errors:
        print("validation errors:", *errors, sep="\n  ")
        sys.exit(1)
    if "--push" in sys.argv:
        push(plan)
