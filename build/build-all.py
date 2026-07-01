# Champions Helper 사이트 데이터 통합 빌드 (87차)
#
# 포켓몬/메가/기술을 데스크탑 master.json + sprites.json (SSOT)에 추가한 뒤
# 이 스크립트 하나만 실행하면 사이트 도감(dex.json) + 계산기(moves.json) + sprite 복사가 한 번에 끝난다.
#   - build-dex.py  : master+sprites → site/data/dex.json + site/sprites/*.png + 영어특성 진단
#   - build-calc.py : master.moves  → site/data/moves.json
# 종족값/타입/특성은 dex.json을 재사용하므로 계산기와 이중관리 없음.
#
# 실행:  python build/build-all.py            (생성만)
#        python build/build-all.py --check    (생성 후 누락 png / 영어특성 잔여를 비정상 종료코드로 보고)
#
# ★자동화 안 되는 잔여 단계(절차서 ADD-POKEMON.md 참고):
#   1) master.json / sprites.json 입력 자체(외부 데이터)         — 이 스크립트 이전
#   2) (신규 공격기 flags) patch_move_flags.py --apply           — 이 스크립트 이전
#   3) 사이트 배포: git push origin dev  →  git push origin dev:main
#   4) /guide/mega-evolution 메가가이드(현재 하드코딩)           — (c) 동적화 전까지 수동
import subprocess, sys, os

# 부모 출력도 utf-8(Windows 콘솔 cp949에서 한글/em-dash 인코딩 에러 방지).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = "--check" in sys.argv

def run(name):
    print(f"\n=== {name} ===")
    # child도 utf-8로 출력하게 강제(Windows 콘솔 cp949로 나가면 부모 디코드가 깨짐).
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(HERE, name)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    sys.stdout.write(r.stdout or "")
    if (r.stderr or "").strip():
        sys.stderr.write(r.stderr)
    if r.returncode != 0:
        print(f"!! {name} 실패 (exit {r.returncode})")
        sys.exit(r.returncode)
    return r.stdout or ""

out_dex  = run("build-dex.py")
out_calc = run("build-calc.py")
out_mon  = run("build-mon-pages.py")   # dex.json → pokedex/<en>/ 상세페이지 + 인덱스 정적목록 + sitemap

print("\n" + "=" * 56)
print("OK — site/data/{dex,moves}.json + site/sprites + pokedex/<en>/ 상세페이지 + sitemap 갱신 완료.")
print("다음: 검토 후  git push origin dev  &&  git push origin dev:main  로 배포.")
print("      (메가가이드 /guide/mega-evolution 는 아직 하드코딩 — 수동 반영 필요.)")

if CHECK:
    problems = []
    # build-dex.py 진단 줄 파싱: "... missing_file=N" / "REMAINING ENGLISH ABILITIES"
    for line in out_dex.splitlines():
        if "missing_file=" in line:
            n = int(line.split("missing_file=")[1].split()[0])
            if n: problems.append(f"sprite 누락 {n}개 (sprites.json은 등록됐는데 png 파일 없음)")
    if "REMAINING ENGLISH ABILITIES" in out_dex:
        problems.append("영어로 남는 특성 있음 → ability_patch.json 보강 필요")
    if problems:
        print("\n--check 실패:")
        for p in problems: print("  - " + p)
        sys.exit(1)
    print("\n--check 통과: 누락 png 0, 영어특성 0.")
