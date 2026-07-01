#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Champions Helper — 상대 기술 사용률(move-usage) 빌드.
  championsbattledata.com API(Singles) → helper-data/move-usage.json

용도: /live "상대" 토글(상대 시점 위력) 모드에서, 상대 포켓몬이 자주 쓰는 기술 상위 N개를
  위력칩으로 보여준다. 영어 기술명 → helper-data/master.json 의 moves(nameEn) 매칭 → 한글명(nameKo).

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


def norm(s):
    """영어 기술명 정규화(영숫자만 소문자). 'Stealth Rock' ↔ 'stealth-rock' 매칭용."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


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

    # 2) 종족 인덱스(메가/지역폼 포함 slug).
    idx = fetch(f"{API}/api/index")
    pages = idx.get("pokemonPages", [])
    if limit:
        pages = pages[:limit]
    print(f"[idx] pokemon pages: {len(pages)}", file=sys.stderr)

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
        rows = [r for r in data.get("rows", []) if r.get("category") == "move"]
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
        if moves:
            out[slug] = {
                "name": p.get("name", slug),
                "base": p.get("baseName", ""),
                "isForm": bool(p.get("isForm", False)),
                "moves": moves,
            }
        if n % 25 == 0:
            print(f"[..] {n}/{len(pages)}", file=sys.stderr)
        time.sleep(DELAY)

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
