#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Champions Helper — 상대 기술 사용률(move-usage) 빌드.
  champs.pokedb.tokyo (싱글 rule=0) → helper-data/move-usage.json

123차 — 소스 교체: championsbattledata.com API(갱신 매우 느림) → champs.pokedb.tokyo 실시간 추종
  (feedback 지시). pokedb 는 서버렌더 HTML 이지만 기술 데이터가 data-move-detail 속성에 JSON 으로
  박혀 있고, 그 move_key 가 전국 기술 ID = master.json moves 의 id 와 완전 일치 → 이름 번역(일↔한)
  없이 ID 직결 매칭(가장 안전). 종족도 URL 의 도감번호-폼번호(0445-00)로 매칭 — 이름 무관.

용도: /live "상대" 토글(상대 시점 위력) 모드에서, 상대 포켓몬이 자주 쓰는 기술 상위 N개를
  위력칩으로 보여준다. + 사이트 도감 상세페이지 "실전 사용 기술" 섹션 / battle-data 순위 페이지.

종족 사용 순위(rank): /pokemon/list?rule=0 (한 페이지 235종, 사용률 내림차순)의
  <div class="pokemon-rank"> 숫자 그대로. 1~235 완전(중복·구멍 검증 후 출력).

출력 스키마(구버전과 동일 — 헬퍼 exe·사이트 빌드 무변경):
  { version, format, season, count, pokemon: { <master nameEn>: {
      name, base, isForm, moves:[{en,ko,pct}], rank } } }
  키 = master.json species nameEn (헬퍼 UsageKeyCandidates·사이트 usage_for 가 이 키로 조회).

자동화(master.json/sprites 와 독립 — 기술 사용률만 따로 갱신):
  .github/workflows/move-usage.yml 가 cron(12h)으로 이 스크립트를 실행 → helper-data/move-usage.json +
  move-usage-version.json 을 커밋·push → GitHub Pages(champions-helper.com/helper-data) 재배포 →
  헬퍼가 켤 때 버전 확인·다운로드(즉시 반영). 개발자 수동 개입 0.

로컬 실행: python build/build-move-usage.py [LIMIT]
  LIMIT(선택) = 처음 N종족만 처리(검증용). 미지정 = 전종족.

pokedb 이용 메모: 프로그램 다운로드 허용(과도한 부하 금지 — DELAY 로 완화, 12h 1회 236 요청).
  앱은 파일을 로컬 캐시해 서빙해야 함 → 정확히 이 구조(빌드 1회 → 우리 호스팅에서 헬퍼가 수신).
"""
import html as _html
import json, os, re, sys, time, urllib.request

REPO   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # build/ 의 상위 = repo 루트
HELPER = os.path.join(REPO, "helper-data")
SITE   = "https://champs.pokedb.tokyo"
RULE   = 0                  # 0 = 싱글 배틀 (포켓몬 챔피언스 헬퍼 대상)
FORMAT = "Singles"          # 스키마 호환 라벨(구버전과 동일)
TOP_N  = 12                 # 위력칩 4개 + 편집 드롭다운(5위~) 여유분 (pokedb 페이지는 상위 10 노출)
UA     = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.8,en;q=0.6",
    "Referer": "https://champs.pokedb.tokyo/",
}

# pokedb 는 클라우드 DC IP 대역을 전면 403(GitHub Actions 러너 실측 — robots.txt 포함 전부).
#   → CI 에선 Cloudflare Worker 릴레이(pch-relay, upstream 고정 + 비밀 헤더) 경유로 fetch.
#   로컬(거주지 IP)은 env 미설정 = 직접 접속. workflow 가 secrets 로 env 2개를 주입한다.
RELAY     = os.environ.get("PCH_FETCH_RELAY", "").rstrip("/")
RELAY_KEY = os.environ.get("PCH_RELAY_KEY", "")
DELAY  = 0.35               # 정중한 호출 간격(초)

# 무인 cron 안전핀 — 사이트 개편 등으로 파싱이 무너지면 옛(정상) json 을 덮지 않고 실패 종료.
MIN_POKEMON = 150           # 정상 = 235종
MAX_EMPTY_RATIO = 0.5       # 기술 0개 페이지가 절반 넘으면 파싱 붕괴로 간주


def fetch_text(url, tries=3):
    headers = dict(UA)
    if RELAY and url.startswith(SITE):
        url = RELAY + url[len(SITE):]
        headers["X-Relay-Key"] = RELAY_KEY
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — best-effort 재시도
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


# pokedb "도감번호-폼번호" → master.json species nameEn (폼번호 00 = 원종, 도감번호=master id 로 자동).
#   전수 검증 2026-07-04 — 29폼 페이지 <title> 일어 표기로 정체 확인(예 0479-04=スピンロトム=rotom-fan).
#   새 폼이 리스트에 나타나면 여기 한 줄 추가(누락 시 [skip][WARN] 로그로 드러남).
FORM2MASTER = {
    "0026-01": "raichu-alola",
    "0038-01": "ninetales-alola",
    "0059-01": "arcanine-hisui",
    "0080-02": "slowbro-galar",            # 01 = 메가야도란(별도 페이지 없음)
    "0128-01": "tauros-paldea-combat-breed",
    "0128-02": "tauros-paldea-blaze-breed",
    "0128-03": "tauros-paldea-aqua-breed",  # ウォーター種
    "0157-01": "typhlosion-hisui",
    "0199-01": "slowking-galar",
    "0479-01": "rotom-heat",
    "0479-02": "rotom-wash",
    "0479-03": "rotom-frost",
    "0479-04": "rotom-fan",                 # スピンロトム
    "0479-05": "rotom-mow",                 # カットロトム
    "0503-01": "samurott-hisui",
    "0571-01": "zoroark-hisui",
    "0618-01": "stunfisk-galar",
    "0666-18": "vivillon",                  # 팬시무늬 = cosmetic → base 종이 순위 대표
    "0670-05": "floette",                   # えいえん(이터널플라워) = master 플라엣테(670) 그 자체
    "0678-01": "meowstic-female",
    "0706-01": "goodra-hisui",
    "0711-01": "gourgeist-small",           # こだま
    "0711-02": "gourgeist-large",           # おおだま
    "0711-03": "gourgeist-super",           # ギガだま
    "0713-01": "avalugg-hisui",
    "0724-01": "decidueye-hisui",
    "0745-01": "lycanroc-midnight",         # まよなか
    "0745-02": "lycanroc-dusk",             # たそがれ
    "0902-01": "basculegion-female",
}


def parse_season(src):
    """리스트 페이지 제목 'シーズンM-3（シングルバトル）' → 'Season M-3' (구 스키마 라벨 호환)."""
    m = re.search(r"シーズン(M-\d+)", src)
    return f"Season {m.group(1)}" if m else ""


def parse_list(src):
    """/pokemon/list — (rank, dex, form) 리스트(사용률 내림차순). 순위는 명시 숫자 파싱."""
    rows = re.findall(
        r'href="/pokemon/show/(\d{4})-(\d{2})\?[^"]*"[^>]*>\s*'
        r'<div class="pokemon-rank[^>]*>\s*(\d+)\s*</div>',
        src)
    return [(int(rk), dex, form) for dex, form, rk in rows]


def parse_moves(src):
    """상세 페이지 data-move-detail JSON blob → [(move_key, rate)] (채용률 내림차순, dedup)."""
    out, seen = [], set()
    for blob in re.findall(r'data-move-detail="([^"]+)"', src):
        try:
            d = json.loads(_html.unescape(blob))
        except Exception:  # noqa: BLE001 — blob 하나 손상은 건너뜀
            continue
        key, rate = d.get("move_key"), d.get("rate")
        if not isinstance(key, int) or key in seen:
            continue
        seen.add(key)
        out.append((d.get("rank", 9999), key, rate))
    out.sort()
    return [(k, r) for _, k, r in out]


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    # 1) 매핑 사전: master.json — moves(id → en/ko), species(id/nameEn).
    with open(os.path.join(HELPER, "master.json"), encoding="utf-8") as f:
        master = json.load(f)
    move_by_id = {mv["id"]: mv for mv in master.get("moves", []) if isinstance(mv.get("id"), int)}
    sp_by_id = {}
    for sp in master.get("species", []):
        if isinstance(sp.get("id"), int) and not sp.get("isMegaForm"):
            sp_by_id.setdefault(sp["id"], sp)
    print(f"[map] master moves: {len(move_by_id)}  species: {len(sp_by_id)}", file=sys.stderr)

    # 2) 사용률 랭킹 리스트(235종, 순위 명시) + 시즌 라벨.
    list_src = fetch_text(f"{SITE}/pokemon/list?rule={RULE}")
    season = parse_season(list_src)
    entries = parse_list(list_src)
    if limit:
        entries = entries[:limit]
    print(f"[idx] list entries: {len(entries)}  season: {season!r}", file=sys.stderr)
    if not limit and len(entries) < MIN_POKEMON:
        raise SystemExit(f"[abort] 리스트 파싱 {len(entries)}종 < {MIN_POKEMON} — 사이트 개편 의심, 기존 json 유지")

    out, miss, empty = {}, {}, 0
    for n, (rank, dex, form) in enumerate(entries, 1):
        # 종족 해석: 폼번호 00 = master id==도감번호 원종 / 그 외 = FORM2MASTER 테이블.
        if form == "00":
            sp = sp_by_id.get(int(dex))
            name_en = sp.get("nameEn") if sp else None
        else:
            name_en = FORM2MASTER.get(f"{dex}-{form}")
        if not name_en:
            print(f"[skip][WARN] {dex}-{form} (rank {rank}) — master 매핑 없음(신규 폼? FORM2MASTER 보강)", file=sys.stderr)
            continue

        try:
            page = fetch_text(f"{SITE}/pokemon/show/{dex}-{form}?rule={RULE}")
        except Exception as e:  # noqa: BLE001 — 개별 종족 실패는 건너뜀(순위만이라도 유지)
            print(f"[skip] {dex}-{form} {name_en}: {e}", file=sys.stderr)
            page = ""

        moves = []
        for key, rate in parse_moves(page)[:TOP_N]:
            mv = move_by_id.get(key)
            if mv is None:
                miss[key] = miss.get(key, 0) + 1
                continue
            moves.append({"en": mv.get("nameEn", ""), "ko": mv.get("nameKo") or mv.get("nameEn", ""),
                          "pct": rate})
        if not moves:
            empty += 1  # 기술 통계 없는 종(저사용·시즌 초)도 순위는 유지 — 구버전과 동일 정책.

        base_sp = sp_by_id.get(int(dex))
        base_en = (base_sp or {}).get("nameEn") or name_en
        if name_en in out:  # cosmetic 폼이 base 로 흡수될 때 등 — 먼저 잡힌(상위 순위) 항목 유지.
            print(f"[dup][WARN] {dex}-{form} → {name_en} 키 중복(rank {out[name_en]['rank']} 유지, {rank} 버림)", file=sys.stderr)
            continue
        out[name_en] = {"name": name_en, "base": base_en,
                        "isForm": form != "00", "moves": moves, "rank": rank}
        if n % 25 == 0:
            print(f"[..] {n}/{len(entries)}", file=sys.stderr)
        time.sleep(DELAY)

    # 3) 무결성 검증 — 순위 중복/구멍 + 파싱 붕괴 안전핀.
    ranks = sorted(v["rank"] for v in out.values())
    dup = sorted({r for r in ranks if ranks.count(r) > 1})
    holes = [r for r in range(1, (max(ranks) if ranks else 0) + 1) if r not in set(ranks)]
    if dup:
        print(f"[rank][WARN] 중복 순위: {dup}", file=sys.stderr)
    if holes:
        print(f"[rank][WARN] 빈 순위: {holes}", file=sys.stderr)
    if not limit and out and empty / len(out) > MAX_EMPTY_RATIO:
        raise SystemExit(f"[abort] 기술 0개 페이지 {empty}/{len(out)} — 파싱 붕괴 의심, 기존 json 유지")

    # 4) 출력 + 버전(epoch 정수, 단조증가 → 헬퍼가 정수 비교로 갱신 판단).
    version = int(time.time())
    result = {"version": version, "format": FORMAT, "season": season,
              "count": len(out), "pokemon": out}
    os.makedirs(HELPER, exist_ok=True)
    with open(os.path.join(HELPER, "move-usage.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(HELPER, "move-usage-version.json"), "w", encoding="utf-8") as f:
        json.dump({"version": version}, f)

    print(f"[done] pokemon: {len(out)}  version: {version}  season: {season!r}  기술없음: {empty}종", file=sys.stderr)
    if miss:
        print(f"[miss][WARN] master 에 없는 move_key: {sorted(miss)} — master.json moves 보강 필요", file=sys.stderr)


if __name__ == "__main__":
    main()
