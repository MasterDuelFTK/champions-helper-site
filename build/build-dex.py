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

def mega_form_key(name_ko):
    if name_ko.endswith("X"): return "megaX"
    if name_ko.endswith("Y"): return "megaY"
    return "mega"

dex = []
need_png = set()
mega_count = 0
for sp in master["species"]:
    if sp.get("isMegaForm") or sp["id"] <= 0:
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

dex.sort(key=lambda e: e["id"])

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

print(f"dex={len(dex)}  mega_forms={mega_count}  png_needed={len(need_png)}  copied={copied}  missing_file={len(missing)}")
if remain:
    print("REMAINING ENGLISH ABILITIES (패치 필요):")
    for k, v in sorted(remain.items()):
        print(f"  [{k}] -> {', '.join(sorted(set(v)))}")
else:
    print("OK: 영어로 남는 특성 없음")
