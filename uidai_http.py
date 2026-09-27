import os
from urllib.parse import urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from dotenv import load_dotenv

load_dotenv()

UIDAI_HOST = "tathya.uidai.gov.in"


def _proxy_url():
    return (
        os.getenv("UIDAI_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
        or ""
    ).strip()


def _redact_proxy(url):
    try:
        parts = urlsplit(url)
        if parts.password:
            netloc = parts.hostname or ""
            if parts.username:
                netloc = f"{parts.username}:***@{netloc}"
            if parts.port:
                netloc = f"{netloc}:{parts.port}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    return url


def make_uidai_session(retries=0, log=print):
    """Session for UIDAI. Uses UIDAI_PROXY when set (required on Heroku)."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        connect=0,
        read=retries,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))

    proxy = _proxy_url()
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})
        log(f"🌐 UIDAI requests via proxy: {_redact_proxy(proxy)}")
    else:
        log("⚠️ UIDAI_PROXY not set. Heroku IPs are usually blocked by tathya.uidai.gov.in")
    return session


def check_uidai_reachability(timeout=8):
    """Returns (ok, message) after a TCP/HTTPS probe to UIDAI."""
    session = make_uidai_session(retries=0, log=lambda *_: None)
    proxy = _proxy_url()
    via = f"proxy {_redact_proxy(proxy)}" if proxy else "direct"
    try:
        res = session.get(f"https://{UIDAI_HOST}/", timeout=timeout, allow_redirects=True)
        return True, f"{via} -> HTTP {res.status_code}"
    except Exception as e:
        return False, f"{via} -> {e}"
