import pytest
from scrapy.http import HtmlResponse, Request


@pytest.fixture
def fake_response():
    def _make(url: str, html: str) -> HtmlResponse:
        return HtmlResponse(url=url, body=html.encode("utf-8"), request=Request(url=url))
    return _make
