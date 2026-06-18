import crawlers.config as _config

BOT_NAME = "tccn_moc_children"
USER_AGENT = _config.USER_AGENT
DOWNLOAD_DELAY = _config.DOWNLOAD_DELAY
CONCURRENT_REQUESTS_PER_DOMAIN = _config.CONCURRENT_REQUESTS_PER_DOMAIN

SPIDER_MODULES = ["crawlers.tier1.moc_children.spiders"]
NEWSPIDER_MODULE = "crawlers.tier1.moc_children.spiders"

ROBOTSTXT_OBEY = False
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"
