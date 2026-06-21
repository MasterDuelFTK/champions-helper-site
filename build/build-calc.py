# Champions Helper 계산기용 기술 데이터 빌드
# master.json(데스크탑 프로젝트) → site/data/moves.json
#
# 유지보수: 게임 업데이트로 기술 추가/변경 시 데스크탑 master.json 갱신 후 이 스크립트 재실행.
# 종족값/타입/특성은 dex.json(build-dex.py)을 그대로 재사용하므로 계산기는 데이터 이중관리가 없다.
import json, os, re

SRC  = r"C:\개인\Claude\PokemonChampionsHelper\Pokemon Champions Helper\tools\PCH.DataBuilder\output"
SITE = r"C:\개인\Claude\champions-helper-site"
hangul = re.compile(r'[가-힣]')

with open(os.path.join(SRC, "master.json"), encoding="utf-8") as f:
    master = json.load(f)

moves = []
skipped_en = 0
for mv in master["moves"]:
    if mv.get("category") == "STATUS":      # 변화기는 데미지 0 → 계산기 제외
        continue
    ko = mv.get("nameKo", "")
    if not hangul.search(ko):               # 한글명 없는 기술 제외(검색 불가)
        skipped_en += 1
        continue
    moves.append({
        "ko":   ko,
        "en":   mv.get("nameEn", ""),
        "type": mv["type"],                 # 영문 대문자 enum (NORMAL, FIRE, ...)
        "cat":  mv["category"],             # PHYSICAL / SPECIAL
        "pow":  mv.get("power", 0),
        "acc":  mv.get("accuracy", 0),
        "flags": mv.get("flags", []),       # Contact/Punch/Bite/... (patch_move_flags.py 로 채움)
    })

moves.sort(key=lambda x: x["ko"])

os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
out = os.path.join(SITE, "data", "moves.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"count": len(moves), "moves": moves}, f, ensure_ascii=False, separators=(",", ":"))

print(f"moves={len(moves)}  skipped_no_hangul={skipped_en}  -> {out}")
