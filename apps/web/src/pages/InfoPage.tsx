import { Link } from "react-router-dom";
import { BookOpenCheck, DatabaseZap, GitCompareArrows, ListChecks, ShieldCheck } from "lucide-react";

const infoCards = [
  {
    to: "/rules",
    icon: <BookOpenCheck size={19} />,
    label: "규칙과 신뢰도",
    title: "TQQQ 200일선 철학",
    body: "QQQ 200일선, 분할매수, 분할매도, 데이터 신뢰도 기준을 한곳에서 확인합니다.",
  },
  {
    to: "/universe",
    icon: <DatabaseZap size={19} />,
    label: "후보군",
    title: "검증 ETF 후보",
    body: "TQQQ 전략과 함께 고려한 ETF, 현금성 대기자산, 제외 후보를 따로 봅니다.",
  },
  {
    to: "/compare",
    icon: <GitCompareArrows size={19} />,
    label: "연구실",
    title: "기본형과 커스텀 비교",
    body: "TQQQ 200일선 기본형, QLD형, QQQ 보유 전략을 같은 원금 기준으로 비교합니다.",
  },
];

export function InfoPage() {
  return (
    <section className="page-grid">
      <div className="hero-panel">
        <div>
          <span className="section-label">Additional Information</span>
          <h2>핵심 판단에 필요하지 않은 연구 정보는 여기서 확인합니다</h2>
          <p>
            첫 화면은 오늘 무엇을 해야 하는지에 집중하고, 규칙의 근거와 ETF 후보군, 전략 비교는 추가정보로 분리했습니다.
          </p>
        </div>
      </div>

      <div className="content-grid">
        <article className="panel span-12 info-principle">
          <div>
            <ShieldCheck size={20} />
            <span className="section-label">앱의 사용 원칙</span>
            <h3>규칙은 앞에, 설명은 뒤에 둡니다</h3>
            <p>
              이 앱은 예측보다 실행 규율을 우선합니다. 사용자는 전략 수립과 오늘 판단 화면에서 필요한 결론을 먼저 보고,
              세부 근거가 필요할 때 이곳에서 검증 자료를 확인합니다.
            </p>
          </div>
          <div className="info-rule-strip">
            <span>QQQ 200일선 기준</span>
            <span>분할 실행 기록</span>
            <span>백테스트 비교</span>
            <span>데이터 신뢰도 점검</span>
          </div>
        </article>

        {infoCards.map((card) => (
          <Link className="panel info-card span-4" to={card.to} key={card.to}>
            <span>{card.icon}{card.label}</span>
            <h3>{card.title}</h3>
            <p>{card.body}</p>
          </Link>
        ))}

        <article className="panel span-12 info-principle compact">
          <div>
            <ListChecks size={20} />
            <span className="section-label">화면 정리 기준</span>
            <h3>매일 보는 정보와 가끔 보는 정보를 분리했습니다</h3>
            <p>
              매일 보는 정보는 전략 수립, 오늘 판단, 전략 관리, 테스트에 남겼고 후보군 설명과 연구성 비교는 추가정보로 보냈습니다.
            </p>
          </div>
        </article>
      </div>
    </section>
  );
}
