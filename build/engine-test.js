/* engine.js 골든 테스트 — C# DamageCalculatorTests.cs 비율/판정을 JS로 재현해 공식 정합성 확인.
 * 종족값/기술 = KnownPokemon.cs. node build/engine-test.js 로 실행.
 */
const E = require("../calc/engine.js");

// 종족값 (KnownPokemon.cs) {hp,atk,def,spa,spd,spe}
const B = {
  garchomp:  {hp:108,atk:130,def:95,spa:80,spd:85,spe:102},
  hippowdon: {hp:108,atk:112,def:118,spa:68,spd:72,spe:47},
  togekiss:  {hp:85,atk:50,def:95,spa:120,spd:115,spe:80},
  heatran:   {hp:91,atk:90,def:106,spa:130,spd:106,spe:77},
  tyranitar: {hp:100,atk:134,def:110,spa:95,spd:100,spe:61},
};
const MV = {
  earthquake:{ko:"지진",en:"earthquake",type:"GROUND",cat:"PHYSICAL",pow:100},
  airslash:  {ko:"에어슬래시",en:"air-slash",type:"FLYING",cat:"SPECIAL",pow:75},
  fireblast: {ko:"대문자",en:"fire-blast",type:"FIRE",cat:"SPECIAL",pow:110},
};

// 공격자 빌드: 물리기는 공격EV/성격, 특수기는 특공EV/성격 적용 (C# MakeAttacker 와 동일 의미)
function atk(base, types, move, {atkEv=0,spaEv=0,nat=null,rank=0,ability=null,item=null,status="none",hpPct=100,extraMult=1}={}){
  const nm = (k)=> nat && nat.up===k?1.1 : nat && nat.down===k?0.9 : 1.0;
  return {
    types, abilKo:ability, item, status, hpPct, extraMult,
    atk: E.calcStat(base.atk, atkEv, nm("atk")),
    spa: E.calcStat(base.spa, spaEv, nm("spa")),
    atkStage:rank, spaStage:rank,
  };
}
// 수비자 빌드: 시나리오 풀H+풀방/풀특방 등
function def(base, types, {hpEv=0,defEv=0,spdEv=0,natDef=1,natSpd=1,rank=0,ability=null,item=null}={}){
  return {
    types, abilKo:ability, item,
    hp: E.calcHp(base.hp, hpEv),
    def: E.calcStat(base.def, defEv, natDef),
    spd: E.calcStat(base.spd, spdEv, natSpd),
    defStage:rank, spdStage:rank,
  };
}
const CTX = (o={})=> Object.assign({weather:"None",terrain:"None",crit:false,reflect:false,light:false,aurora:false}, o);

let pass=0, fail=0;
function check(name, cond, extra=""){ if(cond){pass++; /*console.log("  ok",name);*/} else {fail++; console.log("FAIL:", name, extra);} }
function approx(a,b,tol){ return Math.abs(a-b)<=tol; }

// 1. 한카 지진 → 히드런(풀H풀방): 4배 자속, 확정1타, min%>100
{
  const a = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,spaEv:0,nat:{up:"atk",down:"spa"}});
  const d = def(B.heatran,["FIRE","STEEL"],{hpEv:32,defEv:32,natDef:1.1});
  const r = E.calcDamage(a,d,MV.earthquake,CTX());
  check("garchomp EQ→heatran 확정1타", r.verdict==="확정 1타", r.verdict);
  check("garchomp EQ→heatran min%>100", r.minPct>100, r.minPct.toFixed(1));
}
// 2. 지진 → 비행(토게키스): 0
{
  const a = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const d = def(B.togekiss,["FAIRY","FLYING"],{hpEv:32,defEv:32,natDef:1.1});
  const r = E.calcDamage(a,d,MV.earthquake,CTX());
  check("EQ→flying maxD=0", r.maxD===0, r.maxD);
}
// 3. 쾌청 불꽃 ×1.5
{
  const a = atk(B.heatran,["FIRE","STEEL"],MV.fireblast,{spaEv:32,nat:{up:"spa",down:"atk"}});
  const d = def(B.tyranitar,["ROCK","DARK"],{hpEv:32,spdEv:32,natSpd:1.1});
  const none = E.calcDamage(a,d,MV.fireblast,CTX({weather:"None"}));
  const sun  = E.calcDamage(a,d,MV.fireblast,CTX({weather:"Sun"}));
  check("쾌청 불꽃 ×1.5", approx(sun.maxPct/none.maxPct,1.5,0.05), (sun.maxPct/none.maxPct).toFixed(3));
}
// 4. 리플렉터 물리 ×0.5
{
  const a = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const d = def(B.hippowdon,["GROUND"],{hpEv:32,defEv:32,natDef:1.1});
  const nor = E.calcDamage(a,d,MV.earthquake,CTX());
  const ref = E.calcDamage(a,d,MV.earthquake,CTX({reflect:true}));
  check("리플렉터 물리 ×0.5", approx(ref.maxPct/nor.maxPct,0.5,0.05), (ref.maxPct/nor.maxPct).toFixed(3));
}
// 5. 크리티컬 ×1.5
{
  const a = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const d = def(B.hippowdon,["GROUND"],{hpEv:32});
  const nor = E.calcDamage(a,d,MV.earthquake,CTX());
  const crt = E.calcDamage(a,d,MV.earthquake,CTX({crit:true}));
  check("크리티컬 ×1.5", approx(crt.maxPct/nor.maxPct,1.5,0.05), (crt.maxPct/nor.maxPct).toFixed(3));
}
// 6. 공격 +2 → ×2
{
  const a0 = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const a2 = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"},rank:2});
  const d = def(B.hippowdon,["GROUND"],{hpEv:32});
  const nor = E.calcDamage(a0,d,MV.earthquake,CTX());
  const boo = E.calcDamage(a2,d,MV.earthquake,CTX());
  check("공격+2 ×2", approx(boo.maxPct/nor.maxPct,2.0,0.05), (boo.maxPct/nor.maxPct).toFixed(3));
}
// 7. 방어 +2 → ×0.5
{
  const a = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const d0 = def(B.hippowdon,["GROUND"],{hpEv:32});
  const d2 = def(B.hippowdon,["GROUND"],{hpEv:32,rank:2});
  const nor = E.calcDamage(a,d0,MV.earthquake,CTX());
  const df2 = E.calcDamage(a,d2,MV.earthquake,CTX());
  check("방어+2 ×0.5", approx(df2.maxPct/nor.maxPct,0.5,0.05), (df2.maxPct/nor.maxPct).toFixed(3));
}
// 8. 화상 물리 ×0.5
{
  const a0 = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const ab = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"},status:"brn"});
  const d = def(B.hippowdon,["GROUND"],{hpEv:32,defEv:32,natDef:1.1});
  const nor = E.calcDamage(a0,d,MV.earthquake,CTX());
  const brn = E.calcDamage(ab,d,MV.earthquake,CTX());
  check("화상 물리 ×0.5", approx(brn.maxPct/nor.maxPct,0.5,0.05), (brn.maxPct/nor.maxPct).toFixed(3));
}
// 9. 근성: 화상 ÷2 무효 + 상태이상 ×1.5 → 무화상 대비 ×1.5
{
  const a0 = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const ag = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"},status:"brn",ability:"근성"});
  const d = def(B.hippowdon,["GROUND"],{hpEv:32,defEv:32,natDef:1.1});
  const nor = E.calcDamage(a0,d,MV.earthquake,CTX());
  const grt = E.calcDamage(ag,d,MV.earthquake,CTX());
  check("근성 화상 ×1.5(무효+부스트)", approx(grt.maxPct/nor.maxPct,1.5,0.05), (grt.maxPct/nor.maxPct).toFixed(3));
}
// 9b. 객기(facade): 화상 시 위력2배 + 화상감소 무시 → 무화상 대비 ×2
{
  const facade={ko:"객기",en:"facade",type:"NORMAL",cat:"PHYSICAL",pow:70,flags:["Contact"]};
  const a0 = atk(B.garchomp,["DRAGON","GROUND"],facade,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const ab = atk(B.garchomp,["DRAGON","GROUND"],facade,{atkEv:32,nat:{up:"atk",down:"spa"},status:"brn"});
  const d = def(B.hippowdon,["GROUND"],{hpEv:32});
  const nor = E.calcDamage(a0,d,facade,CTX());
  const brn = E.calcDamage(ab,d,facade,CTX());
  check("객기 화상 ×2", approx(brn.maxPct/nor.maxPct,2.0,0.05), (brn.maxPct/nor.maxPct).toFixed(3));
  // 독 상태에서도 객기 ×2 (화상 아님 → 감소 없음, 순수 ×2)
  const apo = atk(B.garchomp,["DRAGON","GROUND"],facade,{atkEv:32,nat:{up:"atk",down:"spa"},status:"psn"});
  const poi = E.calcDamage(apo,d,facade,CTX());
  check("객기 독 ×2", approx(poi.maxPct/nor.maxPct,2.0,0.05), (poi.maxPct/nor.maxPct).toFixed(3));
}
// 10. 특수기는 Spa랭크만 (Atk+6 무영향, Spa+2 ×2)
{
  const a0 = atk(B.togekiss,["FAIRY","FLYING"],MV.airslash,{spaEv:32,hpPct:100,nat:{up:"spa",down:"atk"}});
  const aPhys = Object.assign({},a0,{atkStage:6,spaStage:0});
  const aSpa  = Object.assign({},a0,{atkStage:0,spaStage:2});
  const d = def(B.garchomp,["DRAGON","GROUND"],{});
  const nor  = E.calcDamage(a0,d,MV.airslash,CTX());
  const phys = E.calcDamage(aPhys,d,MV.airslash,CTX());
  const spa  = E.calcDamage(aSpa,d,MV.airslash,CTX());
  check("특수기 Atk랭크 무영향", phys.maxPct===nor.maxPct, phys.maxPct+" vs "+nor.maxPct);
  check("특수기 Spa+2 ×2", approx(spa.maxPct/nor.maxPct,2.0,0.05), (spa.maxPct/nor.maxPct).toFixed(3));
}
// 11. 생명의구슬 ×1.3 / 구애머리띠 ×1.5
{
  const base = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const lo   = Object.assign({},base,{item:"생명의구슬"});
  const cb   = Object.assign({},base,{item:"구애머리띠"});
  const d = def(B.hippowdon,["GROUND"],{hpEv:32});
  const nor = E.calcDamage(base,d,MV.earthquake,CTX());
  const orb = E.calcDamage(lo,d,MV.earthquake,CTX());
  const band= E.calcDamage(cb,d,MV.earthquake,CTX());
  check("생명의구슬 ×1.3", approx(orb.maxPct/nor.maxPct,1.3,0.04), (orb.maxPct/nor.maxPct).toFixed(3));
  check("구애머리띠 ×1.5", approx(band.maxPct/nor.maxPct,1.5,0.04), (band.maxPct/nor.maxPct).toFixed(3));
}
// 12. 가변위력 분화: HP100 → 위력150, HP50 → 위력75 (절반)
{
  const eruption={ko:"분화",en:"eruption",type:"FIRE",cat:"SPECIAL",pow:150};
  const aFull = atk(B.heatran,["FIRE","STEEL"],eruption,{spaEv:32,hpPct:100,nat:{up:"spa",down:"atk"}});
  const aHalf = atk(B.heatran,["FIRE","STEEL"],eruption,{spaEv:32,hpPct:50,nat:{up:"spa",down:"atk"}});
  const d = def(B.tyranitar,["ROCK","DARK"],{hpEv:32,spdEv:32,natSpd:1.1});
  const full = E.calcDamage(aFull,d,eruption,CTX());
  const half = E.calcDamage(aHalf,d,eruption,CTX());
  check("분화 HP50 ≈ 절반위력", approx(half.maxPct/full.maxPct,0.5,0.06), (half.maxPct/full.maxPct).toFixed(3));
}
// 13. 맹화: HP 30% 불꽃 ×1.5
{
  const a0 = atk(B.heatran,["FIRE","STEEL"],MV.fireblast,{spaEv:32,hpPct:30,nat:{up:"spa",down:"atk"}});
  const ab = Object.assign({},a0,{abilKo:"맹화"});
  const d = def(B.tyranitar,["ROCK","DARK"],{hpEv:32,spdEv:32,natSpd:1.1});
  const nor = E.calcDamage(a0,d,MV.fireblast,CTX());
  const blz = E.calcDamage(ab,d,MV.fireblast,CTX());
  check("맹화 HP30% 불꽃 ×1.5", approx(blz.maxPct/nor.maxPct,1.5,0.04), (blz.maxPct/nor.maxPct).toFixed(3));
}

// 14. 철주먹: 펀치기 ×1.2 (flag 기반)
{
  const punch={ko:"불꽃펀치",en:"fire-punch",type:"FIRE",cat:"PHYSICAL",pow:75,flags:["Contact","Punch","Secondary"]};
  const a0 = atk(B.heatran,["FIRE","STEEL"],punch,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const ai = Object.assign({},a0,{abilKo:"철주먹"});
  const d = def(B.hippowdon,["GROUND"],{hpEv:32,defEv:32,natDef:1.1});
  const nor = E.calcDamage(a0,d,punch,CTX());
  const iro = E.calcDamage(ai,d,punch,CTX());
  check("철주먹 펀치 ×1.2", approx(iro.maxPct/nor.maxPct,1.2,0.04), (iro.maxPct/nor.maxPct).toFixed(3));
}
// 15. 거센턱: 깨물기 ×1.5 / 비깨물기 미발동
{
  const bite={ko:"깨물어부수기",en:"crunch",type:"DARK",cat:"PHYSICAL",pow:80,flags:["Contact","Bite","Secondary"]};
  const nobite={ko:"지진",en:"earthquake",type:"GROUND",cat:"PHYSICAL",pow:100,flags:[]};
  const dd = def(B.hippowdon,["GROUND"],{hpEv:32,defEv:32,natDef:1.1});
  const a0 = atk(B.tyranitar,["ROCK","DARK"],bite,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const aj = Object.assign({},a0,{abilKo:"거센턱"});
  const nor = E.calcDamage(a0,dd,bite,CTX());
  const jaw = E.calcDamage(aj,dd,bite,CTX());
  check("거센턱 깨물기 ×1.5", approx(jaw.maxPct/nor.maxPct,1.5,0.04), (jaw.maxPct/nor.maxPct).toFixed(3));
  const aj2 = atk(B.garchomp,["DRAGON","GROUND"],nobite,{atkEv:32,nat:{up:"atk",down:"spa"},ability:"거센턱"});
  const a02 = atk(B.garchomp,["DRAGON","GROUND"],nobite,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const n2 = E.calcDamage(a02,dd,nobite,CTX());
  const j2 = E.calcDamage(aj2,dd,nobite,CTX());
  check("거센턱 비깨물기 미발동", j2.maxPct===n2.maxPct, j2.maxPct+" vs "+n2.maxPct);
}
// 16. 방음: 소리기 무효 (flag 기반 방어)
{
  const sound={ko:"하이퍼보이스",en:"hyper-voice",type:"NORMAL",cat:"SPECIAL",pow:90,flags:["Sound"]};
  const a = atk(B.togekiss,["FAIRY","FLYING"],sound,{spaEv:32,nat:{up:"spa",down:"atk"}});
  const d0 = def(B.garchomp,["DRAGON","GROUND"],{hpEv:32});
  const dm = def(B.garchomp,["DRAGON","GROUND"],{hpEv:32,ability:"방음"});
  const nor = E.calcDamage(a,d0,sound,CTX());
  const sp = E.calcDamage(a,dm,sound,CTX());
  check("방음 소리 무효(0)", sp.maxD===0, sp.maxD);
  check("방음 없으면 데미지>0", nor.maxD>0, nor.maxD);
}
// 17. 우격다짐: 부가효과 보유기 ×1.3
{
  const sec={ko:"대문자",en:"fire-blast",type:"FIRE",cat:"SPECIAL",pow:110,flags:["Secondary"]};
  const a0 = atk(B.heatran,["FIRE","STEEL"],sec,{spaEv:32,nat:{up:"spa",down:"atk"}});
  const af = Object.assign({},a0,{abilKo:"우격다짐"});
  const d = def(B.tyranitar,["ROCK","DARK"],{hpEv:32,spdEv:32,natSpd:1.1});
  const nor = E.calcDamage(a0,d,sec,CTX());
  const sf = E.calcDamage(af,d,sec,CTX());
  check("우격다짐 부가효과기 ×1.3", approx(sf.maxPct/nor.maxPct,1.3,0.04), (sf.maxPct/nor.maxPct).toFixed(3));
}
// 18. 결정력/내구력 노출 + 합리성 (결정력 = 위력×공격×자속 근사)
{
  const a = atk(B.garchomp,["DRAGON","GROUND"],MV.earthquake,{atkEv:32,nat:{up:"atk",down:"spa"}});
  const d = def(B.hippowdon,["GROUND"],{hpEv:32,defEv:32,natDef:1.1});
  const r = E.calcDamage(a,d,MV.earthquake,CTX());
  const expIdx = Math.floor(a.atk * Math.floor(100) * 1.5); // 위력100×공격×자속1.5
  check("결정력 노출", Number.isFinite(r.powerIndex) && r.powerIndex>0, r.powerIndex);
  check("결정력=위력×공격×자속", r.powerIndex===expIdx, r.powerIndex+" exp "+expIdx);
  check("내구력 노출", Number.isFinite(r.durability) && r.durability>0, r.durability);
  check("내구력=HP×방어/0.411", r.durability===Math.floor(d.hp*d.def/0.411), r.durability);
}

console.log(`\nengine-test: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
