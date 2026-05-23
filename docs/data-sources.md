# 資料來源合規矩陣

| 來源 | 代碼 | URL | 授權類型 | 全文可爬 | Metadata 可爬 | 商用許可 | 狀態 |
|------|------|-----|----------|----------|---------------|----------|------|
| 文化部兒童文化館 | MOC_CHILDREN | https://children.moc.gov.tw/ | 政府資料開放授權條款-第1版（OGDL-Taiwan-1.0） | 僅限已確認授權內容 | ✅ | ✅ | 優先走 OGD JSON + 再視頁面授權抓取 |
| 圓夢繪本資料庫 | YUANMENG | https://storybook.nlpi.edu.tw | 各繪本作者版權（All Rights Reserved） | ❌ 現階段不抓全文 | ✅ | ❌ 需授權 | Phase 2 僅做 metadata dry-run |
| 教育部教育雲 | EDU_CLOUD | https://ebook.nlpi.edu.tw | DRM 保護 | ❌ | ✅ | ❌ | 僅 metadata |
| FunPark / 布克聽聽 | METADATA_ONLY | — | 商業版權 | ❌ | ✅（國資圖入口） | ❌ | 僅書目 |

## 授權確認待辦

- [ ] 發函國立公共資訊圖書館，確認圓夢繪本全文學術研究用途授權
- [x] 確認文化部 OGD 可作為 seed list / metadata 來源
- [x] 確認各平台 robots.txt 現況
- [ ] 正式記錄 data.gov.tw 資料集頁面與 JSON resource URL
- [ ] 文化部站內實頁全文抓取前，需再逐頁複核授權標示與可用性

## robots.txt 檢測紀錄

| 平台 | 檢測日期 | 結果 |
|------|----------|------|
| children.moc.gov.tw | 2026-05-17 | `404 Not Found`，無 robots.txt；實作上仍採 `User-Agent: TCCN-Corpus-Bot/1.0` 與 2 秒 delay |
| storybook.nlpi.edu.tw | 2026-05-17 | `404 Not Found`，無 robots.txt；僅做 metadata dry-run，不抓全文 |
| ebook.nlpi.edu.tw | 2026-05-17 | `404`，無 robots.txt；維持 metadata-only 策略 |

## Phase 2 實作約束

- `crawlers/tier1/moc_children/ogd_fetcher.py` 優先抓 OGD JSON，輸出 `data/raw/moc_ogd.jsonl`
- `crawlers/tier1/moc_children/spiders/animate_spider.py` 使用 OGD 結果當 seed，不直接暴力掃描站台
- `crawlers/tier1/yuanmeng/yuanmeng_crawler.py` 僅驗證 selector / pagination，不輸出全文內容
- 新增 `license_type` schema 欄位，允許值：
  - `ogdl-tw-1`
  - `research-only`
  - `commercial`
