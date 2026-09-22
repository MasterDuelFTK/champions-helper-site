# -*- coding: utf-8 -*-
"""
211차 — 주간 메타 리포트 생성기 (사람 개입 0 · Claude 개입 0)

무엇을 만드나:
  helper-data/move-usage(-double).json 은 폰 수확 파이프라인이 4시간마다 커밋한다.
  이 스크립트는 그 git 이력에서 "기준 시각" 스냅샷과 "7일 전" 스냅샷을 꺼내
  순위·기술·도구·특성·조합·상성 변화를 표로 뽑아 meta/<주차>/index.html 을 쓴다.
  별도 저장소가 필요 없다 — 사이트 repo 의 커밋 이력이 곧 시계열이다.

원칙(도감 템플릿 문단의 실수를 반복하지 않는다):
  · 숫자를 문장으로 위장하지 않는다. 표·스파크라인·짧은 캡션만.
  · 페이지 상단에 "공식 랭크 데이터 자동 집계"를 정직하게 표기한다.
  · 사람 코멘트는 meta/comments/<주차>.md 가 있을 때만 상단에 끼운다(없으면 생략).

껍데기(헤더 9링크·푸터·스타일)는 build-columns.py 와 같은 방식으로 guide/speed-guide 에서
런타임에 떼어 쓴다 — 124차 "전 페이지 헤더 byte 동일" 규칙 유지.

실행:  python build/build-meta-report.py                (기준 = 지금)
       python build/build-meta-report.py --at 2026-09-21T00:30+09:00
       python build/build-meta-report.py --days 7 --top 10
출력:  meta/<YYYY-wNN>/index.html · meta/index.html · meta/reports.json
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(os.path.join(HERE, ".."))
SHELL_SRC = os.path.join(SITE, "guide", "speed-guide", "index.html")
BASE = "https://champions-helper.com"
KST = dt.timezone(dt.timedelta(hours=9))

FILES = {
    "singles": "helper-data/move-usage.json",
    "doubles": "helper-data/move-usage-double.json",
}
FMT_KO = {"singles": "싱글", "doubles": "더블"}

esc = html.escape


# ─────────────────────────── git 시계열 ───────────────────────────

def git(*args, text=True):
    r = subprocess.run(["git", *args], cwd=SITE, capture_output=True,
                       text=text, encoding="utf-8" if text else None, errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def history(path):
    """[(commit, datetime KST)] 최신순."""
    out = []
    for line in git("log", "--format=%H %cI", "--", path).splitlines():
        h, iso = line.split(" ", 1)
        out.append((h, dt.datetime.fromisoformat(iso).astimezone(KST)))
    return out


def pick(hist, at):
    """at 이하 가장 최신 스냅샷 (없으면 None)."""
    for h, t in hist:
        if t <= at:
            return h, t
    return None


def load_at(commit, path):
    return json.loads(git("show", f"{commit}:{path}"))


# ─────────────────────────── 이름·sprite ───────────────────────────

def load_dex():
    p = os.path.join(SITE, "data", "dex.json")
    ko, sprite = {}, {}
    try:
        for e in json.load(io.open(p, encoding="utf-8"))["dex"]:
            key = e.get("en") or e.get("slug")
            if not key:
                continue
            if e.get("ko"):
                ko[key] = e["ko"]
            if e.get("sprite"):
                sprite[key] = e["sprite"]
    except Exception as ex:  # dex 없이도 돌아가게
        print(f"[warn] dex.json 읽기 실패: {ex}", file=sys.stderr)
    return ko, sprite


def ko_from_usage(P, ko):
    """usage 파일 안의 참조(teammates/winVs/loseVs)에 한글명이 있어 그것으로 보강."""
    for v in P.values():
        for fld in ("teammates", "winVs", "loseVs"):
            for r in v.get(fld) or []:
                if r.get("name") and r.get("ko"):
                    ko.setdefault(r["name"], r["ko"])
    return ko


# ─────────────────────────── 분석 ───────────────────────────

def ranked(P):
    return sorted([k for k in P if P[k].get("rank")], key=lambda k: P[k]["rank"])


def first(lst, key="en"):
    return (lst[0].get(key) if lst else None), (lst[0] if lst else None)


def analyze(cur, prev, top=10):
    P = cur["pokemon"]
    Q = prev["pokemon"] if prev else {}
    rank = {k: v["rank"] for k, v in P.items() if v.get("rank")}
    prank = {k: v["rank"] for k, v in Q.items() if v.get("rank")}
    order = ranked(P)
    A = {"rank": rank, "prank": prank, "order": order}

    def delta(k):
        return None if k not in prank else prank[k] - rank[k]

    A["top"] = [(k, rank[k], delta(k)) for k in order[:top]]

    movers = [(k, rank[k], delta(k)) for k in order[:100] if delta(k) is not None and delta(k) != 0]
    A["risers"] = sorted([m for m in movers if m[2] > 0], key=lambda m: (-m[2], m[1]))[:5]
    A["fallers"] = sorted([m for m in movers if m[2] < 0], key=lambda m: (m[2], m[1]))[:5]

    cur50 = set(order[:50])
    prev50 = {k for k in prank if prank[k] <= 50}
    A["new50"] = sorted([(k, rank[k], prank.get(k)) for k in cur50 - prev50], key=lambda x: x[1])
    A["out50"] = sorted([(k, rank.get(k), prank[k]) for k in prev50 - cur50], key=lambda x: x[2])

    shifts = []
    for k in order[:30]:
        if k not in Q:
            continue
        pm = {m["en"]: m["pct"] for m in Q[k].get("moves") or []}
        for m in (P[k].get("moves") or [])[:8]:
            if m["en"] in pm:
                d = round(m["pct"] - pm[m["en"]], 1)
                if abs(d) >= 5:
                    shifts.append((k, m["ko"], pm[m["en"]], m["pct"], d))
    A["shifts"] = sorted(shifts, key=lambda s: -abs(s[4]))[:12]

    lead = []
    for k in order[:50]:
        if k not in Q:
            continue
        for fld, label in (("items", "도구"), ("abils", "특성")):
            ce, c = first(P[k].get(fld) or [])
            pe, p = first(Q[k].get(fld) or [])
            if ce and pe and ce != pe:
                lead.append((k, label, p["ko"], p["pct"], c["ko"], c["pct"]))
    A["lead"] = lead[:12]

    top50 = set(order[:50])
    seen, pairs = set(), []
    for k in order[:30]:
        mates = [t["name"] for t in (P[k].get("teammates") or [])[:6]]
        for t in mates:
            if t in top50 and t != k:
                back = [x["name"] for x in (P[t].get("teammates") or [])[:6]]
                if k in back:
                    key = tuple(sorted((k, t)))
                    if key not in seen:
                        seen.add(key)
                        pairs.append((k, t, rank[k] + rank[t]))
    A["pairs"] = sorted(pairs, key=lambda p: p[2])[:10]

    counters = []
    for k in order[:top]:
        w = next((x["name"] for x in (P[k].get("winVs") or []) if x["name"] != k), None)
        l = next((x["name"] for x in (P[k].get("loseVs") or []) if x["name"] != k), None)
        counters.append((k, w, l))
    A["counters"] = counters
    return A


# ─────────────────────────── 렌더 ───────────────────────────

def _shell():
    s = io.open(SHELL_SRC, encoding="utf-8").read()
    style = s[s.find("<style>"): s.find("</style>") + len("</style>")]
    header = s[s.find("<body>"): s.find('<main class="wrap">')]
    footer = s[s.find("</main>"):]
    return style, header, footer


EXTRA_STYLE = """<style>
/* 껍데기(speed-guide) 변수만 쓴다: --bg --panel --panel2 --line --txt --muted --accent (다크 테마) */
.auto{border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:10px 14px;margin:14px 0;font-size:.92rem;color:var(--txt)}
.meta-sum{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.meta-sum div{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;color:var(--txt)}
.meta-sum b{display:block;font-size:1.05rem;margin-top:2px}
.meta-sum small{color:var(--muted)}
.tw{overflow-x:auto;margin:8px 0 18px;border:1px solid var(--line);border-radius:10px}
table.mt{border-collapse:collapse;width:100%;font-size:14px;min-width:0}
table.mt th,table.mt td{border-bottom:1px solid var(--line);padding:7px 10px;text-align:left;white-space:nowrap}
table.mt th{background:var(--panel2,var(--panel));font-weight:600;color:var(--txt)}
table.mt tr:last-child td{border-bottom:none}
table.mt td.n{text-align:left;font-variant-numeric:tabular-nums}
table.mt small{color:var(--muted)}
.up{color:#5bd38a;font-weight:600}.down{color:#ff7b7b;font-weight:600}.same{color:var(--muted)}.new{color:#8fc1ff;font-weight:700}
.sp img{width:26px;height:26px;vertical-align:middle;margin-right:6px}
.spark svg{vertical-align:middle;color:var(--accent)}
.fmt-tabs{display:flex;gap:8px;margin:18px 0 6px}
.fmt-tabs a{padding:6px 12px;border:1px solid var(--line);border-radius:999px;text-decoration:none;color:var(--txt);font-size:.9rem;background:var(--panel)}
.fmt-tabs a.cur{background:var(--accent);color:#fff;border-color:var(--accent)}
.comment{border-left:4px solid var(--accent);background:var(--panel);padding:10px 14px;margin:14px 0;border-radius:0 10px 10px 0}
.rep-list{list-style:none;padding:0;margin:14px 0}
.rep-list li{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0;background:var(--panel)}
.rep-list li a{font-weight:600;text-decoration:none}
.rep-list li small{display:block;color:var(--muted);margin-top:4px}
h2.fmt{margin-top:28px}
.js .fmt-sec:not(.on){display:none}
@media (max-width:640px){.meta-sum{grid-template-columns:repeat(2,1fr)}}
</style>
<script>document.documentElement.classList.add('js')</script>"""

PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1395643596867142" crossorigin="anonymous"></script>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<title>{title} | Champions Helper</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="{url}" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="Champions Helper" />
<meta property="og:locale" content="ko_KR" />
<meta property="og:url" content="{url}" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta name="twitter:card" content="summary" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{desc}" />
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "{desc}",
  "inLanguage": "ko",
  "datePublished": "{pub}",
  "dateModified": "{pub}",
  "url": "{url}",
  "author": {{ "@type": "Organization", "name": "Champions Helper" }},
  "publisher": {{ "@type": "Organization", "name": "Champions Helper" }},
  "isPartOf": {{ "@type": "WebSite", "name": "Champions Helper", "url": "https://champions-helper.com/" }}
}}
</script>
{style}
{extra}
  <link rel="stylesheet" href="/site-header.css" />
</head>
{header}<main class="wrap">
  <article class="article">
    <div class="crumb">{crumb}</div>
    <h1>{h1}</h1>
    <p class="lead">{lead}</p>
{body}
  </article>
{footer}"""


def dcell(d, prev=None):
    if d is None:
        return '<span class="new">NEW</span>' if prev is None else "－"
    if d > 0:
        return f'<span class="up">▲{d}</span>'
    if d < 0:
        return f'<span class="down">▼{-d}</span>'
    return '<span class="same">－</span>'


def spark(vals, w=120, h=26):
    """순위 시계열 → 인라인 SVG. 위가 좋은 순위."""
    pts = [v for v in vals if v]
    if len(pts) < 2:
        return ""
    lo, hi = min(pts), max(pts)
    span = max(hi - lo, 1)
    n = len(vals)
    xs = [round(i * (w - 4) / max(n - 1, 1) + 2, 1) for i in range(n)]
    coords = []
    for x, v in zip(xs, vals):
        if v:
            y = round(2 + (v - lo) * (h - 4) / span, 1)
            coords.append(f"{x},{y}")
    title = f"{vals[0]}위 → {vals[-1]}위 (최고 {lo}위 · 최저 {hi}위)"
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title><polyline fill="none" stroke="currentColor" stroke-width="1.6" '
            f'points="{" ".join(coords)}"/></svg>')


class R:  # 렌더 컨텍스트
    def __init__(self, ko, sprite):
        self.ko, self.sprite = ko, sprite

    def mon(self, k, link=True):
        name = esc(self.ko.get(k, k))
        img = f'<img src="/sprites/{esc(self.sprite[k])}" alt="" loading="lazy">' if k in self.sprite else ""
        inner = f"{img}{name}"
        if link and os.path.isdir(os.path.join(SITE, "pokedex", k)):
            return f'<a class="sp" href="/pokedex/{esc(k)}/">{inner}</a>'
        return f'<span class="sp">{inner}</span>'


def render_format(fmt, cur, prev, A, series_ranks, r):
    P = cur["pokemon"]
    out = []
    out.append(f'<h2 class="fmt" id="{fmt}">{FMT_KO[fmt]} 배틀</h2>')

    # 1. TOP N
    out.append("<h3>이번 주 TOP 10</h3><div class=\"tw\"><table class=\"mt\"><thead><tr>"
               "<th>순위</th><th>포켓몬</th><th>지난주 대비</th><th>이번 주 추이</th><th>1위 특성</th><th>1위 도구</th></tr></thead><tbody>")
    for k, rk, d in A["top"]:
        ab = (P[k].get("abils") or [{}])[0]
        it = (P[k].get("items") or [{}])[0]
        out.append(f"<tr><td class=\"n\">{rk}</td><td>{r.mon(k)}</td><td>{dcell(d)}</td>"
                   f"<td class=\"spark\">{spark(series_ranks.get(k, []))}</td>"
                   f"<td>{esc(ab.get('ko',''))} <small>{ab.get('pct','')}%</small></td>"
                   f"<td>{esc(it.get('ko',''))} <small>{it.get('pct','')}%</small></td></tr>")
    out.append("</tbody></table></div>")

    if prev is None:
        out.append('<p class="note">비교할 지난주 스냅샷이 없어 변동 항목은 생략합니다.</p>')
        return "\n".join(out)

    # 2. 급상승 / 급하락
    out.append("<h3>급상승 · 급하락 (상위 100 이내)</h3><div class=\"tw\"><table class=\"mt\"><thead><tr>"
               "<th>급상승</th><th>순위</th><th>변동</th><th></th><th>급하락</th><th>순위</th><th>변동</th></tr></thead><tbody>")
    for i in range(max(len(A["risers"]), len(A["fallers"]))):
        a = A["risers"][i] if i < len(A["risers"]) else None
        b = A["fallers"][i] if i < len(A["fallers"]) else None
        out.append("<tr>"
                   + (f"<td>{r.mon(a[0])}</td><td class=\"n\">{a[1]}</td><td>{dcell(a[2])}</td>" if a else "<td></td><td></td><td></td>")
                   + "<td></td>"
                   + (f"<td>{r.mon(b[0])}</td><td class=\"n\">{b[1]}</td><td>{dcell(b[2])}</td>" if b else "<td></td><td></td><td></td>")
                   + "</tr>")
    out.append("</tbody></table></div>")

    # 3. 상위 50 진입 / 이탈
    if A["new50"] or A["out50"]:
        out.append("<h3>상위 50 진입 · 이탈</h3><div class=\"tw\"><table class=\"mt\"><thead><tr>"
                   "<th>진입</th><th>지난주</th><th>이번주</th><th></th><th>이탈</th><th>지난주</th><th>이번주</th></tr></thead><tbody>")
        for i in range(max(len(A["new50"]), len(A["out50"]))):
            a = A["new50"][i] if i < len(A["new50"]) else None
            b = A["out50"][i] if i < len(A["out50"]) else None
            out.append("<tr>"
                       + (f"<td>{r.mon(a[0])}</td><td class=\"n\">{a[2] if a[2] else '－'}</td><td class=\"n\">{a[1]}</td>" if a else "<td></td><td></td><td></td>")
                       + "<td></td>"
                       + (f"<td>{r.mon(b[0])}</td><td class=\"n\">{b[2]}</td><td class=\"n\">{b[1] if b[1] else '순위 밖'}</td>" if b else "<td></td><td></td><td></td>")
                       + "</tr>")
        out.append("</tbody></table></div>")

    # 4. 기술 채용 변화
    if A["shifts"]:
        out.append("<h3>기술 채용률 변화 (상위 30종 · 5%p 이상)</h3><div class=\"tw\"><table class=\"mt\"><thead><tr>"
                   "<th>포켓몬</th><th>기술</th><th>지난주</th><th>이번주</th><th>변화</th></tr></thead><tbody>")
        for k, mv, p, c, d in A["shifts"]:
            cls = "up" if d > 0 else "down"
            out.append(f"<tr><td>{r.mon(k)}</td><td>{esc(mv)}</td><td class=\"n\">{p}%</td><td class=\"n\">{c}%</td>"
                       f"<td class=\"{cls}\">{'+' if d > 0 else ''}{d}%p</td></tr>")
        out.append("</tbody></table></div>")

    # 5. 1위 도구·특성 교체
    if A["lead"]:
        out.append("<h3>1위 도구·특성이 바뀐 포켓몬 (상위 50종)</h3><div class=\"tw\"><table class=\"mt\"><thead><tr>"
                   "<th>포켓몬</th><th>항목</th><th>지난주 1위</th><th>이번주 1위</th></tr></thead><tbody>")
        for k, label, pk, pp, ck, cp in A["lead"]:
            out.append(f"<tr><td>{r.mon(k)}</td><td>{label}</td><td>{esc(pk)} <small>{pp}%</small></td>"
                       f"<td>{esc(ck)} <small>{cp}%</small></td></tr>")
        out.append("</tbody></table></div>")

    # 6. 조합
    if A["pairs"]:
        out.append("<h3>자주 함께 쓰이는 조합 (상위 30종 기준 · 서로를 파트너로 꼽는 쌍)</h3><div class=\"tw\"><table class=\"mt\"><thead><tr>"
                   "<th>조합</th><th>순위 합</th></tr></thead><tbody>")
        for a, b, s in A["pairs"]:
            out.append(f"<tr><td>{r.mon(a)} + {r.mon(b)}</td><td class=\"n\">{s}</td></tr>")
        out.append("</tbody></table></div>")

    # 7. 카운터
    out.append("<h3>이번 주 상성 (TOP 10 기준 · 승패 기록 1위 상대)</h3><div class=\"tw\"><table class=\"mt\"><thead><tr>"
               "<th>포켓몬</th><th>가장 많이 이긴 상대</th><th>가장 많이 진 상대</th></tr></thead><tbody>")
    for k, w, l in A["counters"]:
        out.append(f"<tr><td>{r.mon(k)}</td><td>{r.mon(w) if w else '－'}</td><td>{r.mon(l) if l else '－'}</td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def fmt_dt(t):
    return t.strftime("%Y-%m-%d %H:%M")


def build_report(at, days, top):
    ko, sprite = load_dex()
    hist = history(FILES["singles"])
    base = pick(hist, at)
    if not base:
        raise SystemExit("기준 시각 이전 스냅샷이 없습니다")
    bh, bt = base
    prev = pick(hist, bt - dt.timedelta(days=days))
    series = [(h, t) for h, t in hist if (prev is None or t > prev[1]) and t <= bt]
    series.sort(key=lambda x: x[1])

    iso = bt.isocalendar()
    slug = f"{iso[0]}-w{iso[1]:02d}"
    url = f"{BASE}/meta/{slug}/"

    per = {}
    for fmt, path in FILES.items():
        cur = load_at(bh, path)
        pv = None
        if prev:
            try:
                pv = load_at(prev[0], path)
            except RuntimeError:
                pv = None
        ko = ko_from_usage(cur["pokemon"], ko)
        A = analyze(cur, pv, top)
        topkeys = [k for k, _, _ in A["top"]]
        sr = {k: [] for k in topkeys}
        for h, t in series:
            try:
                snap = load_at(h, path)["pokemon"]
            except RuntimeError:
                continue
            for k in topkeys:
                sr[k].append(snap.get(k, {}).get("rank"))
        per[fmt] = (cur, pv, A, sr)

    r = R(ko, sprite)
    s_cur = per["singles"][0]
    season = s_cur.get("season", "")
    n = s_cur.get("count", 0)
    title = f"주간 메타 리포트 {slug.upper()} — {season} 싱글·더블 순위 변동"
    period = f"{fmt_dt(prev[1]) if prev else '시즌 개막'} → {fmt_dt(bt)}"
    desc = (f"{season} 공식 랭크배틀 사용률 데이터 자동 집계. {period} KST 기준 싱글·더블 순위, "
            f"급상승·급하락, 기술·도구·특성 채용 변화, 조합과 상성.")

    body = []
    body.append('<div class="auto">이 페이지는 <strong>공식 랭크배틀 사용률 데이터를 매주 자동 집계</strong>해 생성합니다. '
                '사람이 쓴 해설이 아니라 데이터 표이며, 원본은 4시간마다 갱신되는 '
                '<a href="/battle-data/">배틀데이터</a>와 같은 파일입니다.</div>')
    s_top1 = per["singles"][2]["top"][0][0] if per["singles"][2]["top"] else None
    d_top1 = per["doubles"][2]["top"][0][0] if per["doubles"][2]["top"] else None
    s_r = per["singles"][2]["risers"][0] if per["singles"][2]["risers"] else None
    d_r = per["doubles"][2]["risers"][0] if per["doubles"][2]["risers"] else None
    body.append('<div class="meta-sum">'
                f'<div><small>시즌</small><b>{esc(season)}</b></div>'
                f'<div><small>집계 구간 (KST)</small><b style="font-size:.95rem">{esc(period)}</b></div>'
                f'<div><small>집계 대상</small><b>{n}종 · 스냅샷 {len(series)}개</b></div>'
                f'<div><small>싱글 1위</small><b>{r.mon(s_top1) if s_top1 else "－"}</b></div>'
                f'<div><small>더블 1위</small><b>{r.mon(d_top1) if d_top1 else "－"}</b></div>'
                f'<div><small>싱글 최다 상승</small><b>{(r.mon(s_r[0]) + " " + dcell(s_r[2])) if s_r else "－"}</b></div>'
                f'<div><small>더블 최다 상승</small><b>{(r.mon(d_r[0]) + " " + dcell(d_r[2])) if d_r else "－"}</b></div>'
                '</div>')

    cpath = os.path.join(SITE, "meta", "comments", f"{slug}.md")
    if os.path.exists(cpath):
        paras = [p.strip() for p in io.open(cpath, encoding="utf-8").read().split("\n\n") if p.strip()]
        body.append('<div class="comment"><strong>운영자 코멘트</strong>' +
                    "".join(f"<p>{esc(p)}</p>" for p in paras) + "</div>")

    # 탭: JS가 있으면 선택한 형식만 보이고, 없으면(크롤러) 둘 다 보인다.
    body.append('<div class="fmt-tabs" role="tablist">'
                '<a href="#singles" data-fmt="singles" class="cur" role="tab">싱글</a>'
                '<a href="#doubles" data-fmt="doubles" role="tab">더블</a></div>')
    for fmt in ("singles", "doubles"):
        cur, pv, A, sr = per[fmt]
        on = " on" if fmt == "singles" else ""
        body.append(f'<section class="fmt-sec{on}" id="{fmt}-sec" data-fmt="{fmt}">'
                    + render_format(fmt, cur, pv, A, sr, r) + "</section>")
    body.append("""<script>
(function(){
  var tabs=document.querySelectorAll('.fmt-tabs a'),secs=document.querySelectorAll('.fmt-sec');
  function show(f){
    tabs.forEach(function(t){t.classList.toggle('cur',t.dataset.fmt===f);});
    secs.forEach(function(s){s.classList.toggle('on',s.dataset.fmt===f);});
  }
  tabs.forEach(function(t){t.addEventListener('click',function(e){e.preventDefault();show(t.dataset.fmt);history.replaceState(null,'','#'+t.dataset.fmt);});});
  if(location.hash==='#doubles')show('doubles');
})();
</script>""")

    body.append('<p class="note">순위·채용률은 게임 내 공식 랭크배틀 집계를 그대로 옮긴 값입니다. '
                '기술·도구·특성의 상세 채용률과 노력치 분포는 각 포켓몬의 <a href="/pokedex/">도감</a> 페이지, '
                '전체 순위는 <a href="/battle-data/">배틀데이터</a>에서 볼 수 있습니다. '
                '지난 리포트는 <a href="/meta/">메타 리포트 목록</a>에 보관됩니다.</p>')

    style, header, footer = _shell()
    page = PAGE.format(title=esc(title), desc=esc(desc), url=url, pub=bt.strftime("%Y-%m-%d"),
                       style=style, extra=EXTRA_STYLE, header=header, footer=footer,
                       crumb=f'<a href="/meta/">메타 리포트</a> › {slug.upper()}',
                       h1=esc(title), lead=esc(f"{period} KST 사이 공식 랭크배틀 사용률 변화를 표로 정리했습니다. "
                                              f"지난주 대비 순위 이동, 기술·도구·특성 채용 변화, 함께 쓰이는 조합과 상성까지 자동 집계입니다."),
                       body="\n".join(body))
    d = os.path.join(SITE, "meta", slug)
    os.makedirs(d, exist_ok=True)
    io.open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)

    entry = {"slug": slug, "date": bt.strftime("%Y-%m-%d"), "season": season, "period": period,
             "singles_top1": ko.get(s_top1, s_top1), "doubles_top1": ko.get(d_top1, d_top1),
             "singles_riser": (ko.get(s_r[0], s_r[0]) + f" ▲{s_r[2]}") if s_r else None,
             "doubles_riser": (ko.get(d_r[0], d_r[0]) + f" ▲{d_r[2]}") if d_r else None,
             "snapshots": len(series)}
    return slug, entry, (style, header, footer)


def build_index(entry, shell):
    mp = os.path.join(SITE, "meta", "reports.json")
    reports = []
    if os.path.exists(mp):
        reports = json.load(io.open(mp, encoding="utf-8"))
    reports = [x for x in reports if x["slug"] != entry["slug"]] + [entry]
    reports.sort(key=lambda x: x["slug"], reverse=True)
    io.open(mp, "w", encoding="utf-8").write(json.dumps(reports, ensure_ascii=False, indent=1))

    style, header, footer = shell
    latest = reports[0]
    items = []
    for x in reports:
        items.append(f'<li><a href="/meta/{esc(x["slug"])}/">주간 메타 리포트 {esc(x["slug"].upper())}</a>'
                     f'<small>{esc(x["season"])} · {esc(x["period"])} KST · 싱글 1위 {esc(x.get("singles_top1") or "－")} · '
                     f'더블 1위 {esc(x.get("doubles_top1") or "－")}'
                     + (f' · 싱글 최다 상승 {esc(x["singles_riser"])}' if x.get("singles_riser") else "")
                     + '</small></li>')
    body = ('<div class="auto">공식 랭크배틀 사용률 데이터를 <strong>매주 자동 집계</strong>한 리포트 모음입니다. '
            '순위 변동·기술·도구·특성 채용 변화·조합·상성을 표로 정리하며, 지난 주차는 그대로 보관됩니다.</div>'
            f'<p>최신: <a href="/meta/{esc(latest["slug"])}/">주간 메타 리포트 {esc(latest["slug"].upper())}</a> '
            f'({esc(latest["period"])} KST)</p>'
            '<ul class="rep-list">' + "".join(items) + '</ul>')
    title = "주간 메타 리포트 — 포켓몬 챔피언스 랭크배틀 순위·채용 변화 기록"
    desc = "공식 랭크배틀 사용률 데이터를 매주 자동 집계한 메타 리포트 모음. 싱글·더블 순위 변동, 기술·도구·특성 채용 변화, 조합과 상성."
    page = PAGE.format(title=esc(title), desc=esc(desc), url=f"{BASE}/meta/", pub=latest["date"],
                       style=style, extra=EXTRA_STYLE, header=header, footer=footer,
                       crumb='<a href="/guide/">가이드</a> › 메타 리포트', h1="주간 메타 리포트",
                       lead=esc("매주 월요일, 지난 7일의 공식 랭크배틀 데이터를 자동으로 비교해 순위와 채용 변화를 기록합니다."),
                       body=body)
    io.open(os.path.join(SITE, "meta", "index.html"), "w", encoding="utf-8").write(page)
    return len(reports)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", help="기준 시각 ISO (기본 지금, 예: 2026-09-21T00:30+09:00)")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--if-missing", action="store_true",
                    help="이번 ISO 주차 리포트가 이미 있으면 아무것도 하지 않는다 (CI 4시간 실행용)")
    a = ap.parse_args()
    at = dt.datetime.fromisoformat(a.at).astimezone(KST) if a.at else dt.datetime.now(KST)
    if a.if_missing:
        iso = at.isocalendar()
        slug0 = f"{iso[0]}-w{iso[1]:02d}"
        if os.path.exists(os.path.join(SITE, "meta", slug0, "index.html")):
            print(f"skip — meta/{slug0}/ 이미 있음")
            return
    slug, entry, shell = build_report(at, a.days, a.top)
    n = build_index(entry, shell)
    print(f"OK — meta/{slug}/index.html 생성 · 리포트 목록 {n}건 · 구간 {entry['period']} · 스냅샷 {entry['snapshots']}개")


if __name__ == "__main__":
    main()
