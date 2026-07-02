#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Champions Helper — 상대 기술 사용률(move-usage) 빌드.
  championsbattledata.com API(Singles) → helper-data/move-usage.json

용도: /live "상대" 토글(상대 시점 위력) 모드에서, 상대 포켓몬이 자주 쓰는 기술 상위 N개를
  위력칩으로 보여준다. 영어 기술명 → helper-data/master.json 의 moves(nameEn) 매칭 → 한글명(nameKo).

종족 사용 순위(rank): /api/battle/Singles/{slug} rows 의 column_position = 그 엔티티의 싱글 순위(1~235).
  ★개별 HTML 페이지의 "Singles rank" 셀은 지역폼 짝(칸토/알로라 라이츄·나인테일 등)에서 서로 값이 뒤섞이는
  소스 결함이 있어 쓰지 않는다. 순위는 /api/index 의 pokemon(=순위 카탈로그 235종) 소속 slug 에만 부여
  (메가/외형폼 페이지는 base 순위가 복제되어 있어 부여 시 중복 순위가 생김).

자동화(master.json/sprites 와 독립 — 기술 사용률만 따로 갱신):
  .github/workflows/move-usage.yml 가 cron(12h)으로 이 스크립트를 실행 → helper-data/move-usage.json +
  move-usage-version.json 을 커밋·push → GitHub Pages(champions-helper.com/helper-data) 재배포 →
  헬퍼가 켤 때 버전 확인·다운로드(즉시 반영). 개발자 수동 개입 0.

로컬 실행: python build/build-move-usage.py [LIMIT]
  LIMIT(선택) = 처음 N종족만 처리(검증용). 미지정 = 전종족.

API 메모: championsbattledata 는 기본 urllib User-Agent 를 403 으로 막는다 → 브라우저 UA 필수.
"""
import json, os, re, sys, time, urllib.request

REPO   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # build/ 의 상위 = repo 루트
HELPER = os.path.join(REPO, "helper-data")
API    = "https://championsbattledata.com"
FORMAT = "Singles"          # 포켓몬 챔피언스 = 싱글 배틀
TOP_N  = 12                 # 위력칩 4개 + 편집 드롭다운(5위~) 여유분
UA     = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PCH-move-usage/1.0"}
DELAY  = 0.25               # 정중한 호출 간격(초)


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 — best-effort 재시도
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def fetch_text(url, tries=3):
    """HTML 페이지 텍스트(종족 사용 순위 파싱용)."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.0 * (i + 1))
    raise last


def norm(s):
    """영어 기술명 정규화(영숫자만 소문자). 'Stealth Rock' ↔ 'stealth-rock' 매칭용."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


# championsbattledata slug → master.json nameEn (사이트 도감 en). 도감 상세페이지·헬퍼가
#   master nameEn 으로도 조회할 수 있게 같은 항목을 별칭 키로 재등록한다.
#   지역폼 = 접두(alolan-) ↔ 접미(-alola) 표기 차이. cosmetic(외형만, master 에 독립 종 없음)은
#   base 종 nameEn 으로 붙인다(도감 base 페이지가 그 순위를 대표).
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
    "vivillon-fancy-pattern": "vivillon",
    "florges-red-flower": "florges",
    "furfrou-natural-form": "furfrou",
    "palafin-zero-form": "palafin",
}


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    # 1) 매핑 사전: master.json moves(nameEn → nameKo). 변화기 포함 전체.
    with open(os.path.join(HELPER, "master.json"), encoding="utf-8") as f:
        master = json.load(f)
    en2ko = {}
    for mv in master.get("moves", []):
        en = mv.get("nameEn", "")
        if en:
            en2ko[norm(en)] = mv.get("nameKo", "") or en
    print(f"[map] master moves: {len(en2ko)}", file=sys.stderr)

    # 2) 종족 인덱스(메가/지역폼 포함 slug) + 순위 카탈로그(235종 — 순위를 갖는 배틀 엔티티 전체).
    idx = fetch(f"{API}/api/index")
    pages = idx.get("pokemonPages", [])
    catalog = {p.get("slug") for p in idx.get("pokemon", []) if p.get("slug")}
    if limit:
        pages = pages[:limit]
    print(f"[idx] pokemon pages: {len(pages)}  catalog(순위): {len(catalog)}", file=sys.stderr)

    out, miss, season = {}, {}, ""
    for n, p in enumerate(pages, 1):
        slug = p.get("slug")
        if not slug:
            continue
        try:
            data = fetch(f"{API}/api/battle/{FORMAT}/{slug}")
        except Exception as e:  # noqa: BLE001 — 개별 종족 실패는 건너뜀
            print(f"[skip] {slug}: {e}", file=sys.stderr)
            continue
        season = season or data.get("season", "")
        allrows = data.get("rows", [])
        rows = [r for r in allrows if r.get("category") == "move"]
        rows.sort(key=lambda r: r.get("rank", 9999))
        moves = []
        for r in rows[:TOP_N]:
            en = (r.get("name") or "").strip()
            if not en:
                continue
            ko = en2ko.get(norm(en))
            if not ko:
                miss[en] = miss.get(en, 0) + 1
                ko = en  # 매핑 실패 시 영어명 노출(드롭다운에서 사용자가 정정 가능)
            moves.append({"en": en, "ko": ko, "pct": r.get("percentage_value")})
        # 종족 사용 순위(싱글) = rows 의 column_position(전 행 동일). 카탈로그 소속 slug 에만 부여
        #   — 메가/외형폼 페이지에도 base 순위가 복제돼 있어 전부 부여하면 중복 순위가 생긴다.
        rank = None
        if slug in catalog:
            for r in allrows:
                cp = r.get("column_position")
                if isinstance(cp, int) and cp > 0:
                    rank = cp
                    break
        # 기술 통계 없는 종(메타몽=변신뿐)도 순위가 있으면 유지 — 드롭하면 순위에 구멍(63위 등).
        if moves or rank is not None:
            entry = {
                "name": p.get("name", slug),
                "base": p.get("baseName", ""),
                "isForm": bool(p.get("isForm", False)),
                "moves": moves,
            }
            if rank is not None:
                entry["rank"] = rank
            out[slug] = entry
        if n % 25 == 0:
            print(f"[..] {n}/{len(pages)}", file=sys.stderr)
        time.sleep(DELAY)

    # 2.4) master nameEn 별칭: 지역폼 등 championsbattledata slug ≠ master nameEn 인 항목을
    #   master 표기(도감 en) 키로도 등록 — 도감 상세페이지·헬퍼가 폼별 데이터(순위 포함)를 정확히 조회.
    #   대상 키가 이미 있으면(예: 순위 카탈로그 엔티티는 vivillon-fancy-pattern 인데 페이지는 vivillon 도 존재)
    #   순위만 이식 — 기술 통계는 기존(base 페이지) 것 유지.
    en_alias, en_rank = 0, 0
    for slug, men in SLUG2MASTER.items():
        src = out.get(slug)
        if not src:
            continue
        tgt = out.get(men)
        if tgt is None:
            out[men] = src
            en_alias += 1
        elif src.get("rank") and not tgt.get("rank"):
            tgt["rank"] = src["rank"]
            en_rank += 1
    print(f"[alias] master nameEn 별칭 추가: {en_alias}  순위 이식: {en_rank}", file=sys.stderr)

    # 2.5) base 별칭: 외형/배틀/성별폼만 있고 base 키가 없는 종족(알크레미 색·캐스트폼·꽃·트림·비비용 무늬·
    #   메가·킬가르도 등)을, 헬퍼가 base 종족명(master nameEn)으로 조회할 수 있도록 base nameEn(정규화) 키로도 등록.
    #   isForm=false(기본형) 우선, 없으면 첫 폼(외형/성별폼은 기술 배치가 base와 동일 → 어느 폼이든 무방).
    alias = {}
    for slug, data in out.items():
        bk = norm(data["base"])
        if not bk or bk in out:
            continue
        if bk not in alias or (not data["isForm"] and alias[bk]["isForm"]):
            alias[bk] = data
    out.update(alias)
    print(f"[alias] base 별칭 추가: {len(alias)}", file=sys.stderr)

    # 2.6) 순위 검증 — column_position 이 소스 그대로의 순위이므로 별도 보정 없이 완전성만 확인.
    #   요약표(top 50)와 교차검증: 불일치·구멍·중복이 있으면 경고(출시 전 사람이 확인).
    ranks = sorted(v["rank"] for k, v in out.items() if v.get("rank") and k in catalog)
    dup = sorted({r for r in ranks if ranks.count(r) > 1})
    holes = [r for r in range(1, (max(ranks) if ranks else 0) + 1) if r not in set(ranks)]
    print(f"[rank] 카탈로그 순위 보유: {len(ranks)}/{len(catalog)}  max={max(ranks) if ranks else 0}", file=sys.stderr)
    if dup:
        print(f"[rank][WARN] 중복 순위: {dup}", file=sys.stderr)
    if holes:
        print(f"[rank][WARN] 빈 순위: {holes}", file=sys.stderr)
    try:
        tbl = fetch_text(f"{API}/pokemon-champions-singles-usage/")
        trows = re.findall(r'<tr><td>(\d+)</td><td><a href="/pokemon/([^/]+)/">', tbl)
        bad = [(s, int(rk), out.get(s, {}).get("rank")) for rk, s in trows
               if s in out and out[s].get("rank") != int(rk)]
        if bad:
            print(f"[rank][WARN] 요약표 불일치: {bad}", file=sys.stderr)
        else:
            print(f"[rank] 요약표 교차검증 OK ({len(trows)}행 일치)", file=sys.stderr)
    except Exception as e:  # noqa: BLE001 — 교차검증 실패는 경고만
        print(f"[rank] 요약표 교차검증 실패(무시): {e}", file=sys.stderr)

    # 3) 출력 + 버전(epoch 정수, 단조증가 → 헬퍼가 정수 비교로 갱신 판단).
    version = int(time.time())
    result = {"version": version, "format": FORMAT, "season": season,
              "count": len(out), "pokemon": out}
    os.makedirs(HELPER, exist_ok=True)
    with open(os.path.join(HELPER, "move-usage.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(HELPER, "move-usage-version.json"), "w", encoding="utf-8") as f:
        json.dump({"version": version}, f)

    print(f"[done] pokemon: {len(out)}  version: {version}  season: {season!r}", file=sys.stderr)
    if miss:
        top = sorted(miss.items(), key=lambda kv: -kv[1])[:30]
        print(f"[miss] unmapped: {len(miss)} distinct (top: {top})", file=sys.stderr)


if __name__ == "__main__":
    main()
