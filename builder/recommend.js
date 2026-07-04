/* Champions Helper — 파티 추천 (팀빌딩 조합 분석)
 * 순수 클라이언트: /data/dex.json + /data/moves.json + /helper-data/move-usage.json.
 * 상성표(TYPE_CHART)·타입 한글명(TYPE_KO)·색(TYPE_COLOR)·effTypes는 /calc/engine.js 재사용(먼저 로드).
 * 헬퍼(로컬 프로그램) 없이도 추천·슬롯 채움 동작(실수치 계산·저장만 헬퍼 필요 = 빌더 기존 정책).
 * 브라우저 전역 PCHReco / node(스모크 테스트) module.exports.
 */
"use strict";

/* ── 튜닝 상수 (선출 추천 PickRecommender 철학: 근거문장 딸린 휴리스틱) ── */
const RECO_POOL_MAX_RANK = 120;   // 후보풀 = 사용률 상위 N위
const RECO_META_TOP = 30;         // 공격 커버리지 평가 대상 = 메타 상위 N
const RECO_ATTACK_PCT_MIN = 15;   // 채용률 몇 % 이상 공격기를 그 종의 공격타입으로 간주
const RECO_SHOW_N = 8;            // 추천 표시 개수
const FAST_SPE = 100;             // "빠르다" 기준 종족값
const BULKY_INDEX = 20000;        // 내구형 기준: hp*(def+spd)

/* ── 데이터 준비(순수) ─────────────────────────────────── */
// moves.json → en/ko 양쪽 인덱스 (ko는 공백 제거 정규화)
function buildMoveIndex(movesJson) {
  const byEn = {}, byKo = {};
  for (const m of movesJson.moves) {
    byEn[m.en] = m;
    byKo[(m.ko || "").replace(/\s+/g, "")] = m;
  }
  return { byEn, byKo };
}

// dex + usage 조인 → 후보풀(사용률 순위 있는 톱레벨 종만, 순위 오름차순)
function buildPool(dexJson, usageJson) {
  const usage = usageJson.pokemon || {};
  const pool = [];
  for (const e of dexJson.dex) {
    const u = usage[e.en];
    if (!u || !u.rank) continue;
    pool.push({ ...e, rank: u.rank, usageMoves: u.moves || [] });
  }
  pool.sort((a, b) => a.rank - b.rank);
  return pool;
}

// 종의 공격 타입 집합: STAB + 실전 채용 공격기(채용률≥RECO_ATTACK_PCT_MIN) 타입.
// ownMovesKo(빌더에 입력된 실제 기술)가 있으면 그걸 우선 사용(+STAB 유지).
function offenseTypes(entry, moveIdx, ownMovesKo) {
  const set = new Set(entry.types);
  const picked = (ownMovesKo || []).map((k) => (k || "").replace(/\s+/g, "")).filter(Boolean);
  if (picked.length) {
    for (const k of picked) {
      const m = moveIdx.byKo[k];
      if (m && m.cat !== "STATUS" && m.pow > 0) set.add(m.type);
    }
  } else {
    for (const um of entry.usageMoves || []) {
      if (um.pct < RECO_ATTACK_PCT_MIN) continue;
      const m = moveIdx.byEn[um.en];
      if (m && m.cat !== "STATUS" && m.pow > 0) set.add(m.type);
    }
  }
  return set;
}

/* ── 파티 프로필(순수) ─────────────────────────────────── */
function classOf(stats) {
  if (stats.atk - stats.spa >= 10) return "phys";
  if (stats.spa - stats.atk >= 10) return "spec";
  return "mixed";
}
function isBulky(stats) { return stats.hp * (stats.def + stats.spd) >= BULKY_INDEX; }

// members: [{entry, movesKo?}] (dex에 못 찾은 슬롯은 호출측에서 제외)
function buildProfile(members, pool, moveIdx) {
  const types = Object.keys(TYPE_KO);
  const weakCount = {}, weakW = {}, resistCount = {};
  types.forEach((t) => { weakCount[t] = 0; weakW[t] = 0; resistCount[t] = 0; });

  for (const m of members) {
    for (const t of types) {
      const e = effTypes(t, m.entry.types);
      if (e >= 2) { weakCount[t] += 1; weakW[t] += (e >= 4 ? 1.5 : 1); }
      else if (e < 1) resistCount[t] += 1;   // 반감·면역
    }
  }

  const offense = new Set();
  for (const m of members) offenseTypes(m.entry, moveIdx, m.movesKo).forEach((t) => offense.add(t));

  const meta = pool.slice(0, RECO_META_TOP);
  const coveredSet = new Set();
  for (const mon of meta) {
    for (const t of offense) if (effTypes(t, mon.types) >= 2) { coveredSet.add(mon.en); break; }
  }

  let phys = 0, spec = 0, fast = 0, bulky = 0;
  for (const m of members) {
    const c = classOf(m.entry.stats);
    if (c === "phys") phys++; else if (c === "spec") spec++; else { phys += 0.5; spec += 0.5; }
    if (m.entry.stats.spe >= FAST_SPE) fast++;
    if (isBulky(m.entry.stats)) bulky++;
  }

  return { members, weakCount, weakW, resistCount, offense, meta, coveredSet, phys, spec, fast, bulky };
}

/* ── 후보 채점(순수) — 반환 {score, reasons:[{txt, val}], warns:[]} ── */
function scoreCandidate(cand, prof, moveIdx) {
  const reasons = [], warns = [];
  let score = 0;

  // ① 방어 시너지: 기존 약점을 받아주면 +, 겹약점 −
  for (const t of Object.keys(TYPE_KO)) {
    const wc = prof.weakCount[t];
    const e = effTypes(t, cand.types);
    if (wc > 0) {
      if (e === 0) { score += 1.6 * prof.weakW[t]; reasons.push({ txt: `${TYPE_KO[t]} 약점 보완(면역)`, val: 1.6 * prof.weakW[t] }); }
      else if (e < 1) { score += 1.2 * prof.weakW[t]; reasons.push({ txt: `${TYPE_KO[t]} 약점 보완${wc >= 2 ? ` (${wc}마리)` : ""}`, val: 1.2 * prof.weakW[t] }); }
      else if (e >= 2) { const p = 1.1 * prof.weakW[t] * (e >= 4 ? 1.5 : 1); score -= p; warns.push({ txt: `${TYPE_KO[t]} 겹약점 (${wc + 1}마리째)`, val: p }); }
    } else if (e >= 2) {
      score -= 0.1;   // 새 약점 소량 감점(표시 안 함)
    }
  }

  // ② 공격 커버리지: 메타 상위 N 중 새로 효과굉장 커버되는 수
  const candOff = offenseTypes(cand, moveIdx);
  let gain = 0;
  for (const mon of prof.meta) {
    if (prof.coveredSet.has(mon.en) || mon.en === cand.en) continue;
    for (const t of candOff) if (effTypes(t, mon.types) >= 2) { gain++; break; }
  }
  if (gain > 0) { score += gain * 0.45; reasons.push({ txt: `공격 커버리지 +${gain} (메타 상위${RECO_META_TOP})`, val: gain * 0.45 }); }

  // ③ 밸런스: 물리/특수·스피드·내구 부족분 충족
  const c = classOf(cand.stats);
  if (prof.phys === 0 && (c === "phys" || c === "mixed")) { score += 0.8; reasons.push({ txt: "물리 어태커 보강", val: 0.8 }); }
  if (prof.spec === 0 && (c === "spec" || c === "mixed")) { score += 0.8; reasons.push({ txt: "특수 어태커 보강", val: 0.8 }); }
  if (c === "phys" && prof.phys >= 3 && prof.spec === 0) score -= 0.4;
  if (c === "spec" && prof.spec >= 3 && prof.phys === 0) score -= 0.4;
  if (prof.fast === 0 && cand.stats.spe >= FAST_SPE) { score += 0.7; reasons.push({ txt: `스피드 ${FAST_SPE}+ 확보`, val: 0.7 }); }
  if (prof.bulky === 0 && isBulky(cand.stats)) { score += 0.5; reasons.push({ txt: "내구형 보강", val: 0.5 }); }

  // ④ 사용률 prior
  const prior = 1.6 * (1 - (cand.rank - 1) / 240);
  score += prior;
  reasons.push({ txt: `사용률 ${cand.rank}위`, val: prior });

  reasons.sort((a, b) => b.val - a.val);
  warns.sort((a, b) => b.val - a.val);
  return { score, reasons, warns };
}

/* ── 추천/자동완성(순수) ───────────────────────────────── */
// members = [{entry, movesKo?}], 반환 = [{entry, score, reasons, warns}] 점수순
function recommend(members, pool, moveIdx) {
  const prof = buildProfile(members, pool, moveIdx);
  const usedBase = new Set(members.map((m) => m.entry.baseId || m.entry.id));
  const out = [];
  for (const cand of pool) {
    if (cand.rank > RECO_POOL_MAX_RANK) break;
    if (usedBase.has(cand.baseId || cand.id)) continue;   // 종족 중복(폼 포함) 제외
    const r = scoreCandidate(cand, prof, moveIdx);
    out.push({ entry: cand, ...r });
  }
  out.sort((a, b) => b.score - a.score);
  return out;
}

// 빈 자리 수만큼 greedy로 채움 → 추가할 entry 배열
function autofill(members, emptyCount, pool, moveIdx) {
  const cur = members.slice();
  const picks = [];
  for (let i = 0; i < emptyCount; i++) {
    const top = recommend(cur, pool, moveIdx)[0];
    if (!top) break;
    picks.push(top);
    cur.push({ entry: top.entry });
  }
  return picks;
}

// 파티 진단(순수): 렌더용 요약
function diagnose(members, pool, moveIdx) {
  const prof = buildProfile(members, pool, moveIdx);
  const dupWeak = [], noAnswer = [];
  for (const t of Object.keys(TYPE_KO)) {
    if (prof.weakCount[t] >= 2) dupWeak.push({ t, n: prof.weakCount[t] });
    else if (prof.weakCount[t] >= 1 && prof.resistCount[t] === 0) noAnswer.push(t);
  }
  dupWeak.sort((a, b) => b.n - a.n);
  const lacks = [];
  if (prof.phys === 0) lacks.push("물리 어태커 없음");
  if (prof.spec === 0) lacks.push("특수 어태커 없음");
  if (prof.fast === 0) lacks.push(`스피드 ${FAST_SPE}+ 없음`);
  if (prof.bulky === 0) lacks.push("내구형 없음");
  return { dupWeak, noAnswer, lacks, covered: prof.coveredSet.size, metaN: prof.meta.length, prof };
}

/* ════════ 이하 브라우저 전용(DOM) ════════ */
if (typeof document !== "undefined") {
(() => {
  let dexById = null, pool = null, moveIdx = null, loading = null;

  async function ensureData() {
    if (pool) return true;
    if (!loading) loading = (async () => {
      const [dex, moves, usage] = await Promise.all([
        fetch("/data/dex.json").then((r) => r.json()),
        fetch("/data/moves.json").then((r) => r.json()),
        fetch("/helper-data/move-usage.json").then((r) => r.json()),
      ]);
      moveIdx = buildMoveIndex(moves);
      pool = buildPool(dex, usage);
      dexById = new Map(dex.dex.map((e) => [e.id, e]));
      // 슬롯의 speciesId → 후보풀 entry(rank/usageMoves 포함) 매핑용
      for (const p of pool) dexById.set(p.id, p);
    })().catch((e) => { loading = null; throw e; });
    await loading;
    return true;
  }

  // state.slots(빌더 전역) → [{entry, movesKo}] + 빈칸 수 + 미식별 수
  function readParty() {
    const members = []; let empty = 0, unknown = 0;
    // 빌더 인라인 스크립트의 top-level const state — window 프로퍼티 아님 → typeof 가드
    for (const s of (typeof state !== "undefined" ? state.slots : [])) {
      if (!s) { empty++; continue; }
      const e = dexById.get(s.speciesId);
      if (e) members.push({ entry: e, movesKo: s.movesKo });
      else unknown++;   // 메가폼 등 도감 톱레벨 밖 → 분석 제외
    }
    return { members, empty, unknown };
  }

  function typeChip(t, extra, tip) {
    return `<span class="reco-type" style="background:${TYPE_COLOR[t]}"${tip ? ` title="${tip}"` : ""}>${TYPE_KO[t]}${extra || ""}</span>`;
  }

  // 진단 "부족" 태그별 구체 설명(hover 툴팁 — 상세는 카드 하단 '태그 설명' 범례)
  const LACK_TIPS = {
    "물리 어태커 없음": "공격 종족값이 특공보다 뚜렷이 높은 멤버가 없음 — 특방 특화 내구형 1마리에게 파티 전체가 막힐 수 있음",
    "특수 어태커 없음": "특공 종족값이 공격보다 뚜렷이 높은 멤버가 없음 — 방어 특화 내구형 1마리에게 파티 전체가 막힐 수 있음",
    [`스피드 ${FAST_SPE}+ 없음`]: `스피드 종족값 ${FAST_SPE} 이상 멤버가 없음 — 메타 상위권 다수에게 선공을 내줌`,
    "내구형 없음": "HP×(방어+특방)이 높은 쿠션 멤버가 없음 — 강한 한 방을 받아줄 포켓몬 부재",
  };
  // 추천 근거 태그 설명(문구 패턴 매칭)
  function reasonTip(txt) {
    if (txt.includes("약점 보완")) return "현재 파티가 약점인 타입 공격을 이 후보가 반감/면역으로 받아줄 수 있음";
    if (txt.startsWith("공격 커버리지")) return "지금 파티가 효과굉장으로 못 때리던 메타 상위 포켓몬을 이 후보가 새로 때릴 수 있게 됨";
    if (txt.includes("어태커 보강")) return "파티에 없던 물리/특수 화력을 채움 — 상대 내구형 한쪽 특화에 안 막히게 됨";
    if (txt.startsWith("스피드")) return "파티에 없던 선공권(빠른 스피드)을 채움";
    if (txt.includes("내구형 보강")) return "강한 한 방을 받아줄 쿠션 멤버를 채움";
    if (txt.startsWith("사용률")) return "실전 채용 순위(champs.pokedb.tokyo) — 높을수록 검증된 픽";
    if (txt.includes("겹약점")) return "주의: 이 후보도 그 타입이 약점 — 파티 약점이 한 타입에 더 쏠림";
    return "";
  }

  // dex entry → 빌더 state.cur 호환 객체(헬퍼 SpeciesDto와 동일 필드)
  function toCurObj(e) {
    return {
      id: e.id, nameKo: e.ko,
      type1: TYPE_KO[e.types[0]], type2: e.types[1] ? TYPE_KO[e.types[1]] : null,
      baseStats: e.stats, abilities: (e.abil || []).map((a) => a.ko),
    };
  }
  function toMember(e) {   // 헬퍼 미연결 시 슬롯 직접 채움용
    const cur = toCurObj(e);
    return { speciesId: cur.id, nameKo: cur.nameKo, type1: cur.type1, type2: cur.type2,
      baseStats: cur.baseStats, abilities: cur.abilities,
      abilityKo: cur.abilities[0] || null, natureKo: "성실",
      evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
      movesKo: ["", "", "", ""], itemKo: null };
  }

  function fillSlot(entry) {
    const idx = state.slots.findIndex((m) => m === null);
    if (idx < 0) return;
    if (typeof natureAc !== "undefined" && natureAc) {   // 헬퍼 연결(폼 초기화됨) → 기존 선택 플로우 재사용
      loadSlot(idx);
      selectSpecies(toCurObj(entry));
      commitSlot();
    } else {                                    // 미연결 → 슬롯 직접 기입
      state.slots[idx] = toMember(entry);
      renderSlots();
    }
    render();
  }

  async function autofillAll() {
    const { members, empty } = readParty();
    if (!empty) return;
    const picks = autofill(members, empty, pool, moveIdx);
    for (const p of picks) fillSlot(p.entry);
  }

  function reasonHtml(r) {
    const top = r.reasons.slice(0, 3).map((x) => `<span class="reco-why" title="${reasonTip(x.txt)}">${x.txt}</span>`).join("");
    const warn = r.warns.length ? `<span class="reco-why bad" title="${reasonTip(r.warns[0].txt)}">${r.warns[0].txt}</span>` : "";
    return top + warn;
  }

  function render() {
    const host = document.getElementById("recoBody");
    if (!host || !pool) return;
    const { members, empty, unknown } = readParty();

    if (!members.length) {
      host.className = "hint";
      host.textContent = "포켓몬을 1마리 이상 슬롯에 넣으면 남은 자리 추천이 표시됩니다.";
      return;
    }
    host.className = "";

    const d = diagnose(members, pool, moveIdx);
    const drow = (label, tip, chips) =>
      `<div class="reco-drow"><span class="reco-glabel" title="${tip}">${label}</span>${chips}</div>`;
    let html = `<div class="reco-diag">`;
    if (d.dupWeak.length) html += drow("겹약점", "같은 타입 공격에 약점(2배 이상)인 멤버가 2마리 이상 — 상대가 그 타입 기술 하나로 파티 여럿을 압박 가능",
      d.dupWeak.map((w) => typeChip(w.t, ` ×${w.n}`, `${TYPE_KO[w.t]} 타입 공격에 약점인 멤버가 ${w.n}마리`)).join(""));
    if (d.noAnswer.length) html += drow("내성 없음", "이 타입에 약점인 멤버는 있는데, 반감·면역으로 받아줄 멤버가 0마리 — 교체로 받아낼 곳이 없음",
      d.noAnswer.map((t) => typeChip(t, "", `${TYPE_KO[t]} 공격: 약점 멤버 있음 + 반감·면역 멤버 없음`)).join(""));
    if (d.lacks.length) html += drow("부족", "파티 구성 밸런스에서 빠져 있는 요소",
      d.lacks.map((l) => `<span class="reco-tag" title="${LACK_TIPS[l] || ""}">${l}</span>`).join(""));
    html += drow("커버리지", "파티의 공격 타입 = 슬롯에 입력한 기술(있으면) + 자속, 없으면 그 종의 실전 채용(15%+) 공격기",
      `<span class="reco-tag ok" title="사용률 상위 ${d.metaN}마리 중 효과굉장(2배 이상)으로 때릴 수 있는 수 — 높을수록 안 막히는 파티">메타 상위${d.metaN} 중 ${d.covered}마리 효과굉장 가능</span>`
      + (unknown ? `<span class="reco-tag" title="도감 목록 밖 폼(메가 등)은 계산에서 제외">분석 제외 ${unknown}마리(도감 외 폼)</span>` : ""));
    html += `</div>`;

    if (empty > 0) {
      const recos = recommend(members, pool, moveIdx).slice(0, RECO_SHOW_N);
      html += `<div class="reco-head-row"><span class="hint">다음 자리 추천 (근거 태그 = 참고용 휴리스틱 · 클릭하면 빈 슬롯에 들어갑니다)</span>`
        + (empty > 1 ? `<button class="btn small" id="recoAutofill">빈 ${empty}자리 자동 완성</button>` : "") + `</div>`;
      html += recos.map((r, i) => `
        <div class="reco-row" data-i="${i}">
          <img class="reco-spr" src="/sprites/${r.entry.sprite}" alt="" loading="lazy" />
          <div class="reco-main">
            <div><b>${r.entry.ko}</b> ${r.entry.types.map((t) => typeChip(t)).join("")}<span class="reco-rank">#${r.entry.rank}위</span></div>
            <div class="reco-whys">${reasonHtml(r)}</div>
          </div>
          <button class="btn small primary reco-add" data-i="${i}">넣기</button>
        </div>`).join("");
      host.innerHTML = html;
      host.querySelectorAll(".reco-add, .reco-row").forEach((el) => {
        el.addEventListener("click", (ev) => {
          const i = +el.dataset.i; ev.stopPropagation(); fillSlot(recos[i].entry);
        });
      });
      const af = document.getElementById("recoAutofill");
      if (af) af.onclick = (ev) => { ev.stopPropagation(); autofillAll(); };
    } else {
      html += `<div class="hint" style="margin-top:6px;">파티 6마리 완성 — 위 진단 태그로 조합을 점검하세요.</div>`;
      host.innerHTML = html;
    }
  }

  // 빌더가 슬롯 변경 시 호출하는 공개 훅
  window.PCHReco = {
    onPartyChanged() {
      // 슬롯 전부 빈 상태 + 데이터 미로드면 fetch 자체를 미룸(페이지 진입 비용 0)
      if (!pool && (typeof state === "undefined" || state.slots.every((s) => !s))) return;
      ensureData().then(render).catch(() => {
      const host = document.getElementById("recoBody");
      if (host) { host.className = "hint bad"; host.textContent = "추천 데이터 로드 실패(새로고침 해보세요)."; }
    }); },
  };
  document.addEventListener("DOMContentLoaded", () => PCHReco.onPartyChanged());
})();
}

/* node 스모크 테스트용 */
if (typeof module !== "undefined" && module.exports) {
  module.exports = { buildMoveIndex, buildPool, offenseTypes, buildProfile,
    scoreCandidate, recommend, autofill, diagnose,
    RECO_POOL_MAX_RANK, RECO_META_TOP };
}
