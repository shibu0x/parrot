#!/usr/bin/env python3
"""Pull the user's own public writing into ~/.writer/samples/<channel>/ so it outranks chat habits.

  python3 scripts/socials.py add medium @you            # blog channel
  python3 scripts/socials.py add substack you           # you.substack.com, blog channel
  python3 scripts/socials.py add rss https://you.dev/feed.xml
  python3 scripts/socials.py add devto you
  python3 scripts/socials.py add bluesky you.bsky.social   # tweet channel
  python3 scripts/socials.py add x ~/Downloads/twitter-archive.zip   # tweet + reply channels
  python3 scripts/socials.py add linkedin ~/Downloads/Basic_LinkedInDataExport.zip
  python3 scripts/socials.py add link <url> [<url> ...]  # single tweets, LinkedIn posts, Medium/blog articles
  python3 scripts/socials.py set <anything> ...          # profile/post links, feeds, export files: type is detected
  python3 scripts/socials.py list | remove <n> | sync
  python3 scripts/socials.py find    # X / LinkedIn exports in ~/Downloads
  python3 scripts/socials.py skip    # user said: don't ask about links again

Add only accounts that belong to the user. `--channel NAME` on `add` overrides the default channel.
"""
import argparse, csv, hashlib, html, io, json, os, re, sys, urllib.parse, urllib.request, zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

from extract import SAMPLES, scrub

CONFIG = os.path.expanduser("~/.writer/socials.json")
DONT_ASK = os.path.expanduser("~/.writer/.socials-dont-ask")
MAX_PER_SOURCE = 500
UA = {"User-Agent": "writer-skill (+https://github.com/shibu0x/writer-skill)"}
DEFAULT_CHANNEL = {"medium": "blog", "substack": "blog", "rss": "blog", "devto": "blog",
                   "bluesky": "tweet", "x": "tweet", "linkedin": "linkedin", "link": "blog"}


class _Text(HTMLParser):
    BLOCK = {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "blockquote", "pre", "tr"}
    SKIP = {"script", "style", "figure", "figcaption", "nav", "header", "footer", "aside", "form", "noscript"}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        self.skip += tag in self.SKIP
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag in self.BLOCK and tag != "br":  # <br /> fires start and end; one newline is enough
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_text(s):
    p = _Text()
    p.feed(s or "")
    text = re.sub(r"[ \t]+", " ", "".join(p.out))
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return r.read()


# Each reader yields (id, text, channel-or-None). None means the entry's channel.

def feed(xml_bytes):
    """RSS or Atom. Prefers full content over the summary."""
    root = ET.fromstring(xml_bytes)
    ns = {"a": "http://www.w3.org/2005/Atom", "c": "http://purl.org/rss/1.0/modules/content/"}
    for it in root.iter("item"):
        body = it.findtext("c:encoded", namespaces=ns) or it.findtext("description") or ""
        title = it.findtext("title") or ""
        yield it.findtext("guid") or it.findtext("link") or title, f"{title}\n\n{html_text(body)}", None
    for e in root.iter("{http://www.w3.org/2005/Atom}entry"):
        body = e.findtext("a:content", namespaces=ns) or e.findtext("a:summary", namespaces=ns) or ""
        title = e.findtext("a:title", namespaces=ns) or ""
        yield e.findtext("a:id", namespaces=ns) or title, f"{title}\n\n{html_text(body)}", None


def devto(user):
    for a in json.loads(get(f"https://dev.to/api/articles?username={user}&per_page=30")):
        full = json.loads(get(f"https://dev.to/api/articles/{a['id']}"))
        yield str(a["id"]), f"{a['title']}\n\n{full.get('body_markdown', '')}", None


def bluesky(handle):
    url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={handle}&limit=100&filter=posts_with_replies"
    for item in json.loads(get(url)).get("feed", []):
        post = item["post"]
        if item.get("reason") or post["author"]["handle"] != handle.lstrip("@"):
            continue  # reposts of other people
        rec = post.get("record", {})
        yield post["uri"], rec.get("text", ""), "reply" if rec.get("reply") else None


def _archive_file(path, names):
    """Bytes of the first matching file inside an export: a zip, a folder, or the file itself."""
    path = os.path.expanduser(path)
    if zipfile.is_zipfile(path):
        z = zipfile.ZipFile(path)
        hit = [n for n in z.namelist() if os.path.basename(n) in names]
        return [z.read(n) for n in hit]
    if os.path.isdir(path):
        return [open(os.path.join(d, f), "rb").read() for d, _, fs in os.walk(path) for f in fs if f in names]
    return [open(path, "rb").read()]


def x_archive(path):
    """tweets.js from X's 'Download an archive of your data'."""
    for raw in _archive_file(path, {"tweets.js", "tweets-part1.js", "tweets-part2.js", "tweet.js"}):
        data = json.loads(raw.decode("utf-8", "ignore").split("=", 1)[1])
        for row in data:
            t = row.get("tweet", row)
            text = html.unescape(t.get("full_text", t.get("text", "")))
            if text.startswith("RT @"):
                continue  # retweets are other people's words
            text = re.sub(r"https://t\.co/\w+", "", text).strip()
            reply = t.get("in_reply_to_status_id_str") or text.startswith("@")
            yield t.get("id_str", text), text, "reply" if reply else None


def linkedin(path):
    """Shares.csv from LinkedIn's 'Get a copy of your data'."""
    for raw in _archive_file(path, {"Shares.csv"}):
        for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig", "ignore"))):
            text = (row.get("ShareCommentary") or "").replace('""', '"').strip()
            if text:
                yield row.get("ShareLink") or text, text, None


def _ld_text(page):
    """Post or article body from a page's JSON-LD (LinkedIn posts, most blogs and news sites)."""
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for d in data if isinstance(data, list) else data.get("@graph", [data]):
            if isinstance(d, dict):
                body = d.get("articleBody") or (d.get("text") if d.get("@type") == "SocialMediaPosting" else None)
                if body:
                    return f"{d.get('headline', '')}\n\n{body}".strip() if d.get("@type") != "SocialMediaPosting" else body
    return ""


def link(url):
    """One post from its URL. Profiles on X and LinkedIn need a login, so those are refused with the alternatives."""
    u = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    host, path = u.netloc.lower().removeprefix("www.").removeprefix("mobile."), u.path
    if host in ("x.com", "twitter.com"):
        m = re.search(r"/status(?:es)?/(\d+)", path)
        if not m:
            raise ValueError("X profiles need a login to read. Give links to single tweets, or your X archive (add x <zip>).")
        # ponytail: the embed CDN accepts any token today; compute the real one if it starts checking
        t = json.loads(get(f"https://cdn.syndication.twimg.com/tweet-result?id={m.group(1)}&token=a"))
        text = re.sub(r"https://t\.co/\w+", "", html.unescape(t.get("text", ""))).strip()
        yield m.group(1), text, "reply" if t.get("in_reply_to_status_id_str") else "tweet"
    elif host.endswith("linkedin.com"):
        if not re.match(r"/(posts|feed/update|pulse)/", path):
            raise ValueError("LinkedIn profiles need a login to read. Give links to single posts, or your LinkedIn export (add linkedin <zip>).")
        yield url, _ld_text(get(url).decode("utf-8", "ignore")), "linkedin"
    elif host == "medium.com" or host.endswith(".medium.com"):
        # Medium blocks scripts on post pages, but the author's feed has the same text
        who = next((p for p in path.split("/") if p.startswith("@")), None) or "@" + host.split(".")[0]
        want = path.rstrip("/").split("/")[-1]
        for pid, text, ch in feed(get(f"https://medium.com/feed/{who}")):
            if want in pid or want.rsplit("-", 1)[-1] in pid:
                yield pid, text, ch
                return
        raise ValueError("not in the author's Medium feed (it only has the newest 10). Paste the text into ~/.writer/samples/blog/ by hand.")
    else:
        page = get(url).decode("utf-8", "ignore")
        text = _ld_text(page)
        if not text:
            art = re.search(r"<article.*?</article>", page, re.S)
            text = html_text(art.group(0)) if art else ""
        if not text:  # plain pages: keep lines that read like prose, drop menus and buttons
            main = re.search(r"<main.*?</main>", page, re.S) or re.search(r"<body.*?</body>", page, re.S)
            paras = [p for p in html_text(main.group(0) if main else page).split("\n\n") if len(p.split()) >= 8]
            text = "\n\n".join(paras) if sum(len(p.split()) for p in paras) >= 50 else ""
        if not text:
            raise ValueError("couldn't find the post text on that page. Paste it into ~/.writer/samples/blog/ by hand.")
        yield url, text, None


def read(entry):
    kind, value = entry["type"], entry["value"]
    if kind == "medium":
        return feed(get(f"https://medium.com/feed/{value if value.startswith('@') else '@' + value}"))
    if kind == "substack":
        host = value if "." in value else f"{value}.substack.com"
        return feed(get(f"https://{host.removeprefix('https://').rstrip('/')}/feed"))
    if kind == "rss":
        return feed(get(value))
    if kind == "devto":
        return devto(value)
    if kind == "bluesky":
        return bluesky(value)
    if kind == "x":
        return x_archive(value)
    if kind == "linkedin":
        return linkedin(value)
    if kind == "link":
        return link(value)
    raise ValueError(f"unknown type {kind}")


def sync(entries, base=SAMPLES, reader=read):
    """Write new pieces to <base>/<channel>/<type>-<hash>.txt. Existing files are left alone, so re-runs only add.
    Returns the entries that worked, so callers only save sources that can actually be read."""
    ok = []
    for entry in entries:
        new = 0
        try:
            pieces = list(reader(entry))[:MAX_PER_SOURCE]
        except Exception as e:  # one dead feed shouldn't stop the rest
            print(f"{entry['type']} {entry['value']}: failed ({e})")
            continue
        ok.append(entry)
        for pid, text, channel in pieces:
            text = scrub(text.strip())
            if len(text) < 3:
                continue
            ch = channel or entry.get("channel") or DEFAULT_CHANNEL[entry["type"]]
            os.makedirs(os.path.join(base, ch), exist_ok=True)
            f = os.path.join(base, ch, f"{entry['type']}-{hashlib.sha1(pid.encode()).hexdigest()[:12]}.txt")
            if not os.path.exists(f):
                open(f, "w").write(text)
                new += 1
        print(f"{entry['type']} {entry['value']}: {len(pieces)} found, {new} new")
    return ok


def _contains(path, names):
    if zipfile.is_zipfile(path):
        return any(os.path.basename(n) in names for n in zipfile.ZipFile(path).namelist())
    return os.path.isdir(path) and any(f in names for _, _, fs in os.walk(path) for f in fs)


def classify(item, getter=None):
    """Turn whatever the user pasted (profile link, post link, feed, export file, handle) into a source entry."""
    path = os.path.expanduser(item)
    if os.path.exists(path):
        if _contains(path, {"tweets.js", "tweet.js"}) or path.endswith(("tweets.js", "tweet.js")):
            return {"type": "x", "value": path}
        if _contains(path, {"Shares.csv"}) or path.endswith("Shares.csv"):
            return {"type": "linkedin", "value": path}
        raise ValueError(f"{item}: not an X archive or LinkedIn export")
    u = urllib.parse.urlparse(item if "://" in item else "https://" + item)
    host = u.netloc.lower().removeprefix("www.")
    parts = [p for p in u.path.split("/") if p]
    if host == "medium.com" and len(parts) == 1 and parts[0].startswith("@"):
        return {"type": "medium", "value": parts[0]}
    if host.endswith(".medium.com") and not parts:
        return {"type": "medium", "value": "@" + host.split(".")[0]}
    if host.endswith(".substack.com") and not parts:
        return {"type": "substack", "value": host.split(".")[0]}
    if host == "bsky.app" and len(parts) >= 2 and parts[0] == "profile":
        return {"type": "bluesky", "value": parts[1]}
    if host == "dev.to" and len(parts) == 1:
        return {"type": "devto", "value": parts[0]}
    if re.search(r"(\.xml|/feed|/rss|/atom)/?$", u.path):
        return {"type": "rss", "value": item}
    if not parts and host not in ("x.com", "twitter.com", "linkedin.com"):
        # a blog's home page: use its feed if it advertises one, so we get every post
        page = (getter or get)(f"https://{host}/").decode("utf-8", "ignore")
        m = re.search(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*>', page)
        href = m and re.search(r'href="([^"]+)"', m.group(0))
        if href:
            return {"type": "rss", "value": urllib.parse.urljoin(f"https://{host}/", html.unescape(href.group(1)))}
    return {"type": "link", "value": item}


def find(downloads="~/Downloads"):
    """X and LinkedIn exports already sitting in Downloads, so the user doesn't have to type a path."""
    d = os.path.expanduser(downloads)
    hits = []
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        f = os.path.join(d, name)
        try:
            if _contains(f, {"tweets.js", "tweet.js"}):
                hits.append(("x", f))
            elif _contains(f, {"Shares.csv"}):
                hits.append(("linkedin", f))
        except (OSError, zipfile.BadZipFile):
            continue
    return hits


def load():
    return json.load(open(CONFIG)) if os.path.exists(CONFIG) else []


def save(entries):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    json.dump(entries, open(CONFIG, "w"), indent=2)


def demo():
    import tempfile
    rss = b"""<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><guid>1</guid>
      <title>My post</title><content:encoded><![CDATA[<p>so i built a thing</p><figure>img</figure><p>it works</p>]]></content:encoded>
      </item></channel></rss>"""
    (pid, text, _), = feed(rss)
    assert text == "My post\n\nso i built a thing\n\nit works", repr(text)
    assert html_text("line one<br />line two<br /><br />next para") == "line one\nline two\n\nnext para"
    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>a</id><title>T</title><content type="html">&lt;p&gt;hi&lt;/p&gt;</content></entry></feed>"""
    assert list(feed(atom))[0][1] == "T\n\nhi"
    with tempfile.TemporaryDirectory() as d:
        tweets = 'window.YTD.tweets.part0 = [{"tweet": {"id_str": "1", "full_text": "shipped it &amp; it works https://t.co/abc"}},' \
                 '{"tweet": {"id_str": "2", "full_text": "RT @someone: not mine"}},' \
                 '{"tweet": {"id_str": "3", "full_text": "@bob yeah agreed", "in_reply_to_status_id_str": "9"}}]'
        os.makedirs(f"{d}/data")
        open(f"{d}/data/tweets.js", "w").write(tweets)
        assert list(x_archive(d)) == [("1", "shipped it & it works", None), ("3", "@bob yeah agreed", "reply")]
        open(f"{d}/Shares.csv", "w").write('Date,ShareLink,ShareCommentary\n2026-01-01,https://l/1,"so we launched today"\n')
        assert list(linkedin(f"{d}/Shares.csv")) == [("https://l/1", "so we launched today", None)]
        zipfile.ZipFile(f"{d}/twitter-2026.zip", "w").writestr("data/tweets.js", tweets)
        assert ("x", f"{d}/twitter-2026.zip") in find(d) and ("x", f"{d}/data") in find(d)
        page = '<script type="application/ld+json">{"@type": "SocialMediaPosting", "text": "so we shipped it"}</script>'
        assert _ld_text(page) == "so we shipped it"
        page = '<script type="application/ld+json">{"@graph": [{"@type": "Article", "headline": "H", "articleBody": "body"}]}</script>'
        assert _ld_text(page) == "H\n\nbody"
        for profile in ["https://x.com/someone", "linkedin.com/in/someone"]:
            try:
                next(link(profile))
                raise AssertionError(profile)
            except ValueError:
                pass
        cases = {
            "https://medium.com/@shibu0x": ("medium", "@shibu0x"), "shibu0x.medium.com": ("medium", "@shibu0x"),
            "https://medium.com/@shibu0x/some-post-5ef44ce67a1e": ("link", None), "noahpinion.substack.com": ("substack", "noahpinion"),
            "https://you.substack.com/p/a-post": ("link", None), "https://bsky.app/profile/jay.bsky.team": ("bluesky", "jay.bsky.team"),
            "https://dev.to/ben": ("devto", "ben"), "https://dev.to/ben/a-post-12": ("link", None),
            "https://site.dev/feed.xml": ("rss", None), "https://x.com/jack/status/20": ("link", None),
            "https://x.com/jack": ("link", None), f"{d}/twitter-2026.zip": ("x", None),
        }
        for item, (kind, value) in cases.items():
            e = classify(item, getter=lambda u: b"")
            assert e["type"] == kind and (value is None or e["value"] == value), (item, e)
        home = b'<link rel="alternate" type="application/rss+xml" href="/index.xml">'
        assert classify("https://myblog.dev", getter=lambda u: home) == {"type": "rss", "value": "https://myblog.dev/index.xml"}
        out = f"{d}/samples"
        fake = lambda e: iter([("1", "hello world", None), ("2", "my key sk-proj-AbCdEf1234567890XyZ", None), ("3", "@bob hi", "reply")])
        sync([{"type": "x", "value": "archive"}], out, fake)
        assert sync([{"type": "x", "value": "archive"}], out, fake) == [{"type": "x", "value": "archive"}]  # re-run adds nothing
        def broken(e):
            raise ValueError("needs a login")
        assert sync([{"type": "link", "value": "https://x.com/jack"}], out, broken) == []
        assert sorted(os.listdir(out)) == ["reply", "tweet"] and len(os.listdir(f"{out}/tweet")) == 2
        assert "sk-proj" not in "".join(open(f"{out}/tweet/{f}").read() for f in os.listdir(f"{out}/tweet"))
    print("socials ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("type", choices=sorted(DEFAULT_CHANNEL))
    add.add_argument("value", nargs="+", help="username, handle, feed URL, export file path, or post links")
    add.add_argument("--channel", help="samples folder to write into (default depends on type)")
    rm = sub.add_parser("remove")
    rm.add_argument("n", type=int, help="number from `list`")
    st = sub.add_parser("set", help="add anything the user pastes: profile or post links, feeds, export files")
    st.add_argument("items", nargs="+")
    sub.add_parser("list")
    sub.add_parser("sync")
    sub.add_parser("find", help="look for X / LinkedIn exports in ~/Downloads")
    sub.add_parser("skip", help="user said don't ask about links again")
    sub.add_parser("test")
    a = ap.parse_args()

    entries = load()
    if a.cmd == "test":
        return demo()
    if a.cmd == "add":
        new = [{"type": a.type, "value": v} for v in (a.value if a.type == "link" else a.value[:1])]
        for e in new:
            if a.channel:
                e["channel"] = a.channel
        save(entries + sync(new))
    elif a.cmd == "set":
        new = []
        for item in a.items:
            try:
                e = classify(item)
            except Exception as err:
                print(f"{item}: {err}")
                continue
            if e in entries + new:
                print(f"{e['type']} {e['value']}: already added")
            else:
                new.append(e)
        save(entries + sync(new))
    elif a.cmd == "remove":
        print("removed", entries.pop(a.n - 1))
        save(entries)
    elif a.cmd == "list":
        for i, e in enumerate(entries, 1):
            print(f"{i}. {e['type']} {e['value']} -> {e.get('channel') or DEFAULT_CHANNEL[e['type']]}")
        if not entries:
            print("no socials yet, see: python3 socials.py --help")
    elif a.cmd == "sync":
        sync(entries)
    elif a.cmd == "find":
        for kind, f in find():
            print(f"{kind} {f}")
    elif a.cmd == "skip":
        open(DONT_ASK, "w").close()
        print("saved, won't ask again")


if __name__ == "__main__":
    sys.exit(main())
