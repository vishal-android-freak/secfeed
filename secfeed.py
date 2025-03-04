# secfeed by Sharon Brizinov 2023
import random
import logging
import requests
import time
import pickle
import re
import sys
import json
from environs import Env

env = Env()

DB_PATH = "secfeed.db"
LIST_PARSED_DATA = []
SLACK_URL = env.str("SLACK_URL", "")
USER_AGENT = "Mozilla/5.0 (Linux; Android 6.0; SAMSUNG SM-G930F Build/MMB29K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/4.0 Chrome/44.0.2403.133 Mobile Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}
SEC_FEEDS = {
         # Example:
         # "URL TO QUERY TO GET LINKS" : 
         #    ("BASE ADDRESS",
         #    r"EXTRACT WITH REGEX AND APPEND TO BASE ADDRESS",
         #    ["LIST", "OF", "KEYWORDS", "THAT AT LEAST", ONE", "MUST", "EXISTS", "IN", "URL"]),

        # https://claroty.com/team82/research/
       	"https://claroty.com/team82/research/":
            ("https://claroty.com/team82/research/",
            r"href=\"/team82/research/([^\"]+)\"",
            None),

        # https://www.us-cert.gov/ics/advisories/icsa-20-147-01
        "https://www.us-cert.gov/ics/advisories/advisories.xml" : 
            ("https://www.us-cert.gov/ics/advisories/",
            r"ics/advisories/(icsm?a-\d+\-\d+\-\d+)",
            None),

        # https://cert.europa.eu/static/SecurityAdvisories/2022/CERT-EU-SA2022-082.pdf
        "https://cert.europa.eu/publications/security-advisories/" :
            ("https://cert.europa.eu/static/SecurityAdvisories/",
            r"(\d+/CERT-EU-SA\d+-\d+\.pdf)", 
            None),

        # https://www.tenable.com/security/research/tra-2020-34
        "https://www.tenable.com/security/research" : 
             ("https://www.tenable.com/security/research/tra-",
             r"/security/research/tra-(\d+\-\d+)",
             None), 

        # https://srcincite.io/blog/
        "https://srcincite.io/blog/":
            ("https://srcincite.io/blog/",
            r"<a class=\"post-link\" href=\"/blog/(\d+/\d+/\d+/[^\"]+)\">",
            None),

        # https://doar-e.github.io/index.html
        "https://doar-e.github.io/index.html":
            ("https://doar-e.github.io/blog/",
            r"\"\./blog/(\d+/\d+/\d+/[^\"]+)\">",
            None),

        # https://www.zerodayinitiative.com/advisories/ZDI-20-683/
        "https://www.zerodayinitiative.com/advisories/published" :
             ("https://www.zerodayinitiative.com/advisories/ZDI-",
             r"ZDI-(\d+\-\d+)",
             None), 

        # https://chemical-facility-security-news.blogspot.com/2020/05/public-ics-disclosures-week-of-5-23-20.html, https://chemical-facility-security-news.blogspot.com/2022/12/review-3-advisories-published-12-8-22.html
        "https://chemical-facility-security-news.blogspot.com/" : 
             ("https://chemical-facility-security-news.blogspot.com/", 
             r"\.blogspot\.com/(\d+/\d+/[\w+\d+\-]+\.html)", 
             ["disclosure", "advisories", "advisory"]), 
         
        "https://talosintelligence.com/vulnerability_reports" : 
            ("https://talosintelligence.com/vulnerability_reports/TALOS-", 
            r"/vulnerability_reports/TALOS-(\d+\-\d+)", 
            None), # https://talosintelligence.com/vulnerability_reports/TALOS-2020-1056
         
        "https://cert.vde.com/en/advisories" : 
            ("https://cert.vde.com/en/advisories/", 
            r"advisories/([vV][dD][eE]\-\d+\-\d+)", 
            None), # https://cert.vde.com/en/advisories/VDE-2021-045/
         
         "https://www.zeroscience.mk/en/vulnerabilities" : 
            ("https://www.zeroscience.mk/en/vulnerabilities/", 
            r"(ZSL-20\d+-\d+.php)", 
            None),
        
        # https://research.nccgroup.com/category/technical-advisory/
        "https://research.nccgroup.com/category/technical-advisory/":
            ("https://research.nccgroup.com/",
            r"\"https://research.nccgroup.com/(\d+/\d+/\d+/[^\"]+)\"",
            None),

        # https://ssd-disclosure.com/apple-safari-javascriptcore-inspector-type-confusion/
        "https://ssd-disclosure.com/advisories/" : 
            ("https://ssd-disclosure.com/", 
            r"<a href=\"https://ssd-disclosure\.com/([^\"]+)\" \>", 
            None), 
         
        "https://awesec.com/advisories.html" : 
            ("https://awesec.com/advisories/", 
            r"advisories\/(AWE-\d+-\d+\.html)\">", 
            None),

        # https://www.nozominetworks.com/blog/technical-analysis-of-the-winbox-payload-in-windigo/
        "https://www.nozominetworks.com/labs/labs-blogs/" : 
            ("https://www.nozominetworks.com/blog/", 
            r"<a href\=\"https://www.nozominetworks.com/blog/([^\"]+)\" >", 
            None), 

        # https://www.armis.com/research/tlstorm/
        "https://www.armis.com/armis-research/" : 
            ("https://www.armis.com/research/", 
            r"armis\.com\/research\/([\w+\d+\-]+\/)\"><", 
            None), 

        # https://research.checkpoint.com/?p=26395
        "https://research.checkpoint.com/feed/" : 
            ("https://research.checkpoint.com/?p=", 
            r"research.checkpoint.com\/\?p=(\d+)<\/guid>", 
            None),

        # https://blog.neodyme.io/posts/secure-randomness-part-2/
        "https://blog.neodyme.io/":
            ("https://blog.neodyme.io",
            r"tr href=\"(/posts/[^\"]+)\" class",
            None),
 
        # https://blog.viettelcybersecurity.com/security-wall-of-s7commplus-3/
        "https://blog.viettelcybersecurity.com":
            ("https://blog.viettelcybersecurity.com",
            r"<a class=\"post-card-image-link\" href=\"([^\"]+)\">",
            None),

        # https://starlabs.sg/blog/2022/12-the-last-breath-of-our-netgear-rax30-bugs-a-tragic-tale-before-pwn2own-toronto-2022/
        "https://starlabs.sg/blog/":
            ("https://starlabs.sg/blog/",
            r"\"https://starlabs.sg/blog/(\d+/[^\"]+)\"",
            None),

        # https://www.seebug.org/vuldb/ssvid-99599
        "https://www.seebug.org/rss/new/":
            ("",
            r"(http://www.seebug.org/vuldb/ssvid-\d+)",
            None),            

}

SLEEP_TIME = 60 * 60 * 2 # 2 hours -+ 10-5000 seconds
IS_TEST_MODE = env.bool("IS_TEST_MODE", False)
SHOULD_REPORT = env.bool("SHOULD_REPORT", True)

def setup_logger():
    logging.basicConfig(filename="secfeed.log", filemode="w", level=logging.DEBUG)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


def notify_slack(url):
    if SHOULD_REPORT:
        data = {"text" : url, "unfurl_links": True, "unfurl_media": True}
        resp = requests.post(SLACK_URL, data=json.dumps(data))
        logging.debug("Slack responded: '{}'".format(resp.text))
setup_logger()


if not IS_TEST_MODE:
    try:
        # First load from database everything we have
        logging.info("Loading data from: {}".format(DB_PATH))
        with open(DB_PATH, "rb") as f:
            LIST_PARSED_DATA = pickle.load(f)
        logging.info("Loaded {} entries from DB".format(len(LIST_PARSED_DATA)))
    except Exception as e:
        pass

while True:
    logging.info("Getting data")

    for sec_feed in SEC_FEEDS:
        if IS_TEST_MODE:
            print("--> {}".format(sec_feed))

        # Prepare
        url_feed = sec_feed
        # one keyword must be present
        base_url, regex_str, keywords = SEC_FEEDS[url_feed]
        # Get data
        try:
            data = requests.get(sec_feed, headers=HEADERS)
        except Exception as e:
            continue
        # Extract
        extracted_datas = re.findall(regex_str, data.text)
        for extracted_data in extracted_datas:
            if not keywords or any([keyword in extracted_data for keyword in keywords]):
                full_url = base_url + extracted_data
                if IS_TEST_MODE:
                    print("  [-] {}".format(full_url))
                else:
                    if full_url not in LIST_PARSED_DATA:
                        logging.info("Saving new url, and notifying slack: '{}'".format(full_url))
                        LIST_PARSED_DATA.append(full_url)
                        notify_slack(full_url)
    if not IS_TEST_MODE:
        logging.info("Saving everything back to DB: {}".format(DB_PATH))
        with open(DB_PATH, "wb") as f:
            pickle.dump(LIST_PARSED_DATA, f)

        rand_time = random.randint(10, 5000)
        logging.info("Going to sleep {:.2f} hours".format((rand_time+SLEEP_TIME) / 3600.0))
        time.sleep(SLEEP_TIME + rand_time)
    else:
        break
