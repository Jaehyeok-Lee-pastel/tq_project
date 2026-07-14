import type {
  Allocation,
  JournalEntry,
  ManagedGuide,
  ManagedStrategy,
  QuoteResponse,
  SplitStep,
  UserSettings
} from "./types";

export const userSettingsKey = "tqcoach.userSettings";

export function loadUserSettings(): UserSettings {
  try {
    const raw = localStorage.getItem(userSettingsKey);
    if (!raw) throw new Error("no settings");
    return {
      targetCashRatio: 20,
      monthlyContribution: 1_000_000,
      payDay: 10,
      usdKrwRate: 1380,
      ...JSON.parse(raw)
    };
  } catch {
    return { targetCashRatio: 20, monthlyContribution: 1_000_000, payDay: 10, usdKrwRate: 1380 };
  }
}

export function formatKrw(value: number) {
  return `${Math.round(value).toLocaleString("ko-KR")}원`;
}
export function formatUsdFromKrw(value: number, usdKrwRate: number) {
  if (!usdKrwRate) return "-";
  return `$${(value / usdKrwRate).toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}
export function formatDualCurrency(value: number, symbol: string, usdKrwRate: number) {
  if (symbol === "CASH" || symbol === "SGOV" || symbol === "BIL") {
    return formatKrw(value);
  }
  return `${formatUsdFromKrw(value, usdKrwRate)} (${formatKrw(value)})`;
}
export function formatPct(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}
export function formatUsd(value?: number | null) {
  if (!value) return "-";
  return `$${value.toFixed(2)}`;
}
export function isUsdAsset(symbol: string) {
  return symbol !== "CASH" && !symbol.startsWith("ACE ");
}
export function quoteKrw(quote: QuoteResponse | undefined, usdKrwRate: number) {
  return quote ? quote.price * usdKrwRate : 0;
}
export function actionLabelWithCurrency(
  label: string,
  amount: number,
  symbol: string,
  usdKrwRate: number
) {
  if (!amount || label === "대기" || label === "실행 금지" || label === "실행 완료") return label;
  const action = label.includes("매도") ? "매도 후보" : "매수 후보";
  return `${action} ${formatDualCurrency(amount, symbol, usdKrwRate)}`;
}
export function formatDate(value: string) {
  return new Date(value).toLocaleString("ko-KR");
}
export function journalTypeLabel(type: JournalEntry["entry_type"]) {
  return {
    buy: "매수",
    sell: "매도",
    hold: "보유",
    rebalance: "리밸런싱",
    review: "리뷰",
    rule_check: "규칙 점검",
    note: "메모",
    deposit: "입금",
    fx: "환전",
    cash_transfer: "현금 이동"
  }[type];
}
export function marketDataAgeDays(asOf: string) {
  const asOfTime = new Date(`${asOf}T00:00:00`).getTime();
  if (Number.isNaN(asOfTime)) return null;
  const now = new Date();
  const todayTime = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  return Math.max(0, Math.floor((todayTime - asOfTime) / 86_400_000));
}
export function marketDataFreshness(asOf: string) {
  const ageDays = marketDataAgeDays(asOf);
  if (ageDays == null) return { level: "watch", label: "기준일 확인 필요" };
  if (ageDays <= 1) return { level: "ok", label: "최신 일봉 기준" };
  if (ageDays <= 4) return { level: "watch", label: `${ageDays}일 전 일봉 기준` };
  return { level: "danger", label: `${ageDays}일 전 데이터` };
}
export function allocationPolicy(symbol: string) {
  if (symbol === "TQQQ" || symbol === "QLD") {
    return "조건부 분할매수";
  }
  if (symbol === "CASH" || symbol === "SGOV" || symbol === "BIL") {
    return "분할매수 대기";
  }
  return "목표 비중 매수";
}
export function allocationPolicyDetail(symbol: string) {
  if (symbol === "TQQQ") {
    return "QQQ 200일선 위, 눌림/돌파/이격 완화 조건일 때만 단계별 실행";
  }
  if (symbol === "QLD") {
    return "TQQQ보다 완만하지만 동일하게 레버리지 분할 원칙 적용";
  }
  if (symbol === "CASH" || symbol === "SGOV" || symbol === "BIL") {
    return "아직 매수하지 않는 대기 자금이며 하락/신호 발생 시 사용";
  }
  return "레버리지 타이밍 자산이 아니라 포트폴리오 완충 코어로 목표 비중까지 매수";
}

export function executableSymbol(
  allocation: Allocation,
  quotes: Record<string, QuoteResponse>,
  usdKrwRate: number
) {
  if (allocation.symbol !== "QQQ") return allocation.symbol;
  const qqqKrw = quoteKrw(quotes.QQQ, usdKrwRate);
  const qqqmKrw = quoteKrw(quotes.QQQM, usdKrwRate);
  if (
    qqqKrw &&
    qqqmKrw &&
    allocation.target_amount < qqqKrw &&
    allocation.target_amount >= qqqmKrw
  ) {
    return "QQQM";
  }
  return "QQQ";
}

export function allocationExecutionDetail(
  allocation: Allocation,
  quotes: Record<string, QuoteResponse>,
  usdKrwRate: number
) {
  if (!isUsdAsset(allocation.symbol)) return "원화/현금성 자산은 원화 기준으로 관리합니다.";
  const symbol = executableSymbol(allocation, quotes, usdKrwRate);
  const quote = quotes[symbol];
  if (!quote) return "현재가를 불러오면 1주 가능 여부와 대체 종목을 계산합니다.";
  const priceKrw = quoteKrw(quote, usdKrwRate);
  const shares = priceKrw ? Math.floor(allocation.target_amount / priceKrw) : 0;
  if (allocation.symbol === "QQQ" && symbol === "QQQM") {
    return `QQQ 1주가 목표금액을 초과합니다. 같은 나스닥100 저가형 ETF인 QQQM 기준 약 ${shares}주 실행이 현실적입니다.`;
  }
  if (shares < 1) {
    return `${symbol} 1주 금액이 목표금액보다 큽니다. 현금 대기, QQQM 같은 저가 대체, 또는 증권사 소수점 매수를 검토하세요.`;
  }
  return `${symbol} 현재가 ${formatUsd(quote.price)} 기준 약 ${shares}주까지 실행 가능합니다.`;
}

export function executionBucketSymbol(symbol: string, allocations: Allocation[]) {
  const upper = symbol.toUpperCase();
  if (upper === "QQQM" && allocations.some((allocation) => allocation.symbol === "QQQ"))
    return "QQQ";
  return upper;
}

export function executionStage(
  row: { symbol: string; targetAmount: number; executedAmount: number; progressPct: number },
  plan: SplitStep[]
) {
  if (row.executedAmount <= 0) return "미집행";
  if (row.progressPct >= 110) return "목표 초과";
  if (isCashLikeSymbol(row.symbol)) return "대기 운용 중";
  if (row.symbol !== "TQQQ" && row.symbol !== "QLD")
    return row.progressPct >= 95 ? "목표 근접" : "진행 중";
  let cumulativeRatio = 0;
  const completed = plan.reduce((count, step) => {
    const stepRatio =
      step.ratio_of_target || (row.targetAmount > 0 ? (step.amount / row.targetAmount) * 100 : 0);
    cumulativeRatio += stepRatio;
    return row.progressPct >= cumulativeRatio * 0.95 ? count + 1 : count;
  }, 0);
  if (completed >= 3) return "3차 완료";
  if (completed === 2) return "2차 완료";
  if (completed === 1) return "1차 완료";
  return "1차 진행";
}

export function nextExecutionHint(
  row: { symbol: string; progressPct: number },
  guide: ManagedGuide | null
) {
  if (row.symbol === "CASH")
    return "분할매수 재원입니다. 최소 버퍼를 넘는 여유 현금은 SGOV 대기 운용을 검토합니다.";
  if (isCashLikeSymbol(row.symbol))
    return "현금성 대기자산입니다. 매수 조건이 오면 매도해 TQQQ/QLD 분할매수 재원으로 전환합니다.";
  if (row.progressPct >= 110) return "추가 매수보다 리밸런싱 검토";
  const nextStep = guide?.execution_plan.find(
    (step) => step.symbol === row.symbol && step.side === "buy" && step.status !== "done"
  );
  if (nextStep) return nextStep.trigger_label || nextStep.trigger;
  if (row.progressPct >= 95) return "목표 비중 유지, 조건 발생 시 리밸런싱";
  return "목표금액과 현재가 기준으로 추가 실행 검토";
}

export function isCashLikeSymbol(symbol: string) {
  return ["CASH", "SGOV", "BIL"].includes(symbol.toUpperCase());
}
export function allocationRatioOf(strategy: ManagedStrategy, symbols: string[]) {
  const targets = symbols.map((symbol) => symbol.toUpperCase());
  return strategy.plan.allocations
    .filter((allocation) => targets.includes(allocation.symbol.toUpperCase()))
    .reduce((sum, allocation) => sum + allocation.target_ratio, 0);
}
export function latestTradeEntries(strategy: ManagedStrategy) {
  return [...strategy.journal]
    .filter((entry) => ["buy", "sell", "rebalance"].includes(entry.entry_type))
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);
}
export function reviewEntry(entry: JournalEntry) {
  const symbol = entry.symbol.toUpperCase();
  const isLeveraged = symbol === "TQQQ" || symbol === "QLD";
  if (entry.entry_type === "buy" && isLeveraged && entry.qqq_distance_from_200ma <= 0) {
    return {
      level: "danger",
      label: "규칙 위반",
      note: "QQQ 200일선 아래에서 레버리지 매수 기록입니다."
    };
  }
  if (entry.entry_type === "buy" && isLeveraged && entry.qqq_distance_from_200ma >= 15) {
    return {
      level: "danger",
      label: "추격 의심",
      note: "QQQ 200일선 대비 +15% 이상 신규 레버리지 매수는 금지 원칙입니다."
    };
  }
  if (entry.entry_type === "buy" && isLeveraged && !entry.reason) {
    return {
      level: "watch",
      label: "근거 부족",
      note: "분할 단계와 실행 조건을 reason에 남기는 편이 좋습니다."
    };
  }
  if (
    (entry.entry_type === "buy" || entry.entry_type === "sell") &&
    (!entry.price || !entry.quantity)
  ) {
    return {
      level: "watch",
      label: "체결 정보 부족",
      note: "체결가와 수량을 기록하면 사후 리뷰 정확도가 올라갑니다."
    };
  }
  return { level: "ok", label: "양호", note: "기록상 핵심 위반은 보이지 않습니다." };
}
