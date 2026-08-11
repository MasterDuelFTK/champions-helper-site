// PCH 계산 엔진 부트스트랩 — 브라우저에서 헬퍼(C#)와 같은 엔진을 띄운다.
//
// ★이 파일은 배선만 한다. 데미지 규칙은 한 줄도 여기 없다 — 전부 wasm 안의 C# 엔진이 판정한다.
//   (규칙 사본은 C# 한 벌이 절대 원칙. JS에 규칙을 다시 적으면 그 순간 두 벌이 된다.)
//
// ★이 파일은 사이트 /calc/ 로 그대로 복사돼 쓰인다. 고칠 때 양쪽을 같이 밀 것.
//   원본 = app\src\PCH.Web\wwwroot\main.js
//
// 쓰는 법:
//   import { bootEngine } from './main.js';
//   const engine = await bootEngine({ dataBase: '/helper-data', onProgress: s => ... });
//   engine.calculate(state)   // → { header, rows, error, speed, field }

import { dotnet } from './_framework/dotnet.js';

/** 진행 단계 라벨 — 로딩 화면 문구에 쓴다. */
export const STAGES = {
  runtime: '계산 엔진 불러오는 중',
  data: '포켓몬 데이터 불러오는 중',
  ready: '준비 완료',
};

async function fetchBytes(url) {
  const res = await fetch(url, { cache: 'force-cache' });
  if (!res.ok) throw new Error(`${url} → ${res.status}`);
  return new Uint8Array(await res.arrayBuffer());
}

/** 빈 문자열 = "못 찾음"이라는 파사드 규약. null로 바꿔 준다. */
function parseOrNull(json) {
  return json ? JSON.parse(json) : null;
}

/**
 * 엔진을 띄운다.
 *
 * @param {object}   opts
 * @param {string}   opts.dataBase   master/sprites/move-usage 가 있는 경로(사이트는 '/helper-data').
 * @param {function} opts.onProgress 단계 콜백(STAGES 키를 받는다).
 */
export async function bootEngine({ dataBase = '/helper-data', onProgress = () => {} } = {}) {
  onProgress('runtime');

  // ★dotnet.run()은 부르지 않는다 — Main을 돌릴 이유가 없고, Main이 반환하면
  //   런타임이 "종료됨"으로 표시돼 이후 [JSExport] 호출이 막힐 수 있다.
  //   getAssemblyExports는 run 없이 동작한다(공식 wasmbrowser 패턴).
  const { getAssemblyExports, getConfig } = await dotnet.withDiagnosticTracing(false).create();

  const asm = await getAssemblyExports(getConfig().mainAssemblyName);
  const F = asm.PCH.Web.CalcFacade;

  onProgress('data');

  // sprites.json은 없어도 돌아간다(자동완성이 로스터 대신 master 전체로 넓어질 뿐).
  const [master, sprites] = await Promise.all([
    fetchBytes(`${dataBase}/master.json`),
    fetchBytes(`${dataBase}/sprites.json`).catch(() => new Uint8Array(0)),
  ]);

  const init = JSON.parse(F.Init(master, sprites));
  if (!init.ok) throw new Error(`엔진 초기화 실패: ${init.error}`);

  const meta = JSON.parse(F.Meta());

  // 채용률은 **선택**이고 무겁다(싱글 1.1MB + 더블 1.05MB). 첫 계산을 막지 않도록
  // 여기서 받지 않고, 필요해질 때 loadUsage()로 뒤늦게 싣는다.
  const usageLoaded = { single: false, double: false };

  async function loadUsage(doubles = false) {
    const key = doubles ? 'double' : 'single';
    if (usageLoaded[key]) return true;

    const file = doubles ? 'move-usage-double.json' : 'move-usage.json';
    try {
      const bytes = await fetchBytes(`${dataBase}/${file}`);
      const res = JSON.parse(F.LoadUsage(bytes, doubles));
      usageLoaded[key] = res.ok;
      return res.ok;
    } catch {
      return false;   // 통계가 없어도 계산 자체는 된다
    }
  }

  onProgress('ready');

  return {
    speciesCount: init.speciesCount,
    rosterCount: init.rosterCount,
    meta,

    loadUsage,
    usageReady: (doubles = false) => usageLoaded[doubles ? 'double' : 'single'],

    /** 이름 자동완성(챔피언스 로스터 235종). */
    suggest: (prefix, max = 8) => JSON.parse(F.Suggest(prefix ?? '', max)),

    /** 종족 정보(타입·종족값·특성·메가 후보·sprite). 못 짚으면 null. */
    species: (nameKo) => parseOrNull(F.SpeciesInfo(nameKo ?? '')),

    /** 기술 정보. 못 짚으면 null. */
    move: (nameKo) => parseOrNull(F.MoveInfo(nameKo ?? '')),

    /** 채용률 1위 추정. 통계 미로드거나 없으면 null. */
    assume: (nameKo, doubles = false) => parseOrNull(F.Assume(nameKo ?? '', !!doubles)),

    describeAbility: (ko) => F.DescribeAbility(ko ?? ''),
    describeItem: (itemKo, speciesKo) => F.DescribeItem(itemKo ?? '', speciesKo ?? ''),

    /** 체력 조건부 특성 문구(급류/멀티스케일 등). 해당 없으면 ''. */
    hpAbilityText: (abilityKo, hpFraction) => F.HpAbilityText(abilityKo ?? '', hpFraction),

    /** 종족값·실수치·노력치 합. 계산과 같은 경로다. */
    realStats: (side) => parseOrNull(F.RealStats(JSON.stringify(side))),

    /**
     * 저장된 파티(헬퍼 /api/parties와 같은 모양) → 계산기 슬롯 목록.
     * 성격 이름 → 스탯 배수, 노력치 32/66 자르기까지 엔진이 한다.
     */
    partySlots: (party) => JSON.parse(F.PartySlots(JSON.stringify(party ?? {}))),

    /** 본체 — 지금 상태로 계산. */
    calculate: (state) => JSON.parse(F.Calculate(JSON.stringify(state))),

    /** 위력 단계가 있는 기술(−/+ 줄). */
    powerSteps: (state) => JSON.parse(F.PowerSteps(JSON.stringify(state))),

    /** PC·앱과 수치가 같은지 확인하는 골든 세트(CalcSamples). 개발용. */
    selfTest: () => F.SelfTest(),

    /** 초기화가 어디서 어긋났는지(파일 없음 vs 파싱 깨짐). 개발용. */
    diag: () => F.Diag(),
  };
}
