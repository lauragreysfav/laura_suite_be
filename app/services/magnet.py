import urllib.parse


def build_magnet(info_hash: str, title: str = "") -> str:
    dn = urllib.parse.quote(title) if title else ""
    if dn:
        return f"magnet:?xt=urn:btih:{info_hash}&dn={dn}"
    return f"magnet:?xt=urn:btih:{info_hash}"
