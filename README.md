# 股聲 StockVoice × OpenAI Ads（ChatGPT 廣告）

2026 年 10 月在 OpenAI Ads 上為股聲（美股社群／個股情緒看板）投放 ChatGPT 對話廣告的完整紀錄：從意圖研究、文案與素材、API 自動化上架，到成效回報與下一階段的 A/B 假設驗證。

## 投放成果（主 campaign，10/13–10/20，台灣）

| 指標 | 數字 |
|---|---|
| 曝光 | 32,698 |
| 點擊 | 812 |
| CTR | 2.48%（10/16 起每日 2.6–4.8%） |
| CPC | 由 NT$34 降到 NT$10 |

- 點擊集中在「財報前後」「美股大跌」兩則，合計佔 62%。
- 10/18 起加開美國、加拿大 campaign，各約 1.0% CTR，樣本尚不足。
- 進站後每次點擊僅看 1.2–1.4 頁，註冊 6 人：**點得進來，但落地頁接不住。**

## A/B 假設驗證

A 版＝用戶口吻的問句標題，B 版＝品牌型標題，同一組 context hint 下對照，OpenAI Pixel 歸因到每則廣告。

| | 曝光 | 點擊 | CTR | 每次點擊看幾頁 | 每次點擊看內容次數 |
|---|---|---|---|---|---|
| A 問句 | 14,125 | 422 | 2.99% | 1.44 | 0.35 |
| B 品牌型 | 12,635 | 181 | 1.43% | 1.35 | 0.22 |

| 假設 | 內容 | 狀態 |
|---|---|---|
| H1 | 廣告講具體處境，落地頁卻是首頁，接不住 | 待驗證：G06、G08 做首頁 vs 深連結對照 |
| H2 | 新手引導與下載彈窗一進站就打斷 | 待驗證：對 ChatGPT 流量關閉彈窗 |
| H3 | 問句標題帶來好奇點擊，不是真需求 | **部分成立**：A 版點擊是 B 版 2 倍，但進站深度不比 B 深；以每千次曝光計 A 版仍較好，不換掉 |
| H4 | 轉換目標太遠，冷流量第一次來就要求註冊 | 待驗證：改用中段事件（點貼文、進個股頁、關注）當 KPI |

下一階段：含功能詞 hint（18 組，已建好）與 ULTRARM 型鏈路 hint。因主 campaign 預算已花滿，新 hint 開獨立 campaign、給同預算，比較曝光、點擊、CPC 與預算是否花得完。

## 目錄

| 路徑 | 內容 |
|---|---|
| `股聲_OpenAI_Ads_下一階段測試_詳細版_2026-10-20.md` / `_ExecutiveSummary_` | 現況拆解、A/B 假設驗證、下一階段測試設計 |
| `股聲_ChatGPT廣告首週回報*.docx/html`, `股聲_OpenAI_Ads_成效_2026-10-15.xlsx` | 首週成效回報（主管版與詳細版） |
| `StockVoice_V5_CLICK_每則廣告成效_2026-10-14.xlsx` | 每則廣告成效 |
| `StockVoice_OpenAI_Ads_V5_含非个股层12组_AB_2026-10-08.xlsx` | V5 文案總表：12 組情境 × A/B 標題 × context hint |
| `StockVoice_OpenAI_Ads_V6_一步距离13组_含功能词hint_2026-10-20.xlsx` | V6 文案總表：13 組「一步距離」情境，含功能詞 hint |
| `StockVoice_意图复盘_V16_2026-10-14.md` + `_附件/` | 意圖復盤：用模擬對話盲判 hint 能否接住對話，找出覆蓋缺口 |
| `StockVoice_文案四项标准审查_2026-10-14.md` | 文案四項標準審查 |
| `ads_images_v6/` | 廣告卡片圖（light/dark、1x/2x）、隱喻圖盲測、110px/64px 對比度稽核 |
| `push_stockvoice_v5_click.py`, `copy_stockvoice_v5_by_country.py`, `push_sv_v6_func_*.py`, `update_sv_v5_country_utm.py` | OpenAI Ads API 自動化：建立 campaign／ad group／ad、跨國複製、批次改 UTM 與 hint（一律以 paused 建立） |
| `sv_*_plan.json` | 各次上架的投放計畫（campaign 結構、hint、文案、UTM） |


