// 사이트 데미지 계산기 — 헬퍼(C#) 엔진을 wasm으로 띄워 쓴다.
//
// ★규칙은 한 줄도 여기 없다. 이 파일은 화면과 상태만 다루고,
//   데미지·상성·특성·도구·스피드 판정은 전부 wasm 안의 C# 엔진이 한다.
//   (규칙 사본 = C# 한 벌이 프로젝트 절대 원칙. 여기에 다시 적으면 그 순간 두 벌이 된다.)
//
// ★상태는 통째로 JSON 한 덩어리(S)이고, 계산은 그걸 그대로 엔진에 넘긴다.
//   엔진 쪽은 무상태라 "화면과 다른 값으로 계산되는" 경로가 존재하지 않는다.

import { bootEngine, STAGES } from './pch-wasm.js';
import * as Parties from './party-store.js';

const $ = (id) => document.getElementById(id);

// 타입 칩 색 — 표시 전용(계산과 무관).
const TYPE_COLOR = {
  노말: '#9fa19f', 불꽃: '#e8703a', 물: '#5090d6', 전기: '#f4d23c', 풀: '#63bc5a',
  얼음: '#74cec0', 격투: '#ce4069', 독: '#aa6bc8', 땅: '#d97845', 비행: '#8fa8dd',
  에스퍼: '#f66f87', 벌레: '#90c12c', 바위: '#c7b78b', 고스트: '#5269ad', 드래곤: '#0b6dc3',
  악: '#5a5465', 강철: '#5a8ea2', 페어리: '#ec8fe6',
};
const typeColor = (ko) => TYPE_COLOR[ko] || '#6b7280';

// 스탯 표 행 = H,A,B,C,D,S. 랭크는 HP가 없어 인덱스가 하나 밀린다.
const STAT_KEYS = ['hp', 'atk', 'def', 'spa', 'spd', 'spe'];

// 지닌도구 = **계산에 실제로 걸리는 것만**. PC 헬퍼 /live의 MY_ITEM_GROUPS / OPP_ITEM_GROUPS와 같은 라인업이다.
// ★master.json의 전체 도구 목록(수백 종)을 그대로 노출하면 대부분이 계산에 아무 영향이 없어
//   "골랐는데 숫자가 안 변한다"가 된다. 헬퍼가 고른 이 목록이 곧 "영향이 있는 도구" 집합이다.
const ITEM_GROUPS = [
  { label: '위력', items: ['생명의구슬', '달인의띠', '힘의머리띠', '박식안경', '구애머리띠', '구애안경', '전기구슬'] },
  { label: '스피드', items: ['구애스카프', '검은철구'] },
  { label: '방어', items: ['돌격조끼', '진화의휘석'] },
  { label: '타입강화 ×1.2', items: ['실크스카프', '목탄', '신비의물방울', '기적의씨', '자석', '부드러운모래', '용의이빨', '검은띠', '독바늘', '예리한부리', '휘어진스푼', '은빛가루', '딱딱한돌', '저주의부적', '검은안경', '금속코트', '녹지않는얼음', '요정의깃털'] },
  // 반감열매 = 그 타입 기술을 효과 굉장으로 맞을 때 ×0.5(카리열매만 노말 1배에서도).
  { label: '반감열매 ×0.5', items: ['오카열매', '꼬시개열매', '초나열매', '린드열매', '플카열매', '로플열매', '으름열매', '슈캐열매', '바코열매', '야파열매', '리체열매', '루미열매', '수불열매', '하반열매', '마코열매', '바리비열매', '로셀열매', '카리열매'] },
];
const ITEM_ALL = new Set(ITEM_GROUPS.flatMap((g) => g.items));

/**
 * 도구 후보 목록(그룹 유지).
 * ★목록 밖의 도구(채용률이 얹어준 메가스톤 등)는 맨 위 「지금 지닌 것」으로 세워 잃지 않게 한다.
 */
function itemEntries(cur) {
  const list = [{ grp: null, v: '', label: '없음' }];
  if (cur && !ITEM_ALL.has(cur)) list.push({ grp: '지금 지닌 것', v: cur, label: cur });
  ITEM_GROUPS.forEach((g) => g.items.forEach((it) => list.push({ grp: g.label, v: it, label: it })));
  return list;
}

// 이중 화살표 아이콘 — 아래=0으로, 위=풀투자(32).
const CHEV = {
  down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 6 12 12 19 6"/><polyline points="5 11 12 17 19 11"/></svg>',
  up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 13 12 7 19 13"/><polyline points="5 18 12 12 19 18"/></svg>',
};

let engine = null;
let meta = null;

// ── 상태 ────────────────────────────────────────────────────────────────────

function newSide() {
  return {
    species: '', ability: null, item: null,
    evs: [0, 0, 0, 0, 0, 0],
    mults: [1, 1, 1, 1, 1, 1],
    stages: [0, 0, 0, 0, 0],
    status: 'None',
    types: [],
    hp: 1.0,          // 기본 = 풀피 가정(헬퍼 189차와 같은 규약)
    mega: null,
    moves: ['', '', '', ''],
    misc: 1.0,
    screen: 0,
    tailwind: false,
  };
}

const S = {
  mode: 'quick',
  // 파티 모드 — 고른 파티와 그 안에서 지금 계산 중인 자리(저장된 members 배열의 인덱스).
  partyId: null,
  memberIdx: -1,
  doubles: false,
  weather: 'None',
  terrain: 'None',
  crit: false,
  spread: false,
  oppView: false,
  powerSteps: {},
  critOverride: {},
  my: newSide(),
  opp: newSide(),
};

/** 종족 정보 캐시(이름 → SpeciesDto). 화면 그릴 때마다 엔진을 두드리지 않으려고. */
const spCache = new Map();
function lookup(name) {
  if (!name) return null;
  if (!spCache.has(name)) spCache.set(name, engine.species(name));
  return spCache.get(name);
}

/** 이름이 가리키는 원종 — 메가 후보 목록은 항상 여기서 나온다. */
const speciesOf = (side) => lookup(S[side].species);

/**
 * 화면에 그릴 종족.
 * ★메가를 켜면 그 열이 **통째로** 메가 폼이 된다 — sprite·타입·종족값·실수치·체력바 분모·기본 특성까지.
 *   계산에만 반영하고 화면은 원종으로 두면, 보고 있는 것과 계산되는 것이 달라진다(PC 187차 feedback).
 */
function displayOf(side) {
  const d = S[side];
  return (d.mega ? lookup(d.mega) : null) ?? speciesOf(side);
}

// ── 부팅 ────────────────────────────────────────────────────────────────────

(async function start() {
  try {
    engine = await bootEngine({
      dataBase: '/helper-data',
      onProgress: (s) => { $('bootMsg').textContent = STAGES[s] ?? s; },
    });
    meta = engine.meta;

    fillDatalists();
    buildFieldBar();
    renderSide('my');
    renderSide('opp');
    renderResult();

    $('boot').hidden = true;
    $('app').hidden = false;

    // 채용률은 무거워서(1.1MB) 첫 그림을 막지 않는다 — 뒤에서 받아 두고,
    // 다 받으면 이미 입력돼 있는 상대에게 소급 적용한다.
    engine.loadUsage(false).then((ok) => { if (ok && S.opp.species) applyAssumption(); });
  } catch (e) {
    const b = $('boot');
    b.classList.add('bad');
    b.innerHTML = `계산 엔진을 불러오지 못했습니다 — ${escapeHtml(e.message)}<br>` +
      `<span style="font-size:12px">새로고침해도 같다면 <a href="https://forms.gle/vzavUFn5xFDtdpu66" target="_blank" rel="noopener">제보</a>해 주세요.</span>`;
  }
})();

function fillDatalists() {
  const put = (id, arr) => {
    $(id).innerHTML = arr.map((v) => `<option value="${escapeAttr(v)}">`).join('');
  };
  put('moveList', meta.moves);
  put('abilList', meta.abilities);
  // 도구는 datalist를 쓰지 않는다 — ITEM_GROUPS로 좁힌 select다(계산에 걸리는 것만).
}

// ── 판 상황 바 ──────────────────────────────────────────────────────────────

function buildFieldBar() {
  const opt = (list) => list.map((c) => `<option value="${escapeAttr(c.key)}">${escapeHtml(c.ko)}</option>`).join('');
  $('weather').innerHTML = opt(meta.weathers);
  $('terrain').innerHTML = opt(meta.terrains);

  $('weather').onchange = (e) => { S.weather = e.target.value; recalc(); };
  $('terrain').onchange = (e) => { S.terrain = e.target.value; recalc(); };
  $('crit').onchange = (e) => { S.crit = e.target.checked; recalc(); };
  $('spread').onchange = (e) => { S.spread = e.target.checked; recalc(); };

  seg('fmt', (v) => {
    const on = v === '1';
    if (on === S.doubles) return;
    S.doubles = on;
    // ★형식이 바뀐 순간에만 광역기 기본값을 다시 잡는다(헬퍼 CalcSession.Doubles와 같은 규칙).
    //   싱글에서 끄는 것이 중요하다 — 버튼이 안 보이는데 값만 살아 있으면 데미지가 조용히 ×0.75 된다.
    S.spread = on;
    $('spread').checked = on;
    engine.loadUsage(on).then(() => applyAssumption());
    recalc();
  });

  seg('view', (v) => {
    S.oppView = v === '1';
    document.querySelectorAll('.side').forEach((el) => el.classList.remove('attacking'));
    renderSide('my'); renderSide('opp'); recalc();
  });

  seg('mode', (v) => {
    S.mode = v;
    $('modeHint').textContent = v === 'quick'
      ? '두 포켓몬 이름만 넣으면 바로 계산합니다. 등록 없이 쓸 수 있습니다.'
      : '저장해 둔 내 파티에서 골라 계산합니다. 상대 쪽과 판 상황은 빠른 계산과 똑같습니다.';

    // ★모드가 바꾸는 것은 "내 포켓몬을 어떻게 고르나" 하나뿐이다 — 지금 화면의 값은 건드리지 않는다.
    //   파티로 넘어왔다고 칩 하나를 자동으로 얹으면 방금까지 맞춰 둔 왼쪽 열이 소리 없이 날아간다.
    renderPartyBar();
    renderSide('my');
  });
}

function seg(id, onPick) {
  const box = $(id);
  box.onclick = (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    [...box.children].forEach((c) => c.classList.toggle('on', c === b));
    onPick(b.dataset.v);
  };
}

// ── 파티 줄(내 파티로 계산) ─────────────────────────────────────────────────
//
// ★두 모드는 **같은 화면**이다. 다른 것은 "내 포켓몬을 어떻게 고르나" 하나뿐 —
//   빠른 계산은 이름을 치고, 파티 모드는 아래 칩에서 고른다. 나머지(상대·판 상황·결과)는 100% 공통.
//
// ★★계산기는 파티를 **고르기만** 한다(사용자 지시). 만들기·고치기·지우기·헬퍼 연동은 전부 /builder 소관 —
//   여기에 파티 편집을 조금이라도 두면 빌더와 두 벌이 되고, 어느 쪽이 진짜인지 사용자가 알 수 없게 된다.
//   저장소(localStorage `pch-parties`)는 빌더가 쓰는 것과 같은 한 벌이라 빌더에서 저장하면 여기 바로 뜬다.

/** 지금 고른 파티(없으면 null). 저장소를 매번 읽는다 — 빌더 탭에서 방금 저장한 것도 그대로 보인다. */
function currentParty() {
  if (!S.partyId) return null;
  return Parties.get(S.partyId);
}

/** 파티 → 계산기 슬롯(성격 이름 → 배수, 노력치 32/66 자르기는 엔진이 한다). */
function currentSlots() {
  const p = currentParty();
  return p ? engine.partySlots(p) : [];
}

function renderPartyBar() {
  const host = $('partyBar');
  host.hidden = S.mode !== 'party';
  if (host.hidden) return;

  const list = Parties.load();
  if (S.partyId && !list.some((p) => p.id === S.partyId)) S.partyId = null;
  if (!S.partyId) S.partyId = list.some((p) => p.id === Parties.lastId()) ? Parties.lastId() : (list[0]?.id ?? null);

  const party = currentParty();
  const slots = currentSlots();

  host.innerHTML = `
    <div class="party-top">
      <label style="font-size:12px;color:var(--muted)">파티</label>
      <select id="partyPick"${list.length ? '' : ' disabled'}>${
        list.length
          ? list.map((p) => `<option value="${escapeAttr(p.id)}"${p.id === S.partyId ? ' selected' : ''}>${
              escapeHtml(p.name)} (${p.members.length})</option>`).join('')
          : '<option value="">저장된 파티 없음</option>'
      }</select>
      <a class="pbtn" href="/builder/">파티 빌더에서 편집</a>
    </div>

    ${party ? `<div class="mons">${
      slots.length
        ? slots.map((s) => `
          <button class="mon${s.index === S.memberIdx ? ' on' : ''}" data-slot="${s.index}" title="${escapeAttr(s.nameKo)}">
            ${s.sprite ? `<img src="/sprites/${escapeAttr(s.sprite)}" alt="">` : ''}
            <span class="nm">${escapeHtml(s.nameKo)}</span>
          </button>`).join('')
        : '<span class="party-msg">이 파티에 등록된 포켓몬이 없습니다.</span>'
    }</div>` : ''}

    <div class="party-msg">${
      party
        ? (slots.length ? '칩을 누르면 그 포켓몬으로 계산합니다.' : '<a href="/builder/">파티 빌더</a>에서 포켓몬을 등록하세요.')
        : '저장된 파티가 없습니다. <a href="/builder/">파티 빌더</a>에서 파티를 만들면 여기에 나타납니다.'
    }</div>
  `;

  wirePartyBar();
}

function wirePartyBar() {
  const pick = $('partyPick');
  if (pick) {
    pick.onchange = () => {
      S.partyId = pick.value || null;
      S.memberIdx = -1;   // 파티가 바뀌면 자리 번호는 뜻이 없어진다
      Parties.setLastId(S.partyId);
      renderPartyBar();
    };
  }

  $('partyBar').onclick = (e) => {
    const chip = e.target.closest('[data-slot]');
    if (chip) pickMember(+chip.dataset.slot);
  };
}

/** 칩 선택 = 그 마리로 갈아끼우기. ★랭크·상태이상·체력은 0/기본에서 시작한다(교체하면 풀리는 게임 정합). */
function pickMember(index) {
  const slot = currentSlots().find((s) => s.index === index);
  if (!slot) return;

  const keep = S.my;
  const d = newSide();

  // 벽·순풍·기타 배수는 **마리가 아니라 진영**에 붙는 것이라 교체해도 남는다.
  d.screen = keep.screen;
  d.tailwind = keep.tailwind;
  d.misc = keep.misc;

  d.species = slot.nameKo;
  d.ability = slot.abilityKo;
  d.item = slot.itemKo;
  d.evs = slot.evs.slice();
  d.mults = slot.mults.slice();
  d.moves = [0, 1, 2, 3].map((i) => slot.movesKo[i] || '');

  S.my = d;
  S.memberIdx = index;

  renderPartyBar();
  renderSide('my');
  recalc();
}

// ── 한쪽 패널 ───────────────────────────────────────────────────────────────

/** 그 열의 종족을 파티 칩이 정하는가(= 이름 입력칸 대신 이름표). 상대 쪽은 늘 이름 입력이다. */
const byParty = (side) => S.mode === 'party' && side === 'my';

function renderSide(side) {
  const host = $(side === 'my' ? 'sideMy' : 'sideOpp');
  const d = S[side];
  const base = speciesOf(side);   // 메가 후보는 원종에서만 나온다
  const sp = displayOf(side);     // 그 밖의 표시는 전부 "지금 폼"을 따른다
  const isAttacker = (side === 'my') ? !S.oppView : S.oppView;

  const title = side === 'my' ? '내 포켓몬' : '상대 포켓몬';
  const tag = isAttacker ? '공격' : '수비';

  host.innerHTML = `
    <h2><span class="tag">${tag}</span> ${title}</h2>

    <div class="row headline">
      <img class="sprite" id="${side}Sprite" alt="" ${sp && sp.sprite ? `src="/sprites/${escapeAttr(sp.sprite)}"` : 'style="visibility:hidden"'}>
      <div class="hcol">
        ${byParty(side) ? `
        <div class="picked">${d.species
            ? escapeHtml(d.species)
            : '<span class="none">위 파티 줄에서 포켓몬을 고르세요</span>'}</div>` : `
        <div style="position:relative">
          <input id="${side}Name" placeholder="이름 입력 (예: ${side === 'my' ? '리자몽' : '한카리아스'})"
                 autocomplete="off" value="${escapeAttr(d.species)}">
        </div>`}
        <div class="chips" id="${side}Types" style="margin-top:6px">${
          sp ? sp.types.map((t) => `<span class="tchip" style="background:${typeColor(t)}">${escapeHtml(t)}</span>`).join('') : ''
        }</div>
        ${base && base.megas.length ? `<div class="chips" id="${side}Megas" style="margin-top:6px">${
          base.megas.map((m) => `<button class="achip mega${d.mega === m.nameKo ? ' on' : ''}" data-mega="${escapeAttr(m.nameKo)}">${escapeHtml(m.label)}</button>`).join('')
        }</div>` : ''}
        ${d.mega ? `<div class="desc" style="color:#b9a4ef">${escapeHtml(d.mega)} — 이 열은 메가 폼 기준입니다</div>` : ''}
        ${sp ? hpBlock(side, d, sp) : ''}
      </div>
    </div>

    ${sp ? `<div class="statline" id="${side}Real"></div>` : '<div class="statline">이름을 넣으면 종족값·특성이 채워집니다.</div>'}

    <div class="row">
      <label>특성</label>
      ${sp ? `<div class="chips" style="margin-bottom:5px" id="${side}AbilChips">${
        sp.abilities.map((a) => `<button class="achip${d.ability === a ? ' on' : ''}" data-abil="${escapeAttr(a)}">${escapeHtml(a)}</button>`).join('')
      }</div>` : ''}
      <input id="${side}Abil" list="abilList" placeholder="특성" autocomplete="off" value="${escapeAttr(d.ability || '')}">
      <div class="desc" id="${side}AbilDesc"></div>
    </div>

    <div class="row">
      <label>지닌도구 <span class="note">계산에 걸리는 도구만</span></label>
      <div class="combo">
        <input id="${side}Item" placeholder="없음 — 이름을 치거나 ▾를 누르세요" autocomplete="off" value="${escapeAttr(d.item || '')}">
        <button type="button" class="combo-caret" id="${side}ItemOpen" tabindex="-1" aria-label="목록 열기">▾</button>
      </div>
      <div class="desc" id="${side}ItemDesc"></div>
    </div>

    <div class="row">
      <label>기술 ${isAttacker ? '<span class="note">이 쪽으로 계산됩니다</span>' : ''}</label>
      ${d.moves.map((m, i) => `<input class="mv" data-i="${i}" list="moveList" placeholder="기술 ${i + 1}"
              autocomplete="off" value="${escapeAttr(m)}" style="margin-bottom:4px">`).join('')}
    </div>

    <div class="row inline">
      <div><label>상태이상</label>
        <select id="${side}Status">${meta.statuses.map((c) =>
          `<option value="${escapeAttr(c.key)}"${d.status === c.key ? ' selected' : ''}>${escapeHtml(c.ko)}</option>`).join('')}</select>
      </div>
      <div><label>기타 배수</label>
        <input id="${side}Misc" type="number" step="0.05" min="${meta.miscMin}" max="${meta.miscMax}" value="${d.misc}" inputmode="decimal">
      </div>
    </div>

    <div class="row inline">
      <div><label>벽</label>
        <select id="${side}Screen">${meta.screens.map((c) =>
          `<option value="${escapeAttr(c.key)}"${String(d.screen) === c.key ? ' selected' : ''}>${escapeHtml(c.ko)}</option>`).join('')}</select>
      </div>
      <div style="display:flex;align-items:flex-end;padding-bottom:8px">
        <label style="display:flex;align-items:center;gap:6px;color:var(--muted);font-size:12px;margin:0">
          <input type="checkbox" id="${side}Tail"${d.tailwind ? ' checked' : ''}> 순풍
        </label>
      </div>
    </div>

    <details class="fold" id="${side}TypeFold"${d.types.length ? ' open' : ''}>
      <summary>타입 변경 ${d.types.length ? `— ${d.types.map((t) => koType(t)).join(' / ')}` : '(안 함)'}</summary>
      <div class="chips" id="${side}TypeChips" style="margin-top:6px">${
        meta.types.map((t) => `<button class="achip${d.types.includes(t.key) ? ' on' : ''}" data-type="${escapeAttr(t.key)}"
          style="${d.types.includes(t.key) ? `background:${typeColor(t.ko)};border-color:${typeColor(t.ko)};color:#fff` : ''}">${escapeHtml(t.ko)}</button>`).join('')
      }</div>
    </details>

    ${sp ? `<div class="row"><table class="stats" id="${side}Table"></table></div>` : ''}

    <div class="btnrow">
      ${side === 'opp' ? '<button data-act="assume">채용률 값으로</button>' : ''}
      <button data-act="reset">이 포켓몬 설정 초기화</button>
    </div>
  `;

  wireSide(side);
  if (sp) { renderStatTable(side); refreshDescs(side); }
}

function hpBlock(side, d, sp) {
  const pct = Math.round(d.hp * 1000) / 10;
  const cls = d.hp > 0.5 ? '' : (d.hp > 0.2 ? 'mid' : 'low');
  return `
    <div class="hpwrap">
      <div class="hpbar ${cls}" id="${side}HpBar" title="눌러서/끌어서 조절"><i style="width:${pct}%"></i></div>
      <div class="hprow">
        <span>HP</span>
        <input id="${side}HpNum" type="number" min="1" inputmode="numeric">
        <span id="${side}HpMax"></span>
        <span id="${side}HpAbil" style="margin-left:auto"></span>
      </div>
    </div>`;
}

function koType(key) {
  const t = meta.types.find((x) => x.key === key);
  return t ? t.ko : key;
}

// ── 이벤트 배선 ─────────────────────────────────────────────────────────────

function wireSide(side) {
  const d = S[side];
  const host = $(side === 'my' ? 'sideMy' : 'sideOpp');

  // 이름 — 로스터 한정 자동완성. ★파티 모드의 내 열에는 입력칸이 없다(칩이 종족을 정한다).
  const nameIn = $(`${side}Name`);
  if (nameIn) {
    attachSpeciesAc(nameIn, (name) => {
      if (name === d.species) return;
      d.species = name;
      // 종족이 바뀌면 그 종족에 매인 것들을 놓는다(엉뚱한 종족의 메가/특성으로 계산되지 않게).
      d.mega = null;
      d.ability = null;
      d.hp = 1.0;
      if (side === 'opp') { applyAssumption(false); }
      renderSide(side);
      recalc();
    });
  }

  // 특성
  const abilIn = $(`${side}Abil`);
  abilIn.oninput = () => { d.ability = abilIn.value.trim() || null; syncAbilChips(side); refreshDescs(side); recalc(); };
  host.querySelector(`#${side}AbilChips`)?.addEventListener('click', (e) => {
    const b = e.target.closest('[data-abil]'); if (!b) return;
    d.ability = (d.ability === b.dataset.abil) ? null : b.dataset.abil;
    abilIn.value = d.ability || '';
    syncAbilChips(side); refreshDescs(side); recalc();
  });

  // 도구 — 드롭다운 + 타이핑 검색
  attachItemCombo(side);

  // 메가
  host.querySelector(`#${side}Megas`)?.addEventListener('click', (e) => {
    const b = e.target.closest('[data-mega]'); if (!b) return;
    d.mega = (d.mega === b.dataset.mega) ? null : b.dataset.mega;
    renderSide(side); recalc();
  });

  // 기술
  host.querySelectorAll('input.mv').forEach((el) => {
    el.oninput = () => { d.moves[+el.dataset.i] = el.value.trim(); recalc(); };
  });

  $(`${side}Status`).onchange = (e) => { d.status = e.target.value; recalc(); };
  $(`${side}Misc`).oninput = (e) => { d.misc = clamp(+e.target.value || 1, meta.miscMin, meta.miscMax); recalc(); };
  $(`${side}Screen`).onchange = (e) => { d.screen = +e.target.value; recalc(); };
  $(`${side}Tail`).onchange = (e) => { d.tailwind = e.target.checked; recalc(); };

  // 타입 변경(최대 2)
  host.querySelector(`#${side}TypeChips`)?.addEventListener('click', (e) => {
    const b = e.target.closest('[data-type]'); if (!b) return;
    const k = b.dataset.type;
    const i = d.types.indexOf(k);
    if (i >= 0) d.types.splice(i, 1);
    else { d.types.push(k); if (d.types.length > 2) d.types.shift(); }
    renderSide(side); recalc();
  });

  // 체력바
  const bar = $(`${side}HpBar`);
  if (bar) {
    const setFromEvent = (ev) => {
      const r = bar.getBoundingClientRect();
      if (!r.width) return;
      let f = (ev.clientX - r.left) / r.width;
      f = clamp(f, 0.01, 1);
      if (f >= 0.97) f = 1;   // 멀티스케일이 갈리는 자리 — 스치듯 지나가면 안 된다
      d.hp = f;
      paintHp(side);
      recalc();
    };
    bar.onpointerdown = (ev) => { bar.setPointerCapture(ev.pointerId); setFromEvent(ev); };
    bar.onpointermove = (ev) => { if (bar.hasPointerCapture(ev.pointerId)) setFromEvent(ev); };

    $(`${side}HpNum`).oninput = (e) => {
      const max = currentMaxHp(side);
      if (!max) return;
      const cur = clamp(Math.round(+e.target.value || 0), 1, max);
      d.hp = cur / max;
      paintHp(side, /*skipNum*/ true);
      recalc();
    };
  }

  host.querySelector('.btnrow')?.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act]'); if (!b) return;
    if (b.dataset.act === 'assume') { applyAssumption(true); renderSide(side); recalc(); }
    if (b.dataset.act === 'reset') {
      // ★포켓몬만 남기고 **전부** 초기값으로. 채용률을 다시 얹지 않는다 —
      //   그러면 옆의 [채용률 값으로]와 같은 버튼이 되어 버린다(사용자 지적).
      //   특성·도구·기술까지 비운 순수 무보정 상태가 이 버튼의 뜻이다.
      const keep = d.species;
      S[side] = newSide();
      S[side].species = keep;
      renderSide(side); recalc();
    }
  });
}

function syncAbilChips(side) {
  const d = S[side];
  document.querySelectorAll(`#${side}AbilChips [data-abil]`)
    .forEach((b) => b.classList.toggle('on', b.dataset.abil === d.ability));
}

function refreshDescs(side) {
  const d = S[side];
  const a = $(`${side}AbilDesc`), i = $(`${side}ItemDesc`);
  if (a) a.textContent = d.ability ? engine.describeAbility(d.ability) : '';
  if (i) i.textContent = d.item ? engine.describeItem(d.item, d.species) : '';
}

// ── 스탯 표 ─────────────────────────────────────────────────────────────────

function renderStatTable(side) {
  const d = S[side];
  const t = $(`${side}Table`);
  if (!t) return;

  const rs = engine.realStats(sideDto(side));
  if (!rs) { t.innerHTML = ''; return; }

  // ★엔진이 실제로 받아들인 값을 상태의 진실로 삼는다 — 32/66에 잘렸으면 잘린 값이 화면에 보여야 한다.
  if (rs.evs) d.evs = rs.evs.slice();

  t.innerHTML = `
    <tr><th></th><th>종족</th><th>랭크</th><th>성격</th><th>노력치</th><th>실수치</th></tr>
    ${STAT_KEYS.map((k, i) => {
      const st = i === 0 ? null : i - 1;   // 랭크는 HP가 없다
      const m = d.mults[i];
      const natCls = m > 1 ? 'up' : (m < 1 ? 'down' : '');
      const natTxt = m > 1 ? '↑' : (m < 1 ? '↓' : '–');
      return `<tr>
        <td class="nm">${meta.shortStat[i]} ${meta.statNames[i].slice(0, 2)}</td>
        <td class="bs">${rs.base[k]}</td>
        <td>${st === null ? '' : `<span class="stepper">
            <button data-stage="${st}" data-dir="-1">−</button>
            <span class="v ${d.stages[st] > 0 ? 'up' : d.stages[st] < 0 ? 'down' : ''}">${d.stages[st] > 0 ? '+' : ''}${d.stages[st]}</span>
            <button data-stage="${st}" data-dir="1">+</button></span>`}</td>
        <td>${i === 0 ? '' : `<button class="natbtn ${natCls}" data-nat="${i}" title="무보정 → ↑1.1 → ↓0.9">${natTxt}</button>`}</td>
        <td><span class="evcell">
          <button class="evb min" data-evset="${i}" data-val="0" title="0으로" aria-label="0으로">${CHEV.down}</button>
          <input data-ev="${i}" type="number" min="0" max="${meta.maxEvPerStat}" value="${d.evs[i]}" inputmode="numeric">
          <button class="evb max" data-evset="${i}" data-val="${meta.maxEvPerStat}" title="풀투자 (${meta.maxEvPerStat})" aria-label="풀투자">${CHEV.up}</button>
        </span></td>
        <td class="rl">${rs.real[k]}</td>
      </tr>`;
    }).join('')}
    <tr><td colspan="6" class="evtot" style="text-align:right;padding-top:4px">${evTotalHtml(rs)}</td></tr>`;

  t.onclick = (e) => {
    const st = e.target.closest('[data-stage]');
    if (st) {
      const i = +st.dataset.stage;
      d.stages[i] = clamp(d.stages[i] + (+st.dataset.dir), -6, 6);
      renderStatTable(side); recalc(); return;
    }
    const nb = e.target.closest('[data-nat]');
    if (nb) {
      const i = +nb.dataset.nat;
      // 무보정 → ↑1.1 → ↓0.9 → 무보정 (MonBuild.CycleMult와 같은 순서)
      d.mults[i] = d.mults[i] === 1 ? 1.1 : (d.mults[i] > 1 ? 0.9 : 1);
      renderStatTable(side); recalc(); return;
    }
    const es = e.target.closest('[data-evset]');
    if (es) {
      setEv(side, +es.dataset.evset, +es.dataset.val);
      renderStatTable(side); recalc();
    }
  };

  // ★타이핑 중에는 표를 다시 그리지 않는다.
  //   종전엔 한 글자마다 innerHTML을 갈아끼워 **포커스가 즉시 날아갔다** — "32"를 치려 해도 "3"에서 빠져나왔다.
  //   숫자만 상태에 반영하고, 실수치·합계·체력바처럼 *계산으로 나오는 칸*만 제자리에서 고쳐 쓴다.
  t.oninput = (e) => {
    const ev = e.target.closest('[data-ev]');
    if (!ev) return;
    setEv(side, +ev.dataset.ev, Math.round(+ev.value || 0));
    refreshComputed(side);
    recalc();
  };

  // 칸을 떠날 때 화면 숫자를 **실제 들어간 값**으로 되돌린다(32/66에 잘렸으면 잘린 값이 보여야 한다 — PC와 같은 규약).
  t.onfocusout = (e) => {
    const ev = e.target.closest('[data-ev]');
    if (!ev) return;
    const v = d.evs[+ev.dataset.ev];
    if (+ev.value !== v) ev.value = v;
  };

  paintHp(side);
}

function evTotalHtml(rs) {
  const full = rs.evTotal >= meta.maxEvTotal;
  return `<span style="color:${full ? 'var(--warn)' : 'var(--muted)'}">노력치 합 ${rs.evTotal} / ${meta.maxEvTotal}${full ? ' (가득)' : ''}</span>`;
}

/**
 * 노력치 한 칸을 정한다.
 *
 * ★남은 예산까지만 넣는다 — **방금 손댄 칸이 깎이게** 하기 위해서다.
 *   엔진에 그냥 넘기면 SetEv가 H→S 순으로 예산을 소진하므로, 예산이 모자랄 때
 *   방금 누른 칸이 아니라 **인덱스가 뒤인 칸**(주로 스피드)이 조용히 깎인다.
 *   PC 계산기는 사용자가 고칠 때마다 SetEv를 부르므로 늘 "마지막에 손댄 것"이 깎인다 — 그쪽을 맞춘다.
 */
function setEv(side, i, v) {
  const d = S[side];
  const others = d.evs.reduce((a, b, j) => a + (j === i ? 0 : b), 0);
  d.evs[i] = clamp(v, 0, Math.min(meta.maxEvPerStat, meta.maxEvTotal - others));
}

/** 표를 다시 그리지 않고 *계산으로 나오는 칸*만 갱신한다(타이핑 중 포커스 보존용). */
function refreshComputed(side) {
  const t = $(`${side}Table`);
  if (!t) return;

  const d = S[side];
  const rs = engine.realStats(sideDto(side));
  if (!rs) return;

  const cells = t.querySelectorAll('td.rl');
  STAT_KEYS.forEach((k, i) => { if (cells[i]) cells[i].textContent = rs.real[k]; });

  // 잘린 노력치를 화면에 되돌린다. ★지금 치고 있는 칸만 건드리지 않는다 —
  //   타이핑 도중 숫자를 바꿔치면 입력이 통째로 어긋난다(떠날 때 focusout이 맞춰 준다).
  if (rs.evs) {
    d.evs = rs.evs.slice();
    t.querySelectorAll('input[data-ev]').forEach((el) => {
      const v = d.evs[+el.dataset.ev];
      if (el !== document.activeElement && +el.value !== v) el.value = v;
    });
  }

  const tot = t.querySelector('td.evtot');
  if (tot) tot.innerHTML = evTotalHtml(rs);

  paintHp(side);
}

function currentMaxHp(side) {
  const rs = engine.realStats(sideDto(side));
  return rs ? rs.real.hp : 0;
}

function paintHp(side, skipNum) {
  const d = S[side];
  const bar = $(`${side}HpBar`);
  if (!bar) return;

  const rs = engine.realStats(sideDto(side));
  const max = rs ? rs.real.hp : 0;
  const cur = Math.max(1, Math.round(max * d.hp));

  bar.querySelector('i').style.width = `${d.hp * 100}%`;
  bar.classList.toggle('mid', d.hp <= 0.5 && d.hp > 0.2);
  bar.classList.toggle('low', d.hp <= 0.2);

  if (!skipNum) $(`${side}HpNum`).value = cur;
  $(`${side}HpMax`).textContent = `/ ${max} · ${Math.round(d.hp * 1000) / 10}%`;

  // 체력 조건부 특성(급류·멀티스케일 등) 상태 한 줄 — 판정은 엔진이 한다.
  $(`${side}HpAbil`).textContent = d.ability ? engine.hpAbilityText(d.ability, d.hp) : '';
}

// ── 채용률 추정 ─────────────────────────────────────────────────────────────

/**
 * 상대에게 채용률 1위를 얹는다.
 * @param {boolean} force 사용자가 [채용률 값으로]를 누른 경우 — 손댄 값까지 덮어쓴다.
 */
function applyAssumption(force) {
  const d = S.opp;
  if (!d.species) return;

  const a = engine.assume(d.species, S.doubles);
  if (!a) return;

  d.ability = a.abilityKo ?? d.ability;
  d.item = a.itemKo ?? d.item;
  if (a.mults) d.mults = a.mults.slice();
  if (a.evs) d.evs = a.evs.slice();
  if (a.moves && a.moves.length) {
    d.moves = [0, 1, 2, 3].map((i) => (a.moves[i] ? a.moves[i].ko : ''));
  }
  if (force) { d.stages = [0, 0, 0, 0, 0]; d.status = 'None'; d.types = []; d.misc = 1.0; d.hp = 1.0; }

  if (!force) renderSide('opp');
}

// ── 계산 ────────────────────────────────────────────────────────────────────

function sideDto(side) {
  const d = S[side];
  return {
    species: d.species, ability: d.ability, item: d.item,
    evs: d.evs, mults: d.mults, stages: d.stages,
    status: d.status, types: d.types, hp: d.hp, mega: d.mega,
    moves: d.moves, misc: d.misc, screen: d.screen, tailwind: d.tailwind,
  };
}

function stateDto() {
  return {
    my: sideDto('my'), opp: sideDto('opp'),
    weather: S.weather, terrain: S.terrain,
    crit: S.crit, spread: S.spread, doubles: S.doubles, oppView: S.oppView,
    powerSteps: S.powerSteps, critOverride: S.critOverride,
  };
}

let timer = null;
function recalc() {
  clearTimeout(timer);
  timer = setTimeout(renderResult, 50);
}

function renderResult() {
  const box = $('result');

  if (!S.my.species || !S.opp.species) {
    box.innerHTML = `<h2>결과</h2><div class="empty">양쪽 포켓몬 이름을 넣으면 계산합니다.</div>`;
    return;
  }

  const out = engine.calculate(stateDto());

  if (out.error) {
    box.innerHTML = `<h2>결과</h2><div class="empty">${escapeHtml(out.error)}</div>`;
    return;
  }

  const steps = engine.powerSteps(stateDto());
  const stepByEn = new Map(steps.map((s) => [s.moveEn, s]));

  box.innerHTML = `
    <h2>결과</h2>
    <div class="rhead">${escapeHtml(out.header)}${out.field ? ` · ${escapeHtml(out.field)}` : ''}</div>
    ${out.rows.length ? `
    <table class="rows">
      <tr><th style="width:26px"></th><th>기술</th><th>타입</th><th class="pw">위력</th>
          <th style="text-align:right">데미지</th><th>판정</th><th></th></tr>
      ${out.rows.map((r) => rowHtml(r, stepByEn.get(r.moveEn))).join('')}
    </table>` : '<div class="empty">기술을 넣으면 데미지가 표시됩니다.</div>'}
    ${out.speed ? `<div class="speedline">스피드 <b>${out.speed.mine}</b>${tag(out.speed.mineNote)} vs <b>${out.speed.theirs}</b>${tag(out.speed.theirsNote)} — <b>${escapeHtml(out.speed.verdict)}</b></div>` : ''}
  `;

  box.querySelectorAll('[data-crit]').forEach((el) => {
    el.onchange = () => {
      const en = el.dataset.crit;
      const def = S.crit;   // 확정급소 여부는 엔진이 안다 — 여기선 값만 실어 보낸다
      if (el.checked === def) delete S.critOverride[en];
      else S.critOverride[en] = el.checked;
      renderResult();
    };
  });

  box.querySelectorAll('[data-step]').forEach((el) => {
    el.onclick = () => {
      const en = el.dataset.step;
      const s = stepByEn.get(en);
      if (!s) return;
      const next = clamp((S.powerSteps[en] ?? s.index) + (+el.dataset.dir), 0, s.maxIndex);
      S.powerSteps[en] = next;
      renderResult();
    };
  });
}

function rowHtml(r, step) {
  const cls = r.verdict.includes('확정 1타') ? 'v-ko'
    : r.verdict.includes('난수 1타') ? 'v-maybe'
    : r.verdict.includes('변화기') ? '' : 'v-safe';

  return `<tr>
    <td><input type="checkbox" data-crit="${escapeAttr(r.moveEn || '')}"${r.crit ? ' checked' : ''} title="급소"></td>
    <td class="mv">${escapeHtml(r.moveKo)}${r.spread ? ' <span class="note">광역</span>' : ''}</td>
    <td><span class="tchip" style="background:${typeColor(r.typeKo)}">${escapeHtml(r.typeKo)}</span></td>
    <td class="pw">${powerCell(r, step)}</td>
    <td class="pc" style="text-align:right">${escapeHtml(r.percent)}</td>
    <td class="vd ${cls}">${escapeHtml(r.verdict)}</td>
    <td>${r.note ? `<span class="note">${escapeHtml(r.note)}</span>` : ''}</td>
  </tr>`;
}

/**
 * 위력 칸 = [−] 숫자 [+] 고정 3칸.
 * ★단계 조절이 없는 기술도 **같은 격자**를 쓴다 — 버튼 자리를 비워만 둔다.
 *   버튼을 숫자 오른쪽에 덧붙이면 그 행만 숫자가 왼쪽으로 밀려 열이 어긋난다(사용자 지적).
 */
function powerCell(r, step) {
  const btn = (dir, label) => (step
    ? `<button class="pwb" data-step="${escapeAttr(step.moveEn)}" data-dir="${dir}" title="위력 단계 ${label}">${label}</button>`
    : '<span class="pwb"></span>');

  return `<span class="pwcell">${btn(-1, '−')}<span class="pwv">${r.power || '—'}</span>${btn(1, '+')}</span>`;
}

const tag = (n) => (n ? ` <span class="note">${escapeHtml(n)}</span>` : '');

// ── 도구 콤보(드롭다운 + 타이핑 검색) ───────────────────────────────────────

/**
 * 목록은 좁게 유지하되(계산에 걸리는 도구만) **찾는 방법은 두 가지**로 둔다 —
 * ▾를 눌러 그룹별로 훑거나, 이름 일부를 쳐서 좁히거나.
 * ★목록 밖의 값이 들어가면 안 되므로, 고르지 않고 떠나면 직전 값으로 되돌린다.
 */
function attachItemCombo(side) {
  const d = S[side];
  const input = $(`${side}Item`);
  const caret = $(`${side}ItemOpen`);
  const wrap = input.parentElement;

  let box = null, hits = [], sel = -1;

  const close = () => { box?.remove(); box = null; hits = []; sel = -1; };

  const commit = (v) => {
    d.item = v || null;
    input.value = v || '';
    close();
    refreshDescs(side);
    renderStatTable(side);   // 돌격조끼·진화의휘석처럼 실수치 표시에 걸리는 도구가 있다
    recalc();
  };

  const paint = () => {
    [...box.querySelectorAll('[data-i]')].forEach((el) => el.classList.toggle('sel', +el.dataset.i === sel));
    box.querySelector('.sel')?.scrollIntoView({ block: 'nearest' });
  };

  const open = (filter) => {
    const q = (filter ?? '').trim();
    hits = itemEntries(d.item).filter((e) => !q || e.label.includes(q));

    if (!hits.length) { close(); return; }

    if (!box) { box = document.createElement('div'); box.className = 'ac'; wrap.appendChild(box); }

    let html = '', grp = Symbol('none');
    hits.forEach((e, i) => {
      if (e.grp !== grp) { grp = e.grp; if (grp) html += `<div class="ac-grp">${escapeHtml(grp)}</div>`; }
      html += `<div data-i="${i}">${escapeHtml(e.label)}</div>`;
    });
    box.innerHTML = html;

    sel = Math.max(0, hits.findIndex((e) => e.v === (d.item || '')));
    paint();

    box.querySelectorAll('[data-i]').forEach((el) => {
      el.onmousedown = (ev) => { ev.preventDefault(); commit(hits[+el.dataset.i].v); };
    });
  };

  input.oninput = () => open(input.value);

  // ★들어오는 순간에는 **전체 목록**을 보여주고 지금 값을 강조한다(치기 시작하면 그때부터 좁힌다).
  //   현재 값으로 걸러 버리면 방금 칸을 누른 사람에게 자기가 이미 고른 것 하나만 보인다.
  //   select()로 잡아 두어, 곧바로 치면 옛 값을 지우지 않고도 새로 검색된다.
  input.onfocus = () => { input.select(); open(''); };
  caret.onmousedown = (e) => {
    e.preventDefault();
    if (box) { close(); return; }
    input.focus();
    open('');                 // ▾는 항상 전체 목록
  };

  // 고르지 않고 떠나면 되돌린다 — 목록에 없는 값이 상태로 새는 것을 막는다.
  input.onblur = () => setTimeout(() => {
    close();
    if (input.value !== (d.item || '')) input.value = d.item || '';
  }, 120);

  input.onkeydown = (e) => {
    if (!box) { if (e.key === 'ArrowDown') { e.preventDefault(); open(''); } return; }

    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + hits.length) % hits.length;
      paint();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (hits[sel]) commit(hits[sel].v);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      close();
      input.value = d.item || '';
    }
  };
}

// ── 종족 자동완성 ───────────────────────────────────────────────────────────

function attachSpeciesAc(input, onPick) {
  let box = null, items = [], sel = -1;

  const close = () => { box?.remove(); box = null; items = []; sel = -1; };

  const open = () => {
    const q = input.value.trim();
    if (!q) { close(); return; }
    items = engine.suggest(q, 8);
    if (!items.length) { close(); return; }

    if (!box) {
      box = document.createElement('div');
      box.className = 'ac';
      input.parentElement.appendChild(box);
    }
    sel = 0;
    box.innerHTML = items.map((n, i) => `<div class="${i === sel ? 'sel' : ''}">${escapeHtml(n)}</div>`).join('');
    [...box.children].forEach((el, i) => {
      el.onmousedown = (e) => { e.preventDefault(); input.value = items[i]; close(); onPick(items[i]); };
    });
  };

  input.oninput = open;
  input.onfocus = open;
  input.onblur = () => setTimeout(close, 120);

  input.onkeydown = (e) => {
    if (!box) {
      if (e.key === 'Enter') onPick(input.value.trim());
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      [...box.children].forEach((el, i) => el.classList.toggle('sel', i === sel));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const v = items[sel] ?? input.value.trim();
      input.value = v; close(); onPick(v);
    } else if (e.key === 'Escape') close();
  };
}

// ── 유틸 ────────────────────────────────────────────────────────────────────

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const escapeHtml = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const escapeAttr = escapeHtml;
