# 진단: 도감 186종의 영어(미번역) 특성·무설명 특성 + 메가 종족 구조
import json, os, re

SRC  = r"C:\개인\Claude\PokemonChampionsHelper\Pokemon Champions Helper\tools\PCH.DataBuilder\output"
SITE = r"C:\개인\Claude\champions-helper-site"
master  = json.load(open(os.path.join(SRC, "master.json"), encoding="utf-8"))
sprites = json.load(open(os.path.join(SRC, "sprites.json"), encoding="utf-8"))
dex     = json.load(open(os.path.join(SITE, "data", "dex.json"), encoding="utf-8"))["dex"]
hangul = re.compile(r'[가-힣]')

print("=== 1. 영어(미번역) 특성 — 도감 186종 ===")
eng = {}
nodesc = {}
for e in dex:
    for a in e["abil"]:
        if not hangul.search(a["ko"]):
            eng.setdefault(a["ko"], []).append(e["ko"])
        elif not a["desc"]:
            nodesc.setdefault(a["ko"], set()).add(e["ko"])
for k, v in sorted(eng.items()):
    print(f"  [{k}] -> {', '.join(v)}")
print(f"  => 영어특성 종류 = {len(eng)}")

print("=== 2. 한글명 있으나 설명 빈 특성 ===")
for k, v in sorted(nodesc.items()):
    print(f"  [{k}] ({len(v)}) ex: {list(v)[:3]}")
print(f"  => 무설명 종류 = {len(nodesc)}")

print("=== 3. 메가 종족 (isMegaForm=true) ===")
sprByDex = {}
for s in sprites["sprites"]:
    sprByDex.setdefault(s["dexId"], {})[s["formKey"]] = s["iconFile"]
dexIds = {e["id"] for e in dex}
megas = [sp for sp in master["species"] if sp.get("isMegaForm")]
print(f"  메가 종족 수 = {len(megas)}")
for sp in sorted(megas, key=lambda x: (x.get("megaBaseSpeciesId") or 0)):
    base = sp.get("megaBaseSpeciesId")
    forms = sprByDex.get(base, {}) if base else {}
    megakeys = [k for k in forms if "mega" in k.lower() and "shiny" not in k.lower()]
    in_dex = "OK" if base in dexIds else "BASE_NOT_IN_DEX"
    abilstr = ",".join(sp.get("abilities", []))
    print(f"  base={base}[{in_dex}] {sp['nameKo']}  abil=[{abilstr}]  spriteForms={megakeys}")
