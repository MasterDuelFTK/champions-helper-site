/**
 * 파티 공유 게시판 — 클라 로직 (목록/상세/글쓰기, 해시 라우팅)
 *
 * 데이터: API = CF Worker pch-board(D1) / 스프라이트 = 사이트 /sprites/*.png (기존 자산 참조)
 * 글쓰기 = 로컬 헬퍼(127.0.0.1:8732) /api/parties에서 "파티 빌더에 저장된 내 파티"를 불러와 선택(수동 입력 없음).
 * dex.json은 speciesId → sprite 파일명/타입 매핑에만 사용.
 * TYPE_KO / TYPE_COLOR = /calc/engine.js 재사용 (index.html에서 먼저 로드)
 * 보안: 사용자 텍스트는 전부 textContent로만 그림(innerHTML에 사용자 데이터 금지).
 */
"use strict";

const IS_LOCAL = location.hostname === "localhost" || location.hostname === "127.0.0.1";
// Worker 배포 주소(128차 실배포 확인). 로컬 검수 = wrangler dev 8787.
const API_BASE = IS_LOCAL ? "http://127.0.0.1:8787" : "https://pch-board.champions-helper.workers.dev";
// Turnstile 사이트키(공개값). 로컬 = CF 공식 테스트키(항상 통과, 위젯 표시됨).
const TURNSTILE_SITEKEY = IS_LOCAL ? "1x00000000000000000000AA" : "0x4AAAAAADv2PWoiLj6xO4Ig";
const HELPER_BASE = "http://127.0.0.1:8732";   // 로컬 헬퍼(파티 빌더 저장소) — 빌더와 동일
const SPRITE_BASE = "/sprites/";
const SPRITE_RE = /^[A-Za-z0-9_.\-]{1,60}\.png$/;

const EV_LABELS = [["hp","HP"],["atk","공격"],["def","방어"],["spa","특공"],["spd","특방"],["spe","스피드"]];

const $ = (s) => document.querySelector(s);

// ── 상태 ────────────────────────────────────────────────────
const state = {
  sort: "recent", page: 1, total: 0,
  dex: null, dexByKo: null, dexById: null,   // 지연 로드
  parties: null,          // 헬퍼에서 불러온 저장 파티 목록
  pickedId: null,         // 선택한 파티 id
  party: [],              // 게시할 멤버(서버 형식으로 매핑됨)
  partyName: "",
  record: null,           // 선택 파티의 헬퍼 집계 실전적 {wins, losses} (없으면 null)
  tsWidgetId: null,
  liked: loadLiked(),
};

function loadLiked() {
  try { return new Set(JSON.parse(localStorage.getItem("pch-board-liked") || "[]")); }
  catch { return new Set(); }
}
function saveLiked() {
  try { localStorage.setItem("pch-board-liked", JSON.stringify([...state.liked])); } catch {}
}

// ── 공통 헬퍼 ───────────────────────────────────────────────
function el(tag, cls, text) {
  const d = document.createElement(tag);
  if (cls) d.className = cls;
  if (text !== undefined && text !== null) d.textContent = text;
  return d;
}
// sprite 파일명이 유효하면 <img>, 아니면 첫 글자 플레이스홀더
function spriteEl(file, ko) {
  if (typeof file === "string" && SPRITE_RE.test(file)) {
    const img = document.createElement("img");
    img.src = SPRITE_BASE + file;
    img.loading = "lazy";
    img.title = ko || "";
    img.onerror = () => { img.replaceWith(el("span", "spr-ph", (ko || "?").slice(0, 1))); };
    return img;
  }
  return el("span", "spr-ph", (ko || "?").slice(0, 1));
}
// 헬퍼 집계 실전적 배지 (직접 입력 불가 — 프로그램이 게임 종료 로그로 자동 집계)
function recordBadge(rec) {
  const total = rec.wins + rec.losses;
  const rate = total ? Math.round((rec.wins / total) * 100) : 0;
  const b = el("span", "badge win", `✓ 전적 ${rec.wins}승 ${rec.losses}패 · ${rate}%`);
  b.title = "Champions Helper 프로그램이 자동 집계한 실제 전적입니다.";
  return b;
}
function timeAgo(ms) {
  const d = Date.now() - ms;
  if (d < 60_000) return "방금 전";
  if (d < 3_600_000) return Math.floor(d / 60_000) + "분 전";
  if (d < 86_400_000) return Math.floor(d / 3_600_000) + "시간 전";
  if (d < 7 * 86_400_000) return Math.floor(d / 86_400_000) + "일 전";
  const t = new Date(ms);
  return `${t.getFullYear()}.${String(t.getMonth() + 1).padStart(2, "0")}.${String(t.getDate()).padStart(2, "0")}`;
}
async function api(path, method, body, headers) {
  const opt = { method: method || "GET", headers: { "Content-Type": "application/json", ...(headers || {}) } };
  if (body !== undefined) opt.body = JSON.stringify(body);
  const r = await fetch(API_BASE + path, opt);
  let d = null;
  try { d = await r.json(); } catch {}
  if (!r.ok) throw new Error((d && d.error) || ("요청 실패 (" + r.status + ")"));
  return d;
}
async function helperApi(path) {
  const r = await fetch(HELPER_BASE + path);
  if (!r.ok) throw new Error("helper " + r.status);
  return r.json();
}
async function loadDex() {
  if (state.dex) return;
  const dexRaw = await fetch("/data/dex.json").then((r) => r.json());
  state.dex = dexRaw.dex || [];
  state.dexByKo = new Map(state.dex.map((e) => [e.ko, e]));
  state.dexById = new Map(state.dex.map((e) => [e.id, e]));
}
function typeChips(entry) {
  const box = el("span");
  if (entry && Array.isArray(entry.types)) {
    for (const t of entry.types) {
      const c = el("span", "type-chip", (typeof TYPE_KO !== "undefined" && TYPE_KO[t]) || t);
      if (typeof TYPE_COLOR !== "undefined" && TYPE_COLOR[t]) c.style.background = TYPE_COLOR[t];
      box.appendChild(c);
    }
  }
  return box;
}

// ── 라우팅 ─────────────────────────────────────────────────
function router() {
  const h = location.hash || "#/";
  const postM = h.match(/^#\/post\/(\d+)$/);
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("on"));
  if (postM) { $("#view-detail").classList.add("on"); renderDetail(parseInt(postM[1], 10)); }
  else if (h === "#/write") { $("#view-write").classList.add("on"); openWrite(); }
  else { $("#view-list").classList.add("on"); if (!$("#postList").childElementCount) refreshList(); }
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", router);

// ── 목록 ────────────────────────────────────────────────────
async function refreshList() {
  state.page = 1;
  $("#postList").replaceChildren(el("div", "hint", "불러오는 중…"));
  await fetchList(true);
}
async function fetchList(replace) {
  let d;
  try { d = await api(`/api/posts?page=${state.page}&sort=${state.sort}`); }
  catch (e) {
    $("#postList").replaceChildren(el("div", "hint bad", "목록을 불러오지 못했습니다: " + e.message));
    $("#moreBtn").style.display = "none";
    return;
  }
  state.total = d.total;
  const cards = d.posts.map(postCard);
  const host = $("#postList");
  if (replace) host.replaceChildren(...cards);
  else host.append(...cards);
  if (!d.total) host.replaceChildren(el("div", "hint", "아직 글이 없습니다. 첫 파티를 공유해 보세요!"));
  $("#moreBtn").style.display = state.page * d.pageSize < d.total ? "" : "none";
}
function postCard(p) {
  const card = el("div", "post-card");
  card.appendChild(el("div", "post-title", p.title));
  const meta = el("div", "post-meta");
  meta.appendChild(el("span", null, p.nickname));
  meta.appendChild(el("span", null, timeAgo(p.createdAt)));
  meta.appendChild(el("span", "likes-chip", "♥ " + p.likes));
  if (p.record) meta.appendChild(recordBadge(p.record));
  card.appendChild(meta);
  const sp = el("div", "post-sprites");
  for (const m of (p.party || []).slice(0, 6)) sp.appendChild(spriteEl(m.sprite, m.ko));
  card.appendChild(sp);
  card.onclick = () => { location.hash = "#/post/" + p.id; };
  return card;
}

// ── 상세 ────────────────────────────────────────────────────
async function renderDetail(id) {
  const host = $("#detailCard");
  host.replaceChildren(el("div", "hint", "불러오는 중…"));
  let d;
  try {
    [d] = await Promise.all([api("/api/posts/" + id), loadDex()]);
  } catch (e) {
    host.replaceChildren(el("div", "hint bad", "글을 불러오지 못했습니다: " + e.message));
    return;
  }
  const p = d.post;
  host.replaceChildren();

  const head = el("div", "detail-head");
  const left = el("div");
  const h = el("h2", null, p.title); h.style.cssText = "margin:0 0 6px; font-size:20px;";
  left.appendChild(h);
  const meta = el("div", "post-meta");
  meta.appendChild(el("span", null, p.nickname));
  meta.appendChild(el("span", null, timeAgo(p.createdAt)));
  if (p.record) meta.appendChild(recordBadge(p.record));
  left.appendChild(meta);
  head.appendChild(left);
  const btns = el("div", "row");
  const copyBtn = el("button", "btn", "⧉ 빌더로 복사");
  copyBtn.onclick = () => copyToBuilder(p);
  const delBtn = el("button", "btn danger", "삭제");
  delBtn.onclick = () => removePost(p.id);
  btns.append(copyBtn, delBtn);
  head.appendChild(btns);
  host.appendChild(head);

  const grid = el("div", "party-grid");
  for (const m of (p.party || []).slice(0, 6)) grid.appendChild(memberCard(m));
  host.appendChild(grid);

  host.appendChild(el("div", "post-content", p.content));

  const likeRow = el("div", "row");
  likeRow.style.cssText = "justify-content:center; margin-top:14px;";
  const likeBtn = el("button", "btn like-btn", "♥ " + p.likes);
  if (state.liked.has(p.id)) likeBtn.classList.add("liked");
  likeBtn.onclick = async () => {
    try {
      const r = await api("/api/posts/" + p.id + "/like", "POST", {});
      likeBtn.textContent = "♥ " + r.likes;
      likeBtn.classList.add("liked");
      state.liked.add(p.id); saveLiked();
    } catch (e) { alert("좋아요 실패: " + e.message); }
  };
  likeRow.appendChild(likeBtn);
  host.appendChild(likeRow);
}
function memberCard(m) {
  const card = el("div", "member");
  const top = el("div", "m-top");
  top.appendChild(spriteEl(m.sprite, m.ko));
  const nameBox = el("div");
  nameBox.appendChild(el("div", "m-name", m.ko));
  nameBox.appendChild(typeChips(state.dexById && state.dexById.get(m.id)));
  top.appendChild(nameBox);
  card.appendChild(top);

  const info = [];
  if (m.ability) info.push("특성 " + m.ability);
  if (m.nature) info.push("성격 " + m.nature);
  if (m.item) info.push("도구 " + m.item);
  if (info.length) card.appendChild(el("div", "m-line", info.join(" · ")));

  if (m.moves && m.moves.length) {
    const mv = el("div", "m-line");
    for (const v of m.moves.slice(0, 4)) mv.appendChild(el("span", "move-chip", v));
    card.appendChild(mv);
  }
  const evTxt = EV_LABELS.filter(([k]) => m.evs && m.evs[k] > 0).map(([k, ko]) => ko + m.evs[k]).join(" ");
  if (evTxt) card.appendChild(el("div", "m-line", "노력치 " + evTxt));
  return card;
}
function copyToBuilder(p) {
  const members = (p.party || []).slice(0, 6).map((m) => ({
    speciesId: m.id, nameKo: m.ko,
    abilityKo: m.ability || null, natureKo: m.nature || null,
    evs: m.evs || {}, movesKo: (m.moves || []).concat(["", "", "", ""]).slice(0, 4),
    itemKo: m.item || null,
  }));
  try { localStorage.setItem("pch-board-import", JSON.stringify({ name: p.title, members })); }
  catch { alert("복사 실패(브라우저 저장소 접근 불가)"); return; }
  location.href = "/builder/";
}
async function removePost(id) {
  const pw = prompt("삭제용 비밀번호를 입력하세요.");
  if (pw === null) return;
  try {
    await api("/api/posts/" + id, "DELETE", { password: pw });
    alert("삭제되었습니다.");
    location.hash = "#/";
    refreshList();
  } catch (e) { alert(e.message); }
}

// ── 글쓰기 — 빌더 저장 파티에서 선택(수동 입력 없음) ────────
async function openWrite() {
  mountTurnstile();
  try { await loadDex(); }
  catch { $("#writeHint").textContent = "데이터 로드 실패 — 새로고침 후 다시 시도하세요."; $("#writeHint").className = "hint bad"; return; }
  renderPartyPreview();
  renderRecordRow();
  await loadHelperParties();
}
async function loadHelperParties() {
  const hint = $("#partyHint");
  hint.textContent = "저장된 파티 불러오는 중…"; hint.className = "hint";
  let list;
  try { list = await helperApi("/api/parties"); }
  catch {
    state.parties = null;
    $("#wOffline").style.display = "block";
    $("#wPartyList").replaceChildren();
    hint.textContent = "프로그램(헬퍼) 연결 실패"; hint.className = "hint bad";
    return;
  }
  $("#wOffline").style.display = "none";
  state.parties = list || [];
  if (!state.parties.length) {
    $("#wPartyList").replaceChildren(el("div", "hint", "저장된 파티가 없습니다 — 파티 빌더에서 먼저 만들어 저장하세요."));
    hint.textContent = ""; return;
  }
  $("#wPartyList").replaceChildren(...state.parties.map((p) => {
    const d = el("div", "pitem" + (p.id === state.pickedId ? " on" : ""));
    d.appendChild(el("span", "pname", p.name));
    d.appendChild(el("span", "pcount", (p.members ? p.members.length : 0) + "마리"));
    d.onclick = () => pickParty(p.id);
    return d;
  }));
  hint.textContent = "공유할 파티를 클릭하세요."; hint.className = "hint";
}
async function pickParty(id) {
  const hint = $("#partyHint");
  let p;
  try { p = await helperApi("/api/parties/" + id); }
  catch { hint.textContent = "파티를 불러오지 못했습니다."; hint.className = "hint bad"; return; }
  state.pickedId = id;
  state.partyName = p.name || "";
  // 실전적 조회 — 구버전 헬퍼(엔드포인트 없음)나 실패는 "전적 없음"으로 처리
  state.record = null;
  try {
    const r = await helperApi("/api/parties/" + id + "/record");
    if (r && Number.isInteger(r.wins) && Number.isInteger(r.losses) && r.wins + r.losses > 0)
      state.record = { wins: r.wins, losses: r.losses };
  } catch {}
  renderRecordRow();
  // 헬퍼 멤버 → 게시 형식 매핑 (sprite/타입은 dex.json에서 speciesId→ko 순으로 조회)
  state.party = (p.members || []).slice(0, 6).map((m) => {
    const e = state.dexById.get(m.speciesId) || state.dexByKo.get(m.nameKo) || null;
    return {
      id: m.speciesId, ko: m.nameKo, sprite: e ? e.sprite : null,
      ability: m.abilityKo || null, nature: m.natureKo || null, item: m.itemKo || null,
      moves: (m.movesKo || []).map((v) => (v || "").trim()).filter(Boolean).slice(0, 4),
      evs: m.evs || {},
    };
  });
  // 선택 표시 + 미리보기 + 제목 비어 있으면 파티명 자동 채움
  [...$("#wPartyList").children].forEach((c, i) => c.classList.toggle("on", state.parties[i] && state.parties[i].id === id));
  renderPartyPreview();
  if (!$("#wTitle").value.trim() && state.partyName) $("#wTitle").value = state.partyName.slice(0, 100);
  hint.textContent = `'${state.partyName}' 선택됨 (${state.party.length}마리)`; hint.className = "hint ok";
}
// 전적 행 — 실전적 있으면 "공개" 체크박스, 없으면 안내문. 직접 입력 UI는 존재하지 않음.
function renderRecordRow() {
  const row = $("#recordRow"), none = $("#recordNone");
  if (state.record) {
    const t = state.record.wins + state.record.losses;
    const rate = Math.round((state.record.wins / t) * 100);
    $("#recordText").textContent = `이 파티의 실제 전적 ${state.record.wins}승 ${state.record.losses}패 (승률 ${rate}%) 을 함께 공개`;
    $("#wRecordShare").checked = true;
    row.style.display = ""; none.style.display = "none";
  } else if (state.pickedId !== null) {
    row.style.display = "none";
    none.textContent = "이 파티는 집계된 전적이 없어 전적 없이 게시됩니다. (전적은 프로그램이 게임 결과로 자동 집계 — 직접 입력할 수 없습니다)";
    none.style.display = "";
  } else {
    row.style.display = "none"; none.style.display = "none";
  }
}
function renderPartyPreview() {
  const host = $("#wSlots");
  if (!state.party.length) { host.replaceChildren(); return; }
  host.replaceChildren(...state.party.map((m) => {
    const d = el("div", "w-slot");
    d.appendChild(spriteEl(m.sprite, m.ko));
    d.appendChild(el("div", "s-name", m.ko));
    return d;
  }));
}

// Turnstile — 글쓰기 뷰 첫 진입 시 스크립트 지연 로드 + 위젯 렌더
function mountTurnstile() {
  if (!TURNSTILE_SITEKEY) { $("#tsWidget").replaceChildren(el("span", "hint bad", "⚠ 스팸 방지 키 미설정 — 게시 불가(배포 설정 필요)")); return; }
  if (state.tsWidgetId !== null) return;   // 이미 렌더됨
  const render = () => { state.tsWidgetId = window.turnstile.render("#tsWidget", { sitekey: TURNSTILE_SITEKEY, theme: "dark" }); };
  if (window.turnstile) { render(); return; }
  const s = document.createElement("script");
  s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=__pchTsReady";
  window.__pchTsReady = render;
  document.head.appendChild(s);
}

async function submitPost() {
  const hint = $("#writeHint");
  const set = (t, bad) => { hint.textContent = t; hint.className = "hint" + (bad ? " bad" : " ok"); };
  const title = $("#wTitle").value.trim();
  const nickname = $("#wNick").value.trim();
  const password = $("#wPw").value;
  const content = $("#wContent").value.trim();
  if (!state.party.length) return set("공유할 파티를 먼저 선택하세요.", true);
  if (!title) return set("제목을 입력하세요.", true);
  if (!nickname) return set("닉네임을 입력하세요.", true);
  if (password.length < 4) return set("삭제용 비밀번호는 4자 이상 입력하세요.", true);
  if (!content) return set("파티 설명을 입력하세요.", true);
  let token = "";
  if (window.turnstile && state.tsWidgetId !== null) token = window.turnstile.getResponse(state.tsWidgetId) || "";
  if (TURNSTILE_SITEKEY && !token) return set("스팸 방지 확인을 완료해 주세요.", true);

  $("#submitBtn").disabled = true;
  set("게시 중…", false);
  try {
    const r = await api("/api/posts", "POST", {
      title, nickname, password, content,
      record: state.record && $("#wRecordShare").checked ? state.record : null,
      party: state.party, turnstileToken: token,
    });
    // 폼 초기화 후 상세로 이동
    state.party = []; state.pickedId = null; state.partyName = ""; state.record = null;
    renderRecordRow(); renderPartyPreview();
    ["#wTitle", "#wNick", "#wPw", "#wContent"].forEach((s) => { $(s).value = ""; });
    if (window.turnstile && state.tsWidgetId !== null) window.turnstile.reset(state.tsWidgetId);
    $("#postList").replaceChildren();   // 목록 캐시 무효화(다음 진입 시 재로드)
    location.hash = "#/post/" + r.id;
  } catch (e) {
    set("게시 실패: " + e.message, true);
  } finally {
    $("#submitBtn").disabled = false;
  }
}

// ── 이벤트 바인딩 + 시작 ────────────────────────────────────
$("#sortRecent").onclick = () => { state.sort = "recent"; $("#sortRecent").classList.add("on"); $("#sortLikes").classList.remove("on"); refreshList(); };
$("#sortLikes").onclick = () => { state.sort = "likes"; $("#sortLikes").classList.add("on"); $("#sortRecent").classList.remove("on"); refreshList(); };
$("#goWrite").onclick = () => { location.hash = "#/write"; };
$("#backBtn").onclick = () => { location.hash = "#/"; };
$("#backBtn2").onclick = () => { location.hash = "#/"; };
$("#moreBtn").onclick = () => { state.page++; fetchList(false); };
$("#reloadParties").onclick = loadHelperParties;
$("#submitBtn").onclick = submitPost;

router();
