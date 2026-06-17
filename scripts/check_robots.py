"""
抓取目標站台的 robots.txt，輸出 Markdown 報告。
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crawlers.config import USER_AGENT

TARGETS = [
    "https://children.moc.gov.tw/robots.txt",
    "https://storybook.nlpi.edu.tw/robots.txt",
    "https://ebook.nlpi.edu.tw/robots.txt",
]


@dataclass
class RobotsResult:
    url: str
    status_code: int
    reason: str
    body_preview: str
    checked_at: str

    @property
    def domain(self) -> str:
        return self.url.removeprefix("https://").removeprefix("http://").split("/", 1)[0]


def fetch_robots(url: str) -> RobotsResult:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read(500).decode("utf-8", errors="replace").strip()
            return RobotsResult(url, response.status, "OK", body, checked_at)
    except HTTPError as exc:
        body = exc.read(500).decode("utf-8", errors="replace").strip()
        return RobotsResult(url, exc.code, exc.reason, body, checked_at)
    except URLError as exc:
        return RobotsResult(url, 0, str(exc.reason), "", checked_at)


def render_report(results: list[RobotsResult]) -> str:
    lines = [
        "# robots.txt 檢測報告",
        "",
        f"檢測時間（UTC）：{datetime.now(timezone.utc).isoformat()}",
        "",
        "| 平台 | 狀態碼 | 結果 | 備註 |",
        "|------|--------|------|------|",
    ]
    for result in results:
        preview = (result.body_preview[:60] + "...") if len(result.body_preview) > 60 else result.body_preview
        preview = preview.replace("\n", " ").replace("|", "\\|")
        lines.append(
            f"| {result.domain} | {result.status_code or 'ERR'} | {result.reason} | {preview or '—'} |"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="data/raw/robots-audit.md",
        help="輸出 Markdown 報告路徑",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = [fetch_robots(url) for url in TARGETS]
    report = render_report(results)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
