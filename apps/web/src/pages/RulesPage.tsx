import { BookOpenCheck, Database, Gauge, Link, ShieldAlert, SlidersHorizontal, TrendingUp } from "lucide-react";

const ruleGroups = [
  {
    icon: <BookOpenCheck size={19} />,
    title: "앱의 철학",
    items: [
      "TQQQ를 무조건 추천하지 않고, 같은 원금 기준으로 여러 전략을 비교합니다.",
      "수익률 1등보다 수익, 낙폭, 회복력, 실행 가능성, 사용자 리스크 적합도를 함께 봅니다.",
      "추천은 매수 지시가 아니라 전략 후보와 점검 근거입니다.",
    ],
  },
  {
    icon: <TrendingUp size={19} />,
    title: "QQQ 200일선 기반 TQQQ 전략",
    items: [
      "QQQ가 장기 이동평균선 위에 있을 때만 TQQQ 진입을 고려합니다.",
      "장기 이동평균선 아래에서는 TQQQ 신규 매수를 보류하고 현금성 자산을 우선합니다.",
      "장기선 위에 있어도 과열 구간이면 대매수보다 분할매수를 우선합니다.",
    ],
  },
  {
    icon: <ShieldAlert size={19} />,
    title: "방어 규칙",
    items: [
      "QQQ가 50일선 아래로 내려가면 일부 리스크 축소를 고려합니다.",
      "QQQ가 200일선 아래에서 2거래일 이상 머물면 방어 전환을 우선합니다.",
      "TQQQ는 일일 3배 상품이므로 손실 구간에서 계좌 변동이 매우 커질 수 있습니다.",
    ],
  },
  {
    icon: <SlidersHorizontal size={19} />,
    title: "검증 원칙",
    items: [
      "200일선 하나만 보지 않고 150/180/200/220/250일선 민감도를 확인합니다.",
      "전체 기간 성과보다 상승장, 하락장, 횡보장에서의 약점을 따로 확인해야 합니다.",
      "백테스트와 실시간 모의 보유 결과가 어긋나면 현재 시장 적합도를 낮게 봅니다.",
    ],
  },
  {
    icon: <Gauge size={19} />,
    title: "최종 점수",
    items: [
      "수익 점수: CAGR과 총수익률",
      "방어 점수: MDD와 최장 손실 기간",
      "적합도 점수: 사용자 리스크 점수와 전략 위험도의 거리",
      "견고성 점수: 이동평균 기준을 바꿔도 결과가 안정적인지",
    ],
  },
];

const evidenceItems = [
  {
    title: "TQQQ는 장기 3배가 아니라 일일 3배 목표 상품",
    principle: "앱은 TQQQ를 장기 방치 자산이 아니라 QQQ 추세 위에서만 제한적으로 쓰는 공격 엔진으로 다룹니다.",
    source: "ProShares TQQQ",
    url: "https://www.proshares.com/our-etfs/leveraged-and-inverse/tqqq",
    note: "ProShares는 TQQQ가 Nasdaq-100 Index의 일일 성과 3배를 목표로 한다고 설명합니다.",
  },
  {
    title: "레버리지 ETF는 하루를 넘기면 목표 배율과 달라질 수 있음",
    principle: "앱은 200일선, 분할매수, 현금성 대기자산, 매도 규칙을 통해 장기 보유 리스크를 줄이는 방향으로 설계합니다.",
    source: "Investor.gov / SEC",
    url: "https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/sec",
    note: "SEC 투자자 경고는 레버리지/인버스 ETF의 하루 초과 성과가 일일 목표와 크게 달라질 수 있다고 설명합니다.",
  },
  {
    title: "QQQ는 Nasdaq-100을 추종하는 기준 자산",
    principle: "앱은 TQQQ 자체 200일선보다 QQQ 200일선을 기준 신호로 사용합니다. 실행 상품과 신호 상품을 분리하기 위해서입니다.",
    source: "Invesco QQQ",
    url: "https://www.invesco.com/qqq-etf/en/home.html",
    note: "Invesco는 QQQ가 Nasdaq-100 Index를 추종하는 ETF이며 유동성이 높은 ETF라고 설명합니다.",
  },
  {
    title: "SGOV는 초단기 미국 국채 대기자산",
    principle: "앱은 SGOV/BIL/CASH를 방치 현금이 아니라 분할매수와 방어 전환을 위한 대기 재원으로 봅니다.",
    source: "iShares SGOV",
    url: "https://www.ishares.com/us/products/314116/ishares-0-3-month-treasury-bond-etf",
    note: "iShares는 SGOV가 0~3개월 미국 Treasury bill 지수를 추종하며 유동성과 낮은 금리 민감도를 추구한다고 설명합니다.",
  },
  {
    title: "백테스트는 의사결정 보조이지 미래 예측이 아님",
    principle: "앱은 동일 원금 비교, 민감도 검증, 모의운용, 실행 기록 리뷰를 함께 보고 과최적화 위험을 낮춥니다.",
    source: "앱 내부 검증 원칙",
    url: "/compare",
    note: "전략 연구실에서 150/180/200/220/250일 이동평균 민감도를 같이 확인합니다.",
  },
  {
    title: "TQQQ와 QLD는 동시 핵심 보유보다 대체 비교 대상",
    principle: "둘 다 Nasdaq-100 레버리지 성격이므로 같은 계좌에서 크게 섞기보다 리스크 점수에 맞춰 하나를 중심으로 선택합니다.",
    source: "앱 후보군/리스크 예산 원칙",
    url: "/universe",
    note: "ETF 후보군 화면에서 QQQ/TQQQ/QLD/SGOV의 역할을 분리해 보여줍니다.",
  },
];

export function RulesPage() {
  return (
    <section className="page-grid">
      <div className="hero-panel rules">
        <div>
          <span className="section-label">Rules & Trust</span>
          <h2>전략 추천이 어떤 원칙으로 만들어지는지 확인합니다.</h2>
          <p>
            신뢰도는 높은 수익률 하나가 아니라, 명확한 규칙과 반복 검증에서 나옵니다.
          </p>
        </div>
      </div>
      <div className="content-grid">
        <article className="panel span-12 evidence-archive">
          <div className="report-head">
            <h2 className="panel-title">
              <Database size={18} />
              근거 아카이브
            </h2>
            <p>앱의 조언이 어떤 자료와 내부 원칙에서 나오는지 확인합니다.</p>
          </div>
          <div className="evidence-grid">
            {evidenceItems.map((item) => (
              <a className="evidence-card" href={item.url} key={item.title} rel="noreferrer" target={item.url.startsWith("http") ? "_blank" : undefined}>
                <div>
                  <span className="section-label">{item.source}</span>
                  <h3>{item.title}</h3>
                </div>
                <p>{item.principle}</p>
                <small>{item.note}</small>
                <em>
                  <Link size={14} />
                  근거 보기
                </em>
              </a>
            ))}
          </div>
        </article>
        {ruleGroups.map((group) => (
          <article className="panel span-12 rule-card" key={group.title}>
            <h2 className="panel-title">
              {group.icon}
              {group.title}
            </h2>
            <ul>
              {group.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}
