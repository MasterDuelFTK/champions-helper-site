/* Champions Helper — 데미지 계산기 UI 바인딩
 * 계산 엔진은 engine.js (전역 함수). 데이터: /data/dex.json + /data/moves.json.
 */
"use strict";

const $ = id => document.getElementById(id);
const T = (t) => `<span class="tchip" style="background:${TYPE_COLOR[t]};color:#181818">${TYPE_KO[t]||t}</span>`;

const ITEM_LIST = ["", "생명의구슬","달인의띠","구애머리띠","구애안경","구애스카프","힘의머리띠","지식의안경",
  "돌격조끼","진화의휘석","기합의띠","먹다남은음식","자뭉열매","풍선",
  ...Object.values(TYPE_BOOST_ITEM)];

let DEX = [], MOVES = [], MOVE_BY = {}, SPECIES_BY = {};
const state = { atk:{ megaIdx:-1 }, def:{ megaIdx:-1 } };

// 결정력은 수비자 없이도 계산 — 중립 더미 방어자(powerIndex 는 방어 무관).
const DUMMY_DEF = { types:["NORMAL"], hp:100, def:100, spd:100, defStage:0, spdStage:0, abilKo:null, item:null };

/* ── 데이터 로드 ─────────────────────────────────────── */
Promise.all([
  fetch("/data/dex.json").then(r => r.json()),
  fetch("/data/moves.json").then(r => r.json()),
]).then(([dx, mv]) => {
  DEX = dx.dex; MOVES = mv.moves;
  DEX.forEach(e => SPECIES_BY[e.ko] = e);
  MOVES.forEach(m => MOVE_BY[m.ko] = m);
  $("speciesList").innerHTML = DEX.map(e => `<option value="${e.ko}">`).join("");
  $("moveList").innerHTML = MOVES.map(m => `<option value="${m.ko}">`).join("");
  fillItems("atkItem"); fillItems("defItem");
  fillRanks("atkRank"); fillRanks("defRank");
  wire();
}).catch(err => {
  $("rVerdict").textContent = "데이터를 불러오지 못했습니다: " + err;
});

function fillItems(id){ $(id).innerHTML = ITEM_LIST.map(i => `<option value="${i}">${i || "— 없음 —"}</option>`).join(""); }
function fillRanks(id){
  let h = "";
  for (let s = 6; s >= -6; s--) h += `<option value="${s}"${s===0?" selected":""}>${s>0?"+"+s:s}</option>`;
  $(id).innerHTML = h;
}

/* ── 폼(기본/메가) 해석 ───────────────────────────────── */
function activeForm(sp, megaIdx){
  if (sp && megaIdx >= 0 && sp.mega && sp.mega[megaIdx]){
    const m = sp.mega[megaIdx];
    return { types: m.types, stats: m.stats, abil: m.abil, name: m.ko };
  }
  return sp ? { types: sp.types, stats: sp.stats, abil: sp.abil, name: sp.ko } : null;
}

/* ── 종족 선택 시 UI 갱신 ─────────────────────────────── */
function refreshSpecies(sideKey){
  const isAtk = sideKey === "atk";
  const sp = SPECIES_BY[$(isAtk ? "atkName" : "defName").value.trim()];
  const st = state[sideKey];
  if (!sp) st.megaIdx = -1;
  const megaBox = $(isAtk ? "atkMega" : "defMega");
  if (sp && sp.mega && sp.mega.length){
    megaBox.innerHTML = sp.mega.map((m, i) => {
      const lbl = sp.mega.length > 1 ? "메가 " + m.ko.slice(-1) : "메가진화";
      return `<button data-side="${sideKey}" data-mi="${i}"${st.megaIdx===i?' class="on"':''}>${lbl}</button>`;
    }).join("");
  } else megaBox.innerHTML = "";
  const f = activeForm(sp, st.megaIdx);
  $(isAtk ? "atkTypes" : "defTypes").innerHTML = f ? f.types.map(T).join("") : "";
  const baseEl = $(isAtk ? "atkBase" : "defBase");
  if (f){
    const s = f.stats;
    baseEl.innerHTML = `종족값 <b>${s.hp}/${s.atk}/${s.def}/${s.spa}/${s.spd}/${s.spe}</b>`;
  } else baseEl.innerHTML = "";
  const abilSel = $(isAtk ? "atkAbil" : "defAbil");
  const prev = abilSel.value;
  let opts = '<option value="">— 없음 —</option>';
  if (f) opts += f.abil.map(a => `<option value="${a.ko}">${a.ko}</option>`).join("");
  abilSel.innerHTML = opts;
  if (f && st.megaIdx >= 0 && f.abil.length) abilSel.value = f.abil[0].ko;
  else if (f && f.abil.some(a => a.ko === prev)) abilSel.value = prev;
  else if (f && f.abil.length) abilSel.value = f.abil[0].ko;
}

/* ── 기술 선택 시 UI 갱신 ─────────────────────────────── */
function refreshMove(){
  const m = MOVE_BY[$("atkMove").value.trim()];
  const box = $("atkMoveBox");
  if (!m){ box.style.display = "none"; return; }
  box.style.display = "block";
  $("atkMoveType").innerHTML = T(m.type);
  $("atkMoveCat").textContent = m.cat === "PHYSICAL" ? "물리" : "특수";
  $("atkPow").value = m.pow;
  const phys = m.cat === "PHYSICAL";
  const defPhys = defenderIsPhysical(m);   // 사이코쇼크류 = 특수기지만 물리방어/방어 랭크
  $("atkEvLbl").textContent = (phys ? "공격" : "특공") + " 노력치 0~32";
  $("atkRankLbl").textContent = "랭크업 (" + (phys ? "공격" : "특공") + ")";
  $("defRankLbl").textContent = "랭크업 (" + (defPhys ? "방어" : "특방") + ")";
}

function natMod(v){ return v === "up" ? 1.1 : v === "down" ? 0.9 : 1.0; }

/* ── 한 진영의 입력 → 계산용 상태 ─────────────────────── */
function buildSide(sideKey, cat, defPhys){
  const isAtk = sideKey === "atk";
  const sp = SPECIES_BY[$(isAtk ? "atkName" : "defName").value.trim()];
  if (!sp) return null;
  const f = activeForm(sp, state[sideKey].megaIdx);
  const abilKo = $(isAtk ? "atkAbil" : "defAbil").value || null;
  const item = $(isAtk ? "atkItem" : "defItem").value || null;
  const phys = cat === "PHYSICAL";
  const clampEv = v => Math.max(0, Math.min(32, parseInt(v) || 0));
  const s = f.stats;
  const out = { types: f.types, abilKo, item, extraMult: 1 };

  if (isAtk){
    const nm = natMod($("atkNat").dataset.v);
    const ev = clampEv($("atkEv").value);
    out.atk = calcStat(s.atk, phys ? ev : 0, phys ? nm : 1);
    out.spa = calcStat(s.spa, !phys ? ev : 0, !phys ? nm : 1);
    const rk = parseInt($("atkRank").value) || 0;
    out.atkStage = rk; out.spaStage = rk;
    out.status = $("atkStatus").value;
    out.hpPct = Math.max(1, Math.min(100, parseInt($("atkHp").value) || 100));
    out.extraMult = Math.max(0, parseFloat($("atkMult").value) || 1);
    out.realStr = `공격 <b>${out.atk}</b> / 특공 <b>${out.spa}</b>` + (phys ? " · 물리기" : " · 특수기");
  } else {
    // 방어 노력치/성격은 통합 입력 — 들어오는 기술이 노리는 방어 스탯에만 적용(공격쪽 미러링).
    const nat = natMod($("defNat").dataset.v);
    const ev = clampEv($("defEv").value);
    out.hp = calcHp(s.hp, clampEv($("defHpEv").value));
    out.def = calcStat(s.def, defPhys ? ev : 0, defPhys ? nat : 1);
    out.spd = calcStat(s.spd, !defPhys ? ev : 0, !defPhys ? nat : 1);
    const rk = parseInt($("defRank").value) || 0;
    out.defStage = rk; out.spdStage = rk;
    out.realStr = defPhys
      ? `HP <b>${out.hp}</b> / 방어 <b>${out.def}</b>`
      : `HP <b>${out.hp}</b> / 특방 <b>${out.spd}</b>`;
  }
  return out;
}

/* ── 메인 재계산 ─────────────────────────────────────── */
function recompute(){
  const move = MOVE_BY[$("atkMove").value.trim()];
  const cat = move ? move.cat : "PHYSICAL";
  const defPhys = defenderIsPhysical(move);   // 사이코쇼크류 = 특수기지만 물리방어
  const ctx = {
    weather: $("weather").value, terrain: $("terrain").value, crit: $("crit").checked,
    reflect: $("reflect").checked, light: $("light").checked, aurora: $("aurora").checked,
  };

  // 공격자 빌드 (종족 있을 때)
  const A = SPECIES_BY[$("atkName").value.trim()] ? buildSide("atk", cat) : null;
  // 수비자 빌드 (종족 있을 때) — 들어오는 기술이 노리는 방어 스탯에 통합 노력치 적용
  const D = SPECIES_BY[$("defName").value.trim()] ? buildSide("def", cat, defPhys) : null;

  // 결정력 — 공격자 + 기술이면 상대 없이 표시
  if (A && move){
    const userPow = parseInt($("atkPow").value);
    const m = Object.assign({}, move);
    if (variablePower(move.en, A.hpPct) == null && Number.isFinite(userPow)) m.pow = userPow;
    const idx = calcDamage(A, DUMMY_DEF, m, ctx).powerIndex;
    $("atkIdx").textContent = idx != null ? idx.toLocaleString() : "—";
    $("atkReal").innerHTML = A.realStr;
  } else {
    $("atkIdx").textContent = "—";
    $("atkReal").innerHTML = A ? A.realStr : "";
  }

  // 내구력 — 들어오는 기술이 노리는 방어 스탯 기준 하나(공격쪽 결정력 미러링)
  $("defIdxKind").textContent = defPhys ? "물리" : "특수";
  if (D){
    const du = durabilities(D);
    $("defIdx").textContent = (defPhys ? du.phys : du.spec).toLocaleString();
    $("defReal").innerHTML = D.realStr;
  } else {
    $("defIdx").textContent = "—";
    $("defReal").innerHTML = "";
  }

  // 전체 데미지 — 양쪽 + 기술 모두 있을 때
  if (A && D && move){
    const userPow = parseInt($("atkPow").value);
    const m = Object.assign({}, move);
    if (variablePower(move.en, A.hpPct) == null && Number.isFinite(userPow)) m.pow = userPow;
    render(calcDamage(A, D, m, ctx));
  } else {
    const msg = !move ? "기술을 입력하면 데미지를 계산합니다." :
                !A ? "공격하는 포켓몬을 입력하세요." : "방어하는 포켓몬을 입력하세요.";
    showEmpty(msg);
  }
}

function showEmpty(msg){
  $("rDmg").textContent = "—"; $("rVerdict").textContent = msg; $("rVerdict").className = "verdict";
  $("rPct").textContent = ""; $("rBar").style.width = "0"; $("rNotes").innerHTML = ""; $("rRolls").textContent = "";
}

function render(r){
  if (r.verdict === "변화기"){ showEmpty("공격기를 선택하세요(변화기는 데미지 0)."); return; }
  $("rDmg").textContent = `${r.minD} ~ ${r.maxD} 데미지`;
  $("rVerdict").textContent = r.verdict;
  let cls = "verdict ";
  if (r.verdict === "확정 1타") cls += "v-ko";
  else if (r.verdict.includes("난수") || r.verdict.includes("2타")) cls += "v-maybe";
  else cls += "v-safe";
  $("rVerdict").className = cls;
  const effStr = r.typeEff === 1 ? "" : `  ·  타입상성 ×${(+r.typeEff.toFixed(3))}`;
  $("rPct").innerHTML = `상대 HP <b>${r.hp}</b> 기준  ${r.minPct.toFixed(1)}% ~ ${r.maxPct.toFixed(1)}%${effStr}`;
  $("rBar").style.left = Math.min(100, r.minPct) + "%";
  $("rBar").style.width = Math.min(100 - Math.min(100, r.minPct), Math.max(1, r.maxPct - r.minPct)) + "%";
  $("rNotes").innerHTML = r.notes.length ? r.notes.map(n => `<span class="note">${n}</span>`).join("") : "";
  $("rRolls").textContent = "난수 16: " + r.rolls.join(" ");
}

/* ── 이벤트 바인딩 ───────────────────────────────────── */
function wire(){
  $("atkName").addEventListener("input", () => { state.atk.megaIdx = -1; refreshSpecies("atk"); recompute(); });
  $("defName").addEventListener("input", () => { state.def.megaIdx = -1; refreshSpecies("def"); recompute(); });
  $("atkMove").addEventListener("input", () => { refreshMove(); recompute(); });

  document.body.addEventListener("click", e => {
    const b = e.target.closest(".megabtns button"); if (!b) return;
    const side = b.dataset.side, mi = +b.dataset.mi;
    state[side].megaIdx = state[side].megaIdx === mi ? -1 : mi;
    refreshSpecies(side); recompute();
  });
  document.querySelectorAll(".seg").forEach(seg => {
    seg.addEventListener("click", e => {
      const b = e.target.closest("button"); if (!b) return;
      seg.dataset.v = b.dataset.n;
      seg.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
      recompute();
    });
  });
  ["atkAbil","defAbil","atkEv","defEv","defHpEv","atkRank","defRank","atkItem","defItem",
   "atkHp","defHp","atkMult","atkPow","atkStatus","weather","terrain","crit","reflect","light","aurora"]
    .forEach(id => {
      const el = $(id);
      el.addEventListener(el.type === "checkbox" ? "change" : "input", recompute);
      if (el.tagName === "SELECT") el.addEventListener("change", recompute);
    });
}
