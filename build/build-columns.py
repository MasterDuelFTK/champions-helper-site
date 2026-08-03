# -*- coding: utf-8 -*-
"""
183차 — 공략 칼럼 생성기 (AdSense 3차 거절 대응).

왜 생성기로 만드나:
  칼럼 = 사람이 쓴 글이지만, 껍데기(헤더·스타일·푸터·메타)는 141차 칼럼 7편과 byte 단위로
  같아야 한다. 손으로 복사하면 nav 링크 하나만 어긋나도 124차가 잡아둔 "전 페이지 헤더 9링크
  byte 동일" 규칙이 깨진다. 그래서 껍데기는 기존 칼럼(speed-guide)에서 런타임에 떼어 쓰고,
  이 파일에는 본문만 둔다.

★본문은 자동생성이 아니다. 아래 COLUMNS 의 body 는 사람이 쓴 원고이고,
  숫자는 전부 helper-data/move-usage(-double).json 실측을 옮긴 것이다.
  데이터가 갱신되면 숫자가 낡으므로 SNAPSHOT 표기를 함께 갱신할 것.

실행: python build-columns.py   (사이트 루트의 build/ 에서)
"""
import io, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(os.path.join(HERE, ".."))
SHELL_SRC = os.path.join(SITE, "guide", "speed-guide", "index.html")

# 본문 숫자의 출처 시점. 데이터 갱신 후 원고를 손볼 때 같이 갱신한다.
SNAPSHOT = "시즌 M-4 · 2026-08-02 집계분"

_shell = io.open(SHELL_SRC, encoding="utf-8").read()
STYLE = _shell[_shell.find("<style>"): _shell.find("</style>") + len("</style>")]
HEADER = _shell[_shell.find("<body>"): _shell.find("<main class=\"wrap\">")]
FOOTER = _shell[_shell.find("</main>"):]

PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1395643596867142" crossorigin="anonymous"></script>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<title>{title} | Champions Helper</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="https://champions-helper.com/guide/{slug}/" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="Champions Helper" />
<meta property="og:locale" content="ko_KR" />
<meta property="og:url" content="https://champions-helper.com/guide/{slug}/" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{ogdesc}" />
<meta name="twitter:card" content="summary" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{ogdesc}" />
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "{ogdesc}",
  "inLanguage": "ko",
  "datePublished": "{pub}",
  "dateModified": "{pub}",
  "url": "https://champions-helper.com/guide/{slug}/",
  "author": {{ "@type": "Organization", "name": "Champions Helper" }},
  "publisher": {{ "@type": "Organization", "name": "Champions Helper" }},
  "isPartOf": {{ "@type": "WebSite", "name": "Champions Helper", "url": "https://champions-helper.com/" }}
}}
</script>
{style}
  <link rel="stylesheet" href="/site-header.css" />
</head>
{header}<main class="wrap">
  <article class="article">
    <div class="crumb"><a href="/guide/">가이드</a> › {crumb}</div>
    <h1>{h1}</h1>
    <p class="lead">{lead}</p>
{body}
    <div class="related">
      <h3>함께 읽기</h3>
{related}
    </div>
    <p class="note">본문 수치는 <strong>{snapshot}</strong> 기준입니다. 원본 데이터는 12시간마다 자동 갱신되므로
      최신 순위·채용률은 <a href="/battle-data/">배틀데이터</a>와 <a href="/pokedex/">도감</a>에서 확인할 수 있습니다.
      집계 방법과 출처는 <a href="/about/">사이트 소개</a>에 정리해 두었습니다.</p>
  </article>
{footer}"""

PUB = "2026-08-03"

COLUMNS = []


def col(slug, title, desc, ogdesc, crumb, h1, lead, body, related=()):
    COLUMNS.append(dict(slug=slug, title=title, desc=desc, ogdesc=ogdesc,
                        crumb=crumb, h1=h1, lead=lead, body=body,
                        related="\n".join(f'      <a href="{u}">{t} →</a>' for u, t in related)))


# ══════════════════════════════════════════════════════════════════════
# 1. 무엇에 죽는가 — 패배 기록으로 본 진짜 위협
# ══════════════════════════════════════════════════════════════════════
col(
    "what-kills-you",
    "무엇에 죽는가 — 랭크배틀 패배 기록으로 본 진짜 위협",
    "포켓몬 챔피언스 랭크배틀에서 상위 50종이 실제로 어떤 기술에 쓰러졌는지 집계했습니다. 지진 19.3%, 땅 타입 19.9% — 채용률 순위가 아니라 패배 기록이 말하는 진짜 위협을 정리합니다.",
    "상위 50종이 실제로 쓰러진 기술 전수 집계. 채용률이 아닌 패배 기록 기준.",
    "무엇에 죽는가",
    "무엇에 죽는가 — 랭크배틀 패배 기록으로 본 진짜 위협",
    "파티를 짤 때 우리는 보통 채용률 순위를 봅니다. 하지만 채용률이 높은 기술과 실제로 내 포켓몬을 쓰러뜨리는 기술은 같지 않습니다. 이 글은 공식 랭크배틀 데이터에서 <strong>상위 50종이 실제로 어떤 기술에 쓰러졌는지</strong>만 뽑아 집계한 것입니다.",
    """
    <h2>왜 채용률이 아니라 패배 기록인가</h2>
    <p>채용률은 "몇 명이 이 기술을 넣었나"입니다. 넣어놓고 한 번도 안 쓴 기술도, 매 판 게임을 끝낸 기술도 똑같이 1로 셉니다. 그래서 채용률만 보면 <strong>안 쓰이는 보험 기술</strong>과 <strong>실제 결정타</strong>가 구분되지 않습니다.</p>
    <p>포켓몬 챔피언스 공식 랭크 데이터에는 각 포켓몬이 <strong>쓰러졌을 때 맞은 기술</strong>의 분포가 따로 들어 있습니다. 아래는 싱글 사용률 상위 50종에 대해 그 분포를 전부 더한 결과입니다. "이 메타에서 포켓몬을 실제로 죽이고 있는 것이 무엇인가"에 대한 직접적인 답입니다.</p>

    <h2>포켓몬을 가장 많이 쓰러뜨린 기술 20</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>순위</th><th>기술</th><th>전체 격침 중 비중</th></tr></thead>
      <tbody>
        <tr><td class="num">1</td><td><strong>지진</strong></td><td class="num"><strong>19.3%</strong></td></tr>
        <tr><td class="num">2</td><td>화염방사</td><td class="num">6.4%</td></tr>
        <tr><td class="num">3</td><td>인파이트</td><td class="num">5.9%</td></tr>
        <tr><td class="num">4</td><td>야습</td><td class="num">4.3%</td></tr>
        <tr><td class="num">5</td><td>문포스</td><td class="num">3.9%</td></tr>
        <tr><td class="num">6</td><td>섀도볼</td><td class="num">3.8%</td></tr>
        <tr><td class="num">7</td><td>용성군</td><td class="num">3.6%</td></tr>
        <tr><td class="num">8</td><td>플레어드라이브</td><td class="num">3.4%</td></tr>
        <tr><td class="num">9</td><td>불릿펀치</td><td class="num">3.4%</td></tr>
        <tr><td class="num">10</td><td>악의파동</td><td class="num">3.3%</td></tr>
        <tr><td class="num">11</td><td>치근거리기</td><td class="num">2.9%</td></tr>
        <tr><td class="num">12</td><td>트릭플라워</td><td class="num">2.7%</td></tr>
        <tr><td class="num">13</td><td>10만볼트</td><td class="num">2.5%</td></tr>
        <tr><td class="num">14</td><td>기습</td><td class="num">2.1%</td></tr>
        <tr><td class="num">15</td><td>오물웨이브</td><td class="num">2.0%</td></tr>
        <tr><td class="num">16</td><td>트리플악셀</td><td class="num">2.0%</td></tr>
        <tr><td class="num">17</td><td>러스터캐논</td><td class="num">2.0%</td></tr>
        <tr><td class="num">18</td><td>바디프레스</td><td class="num">2.0%</td></tr>
        <tr><td class="num">19</td><td>아이언헤드</td><td class="num">1.5%</td></tr>
        <tr><td class="num">20</td><td>탁쳐서떨구기</td><td class="num">1.5%</td></tr>
      </tbody>
    </table>
    </div>
    <p><strong>지진 하나가 전체 격침의 19.3%</strong>입니다. 2위 화염방사(6.4%)의 세 배이고, 2위부터 5위까지를 다 합쳐야 겨우 넘어섭니다. 이 숫자는 "땅 대책은 있으면 좋다"가 아니라 <strong>"땅 대책 없이는 파티가 성립하지 않는다"</strong>에 가깝습니다.</p>

    <h2>타입별로 보면 더 분명합니다</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>타입</th><th>격침 비중</th><th>주된 기술</th></tr></thead>
      <tbody>
        <tr><td><strong>땅</strong></td><td class="num"><strong>19.9%</strong></td><td>지진</td></tr>
        <tr><td>불꽃</td><td class="num">9.9%</td><td>화염방사 · 플레어드라이브</td></tr>
        <tr><td>고스트</td><td class="num">9.5%</td><td>야습 · 섀도볼</td></tr>
        <tr><td>격투</td><td class="num">9.1%</td><td>인파이트 · 바디프레스</td></tr>
        <tr><td>페어리</td><td class="num">7.2%</td><td>문포스 · 치근거리기</td></tr>
        <tr><td>강철</td><td class="num">7.0%</td><td>불릿펀치 · 러스터캐논 · 아이언헤드</td></tr>
        <tr><td>악</td><td class="num">6.9%</td><td>악의파동 · 기습 · 탁쳐서떨구기</td></tr>
        <tr><td>풀</td><td class="num">5.2%</td><td>트릭플라워</td></tr>
        <tr><td>드래곤</td><td class="num">4.7%</td><td>용성군</td></tr>
        <tr><td>전기</td><td class="num">4.6%</td><td>10만볼트</td></tr>
        <tr><td>물</td><td class="num">4.5%</td><td>—</td></tr>
        <tr><td>얼음</td><td class="num">3.7%</td><td>트리플악셀</td></tr>
        <tr><td>독</td><td class="num">2.3%</td><td>오물웨이브</td></tr>
        <tr><td>에스퍼</td><td class="num">2.1%</td><td>—</td></tr>
        <tr><td>비행 · 바위 · 노말 · 벌레</td><td class="num">3.4% (합)</td><td>—</td></tr>
      </tbody>
    </table>
    </div>

    <h3>땅 19.9% — 지진이 메타를 지배하는 구조적 이유</h3>
    <p>지진은 위력 100에 명중 100, 부가 조건이 없고, 무엇보다 <strong>땅을 반감하는 타입이 풀·벌레·비행뿐</strong>입니다. 반면 땅에 약한 타입은 불꽃·전기·독·바위·강철로 다섯이나 되고, 이 다섯은 전부 현재 메타 상위권에 몰려 있습니다. 상위 50종에 강철·불꽃 타입이 얼마나 많은지 <a href="/battle-data/">배틀데이터</a>에서 확인해 보면, 지진이 왜 이 숫자를 찍는지 바로 보입니다.</p>
    <p>실전적으로는 두 가지 결론이 나옵니다. 첫째, <strong>땅에 약한 포켓몬을 3마리 이상 넣으면 파티가 지진 한 방향으로 무너집니다</strong>. 둘째, 비행 타입이나 부유 특성 하나쯤은 파티에 있는 편이 안전합니다. 다만 여기엔 함정이 있는데, 상대가 <strong>검은철구</strong>를 들려주거나 <strong>틀깨기</strong> 계열 특성을 들고 오면 부유 면역이 통째로 무시됩니다.</p>

    <h3>야습 4.3% — 우선도 기술이 이 순위에 있다는 것</h3>
    <p>4위 야습은 위력 40짜리 우선도 +1 기술입니다. 위력만 보면 이 표에 있을 이유가 없는데도 문포스·섀도볼보다 높습니다. 이유는 명확합니다. <strong>우선도 기술은 "체력이 깎인 상대를 마무리할 때"만 쓰이기 때문</strong>입니다. 채용률에서는 낮게 보이던 기술이 격침 기준에서는 튀어 오르는 전형적인 사례입니다.</p>
    <p>9위 불릿펀치(3.4%), 14위 기습(2.1%)도 같은 구조입니다. 셋을 합치면 <strong>9.8%</strong>로 화염방사 하나보다 큽니다. "체력 30% 남았으니 한 턴 더 버틸 수 있다"는 계산이 실전에서 자주 틀리는 이유가 여기 있습니다. 남은 체력이 우선도 기술 사거리 안인지 아닌지는 <a href="/calc/">데미지 계산기</a>에서 미리 재 두는 편이 확실합니다.</p>

    <h3>얼음 3.7% — 생각보다 낮은 이유</h3>
    <p>드래곤·비행·땅·풀을 한꺼번에 찌르는 얼음은 이론상 최고의 공격 타입이지만 실제 격침 비중은 3.7%에 그칩니다. 얼음 기술의 위력이 대체로 낮고(트리플악셀은 1타 위력 20의 연타기), 얼음 타입 자체가 내구가 약해 필드에 오래 못 있기 때문입니다. <strong>"얼음이 유효한 상대"와 "얼음을 실제로 꽂을 수 있는 상황"은 다릅니다.</strong></p>

    <h2>이 표를 파티 구성에 쓰는 법</h2>
    <ul>
      <li><strong>땅 → 불꽃 → 고스트 → 격투</strong> 순으로 대책을 점검합니다. 이 넷이 격침의 48.4%입니다.</li>
      <li>같은 타입 약점을 3마리 이상 공유하면 그 타입 한 방향으로 파티가 무너집니다. 특히 땅은 치명적입니다.</li>
      <li>내구형 포켓몬을 넣을 때는 우선도 기술 사거리를 반드시 확인합니다. 야습·불릿펀치·기습만으로 격침의 약 10%입니다.</li>
      <li>표의 상위 기술은 대부분 <strong>자속 보정을 받는 주력기</strong>입니다. 상대 파티를 봤을 때 이 기술들의 사용자가 누구인지 먼저 찾는 습관이 선출 판단을 크게 줄여 줍니다.</li>
    </ul>
    <p>상대 파티 6마리를 보고 어떤 기술이 날아올지 미리 재 두는 작업은 <a href="/">Champions Helper 데스크탑 앱</a>이 자동으로 해 줍니다. 상대 포켓몬별 최고 화력 기술과 내 포켓몬이 몇 방을 버티는지를 매 턴 계산해 표시합니다.</p>
""",
    related=[("/guide/finishers/", "실제로 경기를 끝내는 기술"),
             ("/guide/matchup-map/", "상성 지도 — 유리·불리 매치업"),
             ("/guide/item-meta/", "지닌도구 메타")])

# ══════════════════════════════════════════════════════════════════════
# 2. 채용률이 알려주지 않는 것 — 실제로 경기를 끝내는 기술
# ══════════════════════════════════════════════════════════════════════
col(
    "finishers",
    "채용률이 알려주지 않는 것 — 실제로 경기를 끝내는 기술",
    "채용률 상위 기술이 곧 결정타는 아닙니다. 포켓몬 챔피언스 공식 데이터에서 승리를 확정한 마지막 기술 분포를 채용률과 대조해, 실제 결정력이 높은 기술과 낮은 기술을 가려냅니다.",
    "승리를 확정한 마지막 기술 분포를 채용률과 대조한 분석.",
    "실제로 경기를 끝내는 기술",
    "채용률이 알려주지 않는 것 — 실제로 경기를 끝내는 기술",
    "\"이 기술 채용률 90%\"라는 말은 그 기술이 강하다는 뜻일까요, 아니면 그냥 넣을 게 그것뿐이라는 뜻일까요. 공식 랭크 데이터에는 <strong>승리를 확정지은 마지막 기술</strong>이 따로 기록돼 있습니다. 이 둘을 나란히 놓으면 채용률만으로는 안 보이던 것이 드러납니다.",
    """
    <h2>비교 방법</h2>
    <p>포켓몬 챔피언스 공식 데이터는 각 포켓몬에 대해 두 가지 분포를 함께 제공합니다.</p>
    <ul>
      <li><strong>채용률</strong> — 그 기술을 배운 개체의 비율</li>
      <li><strong>결정타 분포</strong> — 그 포켓몬이 승리를 확정지었을 때 마지막에 쓴 기술의 비율</li>
    </ul>
    <p>여기서 주의할 점이 하나 있습니다. 결정타 분포는 정의상 <strong>공격기만 등장</strong>합니다. 칼춤·날개쉬기·킹실드 같은 변화기는 경기를 끝내는 기술이 아니므로 언제나 0입니다. 따라서 이 둘을 그대로 빼면 "변화기는 쓸모없다"는 엉뚱한 결론이 나옵니다. 아래 표는 <strong>공격기끼리만</strong> 비중을 정규화해 비교한 것입니다.</p>

    <h2>채용률에 비해 결정타가 적은 기술</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>포켓몬</th><th>기술</th><th>공격기 중 채용 비중</th><th>결정타 비중</th><th>차이</th></tr></thead>
      <tbody>
        <tr><td>더시마사리</td><td>엉겨붙기</td><td class="num">78.5%</td><td class="num">36.6%</td><td class="num">-41.9</td></tr>
        <tr><td>엘풍</td><td>죽기살기</td><td class="num">32.6%</td><td class="num">0.0%</td><td class="num">-32.6</td></tr>
        <tr><td>아머까오</td><td>유턴</td><td class="num">32.3%</td><td class="num">10.1%</td><td class="num">-22.1</td></tr>
        <tr><td>패리퍼</td><td>유턴</td><td class="num">25.3%</td><td class="num">6.0%</td><td class="num">-19.3</td></tr>
        <tr><td>삼삼드래</td><td>유턴</td><td class="num">19.7%</td><td class="num">3.7%</td><td class="num">-16.0</td></tr>
        <tr><td>로토무(워시)</td><td>볼트체인지</td><td class="num">35.4%</td><td class="num">20.3%</td><td class="num">-15.1</td></tr>
        <tr><td>라이츄</td><td>풀묶기</td><td class="num">22.3%</td><td class="num">7.6%</td><td class="num">-14.7</td></tr>
        <tr><td>대쓰여너</td><td>퀵턴</td><td class="num">19.7%</td><td class="num">5.4%</td><td class="num">-14.3</td></tr>
        <tr><td>대짱이</td><td>퀵턴</td><td class="num">19.8%</td><td class="num">6.2%</td><td class="num">-13.6</td></tr>
        <tr><td>찌리배리</td><td>볼트체인지</td><td class="num">51.1%</td><td class="num">38.1%</td><td class="num">-13.1</td></tr>
        <tr><td>몰드류</td><td>스톤샤워</td><td class="num">20.3%</td><td class="num">7.8%</td><td class="num">-12.5</td></tr>
        <tr><td>이어롭</td><td>속이기</td><td class="num">20.8%</td><td class="num">8.5%</td><td class="num">-12.3</td></tr>
        <tr><td>대도각참</td><td>아이언헤드</td><td class="num">28.5%</td><td class="num">17.5%</td><td class="num">-10.9</td></tr>
      </tbody>
    </table>
    </div>
    <p>목록의 성격이 뚜렷합니다. <strong>유턴·볼트체인지·퀵턴</strong>이 반복해서 나옵니다. 당연한 결과입니다. 교체기는 애초에 상대를 쓰러뜨리려고 쓰는 기술이 아니라 <strong>유리한 상황으로 갈아타려고</strong> 쓰는 기술이니까요. 이 표에서 교체기가 하위권이라는 사실은 "교체기가 약하다"는 뜻이 아니라, <strong>결정타 분포로는 교체기의 값어치를 잴 수 없다</strong>는 뜻으로 읽어야 합니다.</p>
    <p>엘풍의 죽기살기가 정확히 0.0%인 것도 같은 이유입니다. 자신이 쓰러지면서 상대 능력을 떨어뜨리는 기술이니 구조적으로 결정타가 될 수 없습니다.</p>
    <p>정작 눈여겨볼 것은 <strong>대도각참의 아이언헤드</strong>입니다. 채용 비중 28.5%인데 결정타는 17.5%입니다. 교체기도 자폭기도 아닌 순수 공격기가 10포인트 넘게 밀린다는 건, 이 기술이 <strong>마무리보다는 견제·중간 딜링 역할</strong>을 하고 있다는 신호입니다.</p>

    <h2>채용률보다 훨씬 자주 끝내는 기술</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>포켓몬</th><th>기술</th><th>공격기 중 채용 비중</th><th>결정타 비중</th><th>차이</th></tr></thead>
      <tbody>
        <tr><td>대쓰여너</td><td>성묘</td><td class="num">26.5%</td><td class="num">62.1%</td><td class="num">+35.7</td></tr>
        <tr><td>몰드류</td><td>지진</td><td class="num">29.0%</td><td class="num">62.2%</td><td class="num">+33.2</td></tr>
        <tr><td>핫삼</td><td>불릿펀치</td><td class="num">38.1%</td><td class="num">67.1%</td><td class="num">+29.1</td></tr>
        <tr><td>엘풍</td><td>문포스</td><td class="num">62.6%</td><td class="num">91.6%</td><td class="num">+29.0</td></tr>
        <tr><td>삼삼드래</td><td>악의파동</td><td class="num">26.5%</td><td class="num">53.7%</td><td class="num">+27.1</td></tr>
        <tr><td>라이츄</td><td>전자포</td><td class="num">29.7%</td><td class="num">55.6%</td><td class="num">+26.0</td></tr>
        <tr><td>님피아</td><td>하이퍼보이스</td><td class="num">58.8%</td><td class="num">81.5%</td><td class="num">+22.7</td></tr>
        <tr><td>타부자고</td><td>섀도볼</td><td class="num">38.2%</td><td class="num">60.2%</td><td class="num">+22.0</td></tr>
        <tr><td>한카리아스</td><td>지진</td><td class="num">37.7%</td><td class="num">57.1%</td><td class="num">+19.3</td></tr>
        <tr><td>아머까오</td><td>바디프레스</td><td class="num">36.9%</td><td class="num">55.4%</td><td class="num">+18.5</td></tr>
        <tr><td>찌리배리</td><td>파라볼라차지</td><td class="num">44.3%</td><td class="num">59.7%</td><td class="num">+15.5</td></tr>
        <tr><td>드래펄트</td><td>드래곤애로</td><td class="num">18.4%</td><td class="num">31.4%</td><td class="num">+13.0</td></tr>
        <tr><td>누리레느</td><td>문포스</td><td class="num">32.9%</td><td class="num">44.1%</td><td class="num">+11.1</td></tr>
      </tbody>
    </table>
    </div>

    <h3>패턴 1 — 자속 고위력기가 결국 이긴다</h3>
    <p>대쓰여너의 성묘, 몰드류·한카리아스의 지진, 삼삼드래의 악의파동, 님피아의 하이퍼보이스. 전부 <strong>자속 보정을 받는 주력기</strong>입니다. 서브 기술은 특정 상대를 찌르려고 넣지만, 실제로 경기를 끝내는 것은 대부분 가장 무거운 자속기였습니다.</p>
    <p>파티를 짤 때 서브 기술 칸을 두고 오래 고민하게 되는데, 이 데이터는 <strong>주력기 화력을 확실히 확보한 다음에 서브를 고민하는 순서</strong>가 맞다고 말합니다.</p>

    <h3>패턴 2 — 우선도 기술은 채용률보다 훨씬 값어치가 크다</h3>
    <p>핫삼의 불릿펀치가 +29.1로 세 번째입니다. 위력 40짜리 기술이 핫삼 승리의 67.1%를 마무리했습니다. 드래펄트의 드래곤애로(+13.0)도 우선도 기술입니다. <a href="/guide/what-kills-you/">패배 기록 분석</a>에서 야습·불릿펀치·기습이 격침의 약 10%를 차지했던 것과 정확히 같은 현상을 반대편에서 본 셈입니다.</p>
    <p><strong>우선도 기술은 채용률이 낮아도 실전 기여가 큽니다.</strong> 반대로 말하면, 내 포켓몬이 체력 30% 이하로 내려간 순간부터는 상대 파티의 우선도 기술 보유자를 반드시 세어 봐야 합니다.</p>

    <h3>패턴 3 — 아머까오의 바디프레스</h3>
    <p>아머까오는 유턴이 -22.1로 최하위권, 바디프레스가 +18.5로 상위권입니다. 같은 포켓몬 안에서 <strong>역할이 명확히 갈린</strong> 사례입니다. 유턴으로 판을 돌리고, 마무리는 바디프레스로 합니다. 바디프레스는 공격이 아니라 <strong>방어 수치</strong>로 데미지를 계산하는 기술이라, 내구에 투자한 아머까오일수록 화력이 올라갑니다. 노력치를 방어에 넣는 것이 수비와 공격을 동시에 챙기는 선택이 됩니다.</p>

    <h2>정리 — 채용률과 결정타를 같이 보는 습관</h2>
    <ul>
      <li>채용률이 높고 결정타가 낮다 → <strong>역할 기술</strong>(교체·견제·상태이상 유발)일 가능성이 큽니다. 약한 게 아닙니다.</li>
      <li>채용률이 낮고 결정타가 높다 → <strong>실전 기여가 과소평가된 기술</strong>입니다. 우선도 기술이 대표적입니다.</li>
      <li>둘 다 높다 → 그 포켓몬의 정체성입니다. 상대할 때 가장 먼저 대비해야 합니다.</li>
    </ul>
    <p>포켓몬별 채용률과 결정타 분포는 <a href="/pokedex/">도감 상세 페이지</a>에서 종별로 볼 수 있습니다.</p>
""",
    related=[("/guide/what-kills-you/", "무엇에 죽는가 — 패배 기록 분석"),
             ("/guide/ev-reality/", "노력치 66의 현실"),
             ("/guide/meta-singles/", "싱글 메타 분석")])

# ══════════════════════════════════════════════════════════════════════
# 3. 상성 지도 — 확실히 이기는 상대, 확실히 지는 상대
# ══════════════════════════════════════════════════════════════════════
col(
    "matchup-map",
    "상성 지도 — 상위 20종이 확실히 이기는 상대와 지는 상대",
    "포켓몬 챔피언스 공식 랭크 데이터의 승리·패배 상대 기록을 교차해, 상위 20종의 유리·불리 매치업과 진짜 5:5 구도를 정리했습니다. 선출 판단에 바로 쓰는 상성 지도.",
    "승리 상대·패배 상대 기록을 교차한 상위 20종 매치업 지도.",
    "상성 지도",
    "상성 지도 — 상위 20종이 확실히 이기는 상대와 지는 상대",
    "타입 상성표는 \"페어리는 드래곤에 강하다\"까지만 알려줍니다. 실제 배틀은 종족값·기술 구성·스피드가 다 얽혀서 상성표대로 가지 않습니다. 공식 랭크 데이터에는 각 포켓몬이 <strong>이겼을 때 마주친 상대</strong>와 <strong>졌을 때 마주친 상대</strong>가 따로 기록돼 있습니다. 이 둘을 교차하면 실전 상성 지도가 나옵니다.",
    """
    <h2>읽는 법 — 세 칸의 의미</h2>
    <ul>
      <li><strong>확실히 이김</strong> — 승리 상대 목록에만 있고 패배 상대 목록에는 없는 포켓몬. 실제로 유리하게 굴러간 매치업입니다.</li>
      <li><strong>확실히 짐</strong> — 패배 상대 목록에만 있는 포켓몬. 마주치면 교체를 먼저 생각해야 합니다.</li>
      <li><strong>양쪽 모두</strong> — 승리·패배 목록에 다 있는 포켓몬. 빌드와 선공 여부에 따라 갈리는 <strong>진짜 5:5</strong>입니다.</li>
    </ul>
    <p>여기서 "확실히"는 통계적 경향이지 절대적 보장이 아닙니다. 지닌 도구·노력치·특성에 따라 개별 판은 얼마든지 뒤집힙니다. 그래도 <strong>선출 화면에서 30초 안에 판단해야 할 때</strong> 이 지도는 충분히 쓸 만합니다.</p>

    <h2>싱글 상위 10종 매치업</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>순위</th><th>포켓몬</th><th>확실히 이김</th><th>확실히 짐</th><th>5:5</th></tr></thead>
      <tbody>
        <tr><td class="num">1</td><td><a href="/pokedex/garchomp/">한카리아스</a></td><td>킬라플로르 · 리자몽 · 라이츄 · 하마돈 · 번치코</td><td>마스카나 · 메타그로스 · 갸라도스 · 개굴닌자 · 아쿠스타</td><td>브리두라스 · 누리레느 · 망나뇽 · 따라큐</td></tr>
        <tr><td class="num">2</td><td><a href="/pokedex/mimikyu/">따라큐</a></td><td>하마돈 · 마폭시 · 망나뇽 · 개굴닌자 · 대쓰여너</td><td>메타그로스 · 갸라도스 · 리자몽 · 번치코 · 핫삼</td><td>한카리아스 · 누리레느 · 마스카나 · 브리두라스</td></tr>
        <tr><td class="num">3</td><td><a href="/pokedex/meowscarada/">마스카나</a></td><td>하마돈 · 망나뇽 · 대쓰여너 · 마폭시</td><td>메타그로스 · 브리두라스 · 리자몽 · 번치코</td><td>한카리아스 · 누리레느 · 갸라도스 · 따라큐 · 개굴닌자</td></tr>
        <tr><td class="num">4</td><td><a href="/pokedex/hippowdon/">하마돈</a></td><td>킬라플로르 · 번치코 · 킬가르도 · 라이츄 · 팬텀 · 찌리배리</td><td>누리레느 · 마스카나 · 리자몽 · 개굴닌자 · 갸라도스 · 망나뇽</td><td>한카리아스 · 브리두라스 · 따라큐 · 메타그로스</td></tr>
        <tr><td class="num">5</td><td><a href="/pokedex/archaludon/">브리두라스</a></td><td>마스카나 · 따라큐 · 하마돈 · 킬라플로르</td><td>리자몽 · 메타그로스 · 망나뇽 · 마폭시 · 라이츄</td><td>한카리아스 · 누리레느 · 갸라도스 · 개굴닌자</td></tr>
        <tr><td class="num">6</td><td><a href="/pokedex/primarina/">누리레느</a></td><td>하마돈 · 마폭시 · 킬라플로르 · 번치코</td><td>갸라도스 · 메타그로스 · 따라큐 · 리자몽</td><td>한카리아스 · 브리두라스 · 마스카나 · 개굴닌자 · 망나뇽</td></tr>
        <tr><td class="num">7</td><td><a href="/pokedex/metagross/">메타그로스</a></td><td>따라큐 · 누리레느 · 하마돈 · 킬라플로르 · 망나뇽</td><td>리자몽 · 마폭시 · 개굴닌자 · 대쓰여너 · 번치코</td><td>한카리아스 · 마스카나 · 브리두라스 · 갸라도스</td></tr>
        <tr><td class="num">11</td><td><a href="/pokedex/charizard/">리자몽</a></td><td>하마돈 · 누리레느 · 개굴닌자 · 로토무(워시)</td><td>망나뇽 · 마폭시 · 대쓰여너</td><td>브리두라스 · 마스카나 · 한카리아스 · 메타그로스 · 따라큐 · 갸라도스</td></tr>
        <tr><td class="num">13</td><td><a href="/pokedex/greninja/">개굴닌자</a></td><td>하마돈 · 킬라플로르 · 망나뇽</td><td>갸라도스 · 리자몽 · 번치코</td><td>한카리아스 · 브리두라스 · 누리레느 · 메타그로스 · 마스카나 · 따라큐</td></tr>
        <tr><td class="num">15</td><td><a href="/pokedex/corviknight/">아머까오</a></td><td>한카리아스 · 마스카나 · 갸라도스 · 개굴닌자 · 킬라플로르 · 대도각참</td><td>리자몽 · 마폭시 · 번치코 · 망나뇽 · 누리레느 · 라이츄</td><td>따라큐 · 메타그로스 · 브리두라스 · 삼삼드래</td></tr>
      </tbody>
    </table>
    </div>

    <h2>지도에서 읽히는 것</h2>

    <h3>하마돈은 상위권 최대의 승점 공급원</h3>
    <p>사용률 4위 하마돈은 상위 10종 중 <strong>일곱 종의 "확실히 이김" 칸</strong>에 이름이 올라 있습니다. 한카리아스·따라큐·마스카나·브리두라스·누리레느·메타그로스·개굴닌자가 전부 하마돈에게 유리합니다. 그런데도 사용률 4위인 이유는, 하마돈이 이기는 상대(킬라플로르·번치코·킬가르도·라이츄·팬텀·찌리배리)가 <strong>메타 중위권에 넓게 퍼져 있기</strong> 때문입니다.</p>
    <p>파티에 하마돈을 넣는다면 상위권 상대에게 선출하지 않는다는 전제가 필요합니다. 반대로 하마돈을 상대할 때는 위 일곱 종 중 하나만 있으면 대체로 해결됩니다.</p>

    <h3>아머까오 — 상위권을 잡고 중위권에 잡힌다</h3>
    <p>아머까오는 흥미로운 형태입니다. 사용률 1위 한카리아스, 3위 마스카나, 8위 갸라도스를 <strong>확실히 이깁니다</strong>. 강철·비행 타입이 땅을 무효화하고 격투·풀을 반감하기 때문입니다. 그런데 리자몽·마폭시·번치코 같은 <strong>불꽃 계열에 확실히 집니다</strong>. 강철 타입의 전형적인 구도입니다.</p>
    <p>즉 아머까오는 "상대 파티에 불꽃이 있느냐 없느냐" 한 줄로 선출 가치가 갈립니다. 이런 포켓몬은 6마리 중 한 자리를 차지할 값어치가 있지만, 상대 파티를 보기 전에는 선출을 확정할 수 없습니다.</p>

    <h3>5:5 칸이 넓은 포켓몬 = 플레이로 갈리는 포켓몬</h3>
    <p>리자몽과 개굴닌자는 5:5 칸이 여섯 종으로 가장 넓습니다. 두 포켓몬 모두 <strong>빌드 분기가 크다</strong>는 공통점이 있습니다. 리자몽은 메가 X/Y 중 무엇이냐에 따라 타입도 역할도 완전히 달라지고, 개굴닌자는 변환자재(82.6%)와 급류(17.4%)가 갈립니다.</p>
    <p>이런 포켓몬을 상대할 때는 <strong>첫 턴 정보가 특히 중요합니다</strong>. 상대의 지닌 도구나 특성이 드러나는 순간 5:5가 명확한 유불리로 바뀝니다. 실전에서 이 정보를 놓치지 않으려면 <a href="/">데스크탑 앱</a>의 확정 패널에 드러난 정보를 그때그때 입력해 두는 편이 좋습니다. 특성·도구가 확정되면 그 자리에서 데미지 계산이 다시 잡힙니다.</p>

    <h3>서로가 서로의 5:5인 최상위권</h3>
    <p>한카리아스·브리두라스·누리레느·따라큐·마스카나는 대부분 서로의 5:5 칸에 들어 있습니다. 최상위권끼리는 <strong>상성이 아니라 선공과 빌드로 갈린다</strong>는 뜻입니다. 이 구간에서 승부를 가르는 건 스피드 라인 계산과 노력치 배분 추정입니다. 각각 <a href="/guide/speed-guide/">스피드 실전 가이드</a>와 <a href="/guide/ev-reality/">노력치 66의 현실</a>에서 다뤘습니다.</p>

    <h2>선출 화면에서 쓰는 순서</h2>
    <ol>
      <li>상대 6마리 중 내 에이스가 <strong>확실히 지는</strong> 상대가 있는지 먼저 봅니다. 있으면 그 포켓몬은 선봉에서 뺍니다.</li>
      <li>내 파티에 상대 에이스를 <strong>확실히 이기는</strong> 카드가 있는지 봅니다. 없으면 그 판은 5:5 구도를 여러 개 만드는 방향으로 갑니다.</li>
      <li>5:5가 많은 상대라면 선공권을 먼저 계산합니다. 스피드가 같은 구간이면 도구(구애스카프)와 순풍 여부가 판을 결정합니다.</li>
    </ol>
    <p>이 판단을 6×6 전 조합에 대해 자동으로 계산해 주는 기능이 데스크탑 앱의 <strong>선출 정보</strong> 패널입니다. 쌍별 타수·스피드 우열·추천 트리오까지 한 화면에 나옵니다.</p>
""",
    related=[("/guide/what-kills-you/", "무엇에 죽는가 — 패배 기록 분석"),
             ("/guide/team-cores/", "실제로 함께 쓰이는 코어"),
             ("/guide/speed-guide/", "스피드 실전 가이드")])

# ══════════════════════════════════════════════════════════════════════
# 4. 지닌도구 메타
# ══════════════════════════════════════════════════════════════════════
col(
    "item-meta",
    "지닌도구 메타 — 먹다남은음식이 1위인 이유",
    "포켓몬 챔피언스 상위 50종의 지닌도구 채용률을 전수 집계했습니다. 먹다남은음식 13.9%, 기합의띠 9.7%, 자뭉열매 9.4% — 도구 선택이 메타를 어떻게 반영하는지 데이터로 정리합니다.",
    "상위 50종 지닌도구 채용률 전수 집계와 해석.",
    "지닌도구 메타",
    "지닌도구 메타 — 먹다남은음식이 1위인 이유",
    "포켓몬 챔피언스는 한 포켓몬에 도구를 하나만 들려줍니다. 그래서 도구 선택은 그 포켓몬에게 무엇을 기대하는지를 그대로 드러냅니다. 싱글 사용률 상위 50종의 도구 채용률을 전부 더해 보면, 지금 메타가 무엇을 중요하게 여기는지가 한눈에 보입니다.",
    """
    <h2>상위 50종 도구 채용률 집계</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>순위</th><th>도구</th><th>비중</th><th>효과</th></tr></thead>
      <tbody>
        <tr><td class="num">1</td><td><strong>먹다남은음식</strong></td><td class="num"><strong>13.9%</strong></td><td>매 턴 최대 HP의 1/16 회복</td></tr>
        <tr><td class="num">2</td><td>기합의띠</td><td class="num">9.7%</td><td>HP 풀에서 치명타를 HP 1로 버팀</td></tr>
        <tr><td class="num">3</td><td>자뭉열매</td><td class="num">9.4%</td><td>HP 절반 이하에서 1/4 회복</td></tr>
        <tr><td class="num">4</td><td>구애스카프</td><td class="num">8.7%</td><td>스피드 ×1.5, 기술 하나로 고정</td></tr>
        <tr><td class="num">5</td><td>생명의구슬</td><td class="num">5.8%</td><td>위력 ×1.3, 반동 피해</td></tr>
        <tr><td class="num">6</td><td>빛의점토</td><td class="num">3.7%</td><td>리플렉터·빛의장막 지속 연장</td></tr>
        <tr><td class="num">7</td><td>검은안경</td><td class="num">2.1%</td><td>악 타입 기술 위력 ×1.2</td></tr>
        <tr><td class="num">8</td><td>리샘열매</td><td class="num">1.6%</td><td>상태이상 1회 자동 회복</td></tr>
        <tr><td colspan="4" style="color:#9aa0a8">이하 각종 메가스톤이 종별로 1.6~2.0%씩 (합계 약 27%)</td></tr>
      </tbody>
    </table>
    </div>

    <h2>1~3위가 전부 "버티는" 도구입니다</h2>
    <p>먹다남은음식·기합의띠·자뭉열매를 합치면 <strong>33.0%</strong>입니다. 화력 도구인 생명의구슬(5.8%)의 여섯 배에 가깝습니다. 이 비율은 챔피언스 메타의 성격을 그대로 보여 줍니다.</p>
    <p>이유는 <a href="/guide/ev-reality/">노력치 구조</a>에 있습니다. 챔피언스는 노력치 합계가 66으로 제한되고 한 능력치에 최대 32까지만 넣을 수 있습니다. 본가처럼 "공격 252 + 스피드 252" 같은 극단적 몰빵이 불가능하니, <strong>화력의 상한 자체가 낮습니다</strong>. 화력 상한이 낮으면 한 방에 죽는 일이 줄고, 한 방에 안 죽으면 매 턴 1/16씩 회복하는 도구의 값어치가 급격히 올라갑니다.</p>

    <h3>기합의띠 9.7% — 이 숫자를 반드시 기억해야 하는 이유</h3>
    <p>기합의띠는 <strong>HP가 가득 찬 상태에서 받은 치명적인 일격을 HP 1로 버티게</strong> 합니다. 상위 50종의 약 10분의 1이 이걸 들고 있다는 뜻은, <strong>"확정 1타"라고 계산이 나와도 열 번 중 한 번은 안 죽는다</strong>는 뜻입니다.</p>
    <p>실전에서 이게 어떻게 손해로 이어지는지가 중요합니다. 확정 1타를 믿고 교체 없이 공격했는데 상대가 HP 1로 버티면, 그 다음 턴에 반격을 그대로 맞습니다. 특히 <a href="/guide/what-kills-you/">우선도 기술</a>을 가진 상대라면 HP 1에서 살아남은 뒤 야습·불릿펀치로 마무리당하는 전개가 나옵니다.</p>
    <p>대응은 두 가지입니다. <strong>연타기</strong>(트리플악셀·스케일샷 등)는 첫 타로 띠를 소진시키고 나머지 타로 마무리합니다. 또 하나는 <strong>스텔스록·압정뿌리기</strong> 같은 설치기입니다. 등장할 때 HP가 조금이라도 깎이면 기합의띠 조건 자체가 성립하지 않습니다. 한카리아스의 스텔스록 채용률이 46.8%로 지진 다음인 것은 우연이 아닙니다.</p>

    <h3>구애스카프 8.7% — 스피드 계산이 무너지는 지점</h3>
    <p>구애스카프는 스피드를 1.5배로 올리는 대신 기술 하나만 반복하게 만듭니다. 8.7%면 <strong>열두 마리 중 한 마리</strong>입니다. 상대 스피드를 최속 기준으로 계산해 놓고 "내가 빠르다"고 판단했는데 실제로는 후공이 되는 상황이 이 확률로 발생합니다.</p>
    <p>다행히 구애스카프는 정체가 빨리 드러납니다. 상대가 같은 기술만 반복하면 구애 계열이 확정입니다. 한 번 확정되면 그 이후로는 계산이 오히려 쉬워집니다 — 스피드는 1.5배로 고정되고, 기술도 하나로 고정되니까요. <a href="/">데스크탑 앱</a>에서는 확정된 도구를 입력해 두면 그 이후 모든 계산에 자동으로 반영됩니다.</p>

    <h3>자뭉열매 9.4% — 챔피언스 고유의 선택</h3>
    <p>자뭉열매가 3위라는 점은 챔피언스만의 특징입니다. HP가 절반 이하로 떨어지면 최대 HP의 1/4을 회복합니다. 앞서 말한 대로 챔피언스는 화력 상한이 낮아 <strong>2타 싸움</strong>이 많습니다. 2타에 죽을 상황에서 자뭉열매가 터지면 3타가 필요해지고, 그 한 턴이 그대로 승패가 됩니다.</p>
    <p>먹다남은음식과 비교하면 성격이 다릅니다. 먹다남은음식은 장기전에서 조금씩 누적되고, 자뭉열매는 <strong>결정적인 한 턴</strong>에 몰아서 들어옵니다. 상위권에서 둘의 채용률이 비슷한 것은 파티 역할에 따라 갈리기 때문입니다.</p>

    <h3>메가스톤 — 합치면 27%지만 종별로는 선택지가 없다</h3>
    <p>표 아래쪽의 메가스톤들은 종별로 1.6~2.0%씩입니다. 언뜻 낮아 보이지만, 이건 <strong>그 포켓몬을 쓰는 사람은 거의 다 메가스톤을 든다</strong>는 뜻입니다. 메가진화 가능한 포켓몬에게 메가스톤은 사실상 유일한 선택지입니다.</p>
    <p>대신 판당 메가진화는 한 번뿐이라, 파티에 메가 후보를 둘 이상 넣으면 한 마리는 도구 슬롯을 낭비하게 됩니다. 메가 선택 기준은 <a href="/guide/mega-picks/">메가진화 선택 가이드</a>에서 따로 다뤘습니다.</p>

    <h2>반감열매 — 표에는 안 보이지만 알아야 할 것</h2>
    <p>오카열매(불꽃)·플카열매(얼음)·하반열매(드래곤) 같은 반감열매는 개별 채용률이 1% 미만이라 위 표에 안 잡힙니다. 하지만 걸렸을 때의 영향은 큽니다. <strong>효과가 굉장한 공격을 받을 때 데미지를 절반으로 줄입니다</strong>(카리열매만 노말 1배에서도 발동). ×2 상성이 그대로 유지된 채 별도로 ×0.5가 곱해지므로, 결과적으로 등배 데미지가 됩니다.</p>
    <p>한카리아스의 플카열매 0.8%, 하반열매 0.4%처럼 낮은 숫자지만, "확정 1타"를 믿고 들어갔다가 상대가 반토막 데미지만 받고 버티면 판이 뒤집힙니다. 상위권 매치업일수록 이런 소수 채용 도구를 염두에 두는 편이 안전합니다.</p>

    <h2>정리</h2>
    <ul>
      <li>메타의 3분의 1이 <strong>버티는 도구</strong>입니다. 챔피언스의 낮은 화력 상한이 만든 구조입니다.</li>
      <li>기합의띠 9.7% — 확정 1타 계산에는 항상 이 확률이 붙어 있다고 생각해야 합니다.</li>
      <li>구애스카프 8.7% — 스피드 우위 판단은 상대 도구가 드러나기 전까지는 잠정입니다.</li>
      <li>포켓몬별 실제 도구 채용률은 <a href="/pokedex/">도감 상세 페이지</a>에 종별로 정리돼 있습니다.</li>
    </ul>
""",
    related=[("/guide/ev-reality/", "노력치 66의 현실"),
             ("/guide/what-kills-you/", "무엇에 죽는가 — 패배 기록 분석"),
             ("/guide/mega-picks/", "메가진화 선택 가이드")])

# ══════════════════════════════════════════════════════════════════════
# 5. 노력치 66의 현실
# ══════════════════════════════════════════════════════════════════════
col(
    "ev-reality",
    "노력치 66의 현실 — 상위 50종은 실제로 어떻게 나눠 쓰는가",
    "포켓몬 챔피언스의 노력치는 스탯당 32, 합계 66입니다. 상위 50종의 실제 배분 1위 스프레드를 전수 집계해, 96%가 선택한 극단 배분 구조와 그 예외를 분석합니다.",
    "상위 50종의 실제 노력치 배분 전수 집계. 96%가 32/32 구조.",
    "노력치 66의 현실",
    "노력치 66의 현실 — 상위 50종은 실제로 어떻게 나눠 쓰는가",
    "포켓몬 챔피언스의 노력치는 본가와 다릅니다. 한 능력치에 최대 32, 합계 66. 이 제약은 생각보다 훨씬 강하게 빌드를 규정합니다. 상위 50종이 실제로 어떤 배분을 가장 많이 썼는지 전부 모아 보면, 사실상 <strong>정답이 정해져 있다</strong>는 것이 보입니다.",
    """
    <h2>먼저 구조부터 — 왜 32/32인가</h2>
    <p>노력치 1당 실수치가 1씩 오릅니다(본가는 4당 1). 한 능력치 상한은 32, 합계 상한은 66입니다. 여기서 산수가 하나 나옵니다.</p>
    <div class="formula">32 + 32 = 64, 남는 것은 2</div>
    <p>즉 <strong>능력치 두 개를 최대로 채우면 66을 거의 다 쓰게 됩니다</strong>. 남은 2를 어디에 넣든 실수치는 2밖에 안 오르니 사실상 잉여입니다. 세 능력치에 22씩 나누는 배분도 가능하지만, 그러면 어느 것도 최대치에 못 미칩니다.</p>
    <p>결과적으로 챔피언스의 노력치 설계는 <strong>"어느 둘을 고를 것인가"</strong>라는 이지선다에 가깝습니다.</p>

    <h2>상위 50종의 1위 배분 — 96%가 같은 구조</h2>
    <p>상위 50종 각각에서 가장 많이 쓰인 배분 하나씩을 뽑아 보면, <strong>48종(96%)이 32급 능력치를 두 개 가진 구조</strong>였습니다. 나머지 2종만 예외입니다.</p>
    <div class="tablewrap">
    <table>
      <thead><tr><th>순위</th><th>포켓몬</th><th>1위 배분</th><th>그 배분의 비율</th><th>유형</th></tr></thead>
      <tbody>
        <tr><td class="num">1</td><td>한카리아스</td><td>H2 A32 S32</td><td class="num">53.1%</td><td>공격+스피드</td></tr>
        <tr><td class="num">2</td><td>따라큐</td><td>H2 A32 S32</td><td class="num">25.1%</td><td>공격+스피드</td></tr>
        <tr><td class="num">3</td><td>마스카나</td><td>H2 A32 S32</td><td class="num">61.9%</td><td>공격+스피드</td></tr>
        <tr><td class="num">4</td><td>하마돈</td><td>H32 B32 D2</td><td class="num">20.4%</td><td>HP+방어</td></tr>
        <tr><td class="num">5</td><td>브리두라스</td><td>H2 C32 S32</td><td class="num">21.8%</td><td>특공+스피드</td></tr>
        <tr><td class="num">6</td><td>누리레느</td><td>H32 C32 S2</td><td class="num">10.0%</td><td>HP+특공</td></tr>
        <tr><td class="num">7</td><td>메타그로스</td><td>H2 A32 S32</td><td class="num">28.8%</td><td>공격+스피드</td></tr>
        <tr><td class="num">8</td><td>갸라도스</td><td>H1 A32 B1 S32</td><td class="num">26.3%</td><td>공격+스피드</td></tr>
        <tr><td class="num">9</td><td>망나뇽</td><td>H2 C32 S32</td><td class="num">23.9%</td><td>특공+스피드</td></tr>
        <tr><td class="num">13</td><td>개굴닌자</td><td>H2 C32 S32</td><td class="num">62.9%</td><td>특공+스피드</td></tr>
        <tr><td class="num">14</td><td>삼삼드래</td><td>H2 C32 S32</td><td class="num">71.9%</td><td>특공+스피드</td></tr>
        <tr><td class="num">15</td><td>아머까오</td><td>H32 B32 D2</td><td class="num">43.1%</td><td>HP+방어</td></tr>
        <tr><td class="num">17</td><td>킬가르도</td><td>H32 A32 B1 D1</td><td class="num">16.9%</td><td>HP+공격</td></tr>
        <tr><td class="num">28</td><td>찌리배리</td><td>H31 B4 D28 S3</td><td class="num">28.7%</td><td class="num">예외</td></tr>
        <tr><td class="num">50</td><td>거북왕</td><td>H19 C18 S29</td><td class="num">12.3%</td><td class="num">예외</td></tr>
      </tbody>
    </table>
    </div>

    <h2>세 가지 유형으로 수렴합니다</h2>
    <h3>① 공격 32 + 스피드 32 — 화력형</h3>
    <p>한카리아스·따라큐·마스카나·메타그로스·갸라도스가 전부 이 형태입니다. 자기 주력기를 최대 위력으로 쏘면서 선공까지 잡겠다는 배분입니다. 마스카나는 이 배분 비율이 <strong>61.9%</strong>, 삼삼드래는 특공판으로 <strong>71.9%</strong>까지 올라갑니다. 사실상 표준형이 하나로 굳었다는 뜻입니다.</p>
    <p>이 유형을 상대할 때는 <strong>내구를 전혀 안 챙긴 상태</strong>라고 가정해도 됩니다. HP에 남는 2만 넣었으니 체력은 종족값 그대로입니다. 이쪽이 먼저 때릴 수 있다면 대부분 유리하게 풀립니다.</p>

    <h3>② HP 32 + 방어(또는 특방) 32 — 내구형</h3>
    <p>하마돈·아머까오·라우드본·블래키·이상해꽃 등이 이 형태입니다. 스피드를 완전히 포기하고 버티는 쪽을 택합니다. HP에 32를 넣는다는 건 <strong>모든 물리·특수 공격에 대해 동시에 내구가 오른다</strong>는 뜻이라 효율이 좋습니다.</p>
    <p>상위 50종 중 <strong>HP에 20 이상 투자한 종이 20종(40%)</strong>입니다. 화력형이 60%, 내구형이 40%로 메타가 갈려 있는 셈입니다.</p>

    <h3>③ HP 32 + 공격/특공 32 — 무거운 화력형</h3>
    <p>누리레느와 킬가르도가 대표적입니다. 스피드를 버리고 <strong>맞으면서 때리는</strong> 쪽을 택합니다. 원래 스피드 종족값이 낮아 32를 넣어도 선공을 못 잡는 포켓몬들이 주로 이 배분을 씁니다.</p>
    <p>누리레느의 1위 배분 비율이 10.0%밖에 안 된다는 점도 눈여겨볼 만합니다. 이 포켓몬은 <strong>배분이 가장 안 굳은 종</strong>이라는 뜻이고, 상대로 만났을 때 추정이 가장 어렵다는 뜻이기도 합니다.</p>

    <h2>예외 2종이 알려주는 것</h2>
    <p>찌리배리(H31 B4 D28 S3)와 거북왕(H19 C18 S29)만 32를 두 번 채우지 않았습니다. 둘 다 <strong>특정 스피드 라인이나 내구 라인을 정확히 맞추려는</strong> 조정형 배분입니다.</p>
    <p>이런 배분은 "이 상대의 이 기술을 확정으로 버틴다" 또는 "이 상대보다 1만 더 빠르다" 같은 구체적 목표가 있을 때 나옵니다. 남는 노력치를 다른 곳에 돌릴 수 있으니 이론적으로는 가장 효율적이지만, 목표로 삼은 상대가 메타에서 사라지면 의미가 없어집니다. 상위권에서 이런 배분이 두 종뿐인 이유입니다.</p>

    <h2>성격 보정이 배분보다 중요할 때</h2>
    <p>노력치 32는 실수치 32를 올립니다. 성격 보정은 <strong>노력치까지 더한 값 전체에 ×1.1</strong>입니다. 실수치가 150인 능력치라면 성격 보정만으로 15가 오릅니다.</p>
    <div class="formula">실수치 = floor( ( floor((2×종족값+31)×50÷100) + 5 + 노력치 ) × 성격보정 )</div>
    <p>즉 노력치 32(=+32)와 성격 보정(=+15 안팎)은 비슷한 급의 조정 수단이 아닙니다. <strong>노력치가 훨씬 큽니다.</strong> 하지만 성격은 노력치를 쓰지 않고 얻는 보너스이므로, 둘을 같은 능력치에 겹쳐 주는 것이 상위권 표준입니다. 실제로 상위 50종의 1위 성격을 보면 그렇게 나옵니다. 자세한 내용은 <a href="/guide/nature-meta/">성격 선택의 실제</a>에서 다뤘습니다.</p>

    <h2>상대 배분을 추정하는 실전 요령</h2>
    <ul>
      <li>상대가 <strong>선공을 잡았다</strong> → 스피드 32 + 성격 보정일 가능성이 높습니다. 그러면 내구는 종족값 그대로입니다.</li>
      <li>상대가 <strong>확정 1타여야 할 공격을 버텼다</strong> → HP 32 계열입니다. 그러면 스피드는 무보정입니다.</li>
      <li>둘 다 아니라면 조정형이거나, 예상과 다른 도구(기합의띠·자뭉열매)를 들었을 가능성을 봅니다.</li>
    </ul>
    <p>챔피언스의 배분이 이렇게 몇 가지로 수렴하기 때문에, <strong>한 가지 정보만 얻으면 나머지가 대부분 따라옵니다</strong>. 이 추정을 자동으로 해 주는 것이 <a href="/">데스크탑 앱</a>의 위력 칩 테두리 표시입니다. 채용률 1위 배분을 기본 가정으로 잡고, 확정된 정보가 들어오면 그쪽으로 갱신합니다.</p>
""",
    related=[("/guide/nature-meta/", "성격 선택의 실제"),
             ("/guide/item-meta/", "지닌도구 메타"),
             ("/guide/ev-nature/", "노력치·성격 배분 가이드")])


# ══════════════════════════════════════════════════════════════════════
# 6. 상대 특성 맞히기
# ══════════════════════════════════════════════════════════════════════
col(
    "ability-guessing",
    "상대 특성 맞히기 — 복수 특성 포켓몬 확률표",
    "포켓몬 챔피언스에서 상대 특성은 보이지 않습니다. 상위 50종 중 복수 특성 종의 실제 채용률을 정리해, 어떤 특성을 기본값으로 가정하고 어디서 예외를 의심해야 하는지 데이터로 제시합니다.",
    "복수 특성 포켓몬의 실제 채용률과 추정 전략.",
    "상대 특성 맞히기",
    "상대 특성 맞히기 — 복수 특성 포켓몬 확률표",
    "상대 포켓몬의 특성은 발동하기 전까지 보이지 않습니다. 그런데 특성 하나로 데미지가 반토막 나거나 기술이 통째로 무효가 되기도 합니다. 다행히 <strong>복수 특성 종이라도 실제 채용은 한쪽으로 크게 기웁니다</strong>. 공식 랭크 데이터의 특성 채용률을 정리하면 상당히 신뢰할 만한 기본 가정을 세울 수 있습니다.",
    """
    <h2>상위 50종 중 특성이 갈리는 종</h2>
    <p>아래는 싱글 사용률 상위 50종 가운데 1위 특성 채용률이 95% 미만인 종입니다. 나머지는 사실상 특성이 하나로 고정돼 있어 추측할 필요가 없습니다.</p>
    <div class="tablewrap">
    <table>
      <thead><tr><th>순위</th><th>포켓몬</th><th>1위 특성</th><th>2위 특성</th><th>그 외</th></tr></thead>
      <tbody>
        <tr><td class="num">3</td><td>마스카나</td><td><strong>변환자재 90.8%</strong></td><td>심록 9.2%</td><td>—</td></tr>
        <tr><td class="num">5</td><td>브리두라스</td><td>지구력 71.6%</td><td>옹골참 28.2%</td><td>굳건한신념 0.2%</td></tr>
        <tr><td class="num">10</td><td>마폭시</td><td><strong>맹화 89.9%</strong></td><td>매지션 10.1%</td><td>—</td></tr>
        <tr><td class="num">11</td><td>리자몽</td><td>맹화 84.0%</td><td>선파워 16.0%</td><td>—</td></tr>
        <tr><td class="num">13</td><td>개굴닌자</td><td>변환자재 82.6%</td><td>급류 17.4%</td><td>—</td></tr>
        <tr><td class="num">15</td><td>아머까오</td><td>프레셔 59.2%</td><td>미러아머 39.0%</td><td>긴장감 1.8%</td></tr>
        <tr><td class="num">16</td><td>킬라플로르</td><td><strong>독치장 93.2%</strong></td><td>부식 6.8%</td><td>—</td></tr>
        <tr><td class="num">18</td><td>대쓰여너</td><td><strong>적응력 94.5%</strong></td><td>쓱쓱 3.7%</td><td>틀깨기 1.8%</td></tr>
        <tr><td class="num">21</td><td>라이츄</td><td>피뢰침 86.4%</td><td>정전기 13.6%</td><td>—</td></tr>
        <tr><td class="num">25</td><td>찌르호크</td><td><strong>위협 91.4%</strong></td><td>이판사판 8.6%</td><td>—</td></tr>
        <tr><td class="num">27</td><td>대도각참</td><td>총대장 87.8%</td><td>오기 11.9%</td><td>프레셔 0.4%</td></tr>
        <tr><td class="num">31</td><td>드래펄트</td><td>틈새포착 76.1%</td><td>저주받은바디 12.8%</td><td>클리어바디 11.1%</td></tr>
        <tr><td class="num">33</td><td>블래키</td><td>정신력 61.1%</td><td>싱크로 38.9%</td><td>—</td></tr>
        <tr><td class="num">35</td><td>이어롭</td><td>유연 75.7%</td><td>헤롱헤롱바디 21.4%</td><td>서투름 2.9%</td></tr>
        <tr><td class="num">36</td><td>대짱이</td><td>급류 79.8%</td><td>습기 20.2%</td><td>—</td></tr>
        <tr><td class="num">37</td><td>메가니움</td><td>심록 62.1%</td><td>리프가드 37.9%</td><td>—</td></tr>
        <tr><td class="num">40</td><td>이상해꽃</td><td>엽록소 70.5%</td><td>심록 29.5%</td><td>—</td></tr>
        <tr><td class="num">42</td><td>몰드류</td><td>틀깨기 69.9%</td><td>모래헤치기 29.2%</td><td>모래의힘 0.9%</td></tr>
        <tr><td class="num">48</td><td>픽시</td><td>천진 85.0%</td><td>매직가드 13.9%</td><td>헤롱헤롱바디 1.1%</td></tr>
        <tr><td class="num">49</td><td>스코빌런</td><td>변덕쟁이 57.5%</td><td>불면 39.4%</td><td>엽록소 3.1%</td></tr>
        <tr><td class="num">50</td><td>거북왕</td><td>급류 72.8%</td><td>젖은접시 27.2%</td><td>—</td></tr>
      </tbody>
    </table>
    </div>

    <h2>세 등급으로 나눠서 다루면 됩니다</h2>

    <h3>① 90% 이상 — 그냥 확정으로 취급</h3>
    <p>마스카나(변환자재 90.8%), 마폭시(맹화 89.9%), 킬라플로르(독치장 93.2%), 대쓰여너(적응력 94.5%), 찌르호크(위협 91.4%). 열 번 중 아홉 번은 맞습니다. <strong>계산할 때 1위 특성을 그냥 확정으로 놓아도 실전 손해가 거의 없습니다.</strong></p>
    <p>다만 예외가 걸렸을 때의 파급이 큰 경우는 따로 기억해 둡니다. 마스카나의 변환자재는 <strong>기술 타입이 곧 자기 타입이 되는</strong> 특성이라, 심록 개체(9.2%)와는 데미지 계산이 완전히 달라집니다.</p>

    <h3>② 70~90% — 기본값으로 쓰되 어긋나면 즉시 갱신</h3>
    <p>리자몽(맹화 84%), 개굴닌자(변환자재 82.6%), 라이츄(피뢰침 86.4%), 대도각참(총대장 87.8%), 드래펄트(틈새포착 76.1%), 이어롭(유연 75.7%), 대짱이(급류 79.8%), 이상해꽃(엽록소 70.5%), 몰드류(틀깨기 69.9%), 거북왕(급류 72.8%), 픽시(천진 85%).</p>
    <p>이 구간은 <strong>다섯 판에 한 번쯤은 틀립니다</strong>. 그래서 "계산이 예상과 어긋났다"는 신호가 나오면 특성을 먼저 의심해야 합니다.</p>
    <p>특히 주의할 조합이 몇 개 있습니다.</p>
    <ul>
      <li><strong>이상해꽃 엽록소 70.5%</strong> — 쾌청이 깔려 있으면 스피드가 2배가 됩니다. 무보정이라고 계산해 놓고 선공을 뺏기는 대표적 사례입니다.</li>
      <li><strong>몰드류 틀깨기 69.9%</strong> — 방어 측 특성 보정을 통째로 무시합니다. 부유로 지진을 피할 생각이었다면 그 계획이 70% 확률로 깨집니다.</li>
      <li><strong>픽시 천진 85%</strong> — 상대의 능력 변화 랭크를 무시합니다. 칼춤을 몇 번 쌓았든 픽시 앞에서는 의미가 없습니다.</li>
      <li><strong>드래펄트 틈새포착 76.1%</strong> — 리플렉터·빛의장막을 관통합니다. 벽을 깔았으니 버틴다는 계산이 무너집니다.</li>
    </ul>

    <h3>③ 70% 미만 — 추측하지 말고 정보를 기다린다</h3>
    <p>아머까오(프레셔 59.2% / 미러아머 39.0%), 블래키(정신력 61.1% / 싱크로 38.9%), 메가니움(심록 62.1% / 리프가드 37.9%), 스코빌런(변덕쟁이 57.5% / 불면 39.4%), 브리두라스(지구력 71.6% / 옹골참 28.2%).</p>
    <p>이 구간은 사실상 <strong>동전 던지기에 가깝습니다</strong>. 브리두라스의 옹골참(28.2%)이 걸리면 HP 풀에서 확정 1타가 아예 성립하지 않습니다. 이런 상대에게는 확정 1타를 전제한 플레이 자체를 피하고, 2타로 잡는 안전한 경로를 잡는 편이 낫습니다.</p>

    <h2>메가진화는 예외입니다</h2>
    <p>메가진화한 포켓몬의 특성은 <strong>폼에 고정</strong>됩니다. 리자몽이 메가 X가 되면 특성은 무조건 단단한발톱, 메가 Y가 되면 무조건 가뭄입니다. 메가 전의 채용률(맹화 84% / 선파워 16%)은 메가 이후에는 아무 의미가 없습니다.</p>
    <p>즉 <strong>상대가 메가진화하는 순간 특성 추측 문제는 사라집니다</strong>. 대신 어떤 메가인지가 새 문제가 되는데, 이건 지닌 도구(메가스톤 종류)로 결정되므로 도구가 드러나면 같이 확정됩니다.</p>

    <h2>특성 정보를 얻는 순간들</h2>
    <ul>
      <li><strong>등장 시 발동</strong> — 위협(공격 1랭크 다운), 프레셔, 가뭄·잔비 같은 날씨 특성은 나오자마자 로그에 뜹니다.</li>
      <li><strong>피격 시 발동</strong> — 까칠한피부·정전기·불꽃몸은 때린 쪽에 효과가 돌아옵니다.</li>
      <li><strong>데미지가 안 맞을 때</strong> — 계산보다 적게 들어갔다면 두꺼운지방·이상한비늘·퍼코트 계열, 아예 0이면 부유·저수·피뢰침 계열입니다.</li>
      <li><strong>기술 타입이 바뀔 때</strong> — 변환자재·-스킨 계열은 로그의 상성 표기로 드러납니다.</li>
    </ul>
    <p><a href="/">데스크탑 앱</a>은 이 추정을 3단계로 자동 관리합니다. 기본값은 <strong>채용률 1위 특성</strong>이고, 배틀 중 확정된 정보를 입력하면 그 값이 우선하며, 가정을 바꿔 보고 싶으면 시뮬레이션 지정이 최우선으로 적용됩니다. 위 표를 외우지 않아도 같은 판단이 자동으로 이뤄집니다.</p>
""",
    related=[("/guide/item-meta/", "지닌도구 메타"),
             ("/guide/matchup-map/", "상성 지도"),
             ("/guide/abilities-items/", "특성·지닌도구 기본 가이드")])

# ══════════════════════════════════════════════════════════════════════
# 7. 싱글과 더블은 다른 게임
# ══════════════════════════════════════════════════════════════════════
col(
    "singles-vs-doubles",
    "싱글과 더블은 다른 게임 — 순위 격차 데이터",
    "포켓몬 챔피언스 싱글·더블 사용률 순위를 나란히 놓으면 같은 포켓몬의 평가가 100계단 넘게 갈립니다. 키키링 176위→8위, 하마돈 4위→130위. 무엇이 이 격차를 만드는지 분석합니다.",
    "싱글·더블 사용률 순위 격차와 그 원인 분석.",
    "싱글과 더블은 다른 게임",
    "싱글과 더블은 다른 게임 — 순위 격차 데이터",
    "싱글에서 잘 쓰던 파티를 더블에 그대로 들고 가면 대개 잘 안 됩니다. 감각적으로는 다들 아는 이야기인데, 공식 랭크 데이터의 싱글·더블 순위를 나란히 놓으면 그 격차가 얼마나 큰지 숫자로 드러납니다. <strong>같은 포켓몬이 100계단 넘게 움직입니다.</strong>",
    """
    <h2>더블에서 급등하는 포켓몬</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>포켓몬</th><th>싱글 순위</th><th>더블 순위</th><th>변동</th></tr></thead>
      <tbody>
        <tr><td>키키링</td><td class="num">176위</td><td class="num"><strong>8위</strong></td><td class="num">+168</td></tr>
        <tr><td>하랑우탄</td><td class="num">227위</td><td class="num">59위</td><td class="num">+168</td></tr>
        <tr><td>폭타</td><td class="num">192위</td><td class="num">58위</td><td class="num">+134</td></tr>
        <tr><td>달코퀸</td><td class="num">153위</td><td class="num">42위</td><td class="num">+111</td></tr>
        <tr><td>코터스</td><td class="num">122위</td><td class="num">22위</td><td class="num">+100</td></tr>
        <tr><td>왕구리</td><td class="num">140위</td><td class="num">45위</td><td class="num">+95</td></tr>
        <tr><td>프테라</td><td class="num">106위</td><td class="num">14위</td><td class="num">+92</td></tr>
        <tr><td>파이어로</td><td class="num">117위</td><td class="num">34위</td><td class="num">+83</td></tr>
        <tr><td>어흥염</td><td class="num">84위</td><td class="num"><strong>3위</strong></td><td class="num">+81</td></tr>
        <tr><td>그우린차</td><td class="num">71위</td><td class="num"><strong>4위</strong></td><td class="num">+67</td></tr>
        <tr><td>밀로틱</td><td class="num">63위</td><td class="num">17위</td><td class="num">+46</td></tr>
      </tbody>
    </table>
    </div>

    <h2>싱글에서만 강한 포켓몬</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>포켓몬</th><th>싱글 순위</th><th>더블 순위</th><th>변동</th></tr></thead>
      <tbody>
        <tr><td>하마돈</td><td class="num"><strong>4위</strong></td><td class="num">130위</td><td class="num">-126</td></tr>
        <tr><td>라우드본</td><td class="num">30위</td><td class="num">123위</td><td class="num">-93</td></tr>
        <tr><td>킬가르도</td><td class="num">17위</td><td class="num">91위</td><td class="num">-74</td></tr>
        <tr><td>블래키</td><td class="num">33위</td><td class="num">105위</td><td class="num">-72</td></tr>
        <tr><td>아쿠스타</td><td class="num">24위</td><td class="num">92위</td><td class="num">-68</td></tr>
        <tr><td>이어롭</td><td class="num">35위</td><td class="num">101위</td><td class="num">-66</td></tr>
        <tr><td>따라큐</td><td class="num"><strong>2위</strong></td><td class="num">63위</td><td class="num">-61</td></tr>
        <tr><td>갸라도스</td><td class="num">8위</td><td class="num">67위</td><td class="num">-59</td></tr>
        <tr><td>찌리배리</td><td class="num">28위</td><td class="num">86위</td><td class="num">-58</td></tr>
        <tr><td>개굴닌자</td><td class="num">13위</td><td class="num">68위</td><td class="num">-55</td></tr>
      </tbody>
    </table>
    </div>

    <h2>격차를 만드는 세 가지 축</h2>

    <h3>① 광역기 — 한 번에 둘을 때린다</h3>
    <p>더블에서 급등한 포켓몬 대부분이 <strong>광역기를 가진 종</strong>입니다. 폭타·코터스는 분화·열풍 계열, 프테라는 스톤샤워를 씁니다. 상대 두 마리를 동시에 때리면 실질 화력이 그대로 두 배가 됩니다.</p>
    <p>다만 광역기는 데미지에 <strong>×0.75 보정</strong>이 붙습니다. 싱글 기준으로 확정 1타였던 계산이 더블에서는 확정이 아니게 되는 경우가 자주 생깁니다. 더블 계산에서 가장 흔한 실수가 이 보정을 빼먹는 것입니다.</p>

    <h3>② 서포트 — 싱글에는 존재하지 않는 역할</h3>
    <p>어흥염이 싱글 84위에서 <strong>더블 3위</strong>로 뛴 것이 대표적입니다. 위협으로 상대 두 마리의 공격을 동시에 떨어뜨리고, 속이기로 한 마리의 행동을 막습니다. 싱글에서는 위협이 한 마리에게만 걸리고 속이기는 한 턴 벌기에 그치지만, 더블에서는 <strong>두 배로 작동</strong>합니다.</p>
    <p>키키링(176→8위)과 그우린차(71→4위)도 같은 계열입니다. 혼자서는 상대를 못 이기지만 파트너를 이기게 만드는 포켓몬들이고, 이런 역할은 싱글에 아예 존재하지 않습니다.</p>

    <h3>③ 장기전 구조의 소멸</h3>
    <p>반대로 하마돈이 4위에서 130위로 떨어진 이유가 여기 있습니다. 하마돈의 강점은 <strong>버티면서 하품으로 상대를 재우고 지진으로 조금씩 깎는</strong> 장기전입니다. 그런데 더블은 상대가 둘이라 한 마리를 재워도 다른 한 마리가 계속 때립니다. 턴당 받는 공격이 두 배가 되면 "버티면서 이긴다"는 전제 자체가 무너집니다.</p>
    <p>블래키·라우드본·이어롭이 함께 떨어진 것도 같은 이유입니다. 게다가 하마돈의 지진은 더블에서 <strong>내 파트너까지 때립니다</strong>. 싱글 최강급 기술이 더블에서는 파트너를 가려 뽑아야 하는 부담이 됩니다.</p>

    <h3>따라큐 2위 → 63위, 조금 다른 이야기</h3>
    <p>따라큐의 하락(-61)은 다른 이유입니다. 탈 특성은 <strong>공격을 딱 한 번 무효화</strong>합니다. 싱글에서는 한 턴을 확실히 버는 강력한 능력이지만, 더블에서는 같은 턴에 두 번 맞으므로 첫 공격에 탈이 벗겨지고 두 번째 공격이 그대로 들어옵니다. <strong>"한 번 무효"의 값어치가 절반이 되는</strong> 구조입니다.</p>
    <p>같은 이유로 기합의띠도 더블에서 값어치가 떨어집니다. 한 번 버텨도 파트너 쪽 공격에 마무리당하기 때문입니다.</p>

    <h2>파티를 옮길 때 점검할 것</h2>
    <ul>
      <li><strong>지진 보유자</strong> — 더블에서는 파트너도 때립니다. 비행 타입이나 부유 파트너와 함께 쓰거나, 기술을 바꿔야 합니다.</li>
      <li><strong>내구·장기전 포켓몬</strong> — 턴당 피해가 두 배가 되므로 대체로 그대로는 안 굴러갑니다.</li>
      <li><strong>서포트 요원 확보</strong> — 위협·속이기·순풍·트릭룸 요원이 하나도 없으면 더블에서는 대체로 불리합니다.</li>
      <li><strong>광역기 계산</strong> — ×0.75 보정을 넣고 다시 계산해야 합니다.</li>
    </ul>
    <p><a href="/battle-data/doubles/">더블 배틀데이터</a>에서 더블 전용 순위·채용률을 따로 볼 수 있고, <a href="/pokedex/">도감 상세 페이지</a>도 싱글과 더블 통계를 나란히 싣고 있습니다. <a href="/">데스크탑 앱</a>은 더블 모드를 감지하면 광역기 보정과 4마리 선출 추천으로 자동 전환합니다.</p>
""",
    related=[("/guide/meta-doubles/", "더블 메타 분석"),
             ("/guide/matchup-map/", "상성 지도"),
             ("/guide/team-cores/", "실제로 함께 쓰이는 코어")])

# ══════════════════════════════════════════════════════════════════════
# 8. 성격 선택의 실제
# ══════════════════════════════════════════════════════════════════════
col(
    "nature-meta",
    "성격 선택의 실제 — 최속이 정답이 아닌 경우",
    "포켓몬 챔피언스 상위 50종의 1위 성격을 집계하면 스피드 상승 성격은 28%뿐입니다. 고집·조심·대담이 왜 더 많이 선택되는지, 성격 보정이 실수치에 얼마나 영향을 주는지 계산과 함께 정리합니다.",
    "상위 50종의 성격 채용 집계 — 스피드 상승은 28%뿐.",
    "성격 선택의 실제",
    "성격 선택의 실제 — 최속이 정답이 아닌 경우",
    "\"일단 최속\"은 오래된 상식입니다. 그런데 포켓몬 챔피언스 상위 50종의 실제 1위 성격을 세어 보면 <strong>스피드를 올리는 성격은 28%에 불과합니다</strong>. 나머지 72%는 스피드를 포기했습니다. 왜 그런지 데이터와 계산으로 따라가 봅니다.",
    """
    <h2>상위 50종의 1위 성격 집계</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>성격</th><th>종 수</th><th>올림 / 내림</th><th>성격이 노리는 것</th></tr></thead>
      <tbody>
        <tr><td><strong>고집</strong></td><td class="num">12종</td><td>공격 ↑ / 특공 ↓</td><td>물리 화력</td></tr>
        <tr><td>조심</td><td class="num">9종</td><td>특공 ↑ / 공격 ↓</td><td>특수 화력</td></tr>
        <tr><td>대담</td><td class="num">9종</td><td>방어 ↑ / 공격 ↓</td><td>물리 내구</td></tr>
        <tr><td>명랑</td><td class="num">7종</td><td>스피드 ↑ / 특공 ↓</td><td>물리 + 선공</td></tr>
        <tr><td>겁쟁이</td><td class="num">7종</td><td>스피드 ↑ / 공격 ↓</td><td>특수 + 선공</td></tr>
        <tr><td>장난꾸러기</td><td class="num">3종</td><td>방어 ↑ / 특공 ↓</td><td>물리 내구</td></tr>
        <tr><td>차분 · 무사태평 · 신중</td><td class="num">각 1종</td><td>특방 계열</td><td>특수 내구</td></tr>
      </tbody>
    </table>
    </div>
    <p><strong>스피드 상승 성격(명랑 + 겁쟁이) = 14종 / 50종 = 28%.</strong> 화력 성격(고집 + 조심)이 21종으로 가장 많고, 내구 성격(대담 + 장난꾸러기 + 특방 계열)이 15종으로 그 다음입니다.</p>

    <h2>왜 최속을 포기하나 — 숫자로 보기</h2>
    <p>성격 보정은 <strong>노력치까지 더한 값 전체에 ×1.1 또는 ×0.9</strong>가 곱해집니다.</p>
    <div class="formula">실수치 = floor( ( floor((2×종족값+31)×50÷100) + 5 + 노력치 ) × 성격보정 )</div>
    <p>종족값 100짜리 능력치를 예로 들면, 무보정은 136, 노력치 32를 다 주면 168, 여기에 성격 ×1.1까지 얹으면 184입니다.</p>
    <div class="tablewrap">
    <table>
      <thead><tr><th>조건</th><th>실수치</th><th>무보정 대비</th></tr></thead>
      <tbody>
        <tr><td>노력치 0 · 성격 무보정</td><td class="num">136</td><td class="num">—</td></tr>
        <tr><td>노력치 32 · 성격 무보정</td><td class="num">168</td><td class="num">+32</td></tr>
        <tr><td>노력치 32 · 성격 ↑</td><td class="num">184</td><td class="num">+48</td></tr>
        <tr><td>노력치 0 · 성격 ↑</td><td class="num">149</td><td class="num">+13</td></tr>
      </tbody>
    </table>
    </div>
    <p>여기서 핵심은 <strong>노력치 32(+32)가 성격 보정(+16)보다 두 배 크다</strong>는 점입니다. 본가에서는 노력치 252가 실수치를 63 올려 성격 보정과 비슷한 급이었지만, 챔피언스는 노력치 상한이 32라 이 균형이 완전히 다릅니다.</p>
    <p>그래서 판단이 이렇게 됩니다. <strong>어차피 노력치 32를 넣어도 상대보다 느리다면, 성격까지 스피드에 태워도 여전히 느립니다.</strong> 그럴 바에는 성격을 화력이나 내구에 돌리는 편이 확실한 이득입니다.</p>

    <h2>실제 배분과 겹쳐 보기</h2>
    <p><a href="/guide/ev-reality/">노력치 배분 분석</a>에서 봤듯 상위 50종의 96%가 32급 능력치를 두 개 가집니다. 성격은 그중 하나에 얹는 것이 표준입니다.</p>
    <ul>
      <li><strong>공격 32 + 스피드 32 + 명랑</strong> — 한카리아스·마스카나·메타그로스형. 선공을 확실히 잡아야 하는 에이스.</li>
      <li><strong>공격 32 + 스피드 32 + 고집</strong> — 스피드는 노력치로만 챙기고 성격은 화력에. 상대 스피드 라인을 넘길 자신이 없을 때.</li>
      <li><strong>HP 32 + 방어 32 + 대담</strong> — 하마돈·아머까오형. 스피드는 완전히 포기.</li>
      <li><strong>HP 32 + 특공 32 + 조심</strong> — 누리레느형. 맞으면서 때리는 구조.</li>
    </ul>
    <p>대담이 9종이나 되는 것은 <a href="/guide/what-kills-you/">패배 기록 분석</a>과 맞물립니다. 격침의 상당수가 물리 기술(지진 19.3%, 인파이트 5.9%, 플레어드라이브 3.4%, 불릿펀치 3.4%)이므로, 물리 내구에 성격을 태우는 선택이 실전에서 자주 보상받습니다.</p>

    <h2>내림 스탯을 고르는 기준</h2>
    <p>성격은 하나를 올리면 반드시 하나를 내립니다. ×0.9는 생각보다 큽니다 — 실수치 136짜리 능력치라면 13이 깎입니다.</p>
    <ul>
      <li><strong>물리 어태커는 특공을 내린다</strong>(고집·명랑). 특수기를 안 쓰니 손해가 0입니다. 12종이 고집인 이유입니다.</li>
      <li><strong>특수 어태커는 공격을 내린다</strong>(조심·겁쟁이). 단 <strong>속임수</strong>를 조심해야 합니다. 이 기술은 <strong>상대의 공격 수치</strong>로 데미지를 계산하므로, 공격을 내린 특수 어태커는 속임수에 오히려 덜 아픕니다. 유리한 쪽입니다.</li>
      <li><strong>내구형은 안 쓰는 공격 계열을 내린다</strong>(대담은 공격, 장난꾸러기는 특공).</li>
      <li><strong>바디프레스 사용자는 공격을 내려도 손해가 없습니다</strong> — 이 기술은 방어 수치로 계산합니다. 아머까오가 대표적입니다.</li>
    </ul>

    <h2>상대 성격을 추정하는 법</h2>
    <p>성격은 보이지 않지만 상위권은 선택이 좁아 추정이 가능합니다. 공식 데이터에는 종별 성격 채용률이 들어 있어, 예컨대 한카리아스는 명랑 54.4% / 고집 26.7% / 장난꾸러기 14.7%로 갈립니다.</p>
    <ul>
      <li>상대가 <strong>먼저 움직였다</strong> → 스피드 상승 성격이거나 구애스카프입니다. 어느 쪽이든 이후 계산이 크게 달라집니다.</li>
      <li>상대의 공격이 <strong>예상보다 아팠다</strong> → 화력 성격입니다. 그러면 대체로 스피드는 무보정입니다.</li>
      <li>상대가 <strong>확정 1타를 버텼다</strong> → 내구 성격이거나 HP 투자형입니다.</li>
    </ul>
    <p><a href="/">데스크탑 앱</a>은 채용률 1위 성격·노력치를 기본 가정으로 잡고, 그 가정이 반영된 데미지 범위를 위력 칩 테두리로 표시합니다. 실전 중에 위 추정을 머릿속으로 할 필요가 없습니다.</p>
""",
    related=[("/guide/ev-reality/", "노력치 66의 현실"),
             ("/guide/speed-guide/", "스피드 실전 가이드"),
             ("/guide/ev-nature/", "노력치·성격 배분 가이드")])

# ══════════════════════════════════════════════════════════════════════
# 9. 실제로 함께 쓰이는 코어
# ══════════════════════════════════════════════════════════════════════
col(
    "team-cores",
    "실제로 함께 쓰이는 코어 — 팀 조합 데이터로 본 파티 구성",
    "포켓몬 챔피언스 공식 랭크 데이터의 팀 조합 기록을 분석해, 상위권이 실제로 어떤 포켓몬을 함께 쓰는지 정리했습니다. 한카리아스·따라큐 중심의 코어 구조와 그 이유.",
    "공식 팀 조합 기록으로 본 실제 파티 코어 구조.",
    "실제로 함께 쓰이는 코어",
    "실제로 함께 쓰이는 코어 — 팀 조합 데이터로 본 파티 구성",
    "\"이 포켓몬과 저 포켓몬은 궁합이 좋다\"는 말은 대체로 감각에 기댑니다. 공식 랭크 데이터에는 각 포켓몬이 <strong>실제로 어떤 포켓몬과 같은 파티에 편성됐는지</strong>가 기록돼 있습니다. 상위권이 실제로 무엇을 함께 쓰는지 보면, 파티 구성의 실전 논리가 드러납니다.",
    """
    <h2>상위권 코어의 실제 모습</h2>
    <p>싱글 사용률 상위 30종을 대상으로, 서로의 팀 조합 목록에 <strong>양방향으로</strong> 등장하는 쌍을 뽑았습니다. 한쪽만 상대를 지목한 게 아니라 서로가 서로를 지목한 조합이라, 우연이 아닌 실제 코어로 볼 수 있습니다.</p>
    <div class="tablewrap">
    <table>
      <thead><tr><th>중심 포켓몬</th><th>함께 쓰이는 상위권</th></tr></thead>
      <tbody>
        <tr><td><a href="/pokedex/garchomp/"><strong>한카리아스</strong></a> (1위)</td><td>따라큐 · 누리레느 · 마스카나 · 메타그로스 · 브리두라스 · 갸라도스 · 마폭시 · 리자몽 · 번치코 · 핫삼</td></tr>
        <tr><td><a href="/pokedex/mimikyu/"><strong>따라큐</strong></a> (2위)</td><td>한카리아스 · 메타그로스 · 하마돈 · 브리두라스 · 누리레느 · 마스카나 · 리자몽 · 갸라도스 · 마폭시 · 개굴닌자</td></tr>
        <tr><td><a href="/pokedex/meowscarada/">마스카나</a> (3위)</td><td>한카리아스 · 따라큐 · 하마돈 · 누리레느 · 메타그로스</td></tr>
      </tbody>
    </table>
    </div>
    <p>한카리아스와 따라큐가 <strong>거의 모든 상위권과 짝을 이룹니다</strong>. 상위 30종 중 열 종씩과 양방향으로 엮여 있습니다. 이건 "이 둘이 특정 포켓몬과 궁합이 좋다"가 아니라 <strong>"이 둘은 아무 파티에나 들어간다"</strong>는 뜻에 가깝습니다.</p>

    <h2>범용 코어와 전용 코어</h2>

    <h3>범용형 — 파티를 안 가린다</h3>
    <p>한카리아스가 이 자리에 있는 이유는 명확합니다. 땅·드래곤 타입에 지진 채용률 99.3%, 스텔스록 46.8%. <a href="/guide/what-kills-you/">격침 1위 기술</a>을 자속으로 쓰면서 설치기까지 겸합니다. 공격 성능과 지원 성능을 한 자리에서 해결하니 어떤 구성에도 들어갑니다.</p>
    <p>따라큐는 다른 방향의 범용성입니다. 탈 특성이 <strong>어떤 공격이든 한 번은 무효화</strong>하므로, 상대가 누구든 최소 한 턴은 확보됩니다. 상성 계산이 필요 없는 안정성이라 파티를 가리지 않습니다.</p>
    <p>이런 포켓몬을 파티에 넣는 것은 안전하지만, <strong>상대도 대비하고 있다</strong>는 점을 잊으면 안 됩니다. 사용률 1·2위라는 건 모든 상대가 이 둘의 대책을 들고 온다는 뜻입니다.</p>

    <h3>전용형 — 특정 구조에서만 작동</h3>
    <p>반대로 하마돈은 따라큐·마스카나와는 자주 묶이는데 한카리아스와는 덜 묶입니다. 둘 다 땅 타입이라 <strong>약점을 공유</strong>하기 때문입니다. 물·풀·얼음 한 방향에 두 마리가 함께 무너지는 구성은 상위권에서 자연스럽게 걸러집니다.</p>
    <p>이것이 팀 조합 데이터에서 읽어야 할 첫 번째 규칙입니다. <strong>강한 포켓몬 둘을 나열하는 게 아니라, 약점이 겹치지 않는 둘을 고르는 것</strong>입니다.</p>

    <h2>코어가 실제로 하는 일</h2>

    <h3>① 약점 상호 보완</h3>
    <p>한카리아스(땅·드래곤)의 약점은 얼음·페어리·드래곤입니다. 자주 짝을 이루는 핫삼(벌레·강철)은 얼음을 반감하고 페어리에 강합니다. 반대로 핫삼의 약점인 불꽃은 한카리아스가 땅으로 받아냅니다. 전형적인 상호 보완 구조입니다.</p>
    <p>누리레느(물·페어리)와의 조합도 같습니다. 누리레느는 한카리아스가 약한 얼음과 드래곤을 모두 반감합니다.</p>

    <h3>② 역할 분담</h3>
    <p>한카리아스 + 메타그로스처럼 <strong>물리 어태커 둘</strong>이 묶이는 경우도 많습니다. 이건 보완이 아니라 압박의 중첩입니다. 상대가 물리 벽을 하나만 준비했다면 둘 중 하나는 반드시 통과합니다.</p>
    <p>반면 한카리아스 + 브리두라스는 물리와 특수를 나눠 가집니다. 상대가 어느 쪽 벽을 내밀어도 다른 쪽이 답이 됩니다.</p>

    <h3>③ 설치와 마무리</h3>
    <p>한카리아스의 스텔스록 채용률 46.8%는 이 포켓몬이 <strong>설치 담당</strong>도 겸한다는 뜻입니다. 설치기가 깔리면 상대가 교체할 때마다 체력이 깎이고, <a href="/guide/item-meta/">기합의띠</a>의 발동 조건(HP 풀)도 깨집니다.</p>
    <p>따라큐·핫삼처럼 <a href="/guide/finishers/">우선도 기술로 마무리하는 포켓몬</a>과 조합하면 이 효과가 배가됩니다. 설치기로 깎고, 주력기로 밀고, 우선도로 끝내는 3단 구성이 상위권 파티의 기본 골격입니다.</p>

    <h2>파티를 짤 때 쓰는 순서</h2>
    <ol>
      <li><strong>에이스를 먼저 정합니다.</strong> 승리 조건이 될 포켓몬 하나를 고릅니다.</li>
      <li><strong>그 에이스의 약점 3개를 적습니다.</strong> 그중 둘 이상을 반감하거나 무효화하는 포켓몬을 두 번째로 넣습니다.</li>
      <li><strong>땅 대책을 확인합니다.</strong> 격침의 19.9%가 땅입니다. 파티에 땅 약점이 셋 이상이면 재구성합니다.</li>
      <li><strong>물리·특수 균형을 맞춥니다.</strong> 한쪽으로 몰리면 벽 하나에 막힙니다.</li>
      <li><strong>설치기와 우선도 기술 보유자를 각각 하나씩</strong> 확보합니다.</li>
    </ol>
    <p><a href="/builder/">파티 빌더</a>는 이 점검을 자동으로 해 줍니다. 슬롯을 채우는 대로 겹치는 약점·부족한 커버리지를 진단 태그로 표시하고, 남은 자리에 넣을 후보를 근거 문장과 함께 추천합니다. 포켓몬별 실제 팀 조합 기록은 <a href="/pokedex/">도감 상세 페이지</a>의 "팀 조합 · 매치업" 항목에서 종별로 확인할 수 있습니다.</p>
""",
    related=[("/guide/matchup-map/", "상성 지도"),
             ("/guide/what-kills-you/", "무엇에 죽는가 — 패배 기록 분석"),
             ("/guide/team-building/", "파티 구성 기본 가이드")])

# ══════════════════════════════════════════════════════════════════════
# 10. 선출 전 30초
# ══════════════════════════════════════════════════════════════════════
col(
    "reading-opponent",
    "선출 전 30초 — 상대 파티 6마리에서 읽어내는 것",
    "포켓몬 챔피언스는 선출 화면에서 상대 6마리를 봅니다. 제한된 시간에 무엇을 먼저 확인해야 하는지, 채용률 데이터를 근거로 우선순위를 정리한 실전 체크리스트입니다.",
    "선출 화면에서 상대 파티를 읽는 실전 우선순위 체크리스트.",
    "선출 전 30초",
    "선출 전 30초 — 상대 파티 6마리에서 읽어내는 것",
    "포켓몬 챔피언스의 승부는 상당 부분 선출 화면에서 갈립니다. 상대 6마리를 보고 내 3마리(더블은 4마리)를 고르는 이 짧은 시간에 무엇을 봐야 하는지, 앞선 칼럼들의 데이터를 근거로 우선순위를 정리했습니다.",
    """
    <h2>왜 순서가 중요한가</h2>
    <p>선출 시간에 6마리 전부를 분석할 수는 없습니다. <strong>확인 순서를 정해 두고 위에서부터 훑는 것</strong>이 현실적입니다. 아래 순서는 실제 데이터에서 영향이 큰 순으로 배열했습니다.</p>

    <h2>1순위 — 땅 기술 사용자를 먼저 찾는다</h2>
    <p><a href="/guide/what-kills-you/">패배 기록 분석</a>에서 지진 한 기술이 전체 격침의 19.3%, 땅 타입 전체가 19.9%였습니다. 상대 파티에서 땅 기술을 쓸 수 있는 포켓몬을 먼저 세는 것이 가장 효율이 높습니다.</p>
    <ul>
      <li>땅 타입 포켓몬(한카리아스·하마돈·몰드류 등)은 지진 채용률이 사실상 100%에 가깝습니다.</li>
      <li>땅이 아니어도 지진을 배우는 포켓몬이 많습니다. 메타그로스·갸라도스·킬가르도 등.</li>
      <li>내 선출 후보 중 땅에 약한 포켓몬이 둘 이상이면 그중 하나는 빼는 것을 고려합니다.</li>
    </ul>

    <h2>2순위 — 내 에이스가 확실히 지는 상대가 있는가</h2>
    <p><a href="/guide/matchup-map/">상성 지도</a>의 "확실히 짐" 칸을 떠올립니다. 내가 축으로 삼으려는 포켓몬을 확실히 잡는 상대가 6마리 안에 있다면, 그 포켓몬은 선봉에서 빼거나 아예 선출하지 않습니다.</p>
    <p>예를 들어 아머까오를 축으로 잡았는데 상대에 리자몽·마폭시·번치코 중 하나라도 있으면 계획을 다시 짜야 합니다. 반대로 상대에 한카리아스·마스카나·갸라도스가 있다면 아머까오는 좋은 선택입니다.</p>

    <h2>3순위 — 스피드 라인을 긋는다</h2>
    <p>상대 6마리 중 <strong>내 에이스보다 빠를 가능성이 있는 포켓몬</strong>만 추립니다. 종족값 기준으로 최속을 계산해 내 실수치와 비교합니다.</p>
    <p>여기서 두 가지 보정을 반드시 넣습니다.</p>
    <ul>
      <li><strong>구애스카프 8.7%</strong> — <a href="/guide/item-meta/">도구 메타</a> 기준 열두 마리 중 하나꼴입니다. 스피드가 애매한 상대는 스카프 가능성을 열어 둡니다.</li>
      <li><strong>스피드 특성</strong> — 이상해꽃의 엽록소(70.5%)처럼 날씨·상태에 따라 2배가 되는 특성이 있습니다. 상대 파티에 날씨 요원이 함께 있으면 특히 주의합니다.</li>
    </ul>
    <p>다만 <a href="/guide/nature-meta/">성격 집계</a>에서 봤듯 상위 50종의 72%는 스피드 상승 성격을 쓰지 않습니다. <strong>모든 상대를 최속으로 가정하면 과하게 비관적</strong>이 됩니다. 채용률 1위 성격을 기본으로 놓고 계산하는 편이 실전에 가깝습니다.</p>

    <h2>4순위 — 특성이 갈리는 포켓몬을 표시해 둔다</h2>
    <p><a href="/guide/ability-guessing/">특성 확률표</a>에서 70% 미만 구간에 있는 포켓몬(아머까오·블래키·브리두라스·스코빌런 등)이 상대 파티에 있으면, 그 포켓몬 상대로는 <strong>확정 1타를 전제한 플레이를 피합니다</strong>. 브리두라스의 옹골참(28.2%)이 걸리면 확정 1타가 성립하지 않습니다.</p>

    <h2>5순위 — 상대 파티의 구조를 읽는다</h2>
    <p>6마리를 개별로만 보지 말고 <a href="/guide/team-cores/">코어 구조</a>를 봅니다.</p>
    <ul>
      <li><strong>설치기 보유자가 있는가</strong> — 스텔스록·압정뿌리기가 깔리면 내 교체 플랜의 비용이 올라갑니다.</li>
      <li><strong>날씨·필드 요원이 있는가</strong> — 가뭄·잔비 특성이나 순풍·트릭룸 요원이 있으면 판의 규칙 자체가 바뀝니다.</li>
      <li><strong>벽 요원이 있는가</strong> — 빛의점토(3.7%) 보유자가 있으면 장기전 구도를 각오해야 합니다.</li>
      <li><strong>메가 후보가 몇인가</strong> — 메가는 판당 한 번뿐이라, 후보가 여럿이면 어느 쪽이 나올지가 곧 상대의 플랜입니다.</li>
    </ul>

    <h2>6순위 — 우선도 기술 보유자를 센다</h2>
    <p>야습·불릿펀치·기습만으로 격침의 약 10%입니다. 상대 파티에 이들이 있으면 <strong>내 포켓몬을 체력 30% 이하로 남겨 두는 판단</strong>이 위험해집니다. 특히 따라큐(야습)·핫삼(불릿펀치)·대도각참(기습)은 상위권에 자주 보입니다.</p>

    <h2>선출 최종 판단</h2>
    <ol>
      <li>확실히 유리한 카드가 <strong>둘 이상</strong> 있으면 그대로 갑니다.</li>
      <li>유리한 카드가 하나뿐이면, 나머지 둘은 <strong>그 하나를 지키는 구성</strong>으로 채웁니다.</li>
      <li>전부 5:5라면 선공권과 설치기 우위로 승부를 봅니다. 이 구도에서는 먼저 스텔스록을 까는 쪽이 유리합니다.</li>
      <li><strong>답이 없는 상대가 하나 있다면</strong>, 그 상대를 만나는 것을 전제로 나머지 둘로 시간을 벌 수 있는지 봅니다.</li>
    </ol>

    <h2>이 판단을 자동으로</h2>
    <p>위 여섯 단계를 30초 안에 손으로 하는 것은 현실적으로 어렵습니다. <a href="/">Champions Helper 데스크탑 앱</a>의 <strong>선출 정보</strong> 기능은 상대 파티를 화면에서 자동 인식한 뒤, 6×6 전 조합에 대해 쌍별 타수·스피드 우열을 계산해 히트맵으로 보여 줍니다. 추천 트리오와 선봉 후보, 순풍·트릭룸·벽 요원 경고까지 한 화면에 나옵니다.</p>
    <p>브라우저에서 미리 연습해 보고 싶다면 <a href="/calc/">데미지 계산기</a>와 <a href="/builder/">파티 빌더</a>로 같은 계산을 수동으로 해 볼 수 있습니다.</p>
""",
    related=[("/guide/matchup-map/", "상성 지도"),
             ("/guide/ability-guessing/", "상대 특성 맞히기"),
             ("/guide/app-guide/", "프로그램 사용 가이드")])


def build():
    n = 0
    for c in COLUMNS:
        d = os.path.join(SITE, "guide", c["slug"])
        os.makedirs(d, exist_ok=True)
        html = PAGE.format(style=STYLE, header=HEADER, footer=FOOTER,
                           snapshot=SNAPSHOT, pub=PUB, **c)
        with io.open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        n += 1
    print(f"OK — 칼럼 {n}편 생성: " + ", ".join(c["slug"] for c in COLUMNS))


if __name__ == "__main__":
    build()
