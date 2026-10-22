"""Every stylesheet a page actually pulls in, not just the inline ones.

I was only reading <style> blocks. That meant the contrast check measured
0 pairs on f-keys.com, 0 on poticas.com and 1 on opticquiz.com, because
on a real site the colours live in a linked sheet. Contrast is the most
cited WCAG failure there is and I was effectively not checking it.

This resolves <link rel=stylesheet> against whatever the page came from
- a file on disk or a URL - and follows one level of @import.

It also reports what it could NOT read, and that matters more than it
looks: if a sheet is missing then the colours I measured are a subset of
the colours on the page, and a clean result over a subset is not a clean
result. The caller is expected to downgrade a pass when `missed` is not
empty, the same way I downgrade a pass for text painted over an image.
"""
from __future__ import annotations

import io
import os
import re
import urllib.parse
import urllib.request

UA = {"user-agent": "Mozilla/5.0 (compatible; a11yhat/0.1)"}
TIMEOUT = 30
MAX_BYTES = 4_000_000          # a stylesheet bigger than this is not a stylesheet
MAX_SHEETS = 40

_LINK = re.compile(r"<link\b([^>]*)>", re.I)
# Unquoted values are legal HTML and I was not matching them, so
# <link rel=stylesheet href=x.css> was invisible and its sheet silently
# never loaded. Three branches: double quoted, single quoted, bare.
_ATTR = re.compile(r'([a-z-]+)\s*=\s*"([^"]*)"'
                   r"|([a-z-]+)\s*=\s*'([^']*)'"
                   r"|([a-z-]+)\s*=\s*([^\s\"'>]+)", re.I)
_IMPORT = re.compile(r'@import\s+(?:url\(\s*)?["\']?([^"\')\s;]+)', re.I)


def _attrs(tag: str) -> dict:
    out = {}
    for m in _ATTR.finditer(tag):
        k = (m.group(1) or m.group(3) or m.group(5) or "").lower()
        v = m.group(2)
        if v is None:
            v = m.group(4)
        if v is None:
            v = m.group(6)
        out[k] = v
    return out


def stylesheet_hrefs(html: str):
    """Hrefs of every <link> that says it is a stylesheet.

    Attribute order is not fixed, so I read the tag's attributes rather
    than matching rel and href in one pattern and hoping they arrive in
    that order. rel can carry several tokens, as in rel="alternate
    stylesheet", so I look for the token rather than equality.
    """
    out = []
    for m in _LINK.finditer(html):
        a = _attrs(m.group(1))
        rel = (a.get("rel") or "").lower().split()
        href = a.get("href")
        if href and ("stylesheet" in rel or a.get("as", "").lower() == "style"):
            out.append(href)
    return out


def _read_local(href: str, base_dir: str):
    """A local stylesheet, resolved the way a browser would see it.

    A root-relative href like /win98.css means the site root, which I do
    not know from a single file, so I try the document's own directory
    and then walk up. Four levels is enough for every layout I ship and
    stops this wandering off into the filesystem.
    """
    clean = href.split("?")[0].split("#")[0]
    if clean.startswith("//") or "://" in clean:
        return None
    cands = []
    if clean.startswith("/"):
        rel = clean.lstrip("/")
        d = base_dir
        for _ in range(5):
            cands.append(os.path.join(d, rel))
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    else:
        cands.append(os.path.join(base_dir, clean))
    for p in cands:
        if os.path.isfile(p):
            return io.open(p, encoding="utf-8", errors="replace").read(MAX_BYTES)
    return None


def _read_remote(href: str, base_url: str):
    url = urllib.parse.urljoin(base_url, href)
    if not url.startswith(("http://", "https://")):
        return None
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(MAX_BYTES).decode("utf-8", "replace")


_VARDEF = re.compile(r"(--[\w-]+)\s*:\s*([^;}]+)")
_VARUSE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*?)\s*)?\)")


def custom_properties(css: str):
    """(values, redefined) for every --token in the sheet.

    I write my colours as tokens, and so does most of the web now. Until
    I resolved them, "color: var(--text)" parsed as nothing and the pair
    was dropped, which is why a 39 KB stylesheet with 126 colour
    declarations produced 0 measurable pairs.

    A token can be defined more than once - that is exactly how I do
    dark mode, redefining the same name under a prefers-color-scheme
    block. I take the FIRST definition, which is the default theme, and
    I return the names that have more than one distinct value so the
    caller can say out loud that it measured one theme and not the
    other. Silently measuring half a design and calling it a pass is the
    thing I am trying not to do.
    """
    values, redefined = {}, set()
    for name, raw in _VARDEF.findall(css):
        v = raw.strip()
        if name in values:
            if values[name] != v:
                redefined.add(name)
        else:
            values[name] = v
    return values, sorted(redefined)


def expand_vars(css: str, values=None, rounds: int = 5) -> str:
    """Substitute var(--x) and var(--x, fallback), nesting included."""
    if values is None:
        values, _ = custom_properties(css)

    def sub(m):
        name, fallback = m.group(1), m.group(2)
        if name in values:
            return values[name]
        return fallback if fallback is not None else m.group(0)

    for _ in range(rounds):
        new = _VARUSE.sub(sub, css)
        if new == css:
            break
        css = new
    return css


def collect(html: str, base: str | None = None):
    """(css, loaded, missed) for one document.

    `base` is the file path or URL the html came from. Without it I can
    only read what is inline, and I say so by returning every linked
    href as missed rather than quietly skipping them - a sheet I did not
    look for is not a sheet that was not there.
    """
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html,
                               re.I | re.S))
    loaded, missed = [], []
    hrefs = stylesheet_hrefs(html)[:MAX_SHEETS]
    if not hrefs:
        return css, loaded, missed

    is_url = bool(base) and base.startswith(("http://", "https://"))
    base_dir = ""
    if base and not is_url:
        base_dir = base if os.path.isdir(base) else os.path.dirname(
            os.path.abspath(base))

    seen = set()
    queue = [(h, 0) for h in hrefs]
    while queue:
        href, depth = queue.pop(0)
        if href in seen or depth > 1:
            continue
        seen.add(href)
        body = None
        if base is None:
            missed.append(href + " (no base given, so nothing was fetched)")
            continue
        try:
            body = _read_remote(href, base) if is_url else _read_local(href, base_dir)
        except Exception as e:                               # noqa: BLE001
            # I never swallow this. A sheet I could not read is the
            # difference between measuring the page and measuring part
            # of it, and the caller has to be told.
            missed.append("%s (%s)" % (href, type(e).__name__))
            continue
        if body is None:
            missed.append(href + " (not found)")
            continue
        css += "\n" + body
        loaded.append(href)
        for imp in _IMPORT.findall(body)[:MAX_SHEETS]:
            queue.append((imp, depth + 1))
    return css, loaded, missed


def collect_resolved(html: str, base: str | None = None):
    """collect(), with the custom properties substituted in.

    Returns (css, loaded, missed, redefined). `redefined` is the tokens
    that carry more than one value - my dark mode - so the caller can
    report which theme it actually measured.
    """
    css, loaded, missed = collect(html, base)
    values, redefined = custom_properties(css)
    return expand_vars(css, values), loaded, missed, redefined
