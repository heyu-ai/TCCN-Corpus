BOT_NAME = "tccn_moc_children"

SPIDER_MODULES = ["crawlers.tier1.moc_children.spiders"]
NEWSPIDER_MODULE = "crawlers.tier1.moc_children.spiders"

USER_AGENT = "TCCN-Corpus-Bot/1.0 (+https://github.com/howie/TCCN-Corpus)"
ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 2.0
CONCURRENT_REQUESTS_PER_DOMAIN = 2
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"
