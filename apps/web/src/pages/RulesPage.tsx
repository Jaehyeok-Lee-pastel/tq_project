import { BookOpenCheck, Database, Gauge, Link, ShieldAlert, SlidersHorizontal, TrendingUp } from "lucide-react";

const ruleGroups = [
  {
    icon: <BookOpenCheck size={19} />,
    title: "앱의 핵심 철학",
    items: [
      "이 앱은 특정 종목 추천기가 아니라 QQQ 200일선 기준의 전략 코치입니다.",
      "QQQ 200일선 위에서는 시장 참여를 유지하되, 위험 조절은 현금보다 레버리지 배수 조절로 먼저 합니다.",
      "QQQ 200일선 아래에서는 수익 기회보다 생존을 우선하고, SGOV/CASH 같은 방어 자산으로 전환합니다.",
    ],
  },
  {
    icon: <TrendingUp size={19} />,
    title: "TQQQ 200일선 운용 원칙",
    items: [
      "신호는 TQQQ 자체가 아니라 QQQ 200일선을 기준으로 봅니다.",
      "정상 상승 구간에서는 TQQQ와 QQQM/SPYM 같은 1x ETF를 조합해 상승 참여를 유지합니다.",
      "과열 구간에서는 신규 TQQQ 추격매수보다 TQQQ 비중을 줄이고 1x ETF로 레버리지 강도를 낮춥니다.",
    ],
  },
  {
    icon: <ShieldAlert size={19} />,
    title: "방어 규칙",
    items: [
      "QQQ가 50일선 아래로 약해지면 TQQQ 일부를 1x ETF로 낮추는 리스크 축소를 검토합니다.",
      "QQQ가 200일선 아래에서 2거래일 이상 머물면 TQQQ와 1x 주식 노출을 줄이고 SGOV/CASH 방어를 우선합니다.",
      "SGOV는 정상 상승장의 기본 대기자산이 아니라 하락장, 극과열, 실행 대기 재원으로 사용합니다.",
    ],
  },
  {
    icon: <SlidersHorizontal size={19} />,
    title: "리스크 0~100 해석",
    items: [
      "리스크 점수가 높을수록 TQQQ 목표 비중이 커지고, 낮을수록 QQQM/SPYM/SGOV 비중이 커집니다.",
      "리스크 70 이상에서만 TQQQ 70% 수준의 공격형 배분을 허용합니다.",
      "같은 Nasdaq 계열인 TQQQ, QLD, QQQM을 과도하게 겹치지 않도록 역할을 분리합니다.",
    ],
  },
  {
    icon: <Gauge size={19} />,
    title: "검증 기준",
    items: [
      "수익률만 보지 않고 MDD, 최장 회복기간, 매매횟수, 규칙 준수 가능성을 함께 봅니다.",
      "순정 TQQQ 200일선, TQQQ+1x 변형, SGOV 방어형을 같은 원금으로 비교합니다.",
      "좋아 보이는 커스텀보다 반복 가능한 규칙과 기록 가능한 실행 판단을 우선합니다.",
    ],
  },
];

const evidenceItems = [
  {
    title: "TQQQ는 장기 3배가 아니라 일일 3배 목표 상품",
    principle: "TQQQ는 QQQ 추세 위에서 제한적으로 쓰는 공격 엔진으로 다루고, 장기 방치 자산으로 보지 않습니다.",
    source: "ProShares TQQQ",
    url: "https://www.proshares.com/our-etfs/leveraged-and-inverse/tqqq",
    note: "ProShares는 TQQQ가 Nasdaq-100 Index의 일일 성과 3배를 목표로 한다고 설명합니다.",
  },
  {
    title: "레버리지 ETF는 보유기간이 길면 목표 배수와 달라질 수 있음",
    principle: "앱은 200일선, 분할매수, 분할매도, 방어 전환을 통해 장기 레버리지 노출의 경로 의존 위험을 줄입니다.",
    source: "Investor.gov / SEC",
    url: "https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/sec",
    note: "SEC 투자자 경고는 레버리지 ETF 성과가 장기에는 기초지수 목표 배수와 크게 달라질 수 있다고 설명합니다.",
  },
  {
    title: "QQQM/SPYM은 상승장 레버리지 완충 자산",
    principle: "정상 상승장에서는 현금을 과도하게 들기보다 TQQQ 일부를 QQQM 또는 SPYM 같은 1x ETF로 낮춰 참여를 유지합니다.",
    source: "Claude playbook 검토",
    url: "/universe",
    note: "QQQM은 Nasdaq-100 노출 유지, SPYM은 S&P 500으로 기술주 집중 완화 역할을 맡습니다.",
  },
  {
    title: "SGOV는 초단기 미국 국채 대기자산",
    principle: "SGOV/BIL/CASH는 하락장 방어, 극과열 대기, 실행 대기 재원으로 사용합니다.",
    source: "iShares SGOV",
    url: "https://www.ishares.com/us/products/314116/ishares-0-3-month-treasury-bond-etf",
    note: "iShares는 SGOV가 0~3개월 미국 Treasury bill 지수를 추종하며 유동성과 낮은 금리 민감도를 추구한다고 설명합니다.",
  },
  {
    title: "백테스트는 미래 예측이 아니라 규칙 검증",
    principle: "앱은 같은 원금으로 순정 전략과 커스텀 전략을 비교해 과최적화 위험을 줄입니다.",
    source: "앱 내부 검증 원칙",
    url: "/test",
    note: "수익 곡선, MDD, 회복기간, 매매 로그를 함께 보며 전략을 판단합니다.",
  },
];

export function RulesPage() {
  return (
    <section className="page-grid">
      <div className="hero-panel rules">
        <div>
          <span className="section-label">Rules & Trust</span>
          <h2>TQQQ 200일선 전략을 어떤 원칙으로 조정하는지 확인합니다.</h2>
          <p>
            이 앱은 상승장에서는 참여를 유지하고, 과열장에서는 레버리지를 낮추며,
            하락장에서는 SGOV/CASH로 생존하는 규칙을 우선합니다.
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
            <p>전략 조언이 어떤 자료와 내부 원칙에서 나오는지 확인합니다.</p>
          </div>
          <div className="evidence-grid">
            {evidenceItems.map((item) => (
              <a
                className="evidence-card"
                href={item.url}
                key={item.title}
                rel="noreferrer"
                target={item.url.startsWith("http") ? "_blank" : undefined}
              >
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
