#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Champions Helper — 상대 기술 사용률(move-usage) 빌드.
  championsbattledata.com API (Singles/Doubles) → helper-data/move-usage[-double].json

154차 — 소스 재교체: champs.pokedb.tokyo → championsbattledata.com API.
  pokedb 가 사용자 거주지 IP 를 403 으로 차단(2026-07-18 실측 — 브라우저·시크릿 포함 전면).
  championsbattledata 는 123차 이전 원래 소스("갱신 매우 느림"으로 폐기)였으나 현재는 매일 갱신
  (index generatedAt·dailyDataFolders 실측) → 24h cron 이면 충분. CI(GitHub 러너)도 직접 접속 가능
  (123차 이전 cron 실적 — pokedb 와 달리 클라우드 IP 차단 없음, 릴레이 불요. 단 브라우저 UA 필수).

매칭: API 가 영어 표기명("Dragon Claw"/"Rough Skin"/"Focus Sash")을 주므로 정규화(영숫자 소문자)로
  master.json nameEn(slug 표기 "dragon-claw")과 직결. pokedb 의 일본어 브릿지(pokeapi-names.json) 불요.
  메가스톤만 예외 — 영문 스톤명("Feraligite")이 master 의 Z-A 스킴("feraligatr-mega-stone")과 달라
  스톤 접미(-ite) → 종족 접두 매칭 폴백(resolve_item). 구세대 스톤(gengarite)·X/Y(charizardite-x)는 직결.

용도: /live "상대" 토글(상대 시점 위력) 모드에서, 상대 포켓몬이 자주 쓰는 기술 상위 N개를
  위력칩으로 보여준다. + 사이트 도감 상세페이지 "실전 사용 기술" 섹션 / battle-data 순위 페이지.

종족 사용 순위(rank): /api/battle/{format}/{slug} rows 의 column_position = 그 엔티티의 순위(1~235).
  순위 카탈로그 = /api/index 의 pokemon(235종 — 순위를 갖는 배틀 엔티티 전체, 메가 페이지 제외).
  ★개별 HTML 페이지의 rank 셀은 지역폼 짝에서 값이 섞이는 소스 결함 전력 → API column_position 만 쓰고
  요약표(/pokemon-champions-*-usage/)와 교차검증(불일치 시 경고).

출력 스키마(pokedb 버전과 완전 동일 — 헬퍼 exe·사이트 빌드 무변경):
  { version, format, season, count, pokemon: { <master nameEn>: {
      name, base, isForm, moves:[{en,ko,pct}], abils:[{en,ko,pct}], items:[{en,ko,pct}], rank } } }
  키 = master.json species nameEn (헬퍼 UsageKeyCandidates·사이트 usage_for 가 이 키로 조회).

자동화(master.json/sprites 와 독립 — 기술 사용률만 따로 갱신):
  .github/workflows/move-usage.yml 가 cron(24h — 소스가 매일 갱신)으로 이 스크립트를 실행 →
  helper-data/move-usage.json + move-usage-version.json 을 커밋·push → GitHub Pages 재배포 →
  헬퍼가 켤 때 버전 확인·다운로드(즉시 반영). 개발자 수동 개입 0.

로컬 실행: python build/build-move-usage.py [LIMIT]
  LIMIT(선택) = 처음 N종족만 처리(검증용). 미지정 = 전종족.

API 메모: championsbattledata 는 기본 urllib User-Agent 를 403 으로 막는다 → 브라우저 UA 필수.
  api-rules 준수(출처표기 = build-mon-pages ATTRIB) + DELAY 로 부하 완화(24h 1회 236 요청/포맷).
"""
import json, os, re, sys, time, urllib.request

REPO   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # build/ 의 상위 = repo 루트
HELPER = os.path.join(REPO, "helper-data")
API    = "https://championsbattledata.com"
# 131차(더블배틀) — rule 파라미터화 유지. env PCH_MOVE_RULE 로 배틀 형식 전환:
#   0 = 싱글(move-usage.json) / 1 = 더블(move-usage-double.json). yml 은 이 env 만 바꿔 두 번 실행.
RULE   = int(os.environ.get("PCH_MOVE_RULE", "0"))
FORMAT = "Doubles" if RULE == 1 else "Singles"
OUT_MOVE = "move-usage-double.json" if RULE == 1 else "move-usage.json"
OUT_VER  = "move-usage-double-version.json" if RULE == 1 else "move-usage-version.json"
SUMMARY_PAGE = "pokemon-champions-doubles-usage" if RULE == 1 else "pokemon-champions-singles-usage"
TOP_N  = 12                 # 위력칩 4개 + 편집 드롭다운(5위~) 여유분
UA     = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PCH-move-usage/1.0"}
DELAY  = 0.35               # 정중한 호출 간격(초)

# 무인 cron 안전핀 — 사이트 개편 등으로 파싱이 무너지면 옛(정상) json 을 덮지 않고 실패 종료.
MIN_POKEMON = 150           # 정상 = 235종
MAX_EMPTY_RATIO = 0.5       # 기술 0개 페이지가 절반 넘으면 파싱 붕괴로 간주


def fetch(url, tries=3, as_json=True):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read().decode("utf-8", "replace")
                return json.loads(body) if as_json else body
        except Exception as e:  # noqa: BLE001 — best-effort 재시도
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def norm(s):
    """영어 표기명 정규화(영숫자만 소문자). 'Dragon Claw' ↔ 'dragon-claw' 매칭용."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# championsbattledata 카탈로그 slug → master.json species nameEn.
#   지역폼 = 접두(alolan-) ↔ 접미(-alola) 표기 차이 / 폼 수식어(-form/-variety/-breed) 표기 차이 /
#   cosmetic·기본폼(외형만, master 에 독립 종 없음)은 base 종 nameEn 으로 흡수.
#   여기 없는 slug 는 정규화 직결(norm(slug) == norm(species nameEn))로 자동 매칭.
#   신규 폼이 카탈로그에 나타나 매칭 실패하면 [skip][WARN] 로그로 드러남 → 여기 한 줄 추가.
SLUG2MASTER = {
    "alolan-raichu": "raichu-alola",
    "alolan-ninetales": "ninetales-alola",
    "hisuian-arcanine": "arcanine-hisui",
    "hisuian-typhlosion": "typhlosion-hisui",
    "hisuian-samurott": "samurott-hisui",
    "hisuian-zoroark": "zoroark-hisui",
    "hisuian-goodra": "goodra-hisui",
    "hisuian-avalugg": "avalugg-hisui",
    "hisuian-decidueye": "decidueye-hisui",
    "galarian-slowbro": "slowbro-galar",
    "galarian-slowking": "slowking-galar",
    "galarian-stunfisk": "stunfisk-galar",
    "paldean-tauros-combat-breed": "tauros-paldea-combat-breed",
    "paldean-tauros-blaze-breed": "tauros-paldea-blaze-breed",
    "paldean-tauros-aqua-breed": "tauros-paldea-aqua-breed",
    "gourgeist-small-variety": "gourgeist-small",
    "gourgeist-large-variety": "gourgeist-large",
    "gourgeist-jumbo-variety": "gourgeist-super",
    "lycanroc-midnight-form": "lycanroc-midnight",
    "lycanroc-dusk-form": "lycanroc-dusk",
    # cosmetic/기본형 — base 종으로 흡수
    "aegislash-shield-forme": "aegislash",
    "basculegion-male": "basculegion",
    "maushold-family-of-four": "maushold",
    "vivillon-fancy-pattern": "vivillon",
    "florges-red-flower": "florges",
    "furfrou-natural-form": "furfrou",
    "palafin-zero-form": "palafin",
}


def season_label(idx):
    """/api/index → 'Season M-4' (pokedb 버전 라벨 형식 유지 — 사이트 '시즌 {season}' 표시 호환).
    dailyDataFolders 마지막 항목('M4/16_07_2026')의 시즌 폴더가 최신. battle 응답 season 은 'Current'라 불용."""
    folders = idx.get("dailyDataFolders") or idx.get("battleDataFolders") or []
    folder = (folders[-1].split("/")[0] if folders else "").strip()
    m = re.match(r"^([A-Za-z]+)(\d+)$", folder)
    return f"Season {m.group(1)}-{m.group(2)}" if m else (folder or "")


def find_species_by_stem(stem, sp_norms):
    """스톤 어간 → 종족 nameEn. 스톤 영문명은 종족명을 줄이거나 변형(Feraligite←Feraligatr,
    Dragoninite←Dragonite, Scraftinite←Scrafty) → 정확 일치 우선, 실패 시 어간을 한 글자씩
    줄여가며(최대 3) 접두 유일 매칭."""
    for cut in range(0, 4):
        s = stem[: len(stem) - cut] if cut else stem
        if len(s) < 4:
            break
        sp_en = sp_norms.get(s)
        if sp_en:
            return sp_en
        cands = {v for k, v in sp_norms.items() if k.startswith(s) and len(k) - len(s) <= 4}
        if len(cands) == 1:
            return next(iter(cands))
    return None


def resolve_item(name, item_by_norm, sp_norms, stone_by_sp):
    """영문 도구명 → master item dict 또는 None.
    ① 정규화 직결(일반 도구·구세대 스톤 gengarite·X/Y charizardite-x 전부 커버).
    ② 메가스톤 폴백: '○○ite[ X/Y]' → 종족 어간 매칭 → nameKo 스톤 인덱스(stone_by_sp).
       인덱스가 nameKo('○○나이트') 기준이라 Z-A 스킴({sp}-mega-stone)·구세대 스킴(gengarite)·
       master nameEn 오표기(druddigonite=드래캄나이트 등)까지 전부 흡수."""
    it = item_by_norm.get(norm(name))
    if it:
        return it
    m = re.match(r"^(.*?)ite( ?[XY])?$", name.strip(), re.I)
    if not m:
        return None
    stem = norm(m.group(1))
    if not stem:
        return None
    sp_en = find_species_by_stem(stem, sp_norms)
    if sp_en is None:
        return None
    xy = m.group(2).strip().upper() if m.group(2) else ""
    return stone_by_sp.get((norm(sp_en), xy)) or item_by_norm.get(norm(f"{sp_en}-mega-stone"))


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    # 1) 매핑 사전: master.json — moves/abilities/items(정규화 nameEn → dict), species(정규화 nameEn → dict).
    with open(os.path.join(HELPER, "master.json"), encoding="utf-8") as f:
        master = json.load(f)
    move_by_norm = {norm(mv.get("nameEn")): mv for mv in master.get("moves", []) if mv.get("nameEn")}
    abil_by_norm = {norm(ab.get("nameEn")): ab for ab in master.get("abilities", []) if ab.get("nameEn")}
    abil_by_en   = {ab.get("nameEn"): ab for ab in master.get("abilities", []) if ab.get("nameEn")}
    item_by_norm = {norm(it.get("nameEn")): it for it in master.get("items", []) if it.get("nameEn")}
    sp_by_norm = {}
    for sp in master.get("species", []):
        if sp.get("nameEn") and not sp.get("isMegaForm"):
            sp_by_norm.setdefault(norm(sp["nameEn"]), sp)
    sp_norms = {k: v["nameEn"] for k, v in sp_by_norm.items()}   # 정규화 → nameEn (스톤 폴백용)
    # 메가스톤 인덱스: (정규화 종족 nameEn, X/Y) → item. nameKo '○○나이트[X/Y]' 의 ○○를 종족 nameKo 로
    #   매칭 — master 스톤 nameEn 이 두 스킴(gengarite / {sp}-mega-stone)이고 일부 오표기까지 있어 ko 가 기준.
    sp_by_ko = {sp.get("nameKo"): sp for sp in master.get("species", [])
                if sp.get("nameKo") and not sp.get("isMegaForm")}
    stone_by_sp = {}
    for it in master.get("items", []):
        mk = re.match(r"^(.+?)나이트([XY])?$", it.get("nameKo") or "")
        if not mk:
            continue
        sp = sp_by_ko.get(mk.group(1))
        if sp:
            stone_by_sp.setdefault((norm(sp["nameEn"]), mk.group(2) or ""), it)
    print(f"[map] master moves: {len(move_by_norm)}  abilities: {len(abil_by_norm)}  items: {len(item_by_norm)}  species: {len(sp_by_norm)}  stones: {len(stone_by_sp)}", file=sys.stderr)

    # 2) 인덱스 — 순위 카탈로그(235종) + 페이지 메타(baseName/isForm) + 시즌 라벨.
    idx = fetch(f"{API}/api/index")
    season = season_label(idx)
    pages_by_slug = {p.get("slug"): p for p in idx.get("pokemonPages", []) if p.get("slug")}
    catalog = [p.get("slug") for p in idx.get("pokemon", []) if p.get("slug")]
    if limit:
        catalog = catalog[:limit]
    print(f"[idx] catalog: {len(catalog)}  season: {season!r}", file=sys.stderr)
    if not limit and len(catalog) < MIN_POKEMON:
        raise SystemExit(f"[abort] 카탈로그 {len(catalog)}종 < {MIN_POKEMON} — 사이트 개편 의심, 기존 json 유지")

    out, slug2key = {}, {}
    miss, miss_ab, miss_it, empty = {}, {}, {}, 0
    for n, slug in enumerate(catalog, 1):
        # 종족 해석: SLUG2MASTER 테이블 → 없으면 정규화 직결(norm(slug) == norm(nameEn)).
        name_en = SLUG2MASTER.get(slug)
        sp = sp_by_norm.get(norm(name_en)) if name_en else sp_by_norm.get(norm(slug))
        if sp is None:
            print(f"[skip][WARN] {slug} — master 매핑 없음(신규 폼? SLUG2MASTER 보강)", file=sys.stderr)
            continue
        name_en = sp["nameEn"]

        try:
            data = fetch(f"{API}/api/battle/{FORMAT}/{slug}")
        except Exception as e:  # noqa: BLE001 — 개별 종족 실패는 건너뜀
            print(f"[skip] {slug} {name_en}: {e}", file=sys.stderr)
            data = {}
        rows = data.get("rows", [])

        # 기술 채용률(내림차순 rank). master 에 없는 이름은 miss 경고만.
        moves = []
        mrows = sorted((r for r in rows if r.get("category") == "move"), key=lambda r: r.get("rank", 9999))
        for r in mrows[:TOP_N]:
            en = (r.get("name") or "").strip()
            mv = move_by_norm.get(norm(en)) if en else None
            if mv is None:
                if en:
                    miss[en] = miss.get(en, 0) + 1
                continue
            moves.append({"en": mv.get("nameEn", ""), "ko": mv.get("nameKo") or mv.get("nameEn", ""),
                          "pct": r.get("percentage_value")})
        if not moves:
            empty += 1  # 기술 통계 없는 종(저사용·시즌 초)도 순위는 유지 — 구버전과 동일 정책.

        # 특성 채용률(내림차순).
        abils = []
        for r in sorted((r for r in rows if r.get("category") == "ability"), key=lambda r: r.get("rank", 9999)):
            en = (r.get("name") or "").strip()
            ab = abil_by_norm.get(norm(en)) if en else None
            if ab is None:
                if en:
                    miss_ab[en] = miss_ab.get(en, 0) + 1
                continue
            abils.append({"en": ab.get("nameEn", ""), "ko": ab.get("nameKo") or ab.get("nameEn", ""),
                          "pct": r.get("percentage_value")})

        # 153차 — 종족 스코프 특성 검증(소스 무관 방어층 유지). 실사고: pokedb 가 그우린차 '대접'을
        #   전국 ID 299(심안)로 송출 → /live "심안 99.1%" 오표시. 해석 결과가 그 종족의 master abilities
        #   목록에 없으면, 아직 안 나온 종족 특성이 정확히 하나일 때만 그걸로 치환(+stderr 로그).
        #   애매하면(잔여 후보 0 또는 2+) 항목 유지 + WARN — 무단 삭제/추측으로 통계를 잃지 않는다.
        sp_ab = [s for s in sp.get("abilities", []) if s]
        if sp_ab:
            have = {a["en"] for a in abils}
            for a in abils:
                if a["en"] in sp_ab:
                    continue
                cand = [s for s in sp_ab if s not in have]
                fix = abil_by_en.get(cand[0]) if len(cand) == 1 else None
                if fix is None:
                    print(f"[abil][WARN] {name_en}: '{a['en']}' 는 종족 특성 {sp_ab} 밖(치환 불가 — 유지)",
                          file=sys.stderr)
                    continue
                print(f"[abil-fix] {name_en}: {a['en']} → {fix.get('nameEn')} (종족 특성 스코프 치환)",
                      file=sys.stderr)
                a["en"] = fix.get("nameEn", "")
                a["ko"] = fix.get("nameKo") or a["en"]
                have.add(a["en"])

        # 도구 채용률(내림차순). 매핑 실패는 miss_it 경고(resolve_item — 메가스톤 폴백 포함).
        items = []
        for r in sorted((r for r in rows if r.get("category") == "held_item"), key=lambda r: r.get("rank", 9999)):
            en = (r.get("name") or "").strip()
            it = resolve_item(en, item_by_norm, sp_norms, stone_by_sp) if en else None
            if it is None:
                if en:
                    miss_it[en] = miss_it.get(en, 0) + 1
                continue
            items.append({"en": it.get("nameEn", ""), "ko": it.get("nameKo") or it.get("nameEn", ""),
                          "pct": r.get("percentage_value")})

        # 종족 사용 순위 = rows 의 column_position(전 행 동일 — 카탈로그 엔티티만 조회하므로 그대로 신뢰).
        rank = None
        for r in rows:
            cp = r.get("column_position")
            if isinstance(cp, int) and cp > 0:
                rank = cp
                break

        page = pages_by_slug.get(slug, {})
        base_sp = sp_by_norm.get(norm(page.get("baseName", "")))
        base_en = (base_sp or {}).get("nameEn") or name_en
        is_form = bool(page.get("isForm", False)) or name_en != base_en
        if name_en in out:  # cosmetic 폼이 base 로 흡수될 때 등 — 먼저 잡힌(상위 순위) 항목 유지.
            print(f"[dup][WARN] {slug} → {name_en} 키 중복(rank {out[name_en].get('rank')} 유지, {rank} 버림)", file=sys.stderr)
            continue
        out[name_en] = {"name": name_en, "base": base_en, "isForm": is_form,
                        "moves": moves, "abils": abils, "items": items, "rank": rank}
        slug2key[slug] = name_en
        if n % 25 == 0:
            print(f"[..] {n}/{len(catalog)}", file=sys.stderr)
        time.sleep(DELAY)

    # 3) 무결성 검증 — 순위 중복/구멍 + 요약표 교차검증 + 파싱 붕괴 안전핀.
    ranks = sorted(v["rank"] for v in out.values() if v.get("rank"))
    dup = sorted({r for r in ranks if ranks.count(r) > 1})
    holes = [r for r in range(1, (max(ranks) if ranks else 0) + 1) if r not in set(ranks)]
    print(f"[rank] 순위 보유: {len(ranks)}/{len(out)}  max={max(ranks) if ranks else 0}", file=sys.stderr)
    if dup:
        print(f"[rank][WARN] 중복 순위: {dup}", file=sys.stderr)
    if holes:
        print(f"[rank][WARN] 빈 순위: {holes}", file=sys.stderr)
    try:
        tbl = fetch(f"{API}/{SUMMARY_PAGE}/", as_json=False)
        trows = re.findall(r'<tr><td>(\d+)</td><td><a href="/pokemon/([^/]+)/">', tbl)
        bad = [(s, int(rk), out[slug2key[s]].get("rank")) for rk, s in trows
               if s in slug2key and out[slug2key[s]].get("rank") != int(rk)]
        if bad:
            print(f"[rank][WARN] 요약표 불일치: {bad}", file=sys.stderr)
        else:
            print(f"[rank] 요약표 교차검증 OK ({len(trows)}행 일치)", file=sys.stderr)
    except Exception as e:  # noqa: BLE001 — 교차검증 실패는 경고만
        print(f"[rank] 요약표 교차검증 실패(무시): {e}", file=sys.stderr)
    if not limit and out and empty / len(out) > MAX_EMPTY_RATIO:
        raise SystemExit(f"[abort] 기술 0개 페이지 {empty}/{len(out)} — 파싱 붕괴 의심, 기존 json 유지")

    # 4) 출력 + 버전(epoch 정수, 단조증가 → 헬퍼가 정수 비교로 갱신 판단).
    version = int(time.time())
    result = {"version": version, "format": FORMAT, "season": season,
              "count": len(out), "pokemon": out}
    os.makedirs(HELPER, exist_ok=True)
    with open(os.path.join(HELPER, OUT_MOVE), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(HELPER, OUT_VER), "w", encoding="utf-8") as f:
        json.dump({"version": version}, f)

    abil_n = sum(1 for v in out.values() if v.get("abils"))
    item_n = sum(1 for v in out.values() if v.get("items"))
    print(f"[done] pokemon: {len(out)}  version: {version}  season: {season!r}  기술없음: {empty}종  특성보유: {abil_n}종  도구보유: {item_n}종", file=sys.stderr)
    if miss:
        print(f"[miss][WARN] master 에 없는 기술명: {sorted(miss)} — master.json moves 보강 필요", file=sys.stderr)
    if miss_ab:
        print(f"[miss][WARN] master 에 없는 특성명: {sorted(miss_ab)} — master.json abilities 보강 필요", file=sys.stderr)
    if miss_it:
        print(f"[miss][WARN] 매핑 실패 도구: {sorted(miss_it)} — resolve_item/master.json items 보강 필요", file=sys.stderr)


if __name__ == "__main__":
    main()
