#!/usr/bin/env python3
"""Pull the user's own public writing into ~/.writer/samples/<channel>/ so it outranks chat habits.

  python3 socials.py add medium @you            # blog channel
  python3 socials.py add substack you           # you.substack.com, blog channel
  python3 socials.py add rss https://you.dev/feed.xml
  python3 socials.py add devto you
  python3 socials.py add bluesky you.bsky.social   # tweet channel
  python3 socials.py add x ~/Downloads/twitter-archive.zip   # tweet + reply channels
  python3 socials.py add linkedin ~/Downloads/Basic_LinkedInDataExport.zip
  python3 socials.py list | remove <n> | sync

Add only accounts that belong to the user. `--channel NAME` on `add` overrides the default channel.
"""
import argparse, csv, hashlib, html, io, json, os, re, sys, urllib.request, zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

from extract import SAMPLES, scrub

CONFIG = os.path.expanduser("~/.writer/socials.json")
MAX_PER_SOURCE = 500
UA = {"User-Agent": "writer-skill (+https://github.com/shibu0x/writer-skill)"}
DEFAULT_CHANNEL = {"medium": "blog", "substack": "blog", "rss": "blog", "devto": "blog",
                   "bluesky": "tweet", "x": "tweet", "linkedin": "linkedin"}


class _Text(HTMLParser):
    BLOCK = {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "blockquote", "pre", "tr"}
    SKIP = {"script", "style", "figure", "figcaption"}

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
        if tag in self.BLOCK:
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
    raise ValueError(f"unknown type {kind}")


def sync(entries, base=SAMPLES, reader=read):
    """Write new pieces to <base>/<channel>/<type>-<hash>.txt. Existing files are left alone, so re-runs only add."""
    for entry in entries:
        new = 0
        try:
            pieces = list(reader(entry))[:MAX_PER_SOURCE]
        except Exception as e:  # one dead feed shouldn't stop the rest
            print(f"{entry['type']} {entry['value']}: failed ({e})")
            continue
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
        out = f"{d}/samples"
        fake = lambda e: iter([("1", "hello world", None), ("2", "my key sk-proj-AbCdEf1234567890XyZ", None), ("3", "@bob hi", "reply")])
        sync([{"type": "x", "value": "archive"}], out, fake)
        sync([{"type": "x", "value": "archive"}], out, fake)  # re-run adds nothing
        assert sorted(os.listdir(out)) == ["reply", "tweet"] and len(os.listdir(f"{out}/tweet")) == 2
        assert "sk-proj" not in "".join(open(f"{out}/tweet/{f}").read() for f in os.listdir(f"{out}/tweet"))
    print("socials ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("type", choices=sorted(DEFAULT_CHANNEL))
    add.add_argument("value", help="username, handle, feed URL, or export file path")
    add.add_argument("--channel", help="samples folder to write into (default depends on type)")
    rm = sub.add_parser("remove")
    rm.add_argument("n", type=int, help="number from `list`")
    sub.add_parser("list")
    sub.add_parser("sync")
    sub.add_parser("test")
    a = ap.parse_args()

    entries = load()
    if a.cmd == "test":
        return demo()
    if a.cmd == "add":
        entry = {"type": a.type, "value": a.value}
        if a.channel:
            entry["channel"] = a.channel
        entries.append(entry)
        save(entries)
        sync([entry])
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


if __name__ == "__main__":
    sys.exit(main())
