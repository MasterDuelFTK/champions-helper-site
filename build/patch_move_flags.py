# master.json moves 의 비어있는 flags 를 Pokémon Showdown 데이터로 채운다.
# 데스크탑 앱(JsonMasterDataProvider.ParseFlags, Enum.TryParse ignoreCase)과 웹(build-calc.py)이
# 같은 master.json 을 쓰므로, 여기 한 번 채우면 양쪽 모두 flag 기반 특성(철주먹·거센턱 등)이 작동한다.
#
# 사용: python patch_move_flags.py            # dry-run (커버리지만 출력)
#       python patch_move_flags.py --apply    # master.json 실제 수정 (백업 .pre-flags.bak)
import json, re, os, sys, shutil

SRC  = r"C:\개인\Claude\PokemonChampionsHelper\Pokemon Champions Helper\tools\PCH.DataBuilder\output"
HERE = os.path.dirname(__file__)
APPLY = "--apply" in sys.argv

master_path = os.path.join(SRC, "master.json")
# 패치 전 원본 백업(최초 1회) — apply 전에 raw 파일을 복사해야 정확.
if APPLY:
    bak = master_path + ".pre-flags.bak"
    if not os.path.exists(bak):
        shutil.copy2(master_path, bak)
        print("backup ->", bak)

with open(master_path, encoding="utf-8") as f:
    master = json.load(f)
with open(os.path.join(HERE, "showdown_moves.json"), encoding="utf-8") as f:
    show = json.load(f)

# Showdown flag 키 → 데스크탑 MoveFlags enum 이름 (ParseFlags 가 ignoreCase 로 매칭)
FLAGMAP = { "contact":"Contact", "punch":"Punch", "bite":"Bite", "pulse":"Pulse",
    "sound":"Sound", "bullet":"Bullet", "powder":"Powder", "slicing":"Slicing",
    "wind":"Wind", "recoil":"Recoil" }

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

# showdown 은 key 가 정규화 id. name 으로도 색인(폴백).
by_name = { norm(v.get("name","")): v for v in show.values() }

matched, miss = 0, []
for mv in master["moves"]:
    key = norm(mv.get("nameEn",""))
    s = show.get(key) or by_name.get(key)
    if not s:
        miss.append(mv.get("nameEn",""))
        continue
    fl = []
    sf = s.get("flags", {}) or {}
    for k, name in FLAGMAP.items():
        if sf.get(k):
            fl.append(name)
    # 부가효과(상대 대상) 보유 → Secondary (우격다짐 트리거). self-boost 는 showdown self 필드라 제외됨.
    if s.get("secondary") or s.get("secondaries"):
        if "Secondary" not in fl:
            fl.append("Secondary")
    mv["flags"] = fl
    matched += 1

total = len(master["moves"])
print(f"moves={total}  matched={matched}  missing={len(miss)}")
# flag 통계
from collections import Counter
cnt = Counter()
for mv in master["moves"]:
    for fnm in mv.get("flags", []):
        cnt[fnm] += 1
print("flag counts:", dict(sorted(cnt.items())))
if miss:
    print("UNMATCHED (showdown 에 없음, flags=[] 유지):", ", ".join(sorted(set(m for m in miss if m))[:40]))

if APPLY:
    # master.json 은 들여쓰기 2칸 포맷 유지(기존 파일과 동일 스타일).
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)
    print("APPLIED -> master.json")
else:
    print("(dry-run) --apply 로 실제 적용")
