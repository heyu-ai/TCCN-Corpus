# TCCN-Corpus

**台灣適齡兒童故事與兒歌語料庫 | Taiwan Age-Appropriate Children's Story & Nursery Rhymes Corpus**

專為 AI 訓練與 RAG 系統設計的結構化兒童語料庫，目標收錄至少 1,500 筆台灣在地化繪本故事與兒歌。

---

## 專案結構

```
TCCN-Corpus/
├── docs/
│   ├── project-plan.md       # 完整計畫書
│   └── data-sources.md       # 資料來源合規矩陣
├── crawlers/
│   ├── tier1/                # 第一級：完全公開資源
│   │   ├── moc_children/     # 文化部兒童文化館
│   │   └── yuanmeng/         # 圓夢繪本資料庫
│   ├── tier2/                # 第二級：需授權資源（僅 metadata）
│   │   └── edu_cloud/        # 教育部教育雲
│   └── tier3/                # 第三級：商業資源（僅書目）
│       └── metadata_only/
├── data/
│   ├── raw/                  # 原始爬取結果（.gitignore）
│   ├── cleaned/              # 清洗後資料（.gitignore）
│   └── labeled/              # 標籤化完成（.gitignore）
├── schemas/
│   └── corpus_schema.json    # 語料庫統一欄位定義
└── scripts/
    ├── clean.py              # 清洗 pipeline
    └── label.py             # 標籤化 pipeline
```

## Schema

所有語料條目遵循 `schemas/corpus_schema.json`，核心欄位：

| 欄位 | 說明 |
|------|------|
| `id` | 唯一識別碼（`{SOURCE}-{序號}`） |
| `content_type` | `story` / `nursery_rhyme` / `picture_book` / `animation_script` |
| `language` | `zh-TW` / `nan-TW`（台語）/ `hak-TW`（客語）/ `indigenous` |
| `age_range` | `{ min, max }`（歲） |
| `developmental_milestone` | 0~6 歲語言發展里程碑標籤 |
| `phonics` | 押韻格式、節拍、重複句型比例 |
| `themes` | 主題標籤 |
| `action_cues` | 互動動作指示 |

## 執行階段

- **Phase 1**：合規審查 + Schema 鎖定
- **Phase 2**：爬蟲開發（Scrapy + Playwright）
- **Phase 3**：全面爬取 + 影音分離
- **Phase 4**：清洗與幼教標籤化
- **Phase 5**：RAG 向量資料庫建置
- **Phase 6**：系統測試與 Prompt 優化

詳見 [docs/project-plan.md](docs/project-plan.md)

## 授權

語料庫內容依各原始來源授權條款為準，詳見 [docs/data-sources.md](docs/data-sources.md)。
