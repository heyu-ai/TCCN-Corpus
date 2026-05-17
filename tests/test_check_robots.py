from scripts.check_robots import RobotsResult, render_report


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
