/* Champions Helper — 타입표 (표시·상성 판정 전용, DOM 비의존)
 *
 * ★★데미지 계산은 여기 없다(199차 제거). 계산 규칙은 **C# 엔진 한 벌**이고 브라우저에서는
 *   wasm으로 돈다(`/calc/pch-wasm.js`). 종전엔 이 파일에 데미지 계산이 JS로 한 벌 더 포팅돼 있어
 *   규칙 사본이 두 벌이었고, 실제로 헬퍼보다 20건 가까이 뒤처져 있었다(광역기 ×0.75·급소의 랭크 무시·
 *   연타/무게/스피드 위력기·프리즈드라이·틀깨기·반감열매 전무). **여기에 계산을 다시 적지 말 것.**
 *
 * 남은 것 = 타입 이름·색·상성표뿐이다. 쓰는 곳 = `builder/recommend.js`(파티 추천의 약점·커버리지
 * 분석), `board/board.js`(타입 칩 표시). 둘 다 표시/휴리스틱이라 데미지 공식과 무관하다.
 */
"use strict";

/* ── 타입 상수 (도감과 동일) ─────────────────────────── */
const TYPE_KO = { NORMAL:"노말", FIRE:"불꽃", WATER:"물", ELECTRIC:"전기", GRASS:"풀", ICE:"얼음",
  FIGHTING:"격투", POISON:"독", GROUND:"땅", FLYING:"비행", PSYCHIC:"에스퍼", BUG:"벌레",
  ROCK:"바위", GHOST:"고스트", DRAGON:"드래곤", DARK:"악", STEEL:"강철", FAIRY:"페어리" };
const TYPE_COLOR = { NORMAL:"#A8A77A", FIRE:"#EE8130", WATER:"#6390F0", ELECTRIC:"#F7D02C", GRASS:"#7AC74C",
  ICE:"#96D9D6", FIGHTING:"#C22E28", POISON:"#A33EA1", GROUND:"#E2BF65", FLYING:"#A98FF3", PSYCHIC:"#F95587",
  BUG:"#A6B91A", ROCK:"#B6A136", GHOST:"#735797", DRAGON:"#6F35FC", DARK:"#705746", STEEL:"#B7B7CE", FAIRY:"#D685AD" };

/* ── 타입 상성표 (TypeChart.cs 포팅, 9세대) ───────────── */
const TYPE_CHART = (() => {
  const keys = Object.keys(TYPE_KO);
  const c = {}; keys.forEach(a => { c[a] = {}; keys.forEach(d => c[a][d] = 1); });
  const S = (a, d, v) => { c[a][d] = v; };
  S("NORMAL","ROCK",.5); S("NORMAL","STEEL",.5); S("NORMAL","GHOST",0);
  S("FIRE","FIRE",.5); S("FIRE","WATER",.5); S("FIRE","GRASS",2); S("FIRE","ICE",2); S("FIRE","BUG",2); S("FIRE","ROCK",.5); S("FIRE","DRAGON",.5); S("FIRE","STEEL",2);
  S("WATER","FIRE",2); S("WATER","WATER",.5); S("WATER","GRASS",.5); S("WATER","GROUND",2); S("WATER","ROCK",2); S("WATER","DRAGON",.5);
  S("ELECTRIC","WATER",2); S("ELECTRIC","ELECTRIC",.5); S("ELECTRIC","GRASS",.5); S("ELECTRIC","GROUND",0); S("ELECTRIC","FLYING",2); S("ELECTRIC","DRAGON",.5);
  S("GRASS","FIRE",.5); S("GRASS","WATER",2); S("GRASS","GRASS",.5); S("GRASS","POISON",.5); S("GRASS","GROUND",2); S("GRASS","FLYING",.5); S("GRASS","BUG",.5); S("GRASS","ROCK",2); S("GRASS","DRAGON",.5); S("GRASS","STEEL",.5);
  S("ICE","FIRE",.5); S("ICE","WATER",.5); S("ICE","GRASS",2); S("ICE","ICE",.5); S("ICE","GROUND",2); S("ICE","FLYING",2); S("ICE","DRAGON",2); S("ICE","STEEL",.5);
  S("FIGHTING","NORMAL",2); S("FIGHTING","ICE",2); S("FIGHTING","POISON",.5); S("FIGHTING","FLYING",.5); S("FIGHTING","PSYCHIC",.5); S("FIGHTING","BUG",.5); S("FIGHTING","ROCK",2); S("FIGHTING","GHOST",0); S("FIGHTING","DARK",2); S("FIGHTING","STEEL",2); S("FIGHTING","FAIRY",.5);
  S("POISON","GRASS",2); S("POISON","POISON",.5); S("POISON","GROUND",.5); S("POISON","ROCK",.5); S("POISON","GHOST",.5); S("POISON","STEEL",0); S("POISON","FAIRY",2);
  S("GROUND","FIRE",2); S("GROUND","ELECTRIC",2); S("GROUND","GRASS",.5); S("GROUND","POISON",2); S("GROUND","FLYING",0); S("GROUND","BUG",.5); S("GROUND","ROCK",2); S("GROUND","STEEL",2);
  S("FLYING","ELECTRIC",.5); S("FLYING","GRASS",2); S("FLYING","FIGHTING",2); S("FLYING","BUG",2); S("FLYING","ROCK",.5); S("FLYING","STEEL",.5);
  S("PSYCHIC","FIGHTING",2); S("PSYCHIC","POISON",2); S("PSYCHIC","PSYCHIC",.5); S("PSYCHIC","DARK",0); S("PSYCHIC","STEEL",.5);
  S("BUG","FIRE",.5); S("BUG","GRASS",2); S("BUG","FIGHTING",.5); S("BUG","POISON",.5); S("BUG","FLYING",.5); S("BUG","PSYCHIC",2); S("BUG","GHOST",.5); S("BUG","DARK",2); S("BUG","STEEL",.5); S("BUG","FAIRY",.5);
  S("ROCK","FIRE",2); S("ROCK","ICE",2); S("ROCK","FIGHTING",.5); S("ROCK","GROUND",.5); S("ROCK","FLYING",2); S("ROCK","BUG",2); S("ROCK","STEEL",.5);
  S("GHOST","NORMAL",0); S("GHOST","PSYCHIC",2); S("GHOST","GHOST",2); S("GHOST","DARK",.5);
  S("DRAGON","DRAGON",2); S("DRAGON","STEEL",.5); S("DRAGON","FAIRY",0);
  S("DARK","FIGHTING",.5); S("DARK","PSYCHIC",2); S("DARK","GHOST",2); S("DARK","DARK",.5); S("DARK","FAIRY",.5);
  S("STEEL","FIRE",.5); S("STEEL","WATER",.5); S("STEEL","ELECTRIC",.5); S("STEEL","ICE",2); S("STEEL","ROCK",2); S("STEEL","STEEL",.5); S("STEEL","FAIRY",2);
  S("FAIRY","FIRE",.5); S("FAIRY","FIGHTING",2); S("FAIRY","POISON",.5); S("FAIRY","DRAGON",2); S("FAIRY","DARK",2); S("FAIRY","STEEL",.5);
  return c;
})();

function effTypes(t, defTypes){ let e = 1; for (const d of defTypes) e *= (TYPE_CHART[t][d] ?? 1); return e; }

if (typeof module !== "undefined" && module.exports){
  module.exports = { TYPE_KO, TYPE_COLOR, TYPE_CHART, effTypes };
}
