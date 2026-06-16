from crawlers.config import USER_AGENT
from scripts.check_robots import USER_AGENT as ROBOTS_USER_AGENT
from scripts.check_robots import RobotsResult, render_report


def test_robots_user_agent_points_to_org_repo():
    # 與 ogd_fetcher 共用同一 config UA，避免再次出現 howie/heyu-ai 漂移。
    assert ROBOTS_USER_AGENT is USER_AGENT
    assert "github.com/heyu-ai/TCCN-Corpus" in ROBOTS_USER_AGENT


def test_render_report_contains_domain_and_status():
    report = render_report(
        [
            RobotsResult(
                url="https://children.moc.gov.tw/robots.txt",
                status_code=404,
                reason="Not Found",
                body_preview="missing",
                checked_at="2026-05-17T00:00:00+00:00",
            )
        ]
    )
    assert "children.moc.gov.tw" in report
    assert "| 404 |" in report
    assert "missing" in report
