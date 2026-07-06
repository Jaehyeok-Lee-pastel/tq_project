import { Award, CheckCircle2, Database, Gauge, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

type CandidateStatus = "selected" | "watch" | "excluded";
type UniverseCandidate = {
  symbol: string;
  name: string;
  role: string;
  category: string;
  liquidity: number;
  stability: number;
  strategyFit: number;
  recommendation: number;
  status: CandidateStatus;
  useCase: string;
  reason: string;
};

const candidates: UniverseCandidate[] = [
  {
    symbol: "QQQ",
    name: "Invesco QQQ Trust",
    role: "신호 기준 / 나스닥 코어",
    category: "Nasdaq-100",
    liquidity: 99,
    stability: 70,
    strategyFit: 98,
    recommendation: 96,
    status: "selected",
    useCase: "200일선 신호 기준, 레버리지 대신 완충 코어",
    reason: "Nasdaq-100 대표 ETF이며 유동성, 옵션시장, 인지도 면에서 TQQQ 전략의 기준 자산으로 가장 적합합니다.",
  },
  {
    symbol: "TQQQ",
    name: "ProShares UltraPro QQQ",
    role: "공격 엔진",
    category: "3x leveraged",
    liquidity: 95,
    stability: 25,
    strategyFit: 92,
    recommendation: 88,
    status: "selected",
    useCase: "QQQ 200일선 위에서만 분할 진입",
    reason: "전략의 핵심 수익 엔진이지만 일간 3배 구조라 과열·이탈 구간에서 비중 제한이 필수입니다.",
  },
  {
    symbol: "QLD",
    name: "ProShares Ultra QQQ",
    role: "완충형 레버리지",
    category: "2x leveraged",
    liquidity: 86,
    stability: 42,
    strategyFit: 90,
    recommendation: 89,
    status: "selected",
    useCase: "TQQQ 부담이 클 때 2배 레버리지 대체",
    reason: "TQQQ보다 변동성이 낮아 공격성과 지속 가능성의 균형을 맞추기 좋습니다.",
  },
  {
    symbol: "SGOV",
    name: "iShares 0-3 Month Treasury Bond ETF",
    role: "현금성 대기자금",
    category: "T-Bill",
    liquidity: 90,
    stability: 96,
    strategyFit: 97,
    recommendation: 96,
    status: "selected",
    useCase: "분할매수 대기자금, 200일선 이탈 방어",
    reason: "짧은 만기 국채 성격이라 가격 변동이 작고 TQQQ 분할매수 대기자금 역할에 적합합니다.",
  },
  {
    symbol: "BIL",
    name: "SPDR Bloomberg 1-3 Month T-Bill ETF",
    role: "현금성 대기자금",
    category: "T-Bill",
    liquidity: 88,
    stability: 96,
    strategyFit: 95,
    recommendation: 94,
    status: "selected",
    useCase: "SGOV 대체 또는 현금성 ETF 분산",
    reason: "오래된 초단기 국채 ETF로 현금성 대기자금 후보로 적합합니다.",
  },
  {
    symbol: "SHY",
    name: "iShares 1-3 Year Treasury Bond ETF",
    role: "단기채 완충",
    category: "Short Treasury",
    liquidity: 84,
    stability: 88,
    strategyFit: 84,
    recommendation: 83,
    status: "selected",
    useCase: "낮은 리스크 점수에서 현금보다 약간 긴 완충",
    reason: "금리 민감도가 비교적 낮아 방어축으로 쓰기 쉽습니다.",
  },
  {
    symbol: "IEF",
    name: "iShares 7-10 Year Treasury Bond ETF",
    role: "중기채 완충",
    category: "Intermediate Treasury",
    liquidity: 82,
    stability: 72,
    strategyFit: 76,
    recommendation: 75,
    status: "selected",
    useCase: "중간 리스크에서 주식 변동성 완충",
    reason: "단기채보다 금리 민감도는 있지만 주식 급락 시 완충 후보가 될 수 있습니다.",
  },
  {
    symbol: "VOO",
    name: "Vanguard S&P 500 ETF",
    role: "광범위 코어",
    category: "S&P 500",
    liquidity: 92,
    stability: 76,
    strategyFit: 80,
    recommendation: 82,
    status: "selected",
    useCase: "낮은 리스크 점수에서 TQQQ 대신 코어 비중",
    reason: "초대형 저비용 S&P 500 ETF로 QQQ/TQQQ 집중도를 낮추는 데 좋습니다.",
  },
  {
    symbol: "SPYM",
    name: "SPDR Portfolio S&P 500 ETF",
    role: "저비용 S&P 500 코어",
    category: "S&P 500",
    liquidity: 82,
    stability: 78,
    strategyFit: 82,
    recommendation: 84,
    status: "selected",
    useCase: "리스크 20~65 구간에서 TQQQ 변동성 완충",
    reason: "SPY와 유사한 S&P 500 노출을 낮은 비용으로 가져가며, TQQQ 전략의 계좌 변동성을 낮추는 코어 후보입니다.",
  },
  {
    symbol: "SMH",
    name: "VanEck Semiconductor ETF",
    role: "반도체 위성",
    category: "Semiconductor",
    liquidity: 80,
    stability: 48,
    strategyFit: 46,
    recommendation: 42,
    status: "excluded",
    useCase: "검토했으나 기본 추천 제외",
    reason: "AI/반도체 트렌드 노출은 좋지만 QQQ/TQQQ와 성장주·나스닥 베타가 겹쳐 이 전략에서는 중복 위험이 큽니다.",
  },
  {
    symbol: "SOXX",
    name: "iShares Semiconductor ETF",
    role: "반도체 위성",
    category: "Semiconductor",
    liquidity: 76,
    stability: 50,
    strategyFit: 44,
    recommendation: 40,
    status: "excluded",
    useCase: "검토했으나 기본 추천 제외",
    reason: "반도체 분산 ETF지만 TQQQ/QLD와 함께 보유하면 기술주 쏠림이 커져 기본 후보군에서는 제외합니다.",
  },
  {
    symbol: "TLT",
    name: "iShares 20+ Year Treasury Bond ETF",
    role: "장기채 위성",
    category: "Long Treasury",
    liquidity: 88,
    stability: 45,
    strategyFit: 58,
    recommendation: 55,
    status: "watch",
    useCase: "금리 하락/경기 둔화 방어 소액 위성",
    reason: "유명하고 유동성은 좋지만 금리 민감도가 커서 안정 자산으로 과신하면 안 됩니다.",
  },
  {
    symbol: "VGT",
    name: "Vanguard Information Technology ETF",
    role: "기술주 위성",
    category: "Technology",
    liquidity: 78,
    stability: 52,
    strategyFit: 48,
    recommendation: 45,
    status: "excluded",
    useCase: "TQQQ 전략에서는 기본 제외",
    reason: "좋은 ETF지만 QQQ/TQQQ와 기술주 중복이 커서 이 전략의 후보군에서는 제외합니다.",
  },
];

const selected = candidates.filter((candidate) => candidate.status === "selected");
const watch = candidates.filter((candidate) => candidate.status === "watch");
const excluded = candidates.filter((candidate) => candidate.status === "excluded");

export function UniversePage() {
  return (
    <section className="page-grid">
      <div className="hero-panel universe">
        <div>
          <span className="section-label">ETF Universe</span>
          <h2>검증된 ETF 후보군과 추천도를 확인합니다</h2>
          <p>거래량, 규모, 안정성, 전략 적합도를 함께 보고 TQQQ 200일선 전략에 필요한 후보만 남깁니다.</p>
        </div>
      </div>

      <div className="content-grid">
        <article className="panel span-12">
          <h2 className="panel-title"><ShieldCheck size={18} />선정 기준</h2>
          <div className="score-grid">
            <Metric label="유동성" value="거래량/AUM" note="실행 가능성" />
            <Metric label="안정성" value="변동성/구조" note="방어 적합성" />
            <Metric label="전략 적합도" value="QQQ 200일선" note="역할 명확성" />
            <Metric label="중복 위험" value="기술주 쏠림" note="TQQQ와 겹침" />
          </div>
        </article>

        <CandidateSection title="선정 후보군" icon={<Award size={18} />} items={selected} />
        <CandidateSection title="조건부 관찰 후보" icon={<Gauge size={18} />} items={watch} />
        <CandidateSection title="이번 전략에서는 제외" icon={<Database size={18} />} items={excluded} />
      </div>
    </section>
  );
}

function CandidateSection({ title, icon, items }: { title: string; icon: ReactNode; items: UniverseCandidate[] }) {
  return (
    <article className="panel span-12">
      <h2 className="panel-title">{icon}{title}</h2>
      <div className="universe-table">
        {items.map((item) => (
          <div className={`universe-row ${item.status}`} key={item.symbol}>
            <div>
              <strong>{item.symbol}</strong>
              <small>{item.name}</small>
            </div>
            <span>{item.role}</span>
            <Score label="추천" value={item.recommendation} />
            <Score label="유동성" value={item.liquidity} />
            <Score label="안정성" value={item.stability} />
            <Score label="적합도" value={item.strategyFit} />
            <p>{item.reason}</p>
            <em>{item.useCase}</em>
          </div>
        ))}
      </div>
    </article>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="score-mini">
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="score-card"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}
