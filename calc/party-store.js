// 브라우저 파티 저장소 — localStorage `pch-parties`.
//
// ★모양은 헬퍼 `/api/parties`가 내려주는 것과 **글자 하나까지 같다**:
//     { id, name, updatedAt, members: [{ speciesId, nameKo, abilityKo, itemKo, natureKo, evs{}, movesKo[] }] }
//   같은 모양이라 헬퍼에서 받아 온 JSON을 변환 없이 저장하고, 변환 없이 엔진에 넘긴다.
//   모양이 갈리면 그 순간 양쪽에 변환기가 하나씩 생기고 둘이 어긋나기 시작한다.
//
// ★speciesId는 **음수도 유효한 종족**이다(로토무 워시 등 폼은 master에서 음수 id). 0만 미선택 —
//   헬퍼 쪽 필터(PchWebServer.ToMembers)와 같은 규약이다. `> 0`으로 거르면 폼이 통째로 사라진다.
//
// ★규칙(계산)은 여기 한 줄도 없다. 이 파일은 보관·모양 검사만 한다.

const KEY = 'pch-parties';
const LAST_KEY = 'pch-parties-last';   // 마지막에 고른 파티 — 새로고침해도 그 파티로 돌아오게

/** 헬퍼(데스크탑 프로그램) 로컬 API. 빌더가 쓰는 주소와 같다. */
export const HELPER_BASE = 'http://127.0.0.1:8732';

export const MAX_MEMBERS = 6;

const EV_KEYS = ['hp', 'atk', 'def', 'spa', 'spd', 'spe'];

function readRaw() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/**
 * 저장된 파티 전부(오래된/깨진 값은 모양을 맞춰 돌려준다).
 * ★여기서 한 번 다듬어 두면 화면·엔진 쪽에 "혹시 없으면" 분기가 퍼지지 않는다.
 */
export function load() {
  const list = readRaw();
  if (!Array.isArray(list)) return [];
  return list.map(sane).filter(Boolean);
}

export function save(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.map(sane).filter(Boolean)));
    return true;
  } catch {
    return false;   // 시크릿 모드 등 — 계산 자체는 계속 된다
  }
}

export function get(id) {
  return load().find((p) => p.id === id) ?? null;
}

/** 있으면 갈아끼우고 없으면 붙인다. 돌려주는 값 = 저장된 파티. */
export function upsert(party) {
  const p = sane(party);
  if (!p) return null;

  p.updatedAt = new Date().toISOString();

  const list = load();
  const i = list.findIndex((x) => x.id === p.id);
  if (i >= 0) list[i] = p; else list.push(p);

  save(list);
  return p;
}

export function remove(id) {
  save(load().filter((p) => p.id !== id));
  if (lastId() === id) setLastId(null);
}

export function lastId() {
  try { return localStorage.getItem(LAST_KEY); } catch { return null; }
}

export function setLastId(id) {
  try {
    if (id) localStorage.setItem(LAST_KEY, id);
    else localStorage.removeItem(LAST_KEY);
  } catch { /* 무시 */ }
}

/** 브라우저에서 만든 파티의 id. 헬퍼가 준 id(GUID)와 섞여도 겹치지 않게 접두를 붙인다. */
export function newId() {
  const rnd = (crypto?.randomUUID?.() ?? String(Math.random()).slice(2)).replace(/-/g, '');
  return `w${rnd.slice(0, 16)}`;
}

/** 브라우저에서 만든 id인가(= 헬퍼는 모르는 파티). */
const isLocalId = (id) => String(id || '').startsWith('w');

/** 빈 노력치 한 벌. */
function emptyEvs() {
  return { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 };
}

/**
 * 헬퍼(데스크탑 프로그램)가 켜져 있는가. ★버튼이 아니라 **상태 표시**의 재료다 —
 * 사용자는 연동을 누르는 것이 아니라, 켜져 있으면 저장이 알아서 프로그램까지 간다.
 */
export async function ping() {
  try {
    const res = await fetch(`${HELPER_BASE}/api/parties`, { headers: { Accept: 'application/json' } });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * 헬퍼에서 파티를 가져와 저장소에 얹는다(같은 id면 덮어쓴다).
 * ★헬퍼 연동은 **빌더에서만** 부른다 — 파티를 건드리는 곳은 빌더 하나여야 하기 때문(사용자 지시).
 * @returns {Promise<{added:number, updated:number}>}
 */
export async function importFromHelper() {
  const res = await fetch(`${HELPER_BASE}/api/parties`, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`헬퍼 응답 ${res.status}`);

  const incoming = await res.json();
  if (!Array.isArray(incoming)) throw new Error('헬퍼가 파티 목록을 주지 않았습니다.');

  const list = load();
  let added = 0, updated = 0;

  incoming.forEach((raw) => {
    const p = sane(raw);
    if (!p) return;
    const i = list.findIndex((x) => x.id === p.id);
    if (i >= 0) { list[i] = p; updated++; } else { list.push(p); added++; }
  });

  save(list);
  return { added, updated };
}

/**
 * 파티 하나를 헬퍼로 보낸다(데스크탑 프로그램에 등록).
 *
 * ★같은 파티를 두 번 보내도 헬퍼에 사본이 쌓이지 않게, **먼저 덮어쓰기(PUT)를 시도**하고
 *   헬퍼가 모르는 파티면(404) 새로 만든다(POST). 새로 만들었으면 헬퍼가 정한 id로
 *   **이쪽 파티의 id도 맞춘다** — 그래야 다음 번에도 같은 파티를 갱신하게 된다.
 * @returns {Promise<{id:string, created:boolean}>}
 */
export async function sendToHelper(party) {
  const p = sane(party);
  if (!p) throw new Error('보낼 파티가 없습니다.');

  const body = {
    name: p.name,
    members: p.members.map((m) => ({
      speciesId: m.speciesId, abilityKo: m.abilityKo, itemKo: m.itemKo,
      natureKo: m.natureKo, evs: m.evs, movesKo: m.movesKo,
    })),
  };

  // 브라우저에서 만든 파티(id 접두 w)는 헬퍼가 알 리 없으므로 PUT을 건너뛴다 —
  // 어차피 404가 날 요청이고, 콘솔에 붉은 404를 남겨 진짜 오류를 가린다.
  if (!isLocalId(p.id)) {
    const put = await fetch(`${HELPER_BASE}/api/parties/${encodeURIComponent(p.id)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (put.ok) return { id: p.id, created: false };
    if (put.status !== 404) throw new Error(`헬퍼 응답 ${put.status}`);
  }

  const post = await fetch(`${HELPER_BASE}/api/parties`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!post.ok) throw new Error(`헬퍼 응답 ${post.status}`);

  const saved = await post.json();
  if (saved?.id && saved.id !== p.id) {
    remove(p.id);
    upsert({ ...p, id: saved.id });
    return { id: saved.id, created: true };
  }
  return { id: p.id, created: true };
}

/**
 * 헬퍼에 있는 같은 파티도 지운다.
 * ★없으면 "지웠는데 새로고침하면 되살아나는" 파티가 생긴다 — 다음 연결 때 다시 가져오기 때문.
 *   헬퍼가 모르는 파티(브라우저에서만 만든 것)면 그냥 아무 일도 없다.
 */
export async function deleteFromHelper(id) {
  const res = await fetch(`${HELPER_BASE}/api/parties/${encodeURIComponent(id)}`, { method: 'DELETE' });
  return res.ok;
}

// ── 모양 맞추기 ─────────────────────────────────────────────────────────────

function sane(p) {
  if (!p || typeof p !== 'object') return null;

  return {
    id: String(p.id || newId()),
    name: String(p.name || '새 파티').slice(0, 40),
    updatedAt: p.updatedAt || new Date().toISOString(),
    members: (Array.isArray(p.members) ? p.members : [])
      .map(saneMember)
      .filter(Boolean)
      .slice(0, MAX_MEMBERS),
  };
}

function saneMember(m) {
  if (!m || typeof m !== 'object') return null;

  const id = Math.trunc(Number(m.speciesId) || 0);
  if (id === 0) return null;   // 0 = 미선택. 음수(폼)는 유효하다.

  const evs = emptyEvs();
  if (m.evs && typeof m.evs === 'object') {
    EV_KEYS.forEach((k) => { evs[k] = Math.max(0, Math.trunc(Number(m.evs[k]) || 0)); });
  }

  return {
    speciesId: id,
    nameKo: m.nameKo ? String(m.nameKo) : null,
    abilityKo: m.abilityKo ? String(m.abilityKo) : null,
    itemKo: m.itemKo ? String(m.itemKo) : null,
    natureKo: m.natureKo ? String(m.natureKo) : null,
    evs,
    movesKo: (Array.isArray(m.movesKo) ? m.movesKo : []).slice(0, 4).map((x) => String(x || '')),
  };
}
