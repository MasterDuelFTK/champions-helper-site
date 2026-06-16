# 진단: default sprite는 없지만 폼 sprite(form01..)는 있는 종족 = 도감에서 누락된 후보
import json, os

SRC = r"C:\개인\Claude\PokemonChampionsHelper\Pokemon Champions Helper\tools\PCH.DataBuilder\output"
sprites = json.load(open(os.path.join(SRC, "sprites.json"), encoding="utf-8"))
master  = json.load(open(os.path.join(SRC, "master.json"), encoding="utf-8"))

byDex = {}
for s in sprites["sprites"]:
    byDex.setdefault(s["dexId"], {})[s["formKey"]] = s["iconFile"]

masterBase = {sp["id"]: sp for sp in master["species"] if not sp.get("isMegaForm") and sp["id"] > 0}

print("=== 670 (플라엣테) 모든 sprite formKey ===")
for k, v in byDex.get(670, {}).items():
    print(f"  {k} -> {v}")

print("=== default 없지만 base형(비-shiny/비-mega) form sprite 있는 종족 ===")
hit = 0
for did in sorted(byDex):
    forms = byDex[did]
    if "default" in forms:
        continue
    base_forms = [k for k in forms if "shiny" not in k.lower() and "mega" not in k.lower()]
    if not base_forms:
        continue
    hit += 1
    nm = masterBase[did]["nameKo"] if did in masterBase else "(master base 없음)"
    print(f"  dex={did} {nm}  base_forms={base_forms}")
print(f"=> 누락 후보 종족 수 = {hit}")
