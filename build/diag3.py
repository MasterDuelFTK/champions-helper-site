# 킬가르도(681) sprite formKey / 종족값 / 스탠스체인지 한글 확인
import json, os
SRC = r"C:\개인\Claude\PokemonChampionsHelper\Pokemon Champions Helper\tools\PCH.DataBuilder\output"
sprites = json.load(open(os.path.join(SRC, "sprites.json"), encoding="utf-8"))
master  = json.load(open(os.path.join(SRC, "master.json"), encoding="utf-8"))

print("=== 681 sprites ===")
for s in sprites["sprites"]:
    if s["dexId"] == 681:
        print(f"  {s['formKey']} -> {s['iconFile']}  ({s.get('nameKo')})")

sp = [x for x in master["species"] if x["id"] == 681]
if sp:
    sp = sp[0]
    print("=== 681 master ===")
    print(f"  {sp['nameKo']} types={sp['types']} stats={sp['baseStats']} abil={sp['abilities']}")

ab = [a for a in master["abilities"] if a["nameEn"] == "stance-change"]
print("=== stance-change ===")
print(f"  {ab[0] if ab else 'NONE'}")
