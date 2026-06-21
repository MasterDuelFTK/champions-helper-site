/* Champions Helper — 데미지 계산 엔진 (순수 함수, DOM 비의존)
 * 데스크탑 src/PCH.Domain/Battle/DamageCalculator.cs · TypeChart.cs · AbilityRegistry.cs ·
 * ItemRegistry.cs · StatCalculator.cs 를 JS로 포팅. 챔피언스 룰(레벨50/IV31/노력치 직접가산).
 * 브라우저에서는 전역 함수로, node(골든 테스트)에서는 module.exports 로 사용.
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

/* ── 타입강화 도구 (ItemRegistry.cs) ─────────────────── */
const TYPE_BOOST_ITEM = { NORMAL:"실크스카프", FIRE:"차콜", WATER:"신비의물방울", GRASS:"기적의씨",
  ELECTRIC:"자석", GROUND:"부드러운모래", DRAGON:"예리한손톱", FIGHTING:"검은띠", POISON:"독바늘",
  FLYING:"뾰족한부리", PSYCHIC:"트위스트스푼", BUG:"은빛가루", ROCK:"딱딱한돌", GHOST:"저주의부적",
  DARK:"검은안경", STEEL:"메탈코트", ICE:"맑은얼음", FAIRY:"묘한사탕" };

/* ── 스탯 계산 (StatCalculator.cs, lvl50/IV31) ────────── */
function calcStat(base, ev, natMod){
  const baseReal = Math.floor((2*base + 31) * 50 / 100) + 5;
  return Math.floor((baseReal + ev) * natMod);
}
function calcHp(base, ev){
  if (base === 1) return 1;
  return Math.floor((2*base + 31) * 50 / 100) + 50 + 10 + ev;
}
function stageMult(s){ s = Math.max(-6, Math.min(6, s)); return s >= 0 ? (2+s)/2 : 2/(2-s); }
// 내구력 = HP실능 × 방어(특방)실능 ÷ 0.411. 수비자만으로 계산(상대 무관). 랭크/벽 제외(순수 내구지수).
function durabilities(D){
  return { phys: Math.floor(D.hp * D.def / 0.411), spec: Math.floor(D.hp * D.spd / 0.411) };
}
function grounded(types, abilKo, item){ return !types.includes("FLYING") && abilKo !== "부유" && item !== "풍선"; }
function effTypes(t, defTypes){ let e = 1; for (const d of defTypes) e *= (TYPE_CHART[t][d] ?? 1); return e; }

/* ── 가변 위력기 (시전자 HP%) ─────────────────────────── */
function variablePower(en, hpPct){
  if (["eruption","water-spout","dragon-energy"].includes(en))
    return Math.max(1, Math.floor(150 * hpPct / 100));
  if (["reversal","flail"].includes(en)){
    const p = hpPct;
    return p >= 68.75 ? 20 : p >= 35.42 ? 40 : p >= 20.83 ? 80 : p >= 10.42 ? 100 : p >= 4.17 ? 150 : 200;
  }
  return null;
}

/* ── 특성 보정 (AbilityRegistry.cs 포팅 + 맹화류 신규) ── */
function applyAbility(name, isAtk, mods, A, D, mtype, cat, ctx, typeEff, flags){
  if (!name) return;
  const phys = cat === "PHYSICAL";
  const hasF = f => Array.isArray(flags) && flags.includes(f);
  if (isAtk){
    switch(name){
      case "천하장사": case "순수한힘":
        if (phys){ mods.atkMult *= 2; mods.note(name + " ×2"); } break;
      case "근성": // Guts — 상태이상이면 물리공격 ×1.5 (화상 ÷2 무효화는 calcDamage 본문)
        if (phys && A.status && A.status !== "none"){ mods.atkMult *= 1.5; mods.note("근성(상태이상) ×1.5"); } break;
      case "테크니션":
        if (mods.pow > 0 && mods.pow <= 60){ mods.powMult *= 1.5; mods.note("테크니션 ×1.5"); } break;
      case "적응력":
        if (mtype === A.types[0] || mtype === A.types[1]){ mods.stabOverride = 2.0; mods.note("적응력 자속 ×2"); } break;
      case "색안경":
        if (typeEff < 1 && typeEff > 0){ mods.typeEffMult *= 2; mods.note("색안경 ×2"); } break;
      case "선파워":
        if (ctx.weather === "Sun" && !phys){ mods.spaMult *= 1.5; mods.note("선파워(쾌청) ×1.5"); } break;
      case "모래의힘":
        if (ctx.weather === "Sand" && ["ROCK","GROUND","STEEL"].includes(mtype)){ mods.powMult *= 1.3; mods.note("모래의힘 ×1.3"); } break;
      case "불꽃의갈기":
        if (mtype === "FIRE"){ mods.powMult *= 1.5; mods.note("불꽃의갈기 ×1.5"); } break;
      case "맹화": if (A.hpPct <= 100/3 && mtype === "FIRE"){ mods.powMult *= 1.5; mods.note("맹화 ×1.5"); } break;
      case "급류": if (A.hpPct <= 100/3 && mtype === "WATER"){ mods.powMult *= 1.5; mods.note("급류 ×1.5"); } break;
      case "심록": if (A.hpPct <= 100/3 && mtype === "GRASS"){ mods.powMult *= 1.5; mods.note("심록 ×1.5"); } break;
      case "벌레의알림": case "벌레의소식":
        if (A.hpPct <= 100/3 && mtype === "BUG"){ mods.powMult *= 1.5; mods.note(name + " ×1.5"); } break;
      // ── flag 기반 (AbilityRegistry.cs 와 동일) ──
      case "철주먹":
        if (hasF("Punch")){ mods.powMult *= 1.2; mods.note("철주먹(펀치) ×1.2"); } break;
      case "단단한발톱":
        if (hasF("Contact")){ mods.powMult *= 1.3; mods.note("단단한발톱(접촉) ×1.3"); } break;
      case "옹골찬턱": case "거센턱":
        if (hasF("Bite")){ mods.powMult *= 1.5; mods.note(name + "(깨물기) ×1.5"); } break;
      case "메가런처":
        if (hasF("Pulse")){ mods.powMult *= 1.5; mods.note("메가런처(파동) ×1.5"); } break;
      case "예리함":
        if (hasF("Slicing")){ mods.powMult *= 1.5; mods.note("예리함(베기) ×1.5"); } break;
      case "우격다짐":
        if (hasF("Secondary")){ mods.powMult *= 1.3; mods.note("우격다짐(부가효과) ×1.3"); } break;
    }
  } else {
    switch(name){
      case "필터": case "하드록": case "프리즘아머":
        if (typeEff > 1){ mods.finalMult *= 0.75; mods.note(name + " ×0.75"); } break;
      case "두꺼운지방":
        if (mtype === "FIRE" || mtype === "ICE"){ mods.finalMult *= 0.5; mods.note("두꺼운지방 ×0.5"); } break;
      case "내열": case "수포":
        if (mtype === "FIRE"){ mods.finalMult *= 0.5; mods.note(name + "(불꽃) ×0.5"); } break;
      case "건조피부":
        if (mtype === "FIRE"){ mods.finalMult *= 1.25; mods.note("건조피부(불꽃) ×1.25"); }
        if (mtype === "WATER"){ mods.finalMult *= 0; mods.note("건조피부(물 무효)"); } break;
      case "복슬복슬":
        if (mtype === "FIRE"){ mods.finalMult *= 2; mods.note("복슬복슬(불꽃) ×2"); }
        if (hasF("Contact")){ mods.finalMult *= 0.5; mods.note("복슬복슬(접촉) ×0.5"); } break;
      case "저수": case "마중물":
        if (mtype === "WATER"){ mods.finalMult *= 0; mods.note(name + "(물 무효)"); } break;
      case "초식": if (mtype === "GRASS"){ mods.finalMult *= 0; mods.note("초식(풀 무효)"); } break;
      case "타오르는불꽃": if (mtype === "FIRE"){ mods.finalMult *= 0; mods.note("타오르는불꽃(불꽃 무효)"); } break;
      case "축전": case "피뢰침": case "전기엔진":
        if (mtype === "ELECTRIC"){ mods.finalMult *= 0; mods.note(name + "(전기 무효)"); } break;
      case "흙먹기": case "부유": case "천정부지":
        if (mtype === "GROUND"){ mods.finalMult *= 0; mods.note(name + "(땅 무효)"); } break;
      // ── flag 기반 (방어) ──
      case "펑크록":
        if (hasF("Sound")){ mods.finalMult *= 0.5; mods.note("펑크록(소리) ×0.5"); } break;
      case "방음":
        if (hasF("Sound")){ mods.finalMult *= 0; mods.note("방음(소리 무효)"); } break;
      case "방진":
        if (hasF("Powder")){ mods.finalMult *= 0; mods.note("방진(가루 무효)"); } break;
    }
  }
}

/* ── 도구 보정 (ItemRegistry.cs 포팅) ─────────────────── */
function applyItem(name, isAtk, mods, mtype, cat){
  if (!name) return;
  const phys = cat === "PHYSICAL";
  if (isAtk){
    if (name === "구애머리띠" && phys){ mods.atkMult *= 1.5; mods.note("구애머리띠 ×1.5"); }
    else if (name === "구애안경" && !phys){ mods.spaMult *= 1.5; mods.note("구애안경 ×1.5"); }
    else if (name === "생명의구슬"){ mods.finalMult *= 1.3; mods.note("생명의구슬 ×1.3"); }
    else if (name === "힘의머리띠" && phys){ mods.powMult *= 1.1; mods.note("힘의머리띠 ×1.1"); }
    else if (name === "지식의안경" && !phys){ mods.powMult *= 1.1; mods.note("지식의안경 ×1.1"); }
    else if (TYPE_BOOST_ITEM[mtype] === name){ mods.powMult *= 1.2; mods.note(name + " ×1.2"); }
  } else {
    if (name === "돌격조끼" && !phys){ mods.spdMult *= 1.5; mods.note("돌격조끼 ×1.5"); }
    else if (name === "진화의휘석"){ if (phys) mods.defMult *= 1.5; else mods.spdMult *= 1.5; mods.note("진화의휘석 ×1.5"); }
  }
}

/* ── 데미지 계산 (DamageCalculator.cs 포팅) ───────────── */
function calcDamage(A, D, move, ctx){
  const mods = { atkMult:1, spaMult:1, defMult:1, spdMult:1, powMult:1, finalMult:1,
    stabOverride:null, typeEffMult:1, pow:move.pow, _notes:[], note(s){ this._notes.push(s); } };
  const phys = move.cat === "PHYSICAL";
  let mtype = move.type;
  let pow = move.pow;

  if (move.cat === "STATUS" || pow <= 0 && variablePower(move.en, A.hpPct) == null)
    return { minD:0, maxD:0, minPct:0, maxPct:0, verdict:"변화기", rolls:[], notes:[], typeEff:1, hp: D.hp };

  // 가변 위력기 (시전자 HP%)
  const vp = variablePower(move.en, A.hpPct);
  if (vp != null){ pow = vp; mods.note(`가변위력 → ${pow} (HP ${A.hpPct}%)`); }
  mods.pow = pow;

  const offWeather = A.abilKo === "메가솔라" ? "Sun" : ctx.weather;

  if (move.en === "weather-ball" && offWeather !== "None"){
    mtype = { Sun:"FIRE", Rain:"WATER", Sand:"ROCK", Snow:"ICE" }[offWeather] || mtype;
    pow = 100; mods.pow = 100; mods.note(`웨더볼 → ${TYPE_KO[mtype]} 위력100`);
  }
  if (mtype === "NORMAL"){
    const ate = { "스카이스킨":"FLYING", "페어리스킨":"FAIRY", "프리즈스킨":"ICE", "일렉트릭스킨":"ELECTRIC", "드래곤스킨":"DRAGON" }[A.abilKo];
    if (ate){ mtype = ate; mods.powMult *= 1.2; mods.note(`${A.abilKo}(노말→${TYPE_KO[ate]}) ×1.2`); }
  }

  const flags = move.flags || [];
  // 객기(facade): 공격자가 화상/독/맹독/마비면 위력 2배 (+ 아래에서 화상 공격감소도 무시)
  if (move.en === "facade" && ["brn","psn","tox","par"].includes(A.status)){ mods.powMult *= 2; mods.note("객기(상태이상) ×2"); }
  let typeEff = effTypes(mtype, D.types);
  applyItem(A.item, true, mods, mtype, move.cat);
  applyItem(D.item, false, mods, mtype, move.cat);
  applyAbility(A.abilKo, true, mods, A, D, mtype, move.cat, ctx, typeEff, flags);
  applyAbility(D.abilKo, false, mods, A, D, mtype, move.cat, ctx, typeEff, flags);

  const fAura = A.abilKo === "페어리오라" || D.abilKo === "페어리오라";
  const dAura = A.abilKo === "다크오라" || D.abilKo === "다크오라";
  const aBreak = A.abilKo === "오라브레이크" || D.abilKo === "오라브레이크";
  if ((mtype === "FAIRY" && fAura) || (mtype === "DARK" && dAura)){
    if (aBreak){ mods.finalMult *= 0.75; mods.note("오라브레이크 ×0.75"); }
    else { mods.finalMult *= 4/3; mods.note((mtype==="FAIRY"?"페어리오라":"다크오라") + " ×1.33"); }
  }
  if (A.item === "달인의띠" && typeEff > 1){ mods.finalMult *= 1.2; mods.note("달인의띠(효과굉장) ×1.2"); }

  typeEff *= mods.typeEffMult;
  pow = mods.pow;

  // 화상 물리 ÷2 — 근성(무효화)·객기(무시)는 예외
  const burnMult = (phys && A.status === "brn" && A.abilKo !== "근성" && move.en !== "facade") ? 0.5 : 1.0;
  if (burnMult < 1) mods.note("화상 공격력 ÷2");
  const Araw = phys
    ? A.atk * stageMult(A.atkStage) * mods.atkMult * burnMult
    : A.spa * stageMult(A.spaStage) * mods.spaMult;
  let weatherDefMult = 1.0;
  if (ctx.weather === "Sand" && !phys && D.types.includes("ROCK")){ weatherDefMult = 1.5; mods.note("모래바람 바위 특방 ×1.5"); }
  else if (ctx.weather === "Snow" && phys && D.types.includes("ICE")){ weatherDefMult = 1.5; mods.note("싸라기눈 얼음 방어 ×1.5"); }
  const Draw = (phys
    ? D.def * stageMult(D.defStage) * mods.defMult
    : D.spd * stageMult(D.spdStage) * mods.spdMult) * weatherDefMult;

  const Aval = Math.floor(Araw);
  const Dval = Math.max(1, Math.floor(Draw));
  const basePower = Math.floor(pow * mods.powMult);
  const step = Math.floor(2 * 50 / 5) + 2; // = 22
  let base = Math.floor(step * basePower * Aval / Dval);
  base = Math.floor(base / 50) + 2;

  let mod = 1.0;
  let weatherPow = 1.0; // 날씨 위력보정 (결정력 계산에 재사용)
  if (offWeather === "Sun"){
    if (mtype === "FIRE") weatherPow = 1.5;
    else if (mtype === "WATER") weatherPow = (move.en === "hydro-steam") ? 1.5 : 0.5;
  } else if (offWeather === "Rain"){
    if (mtype === "WATER") weatherPow = 1.5;
    else if (mtype === "FIRE") weatherPow = 0.5;
  }
  mod *= weatherPow;
  if (["solar-beam","solar-blade"].includes(move.en) && ["Rain","Sand","Snow"].includes(offWeather)){ mod *= 0.5; mods.note("솔라빔류(날씨) ×0.5"); }

  // 필드(테레인) — DamageCalculator엔 없던 신규
  if (ctx.terrain === "Electric" && mtype === "ELECTRIC" && grounded(A.types, A.abilKo, A.item)){ mod *= 1.3; mods.note("일렉트릭필드 ×1.3"); }
  else if (ctx.terrain === "Grassy" && mtype === "GRASS" && grounded(A.types, A.abilKo, A.item)){ mod *= 1.3; mods.note("그래스필드 ×1.3"); }
  else if (ctx.terrain === "Psychic" && mtype === "PSYCHIC" && grounded(A.types, A.abilKo, A.item)){ mod *= 1.3; mods.note("사이코필드 ×1.3"); }
  if (ctx.terrain === "Misty" && mtype === "DRAGON" && grounded(D.types, D.abilKo, D.item)){ mod *= 0.5; mods.note("미스트필드(드래곤) ×0.5"); }

  if (ctx.crit) mod *= 1.5;

  const stab = mods.stabOverride != null ? mods.stabOverride
    : ((mtype === A.types[0] || mtype === A.types[1]) ? 1.5 : 1.0);
  mod *= stab;
  mod *= typeEff;

  if (!ctx.crit){
    if (phys && ctx.reflect) mod *= 0.5;
    if (!phys && ctx.light) mod *= 0.5;
    if (ctx.aurora) mod *= 0.5;
  }
  mod *= mods.finalMult;
  mod *= (A.extraMult ?? 1);

  const rolls = [];
  for (let r = 85; r <= 100; r++){
    let d = Math.floor(base * mod * (r / 100));
    if (d < 1 && typeEff > 0 && basePower > 0 && mods.finalMult > 0) d = 1;
    rolls.push(d);
  }
  const minD = Math.min(...rolls), maxD = Math.max(...rolls);
  const hp = D.hp;
  const minPct = minD * 100 / hp, maxPct = maxD * 100 / hp;
  const koCount = rolls.filter(d => d >= hp).length;
  let verdict;
  if (typeEff === 0) verdict = "효과가 없다 (0 데미지)";
  else if (koCount === 16) verdict = "확정 1타";
  else if (koCount > 0) verdict = `난수 1타 ${Math.floor(koCount*100/16)}%`;
  else if (maxD * 2 >= hp){
    const c = rolls.filter(d => d*2 >= hp).length;
    verdict = c === 16 ? "확정 2타" : `난수 2타 ${Math.floor(c*100/16)}%`;
  } else verdict = maxD * 3 >= hp ? "확정 3타" : "4타 이상";

  // 결정력(화력지수) = 유효공격 × 유효위력 × 자속 × 날씨 × 생명의구슬 (상대 방어/타입 무관, 공격자 단독 지표)
  const lifeOrb = A.item === "생명의구슬" ? 1.3 : 1;
  const powerIndex = Math.floor(Aval * basePower * stab * weatherPow * lifeOrb);
  // 내구력 = HP실능 × 방어실능 ÷ 0.411 (현재 기술 분류 기준. 결정력 ≈ 내구력이면 ~50% 1타)
  const durability = Math.floor(hp * Dval / 0.411);

  return { minD, maxD, minPct, maxPct, verdict, rolls, notes: mods._notes, typeEff, hp, powerIndex, durability };
}

if (typeof module !== "undefined" && module.exports){
  module.exports = { TYPE_KO, TYPE_COLOR, TYPE_CHART, TYPE_BOOST_ITEM,
    calcStat, calcHp, stageMult, effTypes, grounded, variablePower,
    applyAbility, applyItem, calcDamage, durabilities };
}
