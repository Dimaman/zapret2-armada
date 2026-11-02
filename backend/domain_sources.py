"""Fixed allowlisted data sources; snapshot SHA, TLS and bounded parsing."""
import hashlib
import json
import re
import urllib.request
from .config_manager import domains

REPO = "rosakodu/zapret-deck"
FILES = ("list-google.txt", "list-general.txt")
REF_URL = f"https://api.github.com/repos/{REPO}/git/ref/heads/main"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Domain source redirects are forbidden")


def download(url, limit):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "Zapret2-Armada/0.1.0", "Accept": "application/json, text/plain"})
    with opener.open(request, timeout=15) as response:
        if response.status != 200:
            raise ValueError("Domain source did not return HTTP 200")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Domain source exceeds size limit")
        return data


def update(fetch=download):
    ref = json.loads(fetch(REF_URL, 16000))
    sha = ref["object"]["sha"]
    if ref["object"].get("type") != "commit" or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid source snapshot commit")
    result, provenance = set(), []
    for name in FILES:
        url = f"https://raw.githubusercontent.com/{REPO}/{sha}/lists/{name}"
        data = fetch(url, 200000)
        parsed = domains(data.decode("utf-8-sig"))
        if not parsed:
            raise ValueError("Empty domain source")
        result.update(parsed)
        provenance.append({"url": url, "commit": sha, "sha256": hashlib.sha256(data).hexdigest(), "count": len(parsed)})
    return sorted(result), provenance
