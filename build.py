#!/usr/bin/env python3
"""eichiii.co.jp 静的サイトのビルド。

  site/            そのまま公開する静的ファイル（トップ・採用・会場ページ・画像など）
  content/news/    お知らせ記事（1記事 = 1つの Markdown）
  templates/       記事ページ・お知らせ一覧のテンプレート

python3 build.py で dist/ に書き出す。
BASE_PATH=/eichiii-site のように指定すると、サブパス公開（GitHub Pages のプレビュー）用に
サイト内リンクの先頭へ BASE_PATH を付ける。本番（独自ドメイン）では指定しない。
"""
import html
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
CONTENT = ROOT / "content" / "news"
TEMPLATES = ROOT / "templates"
DIST = ROOT / "dist"

SITE_URL = "https://eichiii.co.jp"
SITE_NAME = "株式会社エイチ"
DEFAULT_DESCRIPTION = "全国のホテル・会議室・イベント会場・レンタカー・出張手配をワンストップで提供する法人向けサービス「Eichiii」。予約から清算まで一括対応し、経費精算やインボイス対応の手間を削減します。"
DEFAULT_OG_IMAGE = "/wp-content/uploads/2026/07/symbol-7.png"
PICKUP_COUNT = 3
PER_PAGE = 9
JST = timezone(timedelta(hours=9))
BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")


# ---------- 記事の読み込み ----------

class Post:
    def __init__(self, path: Path):
        text = path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
        if not m:
            sys.exit(f"{path.name}: 先頭に --- で囲んだ設定（タイトル・日付など）がありません")
        meta = yaml.safe_load(m.group(1)) or {}
        for key in ("title", "date", "slug"):
            if not meta.get(key):
                sys.exit(f"{path.name}: {key} がありません")
        self.file = path.name
        self.title = str(meta["title"])
        d = meta["date"]
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        elif not isinstance(d, datetime):  # 日付だけ（2026-12-01）の場合
            d = datetime(d.year, d.month, d.day, 9, 0)
        if d.tzinfo is None:
            d = d.replace(tzinfo=JST)
        self.date = d.astimezone(JST)
        self.slug = str(meta["slug"])
        self.image = meta.get("image")
        self.image_alt = meta.get("image_alt") or self.title
        self.external_url = meta.get("external_url") or ""
        self.description = meta.get("description") or ""
        self.draft = bool(meta.get("draft", False))
        body = m.group(2).strip()
        # 本文は HTML でも Markdown でもよい（HTML はそのまま通る）
        self.body_html = markdown.markdown(body, extensions=["tables", "extra"]) if body else ""

    @property
    def path(self):
        d = self.date
        return f"/{d:%Y}/{d:%m}/{d:%d}/{self.slug}/"

    @property
    def link(self):
        return self.external_url or self.path

    @property
    def date_label(self):
        return f"{self.date:%Y.%m.%d}"


def load_posts():
    posts = [Post(p) for p in sorted(CONTENT.glob("*.md"))]
    seen = {}
    for p in posts:
        if p.path in seen:
            sys.exit(f"URLが重複しています: {p.path}（{seen[p.path]} と {p.file}）")
        seen[p.path] = p.file
    posts = [p for p in posts if not p.draft]
    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


# ---------- 画像 ----------

def image_attrs(src):
    """width/height と、WordPress が作った縮小版があれば srcset を返す。"""
    file = SITE / src.lstrip("/")
    attrs = {}
    try:
        from PIL import Image
        with Image.open(file) as im:
            attrs["width"], attrs["height"] = im.size
    except Exception:
        pass
    stem, ext = os.path.splitext(file.name)
    variants = []
    if file.parent.exists():
        for f in file.parent.iterdir():
            m = re.fullmatch(re.escape(stem) + r"-(\d+)x(\d+)" + re.escape(ext), f.name)
            if m:
                variants.append((int(m.group(1)), f.name))
    if variants and "width" in attrs:
        base = src.rsplit("/", 1)[0]
        items = [f"{src} {attrs['width']}w"] + [f"{base}/{n} {w}w" for w, n in sorted(variants, reverse=True)]
        attrs["srcset"] = ", ".join(items)
        attrs["sizes"] = f"auto, (max-width: {attrs['width']}px) 100vw, {attrs['width']}px"
    return attrs


def img_tag(src, alt, cls, extra=""):
    a = image_attrs(src)
    parts = []
    if "width" in a:
        parts.append(f'width="{a["width"]}" height="{a["height"]}"')
    parts.append(f'src="{html.escape(src)}" class="{cls}" alt="{html.escape(alt)}"{extra}')
    if "srcset" in a:
        parts.append(f'srcset="{html.escape(a["srcset"])}" sizes="{a["sizes"]}"')
    return "<img " + " ".join(parts) + " />"


# ---------- 部品 ----------

CARD_IMG_CLASS = "u-border-radius-top-10 u-clip-star u-thumb-size u-object-fit-cover u-sp-border-radius-10 wp-post-image"


def card_pickup(p):
    img = img_tag(p.image, p.image_alt, CARD_IMG_CLASS, ' loading="lazy" decoding="async"') if p.image else ""
    return f"""
        <article class="p-article u-shadow-2 u-border-radius-10 u-sp-mb-40 u-border-radius-30 u-overflow-hidden">
          <figure class="u-border-radius-top-10 u-shadow-bottom u-all-zero u-sp-p-10 u-bg-lightgray">
            <a href="{html.escape(p.link)}" target="_blank" rel="noopener">
              {img}
            </a>
          </figure>
          <dl>
            <dt class="u-pt-15 u-pl-20 u-pb-5 u-color-red u-font-weight-600 u-font-size-13 u-sp-font-size-26">
              {p.date_label}
            </dt>
            <dd class="u-pb-20 u-pl-20 u-pr-20 u-font-weight-bold u-font-size-18 u-sp-font-size-34 u-sp-line-height-48 u-sp-pb-40">
              {html.escape(p.title)}
            </dd>
          </dl>
        </article>"""


def card_news(p):
    target = ' target="_blank" rel="noopener"' if p.external_url else ""
    img = img_tag(p.image, p.image_alt, CARD_IMG_CLASS, ' loading="lazy" decoding="async"') if p.image else ""
    return f"""
      <article class="p-article u-shadow-2 u-border-radius-10 u-border-radius-30 u-overflow-hidden u-bg-white">
        <figure class="u-border-radius-top-10 u-shadow-bottom u-all-zero u-sp-p-10 u-bg-lightgray">
          <a href="{html.escape(p.link)}"{target}>
            {img}
          </a>
        </figure>
        <dl>
          <dt class="u-pt-15 u-pl-20 u-pb-5 u-color-red u-font-weight-600 u-font-size-13 u-sp-font-size-26">
            {p.date_label}
          </dt>
          <dd class="u-pb-20 u-pl-20 u-pr-20 u-font-weight-bold u-font-size-18 u-sp-font-size-34 u-sp-line-height-48 u-sp-pb-40">
            <a href="{html.escape(p.link)}"{target}>{html.escape(p.title)}</a>
          </dd>
        </dl>
      </article>"""


def seo_block(title, description, url, image, og_type="website", published=None, extra_ld=None):
    abs_img = SITE_URL + image if image.startswith("/") else image
    lines = [
        f'<meta name="description" content="{html.escape(description)}" />',
        '<meta name="robots" content="max-image-preview:large" />',
        f'<link rel="canonical" href="{url}" />',
        '<meta property="og:locale" content="ja_JP" />',
        f'<meta property="og:site_name" content="{SITE_NAME}" />',
        f'<meta property="og:type" content="{og_type}" />',
        f'<meta property="og:title" content="{html.escape(title)}" />',
        f'<meta property="og:description" content="{html.escape(description)}" />',
        f'<meta property="og:url" content="{url}" />',
        f'<meta property="og:image" content="{abs_img}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{html.escape(title)}" />',
        f'<meta name="twitter:description" content="{html.escape(description)}" />',
        f'<meta name="twitter:image" content="{abs_img}" />',
    ]
    if published:
        lines.append(f'<meta property="article:published_time" content="{published}" />')
    if extra_ld:
        lines.append('<script type="application/ld+json">' + json.dumps(extra_ld, ensure_ascii=False) + "</script>")
    return "\n\t\t".join(lines)


def plain_text(h, limit=120):
    t = re.sub(r"<[^>]+>", " ", h)
    t = re.sub(r"\s+", " ", html.unescape(t)).strip()
    return t[:limit] + ("…" if len(t) > limit else "")


# ---------- ページ生成 ----------

def write(path, text):
    out = DIST / path.lstrip("/")
    if path.endswith("/"):
        out = out / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def render(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[a-z_]+\}\}", tpl)
    if left:
        sys.exit(f"テンプレートの置き換え漏れ: {left}")
    return tpl


def build_posts(posts):
    tpl = (TEMPLATES / "post.html").read_text(encoding="utf-8")
    for p in posts:
        thumb = ""
        if p.image:
            thumb = '<figure class="c-single__thumb">\n        ' + img_tag(
                p.image, p.image_alt, "attachment-full size-full wp-post-image", ' decoding="async" fetchpriority="high"'
            ) + "\n      </figure>"
        ext = ""
        if p.external_url:
            ext = f'<p><a href="{html.escape(p.external_url)}" target="_blank" rel="noopener">詳細はこちら</a></p>'
        article = f"""<article class="c-single">
      {thumb}
      <p class="c-single__date">{p.date_label}</p>
      <h1 class="c-single__title">{html.escape(p.title)}</h1>
      <div class="c-single__body">
{p.body_html}{ext}
      </div>
      <div class="c-single__actions">
        <a href="/news/" class="c-single__back">一覧に戻る</a>
      </div>
    </article>"""
        url = SITE_URL + p.path
        desc = p.description or (plain_text(p.body_html) if p.body_html else DEFAULT_DESCRIPTION)
        ld = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": p.title,
            "datePublished": p.date.isoformat(),
            "url": url,
            "image": SITE_URL + p.image if p.image else None,
            "publisher": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/"},
        }
        seo = seo_block(f"{p.title} | {SITE_NAME}", desc, url, p.image or DEFAULT_OG_IMAGE,
                        og_type="article", published=p.date.isoformat(), extra_ld=ld)
        write(p.path, render(tpl, page_title=html.escape(f"{p.title} | {SITE_NAME}"), seo=seo, article=article))


def build_news_list(posts):
    tpl = (TEMPLATES / "news.html").read_text(encoding="utf-8")
    pages = [posts[i:i + PER_PAGE] for i in range(0, len(posts), PER_PAGE)] or [[]]
    total = len(pages)

    def page_url(n):
        return "/news/" if n == 1 else f"/news/page/{n}/"

    for n, items in enumerate(pages, 1):
        nav = []
        if n > 1:
            nav.append(f'<a class="prev page-numbers" href="{page_url(n - 1)}">←</a>')
        for k in range(1, total + 1):
            if k == n:
                nav.append(f'<span aria-current="page" class="page-numbers current">{k}</span>')
            else:
                nav.append(f'<a class="page-numbers" href="{page_url(k)}">{k}</a>')
        if n < total:
            nav.append(f'<a class="next page-numbers" href="{page_url(n + 1)}">→</a>')
        pagination = f'<nav class="c-pagination" aria-label="ページ送り">{"".join(nav)}</nav>' if total > 1 else ""
        listing = '<div class="c-news-grid">' + "".join(card_news(p) for p in items) + "\n    </div>\n    " + pagination
        title = "News・お知らせ一覧 | " + SITE_NAME + ("" if n == 1 else f" | {n}ページ目")
        seo = seo_block(title, "株式会社エイチのお知らせ・開催報告の一覧です。", SITE_URL + page_url(n), DEFAULT_OG_IMAGE)
        write(page_url(n), render(tpl, page_title=html.escape(title), seo=seo, list=listing))


def build_top(posts):
    src = DIST / "index.html"
    s = src.read_text(encoding="utf-8")
    if "<!-- PICKUP -->" not in s:
        sys.exit("site/index.html に <!-- PICKUP --> の目印がありません")
    cards = "".join(card_pickup(p) for p in posts[:PICKUP_COUNT])
    src.write_text(s.replace("<!-- PICKUP -->", cards), encoding="utf-8")


def build_sitemap():
    urls = []
    for f in sorted(DIST.rglob("index.html")):
        rel = "/" + str(f.parent.relative_to(DIST)).replace("\\", "/")
        rel = "/" if rel == "/." else rel + "/"
        if rel.startswith(("/wp-", "/thanks/")):
            continue
        urls.append(SITE_URL + rel)
    body = "\n".join(f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls)
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body + "\n</urlset>\n", encoding="utf-8")
    robots = DIST / "robots.txt"
    if robots.exists():
        r = robots.read_text(encoding="utf-8")
        r = re.sub(r"(?m)^Sitemap: .*sitemap\.rss\s*$\n?", "", r)
        robots.write_text(r, encoding="utf-8")


def apply_base_path():
    """サブパス公開用に、サイト内の絶対パスへ BASE_PATH を付ける。"""
    if not BASE_PATH:
        return
    attr_re = re.compile(r'((?:href|src|action|poster|data-src|data-bg)=")(/(?!/)[^"]*)"')
    srcset_re = re.compile(r'((?:srcset|data-srcset)=")([^"]*)"')
    url_re = re.compile(r'url\((["\']?)(/(?!/)[^)"\']*)\1\)')
    site_re = re.compile(re.escape(SITE_URL) + r'(?=[/"\'])')

    def fix_srcset(m):
        items = []
        for part in m.group(2).split(","):
            part = part.strip()
            if part.startswith("/") and not part.startswith("//"):
                part = BASE_PATH + part
            items.append(part)
        return m.group(1) + ", ".join(items) + '"'

    for f in DIST.rglob("*"):
        if f.suffix not in (".html", ".css"):
            continue
        s = f.read_text(encoding="utf-8", errors="ignore")
        if f.suffix == ".html":
            s = site_re.sub("", s.replace(f'"{SITE_URL}"', '"/"'))
            s = attr_re.sub(lambda m: m.group(1) + BASE_PATH + m.group(2) + '"', s)
            s = srcset_re.sub(fix_srcset, s)
        s = url_re.sub(lambda m: f"url({m.group(1)}{BASE_PATH}{m.group(2)}{m.group(1)})", s)
        f.write_text(s, encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SITE, DIST)
    posts = load_posts()
    build_posts(posts)
    build_news_list(posts)
    build_top(posts)
    build_sitemap()
    apply_base_path()
    (DIST / ".nojekyll").write_text("")
    print(f"記事 {len(posts)} 本 / PICK UP: " + " / ".join(p.title[:20] for p in posts[:PICKUP_COUNT]))


if __name__ == "__main__":
    main()
