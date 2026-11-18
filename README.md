# eichiii.co.jp（静的サイト版）

WordPress + Shifter で運用していたコーポレートサイトを、静的ファイルとビルドスクリプトだけで動く形に移したものです。
`main` に push すると GitHub Actions がビルドし、公開まで行います。

## フォルダ構成

| 場所 | 中身 |
|---|---|
| `content/news/` | お知らせ記事。**1記事 = 1つの Markdown ファイル** |
| `site/` | そのまま公開するページと画像（トップ、Recruit、Interview、会場ページ、Contact など） |
| `templates/` | 記事ページ・お知らせ一覧のテンプレート |
| `build.py` | `dist/` に公開用ファイルを書き出す |
| `check_links.py` | サイト内のリンク切れ・画像切れを確かめる（ビルドのたびに自動で実行） |

ビルドで自動的に作られるもの:

- 記事ページ（`/YYYY/MM/DD/スラッグ/`。WordPress 時代と同じ URL）
- お知らせ一覧 `/news/`（9件ごとにページ分け）
- トップページの PICK UP 2か所（日付が新しい順に3件）
- `sitemap.xml`

## お知らせを追加する

1. 画像を `site/wp-content/uploads/YYYY/MM/` に置く（例: `site/wp-content/uploads/2026/12/eyecatch-xxx.jpg`）
2. `content/news/YYYY-MM-DD-スラッグ.md` を作る

```markdown
---
title: "1Approval×〇〇 共催ウェビナー「タイトル」｜2027.1.20 開催"
date: "2026-12-01T10:00:00+09:00"
slug: "webinar-20270120-xxx"
image: "/wp-content/uploads/2026/12/eyecatch-xxx.jpg"
image_alt: "画像の代替テキスト"
description: "検索結果やSNSで表示される説明文（省略すると本文の冒頭が使われる）"
# external_url: "https://..."   ← 一覧・PICK UP から外部サイトへ直接飛ばしたいときだけ
# draft: true                   ← まだ公開しない場合
---

本文。HTML（WordPress から書き出したブロックの HTML など）でも Markdown でも書けます。
```

3. push する（または Pull Request を作ってマージする）

`date` の新しい順に PICK UP と一覧へ並びます。同じ日に複数出すときは、時刻で並び順を決めてください。

## 手元で確認する

```bash
pip install -r requirements.txt
python build.py && python check_links.py
cd dist && python -m http.server 8000   # → http://localhost:8000/
```

## 公開先

- **GitHub Pages:** リポジトリの Settings → Pages → Source を「GitHub Actions」にする。独自ドメインを使うときは、Settings → Secrets and variables → Actions → Variables に `CUSTOM_DOMAIN`（例: `eichiii.co.jp`）を設定する。未設定の間は `https://<owner>.github.io/<repo>/` で公開される（その場合はビルドでサイト内リンクの先頭にリポジトリ名を付けている）。
- **Cloudflare Pages:** ビルドコマンド `pip install -r requirements.txt && python build.py`、出力ディレクトリ `dist`。

## WordPress から移したときのメモ

- Shifter が最後に書き出した静的サイト（2026-11-18 の「ウェビナー反映」デプロイ）から、実際に参照されているファイルだけを残しています（500MB → 約24MB）。
- お問い合わせフォームは、移行前から Formspree で送信しているため、そのまま動きます。
- 日付別・カテゴリ別・投稿者別のアーカイブページは、どこからもリンクされていないので作っていません。
- WordPress 時代は記事ページの `<title>` と OGP がサイト共通の文言・画像になっていましたが、記事ごとのタイトルとアイキャッチに変えています。
- `known_missing.txt` は、移行前から存在しなかった参照（テーマCSSの古い背景画像など）の一覧です。表示には影響していません。
