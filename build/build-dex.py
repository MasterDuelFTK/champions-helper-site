# Champions Helper 사이트 도감 데이터 빌드
# master.json + sprites.json (데스크탑 프로젝트) + ability_patch.json → site/data/dex.json + site/sprites/*.png
#
# 유지보수: 게임 업데이트로 신규 포켓몬/메가 추가 시
#   1) 데스크탑 master.json / sprites.json 갱신 (DataBuilder, rule#4·#8)
#   2) 영어로 남는 특성이 생기면 ability_patch.json 에 'slug': {ko,desc} 한 줄 추가
#   3) 이 스크립트 재실행 → 도감 자동 갱신 (코드 수정 0)
import json, shutil, os, re

SRC  = r"C:\개인\Claude\PokemonChampionsHelper\Pokemon Champions Helper\tools\PCH.DataBuilder\output"
SITE = r"C:\개인\Claude\champions-helper-site"
hangul = re.compile(r'[가-힣]')

with open(os.path.join(SRC, "master.json"), encoding="utf-8") as f:
    master = json.load(f)
with open(os.path.join(SRC, "sprites.json"), encoding="utf-8") as f:
    sprites = json.load(f)
patch_path = os.path.join(SITE, "build", "ability_patch.json")
with open(patch_path, encoding="utf-8") as f:
    PATCH = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
form_patch_path = os.path.join(SITE, "build", "form_patch.json")
with open(form_patch_path, encoding="utf-8") as f:
    FORM_PATCH = {k: v for k, v in json.load(f).items() if not k.startswith("_")}

# master 특성 맵: slug -> {ko, desc}
mabil = {a["nameEn"]: {"ko": a["nameKo"], "desc": a.get("descriptionKo", "")} for a in master["abilities"]}

def resolve_abil(slug):
    """patch 우선 → master(한글일 때) → 폴백(영어 slug)."""
    if slug in PATCH:
        return {"ko": PATCH[slug]["ko"], "desc": PATCH[slug].get("desc", "")}
    a = mabil.get(slug)
    if a and hangul.search(a["ko"]):
        return {"ko": a["ko"], "desc": a["desc"]}
    return {"ko": slug, "desc": ""}   # 여기 오면 patch 누락 → 진단에 잡힘

# sprite: (dexId, formKey) -> iconFile
spr = {(s["dexId"], s["formKey"]): s["iconFile"] for s in sprites["sprites"]}
# dexId -> {formKey: iconFile}  (default 없는 색깔폼/특수폼 폴백용)
byDex = {}
for s in sprites["sprites"]:
    byDex.setdefault(s["dexId"], {})[s["formKey"]] = s["iconFile"]

def base_icon(sid):
    """default sprite 우선. 없으면(플라엣테 등 색깔폼) 비-shiny/비-mega 폼 sprite로 폴백."""
    icon = spr.get((sid, "default"))
    if icon:
        return icon
    forms = byDex.get(sid, {})
    cand = [v for k, v in forms.items() if "shiny" not in k.lower() and "mega" not in k.lower()]
    return cand[0] if cand else None

# 메가폼: base dexId -> [메가 species...]
megas_by_base = {}
for sp in master["species"]:
    if sp.get("isMegaForm"):
        b = sp.get("megaBaseSpeciesId")
        if b:
            megas_by_base.setdefault(b, []).append(sp)

# 독립 배틀폼(master 음수 id, 비메가) → 도감 톱레벨 항목으로 추가.
#   championsbattledata 순위 카탈로그(235)가 이들을 독립 엔티티로 순위 매김(예: 알로라 라이츄 216위
#   vs 칸토 라이츄 5위) → 도감에 없으면 배틀데이터 순위에 구멍. master id → (base 도감번호, sprite formKey).
#   신규 폼 생기면 여기 한 줄 추가(sprites.json 의 formKey 확인).
FORM_SPRITES = {
    -10100: (26,  "alola"),         # raichu-alola
    -10104: (38,  "alola"),         # ninetales-alola
    -10230: (59,  "hisui"),         # arcanine-hisui
    -10165: (80,  "galar"),         # slowbro-galar
    -10233: (157, "hisui"),         # typhlosion-hisui
    -10172: (199, "galar"),         # slowking-galar
    -10236: (503, "hisui"),         # samurott-hisui
    -10239: (571, "hisui"),         # zoroark-hisui
    -10180: (618, "galar"),         # stunfisk-galar
    -10242: (706, "hisui"),         # goodra-hisui
    -10243: (713, "hisui"),         # avalugg-hisui
    -10244: (724, "hisui"),         # decidueye-hisui
    -10250: (128, "paldeaCombat"),  # tauros-paldea-combat-breed
    -10251: (128, "paldeaBlaze"),   # tauros-paldea-blaze-breed
    -10252: (128, "paldeaWater"),   # tauros-paldea-aqua-breed
    -10008: (479, "rotomHeat"),     # rotom-heat
    -10009: (479, "rotomWash"),     # rotom-wash
    -10010: (479, "rotomFrost"),    # rotom-frost
    -10011: (479, "rotomFan"),      # rotom-fan
    -10012: (479, "rotomMow"),      # rotom-mow
    -10025: (678, "female"),        # meowstic-female
    -10248: (902, "female"),        # basculegion-female
    -10030: (711, "pumpkinSmall"),  # gourgeist-small
    -10031: (711, "pumpkinLarge"),  # gourgeist-large
    -10032: (711, "pumpkinSuper"),  # gourgeist-super
    -10126: (745, "lugaMidnight"),  # lycanroc-midnight
    -10152: (745, "lugaDusk"),      # lycanroc-dusk
}

def mega_form_key(name_ko):
    if name_ko.endswith("X"): return "megaX"
    if name_ko.endswith("Y"): return "megaY"
    return "mega"

dex = []
need_png = set()
mega_count = 0
form_added, form_skipped = 0, []
for sp in master["species"]:
    if sp.get("isMegaForm"):
        continue
    if sp["id"] <= 0:
        # 독립 배틀폼 — FORM_SPRITES 매핑이 있는 것만 도감 항목으로(색깔폼 등 미매핑은 제외·리포트).
        fm = FORM_SPRITES.get(sp["id"])
        if not fm:
            form_skipped.append(sp["nameEn"])
            continue
        base_dex, fkey = fm
        ficon = spr.get((base_dex, fkey))
        if not ficon:
            form_skipped.append(f'{sp["nameEn"]}(sprite {base_dex}/{fkey} 없음)')
            continue
        dex.append({
            "id":     sp["id"],
            "baseId": base_dex,           # 표시용 도감번호(#0026 등) + 정렬 그룹
            "ko":     sp["nameKo"],
            "en":     sp["nameEn"],
            "types":  sp["types"],
            "stats":  sp["baseStats"],
            "abil":   [resolve_abil(a) for a in sp.get("abilities", [])],
            "sprite": ficon,
            "mega":   [],
            "forms":  [],
            "formTitle": None,
        })
        need_png.add(ficon)
        form_added += 1
        continue
    sid = sp["id"]
    icon = base_icon(sid)
    if not icon:                      # 챔피언스 미등장(공식 sprite 없음) → 도감 제외
        continue

    megas = []
    for msp in megas_by_base.get(sid, []):
        fk = mega_form_key(msp["nameKo"])
        micon = spr.get((sid, fk)) or spr.get((sid, "mega"))
        megas.append({
            "ko":     msp["nameKo"],
            "types":  msp["types"],
            "stats":  msp["baseStats"],
            "abil":   [resolve_abil(a) for a in msp.get("abilities", [])],
            "sprite": micon,
        })
        if micon:
            need_png.add(micon)
            mega_count += 1

    fp = FORM_PATCH.get(str(sid))
    forms = []
    if fp:
        for fm in fp["forms"]:
            forms.append({
                "ko":     fm["ko"],
                "types":  fm["types"],
                "stats":  fm["stats"],
                "abil":   [resolve_abil(a) for a in fm.get("abilSlug", [])],
                "sprite": fm["sprite"],
            })
            if fm.get("sprite"):
                need_png.add(fm["sprite"])

    dex.append({
        "id":     sid,
        "ko":     sp["nameKo"],
        "en":     sp["nameEn"],
        "types":  sp["types"],
        "stats":  sp["baseStats"],
        "abil":   [resolve_abil(a) for a in sp.get("abilities", [])],
        "sprite": icon,
        "mega":   megas,
        "forms":  forms,
        "formTitle": fp["sectionTitle"] if fp else None,
    })
    need_png.add(icon)

# 정렬: 도감번호 순, 폼은 base 바로 뒤(base 먼저, 폼은 master id 역순=등록순).
dex.sort(key=lambda e: (e.get("baseId", e["id"]), 0 if e["id"] > 0 else 1, -e["id"]))

os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
with open(os.path.join(SITE, "data", "dex.json"), "w", encoding="utf-8") as f:
    json.dump({"count": len(dex), "dex": dex}, f, ensure_ascii=False, separators=(",", ":"))

# sprite 복사
dst = os.path.join(SITE, "sprites")
os.makedirs(dst, exist_ok=True)
src_spr = os.path.join(SRC, "sprites")
copied, missing = 0, []
for fn in need_png:
    s = os.path.join(src_spr, fn)
    if os.path.exists(s):
        shutil.copy2(s, os.path.join(dst, fn)); copied += 1
    else:
        missing.append(fn)

# 진단: 영어로 남는 특성(패치 누락) 리포트
remain = {}
for e in dex:
    pools = [e["abil"]] + [m["abil"] for m in e["mega"]]
    for pool in pools:
        for a in pool:
            if not hangul.search(a["ko"]):
                remain.setdefault(a["ko"], []).append(e["ko"])

print(f"dex={len(dex)}  (독립폼 {form_added} 포함)  mega_forms={mega_count}  png_needed={len(need_png)}  copied={copied}  missing_file={len(missing)}")
if form_skipped:
    print(f"form 제외(미매핑/미보유 {len(form_skipped)}): {', '.join(form_skipped)}")
if remain:
    print("REMAINING ENGLISH ABILITIES (패치 필요):")
    for k, v in sorted(remain.items()):
        print(f"  [{k}] -> {', '.join(sorted(set(v)))}")
else:
    print("OK: 영어로 남는 특성 없음")
