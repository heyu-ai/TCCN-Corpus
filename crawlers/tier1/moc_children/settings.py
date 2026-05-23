from crawlers.config import CONCURRENT_REQUESTS_PER_DOMAIN, DOWNLOAD_DELAY, USER_AGENT

BOT_NAME = "tccn_moc_children"

SPIDER_MODULES = ["crawlers.tier1.moc_children.spiders"]
NEWSPIDER_MODULE = "crawlers.tier1.moc_children.spiders"

ROBOTSTXT_OBEY = False
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"
