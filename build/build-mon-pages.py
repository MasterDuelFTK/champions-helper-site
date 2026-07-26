# 포켓몬 상세페이지 정적 생성 (SSG) — AdSense 고유 텍스트 콘텐츠 확보
#
# data/dex.json → pokedex/{en}/index.html  (종족값 + 타입상성표 자동계산 + 특성설명 + 메가 + 운용코멘트)
#   + pokedex/index.html 에 정적 "전체 목록" 링크 주입 (마커 <!--ALLLIST-->…<!--/ALLLIST-->)
#   + sitemap.xml 전체 재생성 (정적 라우트 + 209 상세페이지)
#
# 실행:  python build/build-mon-pages.py
# dex.json 갱신(build-all.py) 후 이 스크립트를 돌리면 상세페이지가 자동 재생성된다.
import datetime, json, os, re, html

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # build/ 의 상위 = repo 루트(CI 우분투 호환, 123차)
LASTMOD = datetime.date.today().isoformat()  # cron 자동 재생성(123차)에 맞춰 실행일 스탬프
BASE = "https://champions-helper.com"

with open(os.path.join(SITE, "data", "dex.json"), encoding="utf-8") as f:
    DEX = json.load(f)["dex"]

def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

# 실전 사용률(선택) — helper-data/move-usage.json 이 있으면 상세페이지 + 배틀데이터 페이지에 반영.
#   championsbattledata.com API 유래(154차 소스 재교체 — pokedb 가 사용자 IP 차단, 출처표기 필수).
#   key = 정규화된 master nameEn.
USAGE, USAGE_SEASON, USAGE_SOURCE = {}, "", ""
try:
    with open(os.path.join(SITE, "helper-data", "move-usage.json"), encoding="utf-8") as f:
        _u = json.load(f)
    USAGE_SEASON = _u.get("season", "")
    USAGE_SOURCE = _u.get("source", "")     # 169차 — "official-ranking" 이면 공식 데이터
    USAGE = {_norm(k): v for k, v in _u.get("pokemon", {}).items()}
except FileNotFoundError:
    print("  (move-usage.json 없음 — 사용률 섹션 생략)")

# 131차(더블배틀) — 더블 사용률(move-usage-double.json, PCH_MOVE_RULE=1). 있으면 도감 상세 "더블" 섹션 +
#   /battle-data/doubles/ 페이지 생성. 싱글과 완전 별개 메타(기술/포켓몬 사용률 다름). 없으면 조용히 생략(싱글만).
USAGE_D, USAGE_D_SEASON = {}, ""
try:
    with open(os.path.join(SITE, "helper-data", "move-usage-double.json"), encoding="utf-8") as f:
        _ud = json.load(f)
    USAGE_D_SEASON = _ud.get("season", "")
    USAGE_D = {_norm(k): v for k, v in _ud.get("pokemon", {}).items()}
except FileNotFoundError:
    print("  (move-usage-double.json 없음 — 더블 섹션 생략)")

# 169차 — 출처 표기는 데이터의 source 필드로 자동 전환. 소스를 되돌려도 표기가 어긋나지 않는다.
#   official-ranking = 게임 공식 랭크 배틀 순위 데이터 / 그 외 = 기존 championsbattledata 경유분.
ATTRIB = ('데이터 출처: 포켓몬 챔피언스 공식 랭크 배틀 순위 데이터'
          if USAGE_SOURCE == "official-ranking" else
          'Battle data provided by <a href="https://championsbattledata.com/" '
          'target="_blank" rel="noopener">Pok&eacute;mon Champions Battle Data</a>')

# 순위 = move-usage.json 의 rank(소스 column_position, 1~235 완전) 그대로 사용.
#   (구 DENSE 재부여는 폼 미수록으로 구멍이 있던 시절의 임시조치 — 폼 도감 수록으로 폐기.)

# ── 한글/색상 ──────────────────────────────────────────────────────────
TYPE_KO = {"NORMAL":"노말","FIRE":"불꽃","WATER":"물","ELECTRIC":"전기","GRASS":"풀","ICE":"얼음",
  "FIGHTING":"격투","POISON":"독","GROUND":"땅","FLYING":"비행","PSYCHIC":"에스퍼","BUG":"벌레","ROCK":"바위",
  "GHOST":"고스트","DRAGON":"드래곤","DARK":"악","STEEL":"강철","FAIRY":"페어리"}
TYPE_COLOR = {"NORMAL":"#A8A77A","FIRE":"#EE8130","WATER":"#6390F0","ELECTRIC":"#F7D02C","GRASS":"#7AC74C",
  "ICE":"#96D9D6","FIGHTING":"#C22E28","POISON":"#A33EA1","GROUND":"#E2BF65","FLYING":"#A98FF3","PSYCHIC":"#F95587",
  "BUG":"#A6B91A","ROCK":"#B6A136","GHOST":"#735797","DRAGON":"#6F35FC","DARK":"#705746","STEEL":"#B7B7CE","FAIRY":"#D685AD"}
TYPE_ORDER = ["NORMAL","FIRE","WATER","ELECTRIC","GRASS","ICE","FIGHTING","POISON","GROUND","FLYING",
  "PSYCHIC","BUG","ROCK","GHOST","DRAGON","DARK","STEEL","FAIRY"]
STATS = [("hp","HP","#FF5959"),("atk","공격","#F5AC78"),("def","방어","#FAE078"),
  ("spa","특공","#9DB7F5"),("spd","특방","#A7DB8D"),("spe","스피드","#FA92B2")]
STAT_KO = {"hp":"HP","atk":"공격","def":"방어","spa":"특공","spd":"특방","spe":"스피드"}

# ── 타입 상성표 (공격 → 방어 배율. 1배는 생략) ─────────────────────────
CHART = {
  "NORMAL":  {"ROCK":.5,"STEEL":.5,"GHOST":0},
  "FIRE":    {"GRASS":2,"ICE":2,"BUG":2,"STEEL":2,"FIRE":.5,"WATER":.5,"ROCK":.5,"DRAGON":.5},
  "WATER":   {"FIRE":2,"GROUND":2,"ROCK":2,"WATER":.5,"GRASS":.5,"DRAGON":.5},
  "ELECTRIC":{"WATER":2,"FLYING":2,"ELECTRIC":.5,"GRASS":.5,"DRAGON":.5,"GROUND":0},
  "GRASS":   {"WATER":2,"GROUND":2,"ROCK":2,"FIRE":.5,"GRASS":.5,"POISON":.5,"FLYING":.5,"BUG":.5,"DRAGON":.5,"STEEL":.5},
  "ICE":     {"GRASS":2,"GROUND":2,"FLYING":2,"DRAGON":2,"FIRE":.5,"WATER":.5,"ICE":.5,"STEEL":.5},
  "FIGHTING":{"NORMAL":2,"ICE":2,"ROCK":2,"DARK":2,"STEEL":2,"POISON":.5,"FLYING":.5,"PSYCHIC":.5,"BUG":.5,"FAIRY":.5,"GHOST":0},
  "POISON":  {"GRASS":2,"FAIRY":2,"POISON":.5,"GROUND":.5,"ROCK":.5,"GHOST":.5,"STEEL":0},
  "GROUND":  {"FIRE":2,"ELECTRIC":2,"POISON":2,"ROCK":2,"STEEL":2,"GRASS":.5,"BUG":.5,"FLYING":0},
  "FLYING":  {"GRASS":2,"FIGHTING":2,"BUG":2,"ELECTRIC":.5,"ROCK":.5,"STEEL":.5},
  "PSYCHIC": {"FIGHTING":2,"POISON":2,"PSYCHIC":.5,"STEEL":.5,"DARK":0},
  "BUG":     {"GRASS":2,"PSYCHIC":2,"DARK":2,"FIRE":.5,"FIGHTING":.5,"POISON":.5,"FLYING":.5,"GHOST":.5,"STEEL":.5,"FAIRY":.5},
  "ROCK":    {"FIRE":2,"ICE":2,"FLYING":2,"BUG":2,"FIGHTING":.5,"GROUND":.5,"STEEL":.5},
  "GHOST":   {"PSYCHIC":2,"GHOST":2,"DARK":.5,"NORMAL":0},
  "DRAGON":  {"DRAGON":2,"STEEL":.5,"FAIRY":0},
  "DARK":    {"PSYCHIC":2,"GHOST":2,"FIGHTING":.5,"DARK":.5,"FAIRY":.5},
  "STEEL":   {"ICE":2,"ROCK":2,"FAIRY":2,"FIRE":.5,"WATER":.5,"ELECTRIC":.5,"STEEL":.5},
  "FAIRY":   {"FIGHTING":2,"DRAGON":2,"DARK":2,"FIRE":.5,"POISON":.5,"STEEL":.5},
}

def defense_profile(types):
    """방어 타입 조합 → {공격타입: 최종배율}."""
    out = {}
    for atk in TYPE_ORDER:
        m = 1.0
        for d in types:
            m *= CHART[atk].get(d, 1)
        out[atk] = m
    return out

def esc(s):
    return html.escape(str(s), quote=True)

def slug(en):
    return re.sub(r"[^a-z0-9-]", "-", en.lower()).strip("-")

# ── HTML 조각 ─────────────────────────────────────────────────────────
def tp_chip(t):
    return f'<span class="tp" style="background:{TYPE_COLOR[t]}">{TYPE_KO.get(t,t)}</span>'

def stat_bars(stats):
    rows = []
    for k, lab, c in STATS:
        v = stats[k]
        w = min(100, v / 255 * 100)
        rows.append(f'<div class="stat-row"><span class="lab">{lab}</span>'
                    f'<span class="val">{v}</span>'
                    f'<div class="bar"><i style="width:{w:.1f}%;background:{c}"></i></div></div>')
    total = sum(stats[k] for k, _, _ in STATS)
    rows.append(f'<div class="stat-total"><span>종족값 합계</span><b>{total}</b></div>')
    return "".join(rows)

def mchip(t, mult):
    label = {4:"×4", 2:"×2", 0.5:"×½", 0.25:"×¼", 0:"×0"}.get(mult, f"×{mult:g}")
    return (f'<span class="mchip" style="background:{TYPE_COLOR[t]}">'
            f'{TYPE_KO[t]}<span class="x">{label}</span></span>')

def matchup_block(types):
    prof = defense_profile(types)
    weak   = sorted([(t, m) for t, m in prof.items() if m > 1], key=lambda x: (-x[1], TYPE_ORDER.index(x[0])))
    resist = sorted([(t, m) for t, m in prof.items() if 0 < m < 1], key=lambda x: (x[1], TYPE_ORDER.index(x[0])))
    immune = [t for t in TYPE_ORDER if prof[t] == 0]
    parts = []
    if weak:
        parts.append('<div class="matchup-grp weak"><div class="h">약점 (받는 데미지 증가)</div>'
                     '<div class="mrow">' + "".join(mchip(t, m) for t, m in weak) + '</div></div>')
    if resist:
        parts.append('<div class="matchup-grp resist"><div class="h">반감 (받는 데미지 감소)</div>'
                     '<div class="mrow">' + "".join(mchip(t, m) for t, m in resist) + '</div></div>')
    if immune:
        parts.append('<div class="matchup-grp immune"><div class="h">무효 (데미지 없음)</div>'
                     '<div class="mrow">' + "".join(mchip(t, 0) for t in immune) + '</div></div>')
    if not weak and not resist and not immune:
        parts.append('<p class="matchup-note">모든 타입에 등배(×1)로 데미지를 받습니다.</p>')
    tnames = "·".join(TYPE_KO[t] for t in types)
    parts.append(f'<p class="matchup-note">{tnames} 타입 기준으로, 상대 기술 타입에 따라 최종 데미지가 위 배율만큼 곱해집니다. '
                 f'같은 타입 기술을 방어할 땐 자속 보정(×1.5)까지 함께 고려하세요.</p>')
    return "".join(parts)

def usage_for(en):
    return USAGE.get(_norm(en))

def usage_section(en, usage_map=None, season="", fmt="싱글"):
    # 131차 — 싱글/더블 공용. usage_map=None → 싱글(USAGE) 기본. 더블은 USAGE_D 전달.
    u = (USAGE if usage_map is None else usage_map).get(_norm(en))
    if not u or not u.get("moves"):
        return ""
    rows = []
    for m in u["moves"][:10]:
        pct = m.get("pct")
        w = min(100, pct) if isinstance(pct, (int, float)) else 0
        ptxt = f"{pct:g}%" if isinstance(pct, (int, float)) else "-"
        rows.append(f'<div class="use-row"><span class="use-nm">{esc(m["ko"])}</span>'
                    f'<div class="bar"><i style="width:{w:.0f}%;background:#5b8de0"></i></div>'
                    f'<span class="use-pct">{ptxt}</span></div>')
    season_txt = f' · 시즌 {esc(season)} {fmt} 배틀' if season else ''
    _rk = u.get("rank")
    sub = f'{fmt} 사용 순위 {_rk}위' if _rk else '랭크 배틀 채용률'
    return (f'<section class="card"><h2>실전 사용 기술 <span class="sub">{sub}</span></h2>'
            f'<p class="matchup-note" style="margin:0 0 12px">실제 랭크 배틀({fmt})에서 이 포켓몬이 자주 채용하는 기술과 채용률입니다. '
            '상대로 만났을 때 어떤 기술을 조심해야 하는지 예측하는 데 참고하세요.</p>'
            '<div class="use-list">' + "".join(rows) + '</div>'
            f'<p class="attrib">{ATTRIB}{season_txt}</p></section>')

def ability_usage_section(en, usage_map=None, season="", fmt="싱글"):
    # 특성 채용률(abils) 섹션 — usage_section(기술)의 특성판 거울. move-usage.json 의 abils(내림차순 %)를
    #   기술과 동일한 use-list 레이아웃으로 렌더(CSS 재사용). abils 없으면 조용히 생략(구버전 json 안전).
    u = (USAGE if usage_map is None else usage_map).get(_norm(en))
    if not u or not u.get("abils"):
        return ""
    rows = []
    for a in u["abils"][:8]:
        pct = a.get("pct")
        w = min(100, pct) if isinstance(pct, (int, float)) else 0
        ptxt = f"{pct:g}%" if isinstance(pct, (int, float)) else "-"
        rows.append(f'<div class="use-row"><span class="use-nm">{esc(a["ko"])}</span>'
                    f'<div class="bar"><i style="width:{w:.0f}%;background:#6fd08a"></i></div>'
                    f'<span class="use-pct">{ptxt}</span></div>')
    season_txt = f' · 시즌 {esc(season)} {fmt} 배틀' if season else ''
    return (f'<section class="card"><h2>자주 채용하는 특성 <span class="sub">{fmt} 채용률</span></h2>'
            f'<p class="matchup-note" style="margin:0 0 12px">실제 랭크 배틀({fmt})에서 이 포켓몬이 채용한 특성의 비율입니다. '
            '복수 특성 포켓몬이라면 상대가 어떤 특성일 확률이 높은지 예측하는 데 참고하세요.</p>'
            '<div class="use-list">' + "".join(rows) + '</div>'
            f'<p class="attrib">{ATTRIB}{season_txt}</p></section>')

def item_usage_section(en, usage_map=None, season="", fmt="싱글"):
    # 도구 채용률(items) 섹션 — 특성 섹션의 도구판 거울. move-usage.json 의 items(내림차순 %)를
    #   기술/특성과 동일한 use-list 레이아웃으로 렌더(CSS 재사용). items 없으면 조용히 생략(구버전 json 안전).
    u = (USAGE if usage_map is None else usage_map).get(_norm(en))
    if not u or not u.get("items"):
        return ""
    rows = []
    for a in u["items"][:8]:
        pct = a.get("pct")
        w = min(100, pct) if isinstance(pct, (int, float)) else 0
        ptxt = f"{pct:g}%" if isinstance(pct, (int, float)) else "-"
        rows.append(f'<div class="use-row"><span class="use-nm">{esc(a["ko"])}</span>'
                    f'<div class="bar"><i style="width:{w:.0f}%;background:#e0b26a"></i></div>'
                    f'<span class="use-pct">{ptxt}</span></div>')
    season_txt = f' · 시즌 {esc(season)} {fmt} 배틀' if season else ''
    return (f'<section class="card"><h2>자주 드는 지닌도구 <span class="sub">{fmt} 채용률</span></h2>'
            f'<p class="matchup-note" style="margin:0 0 12px">실제 랭크 배틀({fmt})에서 이 포켓몬이 지닌 도구의 채용률입니다. '
            '상대가 구애 도구·기합의띠·열매 등 무엇을 들고 있을지 예측하는 데 참고하세요.</p>'
            '<div class="use-list">' + "".join(rows) + '</div>'
            f'<p class="attrib">{ATTRIB}{season_txt}</p></section>')

# ── 169차 신규 — usage 소스를 공식 순위데이터로 교체하며 함께 들어온 항목들 ─────────
#   move-usage.json 의 natures / spreads / teammates / winVs / loseVs 를 쓴다.
#   구 데이터(해당 키 없음)에서는 전부 조용히 생략 → 소스를 되돌려도 안전.
STAT_ABBR = {"hp": "H", "atk": "A", "def": "B", "spa": "C", "spd": "D", "spe": "S"}

def nature_usage_section(en, usage_map=None, season="", fmt="싱글"):
    """자주 쓰는 성격 — 스탯 보정(↑/↓)까지 표기. 상대 실수치 추정에 직결."""
    u = (USAGE if usage_map is None else usage_map).get(_norm(en))
    if not u or not u.get("natures"):
        return ""
    rows = []
    for n in u["natures"][:8]:
        pct = n.get("pct")
        w = min(100, pct) if isinstance(pct, (int, float)) else 0
        ptxt = f"{pct:g}%" if isinstance(pct, (int, float)) else "-"
        up, down = n.get("up"), n.get("down")
        mod = (f' <span style="color:var(--muted);font-weight:500">'
               f'{STAT_ABBR.get(up, up)}↑{STAT_ABBR.get(down, down)}↓</span>') if up and down else \
              ' <span style="color:var(--muted);font-weight:500">무보정</span>'
        rows.append(f'<div class="use-row"><span class="use-nm">{esc(n["ko"])}{mod}</span>'
                    f'<div class="bar"><i style="width:{w:.0f}%;background:#D685AD"></i></div>'
                    f'<span class="use-pct">{ptxt}</span></div>')
    season_txt = f' · 시즌 {esc(season)} {fmt} 배틀' if season else ''
    return (f'<section class="card"><h2>자주 쓰는 성격 <span class="sub">{fmt} 채용률</span></h2>'
            f'<p class="matchup-note" style="margin:0 0 12px">실제 랭크 배틀({fmt})에서 이 포켓몬이 채용한 성격의 비율입니다. '
            '성격은 스탯에 ×1.1 / ×0.9 보정을 주므로, 상대의 실제 수치(특히 스피드)를 추정할 때 참고하세요.</p>'
            '<div class="use-list">' + "".join(rows) + '</div>'
            f'<p class="attrib">{ATTRIB}{season_txt}</p></section>')

def spread_usage_section(en, usage_map=None, season="", fmt="싱글"):
    """노력치 배분 순위 — 챔피언스는 스탯당 최대 32 / 합 66."""
    u = (USAGE if usage_map is None else usage_map).get(_norm(en))
    if not u or not u.get("spreads"):
        return ""
    order = ["H", "A", "B", "C", "D", "S"]
    rows = []
    for s in u["spreads"][:10]:
        ev = s.get("ev") or []
        if len(ev) != 6:
            continue
        label = " ".join(f"{order[i]}{v}" for i, v in enumerate(ev) if v) or "노력치 없음"
        pct = s.get("pct")
        w = min(100, pct) if isinstance(pct, (int, float)) else 0
        ptxt = f"{pct:g}%" if isinstance(pct, (int, float)) else "-"
        rows.append(f'<div class="use-row"><span class="use-nm" style="font-family:Consolas,monospace">{esc(label)}</span>'
                    f'<div class="bar"><i style="width:{w:.0f}%;background:#96D9D6"></i></div>'
                    f'<span class="use-pct">{ptxt}</span></div>')
    if not rows:
        return ""
    season_txt = f' · 시즌 {esc(season)} {fmt} 배틀' if season else ''
    return (f'<section class="card"><h2>노력치 배분 순위 <span class="sub">{fmt} 채용률</span></h2>'
            f'<p class="matchup-note" style="margin:0 0 12px">실제 랭크 배틀({fmt})에서 많이 쓰인 노력치 배분입니다. '
            '챔피언스의 노력치는 스탯당 최대 32, 합계 66입니다. '
            'H=HP · A=공격 · B=방어 · C=특공 · D=특방 · S=스피드.</p>'
            '<div class="use-list">' + "".join(rows) + '</div>'
            f'<p class="attrib">{ATTRIB}{season_txt}</p></section>')

# nameEn → sprite 파일명. 팀조합/매치업 칩에 아이콘을 붙인다(이름만 있으면 어떤 폼인지 알아보기 어렵다).
SPRITE_BY_EN = {_norm(e["en"]): e["sprite"] for e in DEX if e.get("sprite")}

def _mon_links(lst):
    out = []
    for m in lst[:10]:
        en, ko = m.get("name"), (m.get("ko") or m.get("name"))
        if not en:
            continue
        sp = SPRITE_BY_EN.get(_norm(en))
        img = (f'<img src="/sprites/{esc(sp)}" alt="" width="28" height="28" loading="lazy" '
               'style="image-rendering:pixelated;vertical-align:middle">') if sp else ''
        out.append(f'<a href="/pokedex/{slug(en)}/" class="mon-chip">{img}<span>{esc(ko)}</span></a>')
    return "".join(out)

def synergy_section(en, usage_map=None, season="", fmt="싱글"):
    """팀 조합 · 매치업 — 같이 쓰인 포켓몬 / 이길 때·질 때 자주 만난 상대."""
    u = (USAGE if usage_map is None else usage_map).get(_norm(en))
    if not u:
        return ""
    team, win, lose = u.get("teammates") or [], u.get("winVs") or [], u.get("loseVs") or []
    if not (team or win or lose):
        return ""
    blocks = []
    if team:
        blocks.append('<div class="matchup-grp"><div class="h">자주 같이 쓰는 포켓몬</div>'
                      f'<div class="mrow">{_mon_links(team)}</div></div>')
    if win:
        blocks.append('<div class="matchup-grp resist"><div class="h">이길 때 자주 만난 상대</div>'
                      f'<div class="mrow">{_mon_links(win)}</div></div>')
    if lose:
        blocks.append('<div class="matchup-grp weak"><div class="h">질 때 자주 만난 상대</div>'
                      f'<div class="mrow">{_mon_links(lose)}</div></div>')
    season_txt = f' · 시즌 {esc(season)} {fmt} 배틀' if season else ''
    return (f'<section class="card"><h2>팀 조합 · 매치업 <span class="sub">{fmt} 통계</span></h2>'
            f'<p class="matchup-note" style="margin:0 0 12px">실제 랭크 배틀({fmt})에서 이 포켓몬과 함께 편성된 포켓몬, '
            '그리고 승패가 갈렸을 때 자주 마주친 상대입니다. 파티를 짤 때와 상대 파티를 읽을 때 참고하세요.</p>'
            + "".join(blocks) +
            f'<p class="attrib">{ATTRIB}{season_txt}</p></section>')

def usage_block(en):
    """169차 — 실전 통계 전체를 싱글/더블 탭으로 묶는다.

    종전엔 싱글 6섹션 + 더블 6섹션이 상세페이지에 통째로 쌓여 페이지가 지나치게 길었다.
    헬퍼 로컬 뷰어(/usage)와 동일하게 한 번에 한 포맷만 보이고 탭으로 전환한다.
    ★JS 없이도(크롤러 포함) 두 포맷 모두 DOM 에 있으므로 색인·접근성 손실은 없다.
    """
    def pane(usage_map, season, fmt):
        return (usage_section(en, usage_map, season, fmt)
                + ability_usage_section(en, usage_map, season, fmt)
                + item_usage_section(en, usage_map, season, fmt)
                + nature_usage_section(en, usage_map, season, fmt)
                + spread_usage_section(en, usage_map, season, fmt)
                + synergy_section(en, usage_map, season, fmt))

    single = pane(USAGE, USAGE_SEASON, "싱글")
    double = pane(USAGE_D, USAGE_D_SEASON, "더블")
    if not single and not double:
        return ""
    if not (single and double):                       # 한쪽뿐이면 탭 없이 그대로
        return single or double
    return ('<div class="fmt-tabs" role="tablist">'
            '<button class="active" data-fmt="single" type="button">싱글</button>'
            '<button data-fmt="double" type="button">더블</button>'
            '</div>'
            f'<div class="fmt-pane" data-fmt="single">{single}</div>'
            f'<div class="fmt-pane" data-fmt="double" hidden>{double}</div>')

def abil_cards(abils):
    return "".join(
        f'<div class="abil"><div class="an">{esc(a["ko"])}</div>'
        + (f'<div class="ad">{esc(a["desc"])}</div>' if a.get("desc") else "")
        + '</div>'
        for a in abils)

def mega_card(m):
    types_html = "".join(tp_chip(t) for t in m["types"])
    return (f'<div class="mega-card"><div class="mega-head">'
            f'<img src="/sprites/{esc(m["sprite"])}" alt="{esc(m["ko"])}" width="72" height="72" loading="lazy">'
            f'<div><div class="mega-nm">{esc(m["ko"])}</div><div class="tps">{types_html}</div></div></div>'
            f'{stat_bars(m["stats"])}'
            f'<div class="mega-abil">{abil_cards(m["abil"])}</div>'
            f'<div style="margin-top:12px">{matchup_block(m["types"])}</div></div>')

# ── 운용 코멘트 (데이터 기반, 자동 서술) ───────────────────────────────
def commentary(e):
    s = e["stats"]
    total = sum(s.values())
    tnames = "·".join(TYPE_KO[t] for t in e["types"])
    # 최고 능력치 2개
    ranked = sorted(STATS, key=lambda x: -s[x[0]])
    top = ranked[0]
    top_ko, top_v = STAT_KO[top[0]], s[top[0]]
    # 물리/특수 성향
    if s["atk"] - s["spa"] >= 15:
        atk_kind = "물리 공격 위주"
    elif s["spa"] - s["atk"] >= 15:
        atk_kind = "특수 공격 위주"
    else:
        atk_kind = "물리·특수 균형형"
    # 스피드
    spe = s["spe"]
    if spe >= 110: spd_txt = "매우 빠른 스피드"
    elif spe >= 90: spd_txt = "준수한 스피드"
    elif spe >= 60: spd_txt = "평범한 스피드"
    else: spd_txt = "느린 스피드"
    # 내구
    bulk = s["hp"] + s["def"] + s["spd"]
    if bulk >= 300: bulk_txt = "높은 내구"
    elif bulk >= 230: bulk_txt = "무난한 내구"
    else: bulk_txt = "낮은 내구"
    # 약점 요약
    prof = defense_profile(e["types"])
    weaks = [TYPE_KO[t] for t in TYPE_ORDER if prof[t] > 1]
    resists = [TYPE_KO[t] for t in TYPE_ORDER if 0 < prof[t] < 1]
    immunes = [TYPE_KO[t] for t in TYPE_ORDER if prof[t] == 0]

    p1 = (f'<strong>{esc(e["ko"])}</strong>은(는) {tnames} 타입 포켓몬으로, 종족값 합계는 <strong>{total}</strong>입니다. '
          f'가장 높은 능력치는 {top_ko}({top_v})이며 {atk_kind}에 {spd_txt}, {bulk_txt}를 지닌 배분입니다.')

    seg = []
    if weaks:
        seg.append(f'받는 약점은 {", ".join(weaks)} 타입 기술이므로, 이런 상대 앞에서는 교체나 방어를 고려하는 편이 좋습니다.')
    if resists:
        seg.append(f'반대로 {", ".join(resists)} 타입 공격은 반감으로 버텨냅니다.')
    if immunes:
        seg.append(f'{", ".join(immunes)} 타입 공격은 완전히 무효화합니다.')
    p2 = " ".join(seg)

    p3 = ""
    if e.get("mega"):
        mt = sum(e["mega"][0]["stats"].values())
        names = ", ".join(m["ko"] for m in e["mega"])
        p3 = (f'{esc(e["ko"])}은(는) 전투 중 <strong>{names}</strong>(으)로 메가진화할 수 있으며, '
              f'메가진화 시 종족값 합계가 <strong>{mt}</strong>까지 상승합니다. '
              f'메가 이후의 타입·특성 변화는 위 메가진화 항목에서 확인하세요.')
    elif e.get("forms"):
        title = e.get("formTitle") or "폼체인지"
        p3 = f'{esc(e["ko"])}은(는) {esc(title)}에 따라 능력치와 특성이 달라집니다. 자세한 변화는 위 항목을 참고하세요.'

    p4 = ('실제 대전에서 이 포켓몬이 상대를 한 번에 쓰러뜨릴 수 있는지, 혹은 상대의 공격을 버틸 수 있는지는 '
          '<a href="/calc/">데미지 계산기</a>에서 노력치·성격·지닌 도구·랭크·날씨까지 넣어 정확히 확인할 수 있습니다.')

    return "".join(f"<p>{x}</p>" for x in (p1, p2, p3, p4) if x)

# ── 페이지 템플릿 ─────────────────────────────────────────────────────
PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1395643596867142" crossorigin="anonymous"></script>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<title>{title}</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="{canon}" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="Champions Helper" />
<meta property="og:locale" content="ko_KR" />
<meta property="og:url" content="{canon}" />
<meta property="og:title" content="{ogtitle}" />
<meta property="og:description" content="{desc}" />
<meta property="og:image" content="{ogimg}" />
<meta name="twitter:card" content="summary" />
<link rel="stylesheet" href="/pokedex/mon.css" />
<link rel="stylesheet" href="/site-header.css" />
<script type="application/ld+json">
{jsonld}
</script>
</head>
<body>
<header>
  <div class="nav">
    <a class="brand" href="/"><span class="dot"></span> Champions Helper</a>
    <nav class="nav-links">
      <a href="/#features">기능</a>
      <a href="/pokedex/" class="active">도감</a>
      <a href="/#how">사용법</a>
      <a href="/builder/">파티 빌더</a>
      <a href="/calc/">계산기</a>
      <a href="/battle-data/">배틀데이터</a>
      <a href="/guide/">가이드</a>
      <a href="/board/">게시판</a>
      <a href="/#download">다운로드</a>
      <a href="https://discord.gg/aTrGZyDEwH" target="_blank" rel="noopener">디스코드</a>
    </nav>
  </div>
</header>

<main class="wrap">
  <div class="crumb"><a href="/">홈</a> › <a href="/pokedex/">도감</a> › {ko}</div>

  <div class="mon-head">
    <img src="/sprites/{sprite}" alt="{ko}" width="108" height="108" />
    <div>
      <div class="num">{num}</div>
      <h1>{ko}</h1>
      <div class="en">{en}</div>
      <div class="tps">{types}</div>
    </div>
  </div>

  <section class="card">
    <h2>종족값 <span class="sub">Base Stats</span></h2>
    {stats}
  </section>

  <section class="card">
    <h2>타입 상성 <span class="sub">받는 데미지 배율</span></h2>
    {matchup}
  </section>

  <section class="card">
    <h2>특성 <span class="sub">Abilities</span></h2>
    {abils}
  </section>
  {usage}
  {mega}
  <section class="card">
    <h2>{ko} 운용 포인트</h2>
    <div class="prose">{prose}</div>
  </section>

  <section class="card">
    <h2>관련 페이지</h2>
    <div class="related">
      <a href="/calc/">데미지 계산기로 계산</a>
      <a href="/pokedex/">전체 도감</a>
      <a href="/battle-data/">실전 사용률 통계</a>
      <a href="/builder/">파티 빌더</a>
      <a href="/guide/type-chart/">타입 상성표 가이드</a>
    </div>
  </section>

  <div class="pager">
    <span>{prev}</span>
    <span>{next}</span>
  </div>
</main>
<script>
/* 169차 — 실전 통계 싱글/더블 탭. JS 가 없으면 두 포맷이 모두 보일 뿐이라 기능 손실은 없다(색인도 동일).
   ★이 템플릿은 str.format() 으로 렌더되므로 중괄호는 반드시 {{ }} 로 이스케이프한다. */
(function () {{
  var tabs = document.querySelector(".fmt-tabs");
  if (!tabs) return;
  tabs.addEventListener("click", function (ev) {{
    var b = ev.target.closest("button[data-fmt]");
    if (!b) return;
    tabs.querySelectorAll("button").forEach(function (x) {{ x.classList.toggle("active", x === b); }});
    document.querySelectorAll(".fmt-pane").forEach(function (p) {{ p.hidden = p.dataset.fmt !== b.dataset.fmt; }});
  }});
}})();
</script>

<footer>
  <div class="wrap">
    <p class="foot-links"><a href="/about/">사이트 소개</a> · <a href="/privacy/">개인정보처리방침</a> · <a href="/terms/">이용약관</a> · <a href="/pokedex/">도감</a></p>
    <p class="disclaimer">
      Champions Helper는 팬이 만든 비공식 보조 도구입니다.
      &ldquo;Pok&eacute;mon&rdquo;(포켓몬) 및 관련 명칭·이미지·캐릭터는 Nintendo, Game Freak, The Pok&eacute;mon Company의
      상표 및 저작물이며, 본 사이트는 이들과 어떠한 제휴·후원·승인 관계도 없습니다.<br>&copy; 2026 Champions Helper.
    </p>
  </div>
</footer>
</body>
</html>
"""

def mega_section(e):
    if e.get("mega"):
        return ('<section class="card"><h2>메가진화 <span class="sub">Mega Evolution</span></h2>'
                + "".join(mega_card(m) for m in e["mega"]) + '</section>')
    if e.get("forms"):
        title = esc(e.get("formTitle") or "폼체인지")
        return (f'<section class="card"><h2>{title}</h2>'
                + "".join(mega_card(m) for m in e["forms"]) + '</section>')
    return ""

def pager_link(e, arrow):
    if not e:
        return ""
    if arrow == "prev":
        return f'<a href="/pokedex/{slug(e["en"])}/">← {esc(e["ko"])}</a>'
    return f'<a href="/pokedex/{slug(e["en"])}/">{esc(e["ko"])} →</a>'

def build_pages():
    # 순서 = dex.json 그대로(도감번호 순, 독립폼은 base 바로 뒤) — prev/next 페이저도 이 순서.
    n = 0
    seen = set()
    for i, e in enumerate(DEX):
        sg = slug(e["en"])
        if sg in seen:
            print(f"  !! slug 중복 skip: {sg} ({e['ko']})")
            continue
        seen.add(sg)
        canon = f"{BASE}/pokedex/{sg}/"
        num = "#" + str(e.get("baseId") or e["id"]).zfill(4)
        tnames = "·".join(TYPE_KO[t] for t in e["types"])
        total = sum(e["stats"].values())
        desc = (f'{e["ko"]}({e["en"]})의 종족값(합계 {total})·타입 상성(약점/반감)·한글 특성'
                + ('·메가진화' if e.get("mega") else '')
                + ' 정보. 포켓몬 챔피언스 도감.')
        jsonld = json.dumps({
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": f'{e["ko"]} — 포켓몬 챔피언스 도감',
            "inLanguage": "ko",
            "url": canon,
            "image": f"{BASE}/sprites/{e['sprite']}",
            "description": desc,
            "isPartOf": {"@type": "WebSite", "name": "Champions Helper", "url": BASE + "/"},
        }, ensure_ascii=False, indent=2)
        preve = DEX[i-1] if i > 0 else None
        nexte = DEX[i+1] if i < len(DEX)-1 else None

        page = PAGE.format(
            title=esc(f'{e["ko"]} 종족값·타입상성·특성 | 포켓몬 챔피언스 도감'),
            ogtitle=esc(f'{e["ko"]} — 포켓몬 챔피언스 도감'),
            desc=esc(desc),
            canon=canon,
            ogimg=f"{BASE}/sprites/{esc(e['sprite'])}",
            jsonld=jsonld,
            ko=esc(e["ko"]),
            en=esc(e["en"]),
            num=num,
            sprite=esc(e["sprite"]),
            types="".join(tp_chip(t) for t in e["types"]),
            stats=stat_bars(e["stats"]),
            matchup=matchup_block(e["types"]),
            abils=abil_cards(e["abil"]),
            usage=usage_block(e["en"]),
            mega=mega_section(e),
            prose=commentary(e),
            prev=pager_link(preve, "prev"),
            next=pager_link(nexte, "next"),
        )
        d = os.path.join(SITE, "pokedex", sg)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(page)
        n += 1
    return n, seen

# ── 도감 인덱스에 정적 전체목록 주입 ──────────────────────────────────
def inject_index():
    path = os.path.join(SITE, "pokedex", "index.html")
    with open(path, encoding="utf-8") as f:
        html_src = f.read()
    items = []
    for e in DEX:  # dex.json 순서(도감번호 순, 독립폼은 base 바로 뒤)
        sg = slug(e["en"])
        tag = ""
        if e.get("mega"): tag = '<span class="ml-mega">메가</span>'
        elif e.get("forms"): tag = '<span class="ml-form">폼</span>'
        items.append(f'<li><a href="/pokedex/{sg}/">{esc(e["ko"])}{tag}</a></li>')
    block = (
        '<!--ALLLIST-->\n'
        '<section class="all-list-sec" style="max-width:960px;margin:8px auto 0;padding:22px 0 8px;border-top:1px solid var(--line);">\n'
        '  <h2 style="font-size:18px;font-weight:800;margin:0 0 6px;">포켓몬 전체 목록</h2>\n'
        '  <p style="color:var(--muted);font-size:13px;margin:0 0 14px;">각 포켓몬을 누르면 종족값·타입 상성·특성·메가진화 정보를 담은 상세 페이지로 이동합니다.</p>\n'
        '  <style>.all-list{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:4px 14px}'
        '.all-list a{display:block;padding:5px 4px;font-size:14px;color:var(--txt);border-bottom:1px solid transparent}'
        '.all-list a:hover{color:var(--accent2);text-decoration:none}'
        '.ml-mega,.ml-form{font-size:10px;font-weight:700;margin-left:5px;padding:0 5px;border-radius:7px;vertical-align:middle}'
        '.ml-mega{color:#ffd479;background:rgba(255,170,40,.16)}.ml-form{color:#9fd0ff;background:rgba(60,130,220,.16)}</style>\n'
        '  <ul class="all-list">\n    ' + "\n    ".join(items) + '\n  </ul>\n'
        '</section>\n'
        '<!--/ALLLIST-->'
    )
    if "<!--ALLLIST-->" in html_src:
        html_src = re.sub(r"<!--ALLLIST-->.*?<!--/ALLLIST-->", lambda _: block, html_src, flags=re.S)
    else:
        html_src = html_src.replace("</main>", block + "\n</main>", 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_src)

# ── sitemap 재생성 ────────────────────────────────────────────────────
STATIC_ROUTES = [
    ("/", "weekly", "1.0"),
    ("/pokedex/", "weekly", "0.9"),
    ("/calc/", "weekly", "0.9"),
    ("/battle-data/", "weekly", "0.8"),
    ("/battle-data/doubles/", "weekly", "0.7"),
    ("/builder/", "weekly", "0.8"),
    ("/board/", "daily", "0.7"),
    ("/guide/", "monthly", "0.7"),
    ("/about/", "yearly", "0.5"),
    ("/guide/meta-singles/", "weekly", "0.8"),
    ("/guide/meta-doubles/", "weekly", "0.8"),
    ("/guide/speed-guide/", "monthly", "0.7"),
    ("/guide/ev-nature/", "monthly", "0.7"),
    ("/guide/team-building/", "monthly", "0.7"),
    ("/guide/mega-picks/", "monthly", "0.7"),
    ("/guide/status-moves/", "monthly", "0.7"),
    ("/guide/app-guide/", "monthly", "0.8"),
    ("/guide/getting-started/", "monthly", "0.7"),
    ("/guide/damage-formula/", "monthly", "0.7"),
    ("/guide/type-chart/", "monthly", "0.7"),
    ("/guide/abilities-items/", "monthly", "0.7"),
    ("/guide/mega-evolution/", "monthly", "0.7"),
    ("/privacy/", "yearly", "0.3"),
    ("/terms/", "yearly", "0.3"),
]

def build_sitemap():
    urls = []
    def u(loc, freq, pri):
        urls.append(f"  <url>\n    <loc>{BASE}{loc}</loc>\n    <lastmod>{LASTMOD}</lastmod>\n"
                    f"    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>")
    for loc, freq, pri in STATIC_ROUTES:
        u(loc, freq, pri)
    for e in DEX:
        u(f"/pokedex/{slug(e['en'])}/", "monthly", "0.6")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)

BD_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1395643596867142" crossorigin="anonymous"></script>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<title>포켓몬 챔피언스 {fmt_label}배틀 실전 사용률 — 배틀 데이터 | Champions Helper</title>
<meta name="description" content="포켓몬 챔피언스 {fmt_label}배틀 랭크({season}) 기준, 포켓몬별 자주 채용하는 기술과 채용률 통계. 상대가 무엇을 들고 오는지 예측하세요." />
<link rel="canonical" href="{canon_url}" />
<meta property="og:type" content="website" />
<meta property="og:site_name" content="Champions Helper" />
<meta property="og:locale" content="ko_KR" />
<meta property="og:url" content="{canon_url}" />
<meta property="og:title" content="포켓몬 챔피언스 {fmt_label}배틀 실전 사용률 — 배틀 데이터" />
<meta property="og:description" content="포켓몬 챔피언스 랭크 배틀 기준, 포켓몬별 기술 채용률 통계." />
<meta name="twitter:card" content="summary" />
<link rel="stylesheet" href="/pokedex/mon.css" />
<link rel="stylesheet" href="/site-header.css" />
<style>
  .bd-list {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 8px; }}
  .bd-row {{ display: flex; align-items: center; gap: 11px; background: var(--panel); border: 1px solid var(--line);
    border-radius: 10px; padding: 9px 12px; color: var(--txt); }}
  .bd-row:hover {{ border-color: var(--accent); text-decoration: none; }}
  .bd-row img {{ width: 42px; height: 42px; object-fit: contain; image-rendering: pixelated; flex: none; }}
  .bd-rank {{ flex: none; width: 34px; text-align: center; font-weight: 800; font-size: 13px; color: var(--accent2); }}
  .bd-nm {{ font-weight: 800; font-size: 14px; flex: none; width: 90px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .bd-mv {{ font-size: 12.5px; color: var(--muted); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .bd-mv b {{ color: var(--accent2); }}
  .bd-ab {{ flex: none; max-width: 130px; font-size: 11.5px; font-weight: 700; color: var(--ok);
    background: rgba(111,208,138,.12); border: 1px solid rgba(111,208,138,.32); border-radius: 4px;
    padding: 1px 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .bd-h {{ font-size: 16px; font-weight: 800; margin: 24px 0 10px; }}
  .bd-h .c {{ color: var(--muted); font-weight: 500; font-size: 13px; margin-left: 6px; }}
  .bd-toggle {{ display: inline-flex; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; margin: 8px 0 4px; }}
  .bd-toggle a {{ padding: 8px 22px; font-weight: 800; font-size: 14px; color: var(--muted); background: var(--panel); }}
  .bd-toggle a.active {{ background: var(--accent); color: #fff; }}
  .bd-toggle a:hover {{ text-decoration: none; color: var(--txt); }}
  .bd-toggle a.active:hover {{ color: #fff; }}
</style>
</head>
<body>
<header>
  <div class="nav">
    <a class="brand" href="/"><span class="dot"></span> Champions Helper</a>
    <nav class="nav-links">
      <a href="/#features">기능</a>
      <a href="/pokedex/">도감</a>
      <a href="/#how">사용법</a>
      <a href="/builder/">파티 빌더</a>
      <a href="/calc/">계산기</a>
      <a href="/battle-data/" class="active">배틀데이터</a>
      <a href="/guide/">가이드</a>
      <a href="/board/">게시판</a>
      <a href="/#download">다운로드</a>
      <a href="https://discord.gg/aTrGZyDEwH" target="_blank" rel="noopener">디스코드</a>
    </nav>
  </div>
</header>

<main class="wrap">
  <div class="crumb"><a href="/">홈</a> › 배틀데이터</div>
  <div style="padding:16px 0 4px">
    <h1 style="font-size:28px;margin:0 0 8px;font-weight:800;">{fmt_label}배틀 실전 사용률</h1>
    <p style="color:var(--muted);margin:0;font-size:14.5px;line-height:1.7;">
      포켓몬 챔피언스 <strong style="color:var(--txt)">랭크 배틀 {season}</strong> 통계를 바탕으로, 포켓몬별로
      실제 대전에서 자주 채용되는 기술·특성과 채용률을 정리했습니다. 상대가 어떤 기술·특성을 들고 오는지 예측하는 데 활용하세요.
      각 포켓몬을 누르면 종족값·타입 상성과 함께 <strong style="color:var(--txt)">기술·특성별 채용률 전체</strong>를 볼 수 있습니다.
    </p>
  </div>

  <section class="card">
    <p class="attrib" style="margin:0">{attrib} · 시즌 {season} · {fmt_label} 배틀 · 데이터는 시즌 통계에 따라 주기적으로 갱신됩니다.</p>
  </section>

  {body}

  <section class="card" style="margin-top:20px">
    <h2 style="font-size:16px;margin:0 0 10px;font-weight:800;">이 데이터는 어떻게 쓰이나요?</h2>
    <div class="prose">
      <p>Champions Helper 데스크탑 프로그램의 <strong>상대 시점 위력 모드</strong>는 이 사용률 데이터를 이용해,
      상대 포켓몬이 자주 쓰는 상위 기술을 자동으로 위력칩에 띄워 줍니다. 덕분에 상대의 예상 기술 기준으로 내 포켓몬이
      얼마나 버틸 수 있는지 즉시 확인할 수 있습니다.</p>
      <p>웹에서도 <a href="/pokedex/">도감</a>의 각 포켓몬 페이지에서 같은 채용률을 확인할 수 있고,
      <a href="/calc/">데미지 계산기</a>에 기술을 넣어 실제 데미지까지 계산할 수 있습니다.</p>
    </div>
  </section>
</main>

<footer>
  <div class="wrap">
    <p class="foot-links"><a href="https://forms.gle/vzavUFn5xFDtdpu66" target="_blank" rel="noopener">🐞 버그 제보</a> · <a href="https://discord.gg/aTrGZyDEwH" target="_blank" rel="noopener">💬 디스코드</a> · <a href="/about/">사이트 소개</a> · <a href="/privacy/">개인정보처리방침</a> · <a href="/terms/">이용약관</a></p>
    <p class="attrib" style="margin:0 0 10px">{attrib}</p>
    <p class="disclaimer">
      Champions Helper는 팬이 만든 비공식 보조 도구입니다.
      &ldquo;Pok&eacute;mon&rdquo;(포켓몬) 및 관련 명칭·이미지·캐릭터는 Nintendo, Game Freak, The Pok&eacute;mon Company의
      상표 및 저작물이며, 본 사이트는 이들과 어떠한 제휴·후원·승인 관계도 없습니다.<br>&copy; 2026 Champions Helper.
    </p>
  </div>
</footer>
</body>
</html>
"""

def _bd_row(e, u, rank):
    top = u["moves"][:3]
    mv = ", ".join(
        f'{esc(m["ko"])} <b>{m["pct"]:g}%</b>' if isinstance(m.get("pct"), (int, float))
        else esc(m["ko"]) for m in top) or "기술 통계 없음"
    # 1위 채용 특성칩(있으면). 채용률까지 표기 — 복수 특성 종족의 최다 채용을 한눈에.
    ab = u.get("abils") or []
    ab_html = (f'<span class="bd-ab">{esc(ab[0]["ko"])} {ab[0]["pct"]:g}%</span>'
               if ab and isinstance(ab[0].get("pct"), (int, float)) else "")
    rk = f'<span class="bd-rank">{rank}</span>' if rank else '<span class="bd-rank">–</span>'
    return (f'<a class="bd-row" href="/pokedex/{slug(e["en"])}/">{rk}'
            f'<img src="/sprites/{esc(e["sprite"])}" alt="{esc(e["ko"])}" width="42" height="42" loading="lazy">'
            f'<span class="bd-nm">{esc(e["ko"])}</span>'
            f'{ab_html}'
            f'<span class="bd-mv">{mv}</span></a>')

def bd_toggle(active):
    # 131차 — 싱글/더블 배틀데이터 전환 탭. active = 'single' | 'double'.
    s = ' active' if active == 'single' else ''
    d = ' active' if active == 'double' else ''
    return (f'<div class="bd-toggle"><a href="/battle-data/" class="tab{s}">싱글배틀</a>'
            f'<a href="/battle-data/doubles/" class="tab{d}">더블배틀</a></div>')

def build_battle_data_page(usage_map, season, fmt_label, subdir, canon_url, active_tab):
    # 131차 — 싱글/더블 공용. usage_map=USAGE(싱글) or USAGE_D(더블). 없으면 조용히 생략.
    if not usage_map:
        print(f"  (move-usage {fmt_label} 없음 — /{subdir}/ 생략)")
        return 0
    ranked, unranked = [], []
    for e in DEX:
        u = usage_map.get(_norm(e["en"]))
        if not u:
            continue
        rk = u.get("rank")
        if rk:
            ranked.append((e, u, rk))
        elif u.get("moves"):
            unranked.append((e, u, None))
    ranked.sort(key=lambda x: (x[2], x[0]["id"]))
    # 검증: 순위 완전성(구멍/중복) — 소스 1..N 그대로 나와야 정상.
    rks = [r for _, _, r in ranked]
    dup = sorted({r for r in rks if rks.count(r) > 1})
    holes = sorted(set(range(1, (max(rks) if rks else 0) + 1)) - set(rks))
    if dup:
        print(f"  !! {fmt_label} 배틀데이터 중복 순위: {dup}")
        for r in dup:
            print(f"     {r}: {[e['ko'] for e, _, rr in ranked if rr == r]}")
    if holes:
        print(f"  !! {fmt_label} 배틀데이터 빈 순위: {holes}")
    parts = [bd_toggle(active_tab),
             f'<h2 class="bd-h">실전 사용 순위 <span class="c">({len(ranked)}종 · 채용률 높은 순)</span></h2>',
             '<div class="bd-list">' + "".join(_bd_row(e, u, dr) for e, u, dr in ranked) + '</div>']
    if unranked:
        parts += [f'<h2 class="bd-h">순위권 밖 등장 포켓몬 <span class="c">({len(unranked)}종 · 도감 순)</span></h2>',
                  '<div class="bd-list">' + "".join(_bd_row(e, u, None) for e, u, _ in unranked) + '</div>']
    page = BD_PAGE.format(season=esc(season or "현재 시즌"), attrib=ATTRIB,
                          body="\n  ".join(parts), fmt_label=fmt_label, canon_url=canon_url)
    d = os.path.join(SITE, subdir)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    return len(ranked) + len(unranked)

if __name__ == "__main__":
    n, seen = build_pages()
    inject_index()
    bd = build_battle_data_page(USAGE, USAGE_SEASON, "싱글", "battle-data",
                                "https://champions-helper.com/battle-data/", "single")
    bd_d = build_battle_data_page(USAGE_D, USAGE_D_SEASON, "더블", os.path.join("battle-data", "doubles"),
                                  "https://champions-helper.com/battle-data/doubles/", "double")
    build_sitemap()
    print(f"OK — 상세페이지 {n}개 생성 (pokedex/<en>/index.html), 사용률 매칭 {sum(1 for e in DEX if usage_for(e['en']))}종")
    print(f"     배틀데이터 싱글 {bd}종 · 더블 {bd_d}종 · 도감 인덱스 정적목록 주입 · sitemap {len(STATIC_ROUTES)}정적 + {len(seen)}상세 재생성")
