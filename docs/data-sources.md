# 資料來源合規矩陣

| 來源 | 代碼 | URL | 授權類型 | 全文可爬 | Metadata 可爬 | 商用許可 | 狀態 |
|------|------|-----|----------|----------|---------------|----------|------|
| 文化部兒童文化館 | MOC_CHILDREN | https://children.moc.gov.tw/ | 政府資料開放授權條款-第1版（OGDL-Taiwan-1.0） | 僅限已確認授權內容 | ✅ | ✅ | 優先走 OGD JSON + 再視頁面授權抓取 |
| 圓夢繪本資料庫 | YUANMENG | https://storybook.nlpi.edu.tw | 各繪本作者版權（All Rights Reserved） | ❌ 現階段不抓全文 | ✅ | ❌ 需授權 | Phase 2 僅做 metadata dry-run |
| 教育部教育雲 | EDU_CLOUD | https://ebook.nlpi.edu.tw | DRM 保護 | ❌ | ✅ | ❌ | 僅 metadata |
| FunPark / 布克聽聽 | METADATA_ONLY | — | 商業版權 | ❌ | ✅（國資圖入口） | ❌ | 僅書目 |

## 授權確認待辦

- [ ] 發函國立公共資訊圖書館，確認圓夢繪本全文學術研究用途授權（owner：法務／PM，人工流程）
- [x] 確認文化部 OGD 可作為 seed list / metadata 來源（授權為 OGDL-Taiwan-1.0；但資料集現已下架，見下節 blocker）
- [x] 確認各平台 robots.txt 現況（2026-06-16 重新檢測，仍為 404）
- [x] 正式記錄 data.gov.tw 資料集頁面（見下節）；⚠️ JSON resource URL 因資料集下架暫不可得
- [ ] 文化部站內實頁全文抓取前，需再逐頁複核授權標示與可用性

## 文化部 OGD 介接確認（2026-06-16）

於 data.gov.tw 確認三筆「兒童文化館」資料集，授權皆為「政府資料開放授權條款-第1版（OGDL-Taiwan-1.0）」、免費、提供機關為文化部、相關網址 https://children.moc.gov.tw：

| 資料集 | data.gov.tw 頁面 | 狀態 | 備註 |
|--------|------------------|------|------|
| 兒童文化館-主題閱讀區動畫書目 | https://data.gov.tw/dataset/24973 | ⚠️ 已下架（歷史資料留存） | 平台無 active 下載連結 |
| 兒童文化館-繪本花園動畫書目 | https://data.gov.tw/dataset/24968 | ⚠️ 已下架（歷史資料留存） | 平台無 active 下載連結 |
| 兒童文化館-聽書（有聲書）書目 | https://data.gov.tw/dataset/113587 | ⚠️ 已下架（歷史資料留存） | 平台無 active 下載連結 |

**Blocker / 後續行動：**

- 三筆資料集均顯示「資料集已下架，此為歷史資料留存」，data.gov.tw 上**無可用 JSON/CSV resource URL**，無法直接作為 OGD seed list。
- 另查得 data.gov.tw **並非標準 CKAN 平台**：`https://data.gov.tw/api/3/action/package_search` 回傳 404。`crawlers/tier1/moc_children/ogd_fetcher.py` 的 `discover_from_ckan_api` fallback 對 data.gov.tw 無效，Phase 2 需改走實際 API（`/api/v2/rest/dataset/{id}`，GET 對 search path 回 405，需確認正確參數）或洽文化部窗口取得資料檔。
- 文化部窗口（資料集聯絡人）：呂學榮 02-85126470，可發函確認歷史資料集是否仍可索取或改由站內 metadata 擷取。
- 在取得有效 resource URL 前，`make ogd-check` 需以 `--resource-url` / `--dataset-url`（或對應環境變數）手動指定；無 URL 時 fetcher 會明確報錯提示。

## robots.txt 檢測紀錄

| 平台 | 檢測日期 | 結果 |
|------|----------|------|
| children.moc.gov.tw | 2026-06-16 | `404 Not Found`，無 robots.txt；實作上仍採 `User-Agent: TCCN-Corpus-Bot/1.0` 與 2 秒 delay（2026-05-17 首測亦為 404） |
| storybook.nlpi.edu.tw | 2026-06-16 | `404 Not Found`，無 robots.txt；僅做 metadata dry-run，不抓全文 |
| ebook.nlpi.edu.tw | 2026-06-16 | `404 Not Found`，無 robots.txt；維持 metadata-only 策略 |

> robots 報告可隨時以 `make robots-check` 重新產生（輸出 `data/raw/robots-audit.md`）。

## Phase 2 實作約束

- `crawlers/tier1/moc_children/ogd_fetcher.py` 優先抓 OGD JSON，輸出 `data/raw/moc_ogd.jsonl`
- `crawlers/tier1/moc_children/spiders/animate_spider.py` 使用 OGD 結果當 seed，不直接暴力掃描站台
- `crawlers/tier1/yuanmeng/yuanmeng_crawler.py` 僅驗證 selector / pagination，不輸出全文內容
- 新增 `license_type` schema 欄位，允許值：
  - `ogdl-tw-1`
  - `research-only`
  - `commercial`
