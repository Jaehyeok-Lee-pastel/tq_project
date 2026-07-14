import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpenCheck,
  ClipboardCheck,
  FlaskConical,
  History,
  ListChecks,
  RefreshCw,
  Save,
  SlidersHorizontal,
  Target,
  Trash2
} from "lucide-react";
const AUTO_MARKET_REFRESH_MS = 30 * 60 * 1000;

import type {
  AdjustmentAdvice,
  BacktestStrategy,
  ContributionAdvice,
  DataReliabilityResponse,
  ExecutionStep,
  FxRate,
  HistoryResponse,
  JournalEntry,
  ManagedGuide,
  ManagedStrategy,
  ManageTab,
  PhilosophyUpgradeAdvice,
  QuoteResponse,
  TodayDecision
} from "./types";
import {
  actionLabelWithCurrency,
  allocationExecutionDetail,
  allocationPolicy,
  allocationPolicyDetail,
  allocationRatioOf,
  executableSymbol,
  executionBucketSymbol,
  executionStage,
  formatDate,
  formatDualCurrency,
  formatKrw,
  formatPct,
  formatUsd,
  formatUsdFromKrw,
  isCashLikeSymbol,
  isUsdAsset,
  journalTypeLabel,
  latestTradeEntries,
  loadUserSettings,
  marketDataFreshness,
  nextExecutionHint,
  reviewEntry,
  userSettingsKey
} from "./model";
import { fetchJson } from "./api";
import { ListBlock, PanelTitle, RuleList } from "./components";
export function ManagementWorkspace() {
  const navigate = useNavigate();
  const initialSettings = useMemo(() => loadUserSettings(), []);
  const [strategies, setStrategies] = useState<ManagedStrategy[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [guide, setGuide] = useState<ManagedGuide | null>(null);
  const [adjustmentAdvice, setAdjustmentAdvice] = useState<AdjustmentAdvice | null>(null);
  const [contributionAdvice, setContributionAdvice] = useState<ContributionAdvice | null>(null);
  const [philosophyAdvice, setPhilosophyAdvice] = useState<PhilosophyUpgradeAdvice | null>(null);
  const [selectedContributionPlanId, setSelectedContributionPlanId] = useState("balanced");
  const [targetCashRatio, setTargetCashRatio] = useState(initialSettings.targetCashRatio);
  const [monthlyContribution, setMonthlyContribution] = useState(
    initialSettings.monthlyContribution
  );
  const [payDay, setPayDay] = useState(initialSettings.payDay);
  const [usdKrwRate, setUsdKrwRate] = useState(initialSettings.usdKrwRate);
  const [manualCashUsd, setManualCashUsd] = useState(0);
  const [fxStatus, setFxStatus] = useState("수동 환율");
  const [liveQuotes, setLiveQuotes] = useState<Record<string, QuoteResponse>>({});
  const [quoteStatus, setQuoteStatus] = useState("현재가를 불러오기 전입니다.");
  const [dataReliability, setDataReliability] = useState<DataReliabilityResponse | null>(null);
  const [dataReliabilityStatus, setDataReliabilityStatus] =
    useState("데이터 신뢰도 점검 전입니다.");
  const [marketStatus, setMarketStatus] = useState("QQQ 시장 지표는 저장된 스냅샷 기준입니다.");
  const [status, setStatus] = useState("채택한 전략을 불러오는 중입니다.");
  const [activeTab, setActiveTab] = useState<ManageTab>("overview");
  const [todayDecision, setTodayDecision] = useState<TodayDecision | null>(null);
  const [todayStatus, setTodayStatus] = useState("");
  const [depositAmount, setDepositAmount] = useState(0);
  const [depositNote, setDepositNote] = useState("");
  const [depositing, setDepositing] = useState(false);
  const [parkingSgov, setParkingSgov] = useState(false);
  const marketRefreshInFlight = useRef(false);
  const [draft, setDraft] = useState({
    entry_type: "note" as JournalEntry["entry_type"],
    symbol: "TQQQ",
    amount: 0,
    quantity: 0,
    price: 0,
    reason: "",
    mood: "neutral",
    note: ""
  });

  const selected = useMemo(
    () =>
      guide?.strategy ?? strategies.find((strategy) => strategy.id === selectedId) ?? strategies[0],
    [guide, selectedId, strategies]
  );
  const todayAlreadyLogged = useMemo(() => {
    if (!selected || !todayDecision) return false;
    const marker = `오늘의 판단 자동 기록 (${todayDecision.as_of})`;
    return selected.journal.some((entry) => entry.note?.includes(marker));
  }, [selected, todayDecision]);
  const monthExecution = useMemo(() => {
    if (!selected?.research_config) return null;
    const now = new Date();
    const prefix = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    let bought = 0;
    const days = new Set<string>();
    selected.journal.forEach((entry) => {
      if (entry.entry_type !== "buy" || !entry.created_at.startsWith(prefix)) return;
      bought += entry.amount || 0;
      days.add(entry.created_at.slice(0, 10));
    });
    return { bought, days: days.size, budget: selected.research_config.monthly_contribution };
  }, [selected]);
  const manualCashKrw = manualCashUsd > 0 ? manualCashUsd * usdKrwRate : null;

  useEffect(() => {
    localStorage.setItem(
      userSettingsKey,
      JSON.stringify({ targetCashRatio, monthlyContribution, payDay, usdKrwRate })
    );
  }, [monthlyContribution, payDay, targetCashRatio, usdKrwRate]);

  const executionRows = useMemo(() => {
    if (!selected) return [];
    const targetMap = new Map(
      selected.plan.allocations.map((allocation) => [allocation.symbol, allocation])
    );
    const cashAllocation =
      targetMap.get("CASH") ??
      selected.plan.allocations.find((allocation) => isCashLikeSymbol(allocation.symbol));
    const executed = new Map<string, { amount: number; quantity: number; symbols: Set<string> }>();
    let spentAmount = 0;
    selected.journal.forEach((entry) => {
      if (
        entry.entry_type !== "buy" &&
        entry.entry_type !== "sell" &&
        entry.entry_type !== "rebalance"
      )
        return;
      const symbol = executionBucketSymbol(entry.symbol || "CASH", selected.plan.allocations);
      const current = executed.get(symbol) ?? {
        amount: 0,
        quantity: 0,
        symbols: new Set<string>()
      };
      const sign = entry.entry_type === "sell" ? -1 : 1;
      spentAmount += sign * (entry.amount || 0);
      current.amount += sign * (entry.amount || 0);
      current.quantity += sign * (entry.quantity || 0);
      if (entry.symbol) current.symbols.add(entry.symbol.toUpperCase());
      executed.set(symbol, current);
    });
    const autoIdleCash = Math.max(selected.total_capital - spentAmount, 0);
    const cashRowAmount = manualCashKrw ?? autoIdleCash;
    const symbols = Array.from(
      new Set([...targetMap.keys(), ...executed.keys(), ...(cashRowAmount > 0 ? ["CASH"] : [])])
    );
    return symbols.map((symbol) => {
      const directAllocation = targetMap.get(symbol);
      const isCashRow = symbol === "CASH";
      const isCashLikeRow = isCashLikeSymbol(symbol);
      const allocationForTarget = directAllocation ?? (isCashLikeRow ? cashAllocation : undefined);
      const actual = executed.get(symbol) ?? { amount: 0, quantity: 0, symbols: new Set<string>() };
      const targetAmount = allocationForTarget?.target_amount ?? 0;
      const executionSymbol = Array.from(actual.symbols)[0] ?? symbol;
      const quote = liveQuotes[executionSymbol] ?? liveQuotes[symbol];
      const executedAmount = isCashRow ? cashRowAmount : Math.max(actual.amount, 0);
      const currentValue = isCashRow
        ? cashRowAmount
        : actual.quantity > 0 && quote && isUsdAsset(executionSymbol)
          ? actual.quantity * quote.price * usdKrwRate
          : actual.amount;
      const progressPct = targetAmount > 0 ? (executedAmount / targetAmount) * 100 : 0;
      const currentWeight =
        selected.total_capital > 0 ? (currentValue / selected.total_capital) * 100 : 0;
      const row = {
        symbol,
        executionSymbol,
        role: directAllocation?.role ?? (isCashLikeRow ? "현금성 대기자산" : "기록 기반 자산"),
        targetAmount,
        executedAmount,
        quantity: Math.max(actual.quantity, 0),
        currentValue: Math.max(currentValue, 0),
        progressPct,
        currentWeight
      };
      return {
        ...row,
        stage: executionStage(row, selected.plan.buy_plan),
        nextHint: nextExecutionHint(row, guide)
      };
    });
  }, [guide, liveQuotes, manualCashKrw, selected, usdKrwRate]);

  const cashStatus = useMemo(() => {
    if (!selected) {
      return {
        spentAmount: 0,
        growthInvested: 0,
        cashLikeValue: 0,
        idleCash: 0,
        pendingSplitAmount: 0,
        minimumCashBuffer: 0,
        suggestedSgovAmount: 0,
        cashReserveRatio: 0,
        autoIdleCash: 0
      };
    }
    let spentAmount = 0;
    let growthInvested = 0;
    let cashLikeValue = 0;
    selected.journal.forEach((entry) => {
      if (
        entry.entry_type !== "buy" &&
        entry.entry_type !== "sell" &&
        entry.entry_type !== "rebalance"
      )
        return;
      const symbol = entry.symbol.toUpperCase();
      const sign = entry.entry_type === "sell" ? -1 : 1;
      const amount = sign * (entry.amount || 0);
      spentAmount += amount;
      if (isCashLikeSymbol(symbol)) {
        const quote = liveQuotes[symbol];
        const value =
          entry.quantity > 0 && quote ? entry.quantity * quote.price * usdKrwRate : entry.amount;
        cashLikeValue += sign * value;
      } else {
        growthInvested += amount;
      }
    });
    const autoIdleCash = Math.max(selected.total_capital - spentAmount, 0);
    const idleCash = manualCashKrw ?? autoIdleCash;
    const pendingSplitAmount =
      guide?.execution_plan
        .filter((step) => step.side === "buy" && step.status !== "done")
        .reduce((sum, step) => sum + step.amount, 0) ?? 0;
    const isResearch = Boolean(selected.research_config);
    // Research strategies: keep exactly one month of buy budget liquid and
    // park only the excess. In defense regime everything may park in SGOV —
    // that IS the defensive posture (sold back via the 21-day redeploy).
    const minimumCashBuffer = isResearch
      ? todayDecision?.regime === "defense"
        ? 0
        : (selected.research_config?.monthly_contribution ?? 0)
      : Math.max(pendingSplitAmount, selected.total_capital * 0.1);
    let suggestedSgovAmount = Math.max(idleCash - minimumCashBuffer, 0);
    if (isResearch && suggestedSgovAmount < 100_000) {
      // Avoid churning SGOV with micro transfers.
      suggestedSgovAmount = 0;
    }
    const cashReserveRatio =
      selected.total_capital > 0 ? ((idleCash + cashLikeValue) / selected.total_capital) * 100 : 0;
    return {
      spentAmount,
      growthInvested,
      cashLikeValue,
      idleCash,
      pendingSplitAmount,
      minimumCashBuffer,
      suggestedSgovAmount,
      cashReserveRatio,
      autoIdleCash
    };
  }, [guide, liveQuotes, manualCashKrw, selected, todayDecision, usdKrwRate]);

  const cashLedger = useMemo(() => {
    if (!selected) {
      return {
        entries: [] as JournalEntry[],
        deposits: 0,
        fx: 0,
        transfers: 0,
        cashLikeBuys: 0,
        cashLikeSells: 0,
        growthBuys: 0,
        growthSells: 0
      };
    }
    const entries = selected.journal.filter((entry) => {
      const symbol = entry.symbol.toUpperCase();
      return (
        entry.entry_type === "deposit" ||
        entry.entry_type === "fx" ||
        entry.entry_type === "cash_transfer" ||
        (["buy", "sell", "rebalance"].includes(entry.entry_type) && isCashLikeSymbol(symbol))
      );
    });
    const summary = {
      deposits: 0,
      fx: 0,
      transfers: 0,
      cashLikeBuys: 0,
      cashLikeSells: 0,
      growthBuys: 0,
      growthSells: 0
    };
    selected.journal.forEach((entry) => {
      const amount = entry.amount || 0;
      const symbol = entry.symbol.toUpperCase();
      if (entry.entry_type === "deposit") summary.deposits += amount;
      if (entry.entry_type === "fx") summary.fx += amount;
      if (entry.entry_type === "cash_transfer") summary.transfers += amount;
      if (entry.entry_type === "buy" || entry.entry_type === "rebalance") {
        if (isCashLikeSymbol(symbol)) summary.cashLikeBuys += amount;
        else summary.growthBuys += amount;
      }
      if (entry.entry_type === "sell") {
        if (isCashLikeSymbol(symbol)) summary.cashLikeSells += amount;
        else summary.growthSells += amount;
      }
    });
    return { entries, ...summary };
  }, [selected]);

  const riskBudget = useMemo(() => {
    if (!selected) return [];
    const leverageRatio = allocationRatioOf(selected, ["TQQQ", "QLD"]);
    const tqqqRatio = allocationRatioOf(selected, ["TQQQ"]);
    const cashRatio = allocationRatioOf(selected, ["CASH", "SGOV", "BIL"]);
    const largestReadyStep =
      guide?.execution_plan
        .filter((step) => step.status === "ready")
        .reduce((max, step) => Math.max(max, step.amount), 0) ?? 0;
    const distance = (selected.market.qqq_close / selected.market.qqq_sma200 - 1) * 100;
    return [
      {
        title: "레버리지 총량",
        value: `${leverageRatio.toFixed(1)}%`,
        limit: "권장 60% 이하",
        level: leverageRatio > 70 ? "danger" : leverageRatio > 60 ? "watch" : "ok"
      },
      {
        title: "TQQQ 단일 비중",
        value: `${tqqqRatio.toFixed(1)}%`,
        limit: "권장 50% 이하",
        level: tqqqRatio > 60 ? "danger" : tqqqRatio > 50 ? "watch" : "ok"
      },
      {
        title: "현금성 대기",
        value: `${cashRatio.toFixed(1)}%`,
        limit: distance >= 15 ? "과열권 30~35% 권장" : "최소 15~25%",
        level: cashRatio < 15 ? "danger" : cashRatio < 25 && distance >= 8 ? "watch" : "ok"
      },
      {
        title: "1회 실행 한도",
        value: formatKrw(largestReadyStep),
        limit: `원금 10% ${formatKrw(selected.total_capital * 0.1)}`,
        level:
          largestReadyStep > selected.total_capital * 0.1
            ? "danger"
            : largestReadyStep > selected.total_capital * 0.06
              ? "watch"
              : "ok"
      },
      {
        title: "QQQ 200일선",
        value: formatPct(distance),
        limit: "0% 아래 신규매수 금지",
        level: distance <= 0 ? "danger" : distance >= 15 ? "watch" : "ok"
      },
      {
        title: "대기재원",
        value: formatKrw(cashStatus.idleCash + cashStatus.cashLikeValue),
        limit: `미집행 계획 ${formatKrw(cashStatus.pendingSplitAmount)}`,
        level:
          cashStatus.idleCash + cashStatus.cashLikeValue < cashStatus.pendingSplitAmount * 0.7
            ? "watch"
            : "ok"
      }
    ];
  }, [cashStatus, guide, selected]);

  const executionReview = useMemo(() => {
    if (!selected)
      return {
        score: 0,
        entries: [] as { entry: JournalEntry; review: ReturnType<typeof reviewEntry> }[],
        summary: "전략이 선택되지 않았습니다."
      };
    const entries = latestTradeEntries(selected).map((entry) => ({
      entry,
      review: reviewEntry(entry)
    }));
    const danger = entries.filter((item) => item.review.level === "danger").length;
    const watch = entries.filter((item) => item.review.level === "watch").length;
    const score = Math.max(0, 100 - danger * 35 - watch * 12);
    const summary = entries.length
      ? danger
        ? "최근 실행 기록에 규칙 위반 가능성이 있습니다."
        : watch
          ? "최근 실행 기록은 대체로 양호하지만 보강할 기록이 있습니다."
          : "최근 실행 기록은 현재 규칙과 잘 맞습니다."
      : "아직 매수/매도/리밸런싱 실행 기록이 없습니다.";
    return { score, entries, summary };
  }, [selected]);

  useEffect(() => {
    void loadStrategies();
    void loadFxRate();
    void loadDataReliability();
    // Initial hydration only; loaders update state and are intentionally not reactive.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedId) void loadGuide(selectedId);
  }, [selectedId]);

  useEffect(() => {
    if (selected?.research_config?.strategy === "tqqq_daily_200ma") {
      void loadTodayDecision(selected.id);
    } else {
      setTodayDecision(null);
    }
  }, [selected?.id, selected?.research_config?.strategy]);

  useEffect(() => {
    if (selected) void loadLiveQuotes(selected);
    // Quotes refresh when strategy identity or display FX changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.id, usdKrwRate]);

  useEffect(() => {
    if (!selected?.id) return;
    void refreshMarketSnapshot({ silent: true });
    const timer = window.setInterval(() => {
      void refreshMarketSnapshot({ silent: true });
    }, AUTO_MARKET_REFRESH_MS);
    return () => window.clearInterval(timer);
    // One timer per selected strategy; refresh callback reads the latest state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.id]);

  async function loadStrategies() {
    try {
      const next = await fetchJson<ManagedStrategy[]>("/managed-strategies");
      setStrategies(next);
      if (next[0] && !selectedId) setSelectedId(next[0].id);
      setStatus(
        next.length
          ? "채택한 전략을 불러왔습니다."
          : "아직 채택한 전략이 없습니다. 전략 수립 화면에서 먼저 채택하세요."
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 목록을 불러오지 못했습니다.");
    }
  }

  async function submitDeposit() {
    if (!selected) return;
    const amount =
      depositAmount > 0 ? depositAmount : (selected.research_config?.monthly_contribution ?? 0);
    if (amount <= 0) {
      setStatus("입금액을 입력하세요.");
      return;
    }
    setDepositing(true);
    try {
      const updated = await fetchJson<ManagedStrategy>(
        `/managed-strategies/${selected.id}/deposit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            amount,
            note: depositNote || `월급일(매월 ${payDay}일) 정기 입금`
          })
        }
      );
      setStrategies((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setGuide((current) => (current ? { ...current, strategy: updated } : current));
      setDepositNote("");
      setStatus(
        `${formatKrw(amount)} 입금을 반영했습니다. 총자본 ${formatKrw(updated.total_capital)} — 규칙에 따라 하루 ${formatKrw(amount / 21)}씩 분할 집행됩니다.`
      );
    } catch (error) {
      setStatus(error instanceof Error ? `입금 반영 실패: ${error.message}` : "입금 반영 실패");
    } finally {
      setDepositing(false);
    }
  }

  async function removeStrategy(strategy: ManagedStrategy) {
    const confirmed = window.confirm(
      `'${strategy.plan.title}' 전략을 삭제할까요?\n실행 기록(저널 ${strategy.journal.length}건)과 버전 이력이 함께 삭제되며 되돌릴 수 없습니다.`
    );
    if (!confirmed) return;
    try {
      const remaining = await fetchJson<ManagedStrategy[]>(`/managed-strategies/${strategy.id}`, {
        method: "DELETE"
      });
      setStrategies(remaining);
      setSelectedId(remaining[0]?.id ?? "");
      setGuide(null);
      setTodayDecision(null);
      setStatus(
        remaining.length ? "전략을 삭제했습니다." : "전략을 삭제했습니다. 남은 전략이 없습니다."
      );
    } catch (error) {
      setStatus(error instanceof Error ? `전략 삭제 실패: ${error.message}` : "전략 삭제 실패");
    }
  }

  async function loadTodayDecision(id: string) {
    setTodayStatus("오늘 판단을 계산하는 중입니다...");
    try {
      const next = await fetchJson<TodayDecision>(`/managed-strategies/${id}/today`);
      setTodayDecision(next);
      setTodayStatus(
        `기준일 ${next.as_of}${next.data_age_days > 1 ? ` (데이터 ${next.data_age_days}일 경과 — 최신 여부 확인)` : ""}`
      );
    } catch (error) {
      setTodayDecision(null);
      setTodayStatus(
        error instanceof Error ? `오늘 판단 계산 실패: ${error.message}` : "오늘 판단 계산 실패"
      );
    }
  }

  async function logTodayDecision() {
    if (!selected || !todayDecision || todayAlreadyLogged) return;
    const decision = todayDecision;
    const entries: {
      entry_type: JournalEntry["entry_type"];
      symbol: string;
      amount: number;
      reason: string;
    }[] = [];
    const oneX = selected.research_config?.one_x_symbol ?? "QQQM";
    if (
      decision.action === "accumulate" ||
      decision.action === "accumulate_decelerated" ||
      decision.action === "stop_new_tqqq"
    ) {
      if (decision.tqqq_buy_amount > 0) {
        entries.push({
          entry_type: "buy",
          symbol: "TQQQ",
          amount: decision.tqqq_buy_amount,
          reason: decision.headline
        });
      }
      if (decision.one_x_buy_amount > 0) {
        entries.push({
          entry_type: "buy",
          symbol: oneX,
          amount: decision.one_x_buy_amount,
          reason: decision.headline
        });
      }
      if (!entries.length) {
        entries.push({ entry_type: "hold", symbol: "CASH", amount: 0, reason: decision.headline });
      }
    } else if (decision.action === "defense_sell") {
      entries.push({
        entry_type: "sell",
        symbol: "TQQQ",
        amount: 0,
        reason: `${decision.headline} — 전량 매도`
      });
      if (decision.defense_mode !== "hold_one_x") {
        entries.push({
          entry_type: "sell",
          symbol: oneX,
          amount: 0,
          reason: `${decision.headline} — 방어 모드에 따라 함께 매도`
        });
      }
      if (decision.defense_mode === "spym_sgov_half") {
        entries.push({
          entry_type: "buy",
          symbol: "SPYM",
          amount: 0,
          reason: "방어 자금의 50% SPYM 배치"
        });
      }
    } else {
      entries.push({
        entry_type: "hold",
        symbol: "CASH",
        amount: 0,
        reason: `${decision.headline} — ${decision.instructions[0] ?? ""}`
      });
    }
    try {
      for (const entry of entries) {
        await fetchJson<ManagedStrategy>(`/managed-strategies/${selected.id}/journal`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...entry,
            quantity: 0,
            price: 0,
            mood: "calm",
            note: `오늘의 판단 자동 기록 (${decision.as_of})`
          })
        });
      }
      setStatus(`오늘의 판단을 실행 기록에 남겼습니다 (${entries.length}건).`);
      await loadStrategies();
      if (selected.id) await loadGuide(selected.id);
    } catch (error) {
      setStatus(error instanceof Error ? `기록 실패: ${error.message}` : "기록 실패");
    }
  }

  async function loadGuide(id: string) {
    try {
      const next = await fetchJson<ManagedGuide>(`/managed-strategies/${id}/guide`);
      setGuide(next);
      setAdjustmentAdvice(null);
      setContributionAdvice(null);
      setPhilosophyAdvice(null);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 가이드를 불러오지 못했습니다.");
    }
  }

  async function loadFxRate() {
    try {
      const fx = await fetchJson<FxRate>("/market/fx/usd-krw");
      setUsdKrwRate(Number(fx.rate.toFixed(2)));
      setFxStatus(`${fx.provider} · ${fx.freshness} · ${fx.as_of}`);
    } catch (error) {
      setFxStatus(error instanceof Error ? `환율 갱신 실패: ${error.message}` : "환율 갱신 실패");
    }
  }

  async function loadDataReliability() {
    try {
      const next = await fetchJson<DataReliabilityResponse>(
        "/market/reliability?symbols=QQQ&symbols=TQQQ&symbols=QLD&symbols=SGOV"
      );
      setDataReliability(next);
      const qqq = next.items.find((item) => item.symbol === "QQQ");
      setDataReliabilityStatus(
        qqq ? `QQQ 데이터 신뢰도 ${qqq.score}점 · ${qqq.message}` : "데이터 신뢰도 점검 완료"
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "알 수 없는 오류";
      setDataReliability(null);
      if (message.includes("404")) {
        setDataReliabilityStatus(
          "데이터 신뢰도 API를 찾지 못했습니다. 현재 실행 중인 FastAPI 서버가 최신 코드가 아닐 수 있으니 API 서버를 재시작한 뒤 다시 갱신하세요. 임시로 저장된 QQQ 지표 기준 판단만 사용합니다."
        );
        return;
      }
      setDataReliabilityStatus(`데이터 신뢰도 점검 실패: ${message}`);
    }
  }

  async function loadLiveQuotes(strategy: ManagedStrategy) {
    const symbols = Array.from(
      new Set([
        "QQQ",
        "QQQM",
        "SGOV",
        ...strategy.plan.allocations
          .map((allocation) => allocation.symbol.toUpperCase())
          .filter((symbol) => isUsdAsset(symbol))
      ])
    );
    setQuoteStatus("현재가를 갱신하는 중입니다.");
    try {
      const settled = await Promise.allSettled(
        symbols.map(
          async (symbol) =>
            [symbol, await fetchJson<QuoteResponse>(`/market/quote/${symbol}`)] as const
        )
      );
      const quotes = Object.fromEntries(
        settled
          .filter(
            (item): item is PromiseFulfilledResult<readonly [string, QuoteResponse]> =>
              item.status === "fulfilled"
          )
          .map((item) => item.value)
      );
      const failed = symbols.filter((symbol) => !quotes[symbol]);
      setLiveQuotes(quotes);
      setQuoteStatus(
        failed.length
          ? `일부 현재가 갱신 실패: ${failed.join(", ")}`
          : `현재가 갱신 완료: ${new Date().toLocaleTimeString("ko-KR")}`
      );
    } catch (error) {
      setQuoteStatus(
        error instanceof Error ? `현재가 갱신 실패: ${error.message}` : "현재가 갱신 실패"
      );
    }
  }

  async function refreshMarketSnapshot(options?: { silent?: boolean }) {
    if (!selected || marketRefreshInFlight.current) return;
    marketRefreshInFlight.current = true;
    const silent = Boolean(options?.silent);
    if (!silent) setMarketStatus("QQQ 20/50/200일선과 20일 고점을 갱신하는 중입니다.");
    try {
      const history = await fetchJson<HistoryResponse>("/market/history/QQQ?limit=1200");
      if (!history.sma20 || !history.sma50 || !history.sma200 || !history.high20) {
        throw new Error("QQQ 이동평균 계산에 필요한 일봉 데이터가 부족합니다.");
      }
      const market = {
        qqq_close: history.latest.close,
        qqq_sma20: history.sma20,
        qqq_sma50: history.sma50,
        qqq_sma200: history.sma200,
        qqq_high20: history.high20,
        as_of: history.latest.date
      };
      const updated = await fetchJson<ManagedStrategy>(`/managed-strategies/${selected.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ market })
      });
      setStrategies((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setGuide((current) => (current ? { ...current, strategy: updated } : current));
      await loadGuide(updated.id);
      const refreshedAt = new Date().toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit"
      });
      setMarketStatus(
        `${silent ? "자동 " : ""}QQQ 지표 갱신 완료: ${history.latest.date} · ${refreshedAt} · 종가 ${formatUsd(history.latest.close)} · 20일선 ${formatUsd(history.sma20)} · 50일선 ${formatUsd(history.sma50)} · 200일선 ${formatUsd(history.sma200)}`
      );
      if (!silent) setStatus("최신 QQQ 지표를 반영해 분할 실행 계획을 다시 계산했습니다.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "QQQ 시장 지표 갱신에 실패했습니다.";
      if (!silent) {
        setMarketStatus(message);
        setStatus(message);
      }
    } finally {
      marketRefreshInFlight.current = false;
    }
  }

  async function requestAdjustmentAdvice() {
    if (!selected) return;
    try {
      const advice = await fetchJson<AdjustmentAdvice>(
        `/managed-strategies/${selected.id}/adjustment-advice`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target_cash_ratio: targetCashRatio,
            note: `현금 비중을 ${targetCashRatio}%로 조정하고 싶습니다.`
          })
        }
      );
      setAdjustmentAdvice(advice);
      setStatus(advice.headline);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 조정 조언을 불러오지 못했습니다.");
    }
  }

  async function requestPhilosophyAdvice() {
    if (!selected) return;
    try {
      setStatus("현재 전략을 최신 TQQQ 200일선 철학으로 점검하는 중입니다.");
      const advice = await fetchJson<PhilosophyUpgradeAdvice>(
        `/managed-strategies/${selected.id}/philosophy-advice`,
        {
          method: "POST"
        }
      );
      setPhilosophyAdvice(advice);
      setStatus(advice.headline);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "최신 철학 점검을 불러오지 못했습니다.");
    }
  }

  async function applyPhilosophyAdvice() {
    if (!selected || !philosophyAdvice) return;
    try {
      const updated = await fetchJson<ManagedStrategy>(
        `/managed-strategies/${selected.id}/apply-philosophy-upgrade`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            accepted_headline: philosophyAdvice.headline
          })
        }
      );
      setStrategies((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setGuide((current) => (current ? { ...current, strategy: updated } : current));
      setPhilosophyAdvice(null);
      await loadGuide(updated.id);
      setStatus("최신 철학을 새 버전으로 반영했습니다. 기존 버전은 이력에 보존됩니다.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "최신 철학 적용에 실패했습니다.");
    }
  }

  async function applyAdjustmentAdvice() {
    if (!selected || !adjustmentAdvice) return;
    try {
      const updated = await fetchJson<ManagedStrategy>(
        `/managed-strategies/${selected.id}/apply-adjustment`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target_cash_ratio: targetCashRatio,
            note: `현금 비중 ${targetCashRatio}% 조정안을 적용합니다.`,
            accepted_headline: adjustmentAdvice.headline
          })
        }
      );
      setStrategies((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setGuide((current) => (current ? { ...current, strategy: updated } : current));
      setAdjustmentAdvice(null);
      setStatus(`조정안이 v${updated.version}으로 적용됐습니다.`);
      await loadGuide(updated.id);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "조정안 적용에 실패했습니다.");
    }
  }

  async function requestContributionAdvice() {
    if (!selected) return;
    try {
      const advice = await fetchJson<ContributionAdvice>(
        `/managed-strategies/${selected.id}/contribution-advice`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contribution_amount: monthlyContribution,

            pay_day: payDay,
            note: `매달 ${payDay}일 월급 중 ${monthlyContribution.toLocaleString("ko-KR")}원을 추가 투입합니다.`
          })
        }
      );
      setContributionAdvice(advice);
      setSelectedContributionPlanId(
        advice.recommended_plan_id || advice.plans[0]?.id || "balanced"
      );
      setStatus(advice.headline);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "추가금 코칭을 불러오지 못했습니다.");
    }
  }

  async function applyContributionAdvice() {
    if (!selected || !contributionAdvice) return;
    try {
      const updated = await fetchJson<ManagedStrategy>(
        `/managed-strategies/${selected.id}/apply-contribution`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contribution_amount: monthlyContribution,
            pay_day: payDay,
            selected_plan_id: selectedContributionPlanId,
            accepted_headline:
              contributionAdvice.plans.find((plan) => plan.id === selectedContributionPlanId)
                ?.headline ?? contributionAdvice.headline,
            note: "월급 추가금을 총 운용자본과 미사용 현금에 반영합니다."
          })
        }
      );
      setStrategies((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setGuide((current) => (current ? { ...current, strategy: updated } : current));
      setContributionAdvice(null as unknown as ContributionAdvice);
      setStatus(
        `추가금이 v${updated.version} 전략에 반영됐습니다. 실행 기록에서 실제 주문을 남겨주세요.`
      );
      await loadGuide(updated.id);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "추가금 반영에 실패했습니다.");
    }
  }

  function prepareExecution(step: ExecutionStep) {
    const quote = liveQuotes[step.symbol];
    const estimatedQuantity =
      quote && usdKrwRate ? Number((step.amount / (quote.price * usdKrwRate)).toFixed(4)) : 0;
    setDraft({
      ...draft,
      entry_type: step.side,
      symbol: step.symbol,
      amount: Math.round(step.amount),
      quantity: estimatedQuantity,
      price: quote?.price ?? 0,
      reason: `${step.step} ${step.side === "buy" ? "분할매수" : "분할매도"}: ${step.trigger}`,
      note: step.reason
    });
    setStatus(`${step.step} 기록 초안을 만들었습니다. 실제 실행 전 금액과 가격을 확인하세요.`);
  }

  function updateExecutionPrice(next: Partial<typeof draft>) {
    const nextDraft = { ...draft, ...next };
    if (isUsdAsset(nextDraft.symbol) && nextDraft.price > 0 && nextDraft.quantity > 0) {
      nextDraft.amount = Math.round(nextDraft.price * nextDraft.quantity * usdKrwRate);
    }
    setDraft(nextDraft);
  }

  function prepareSgovParking() {
    const amount = Math.round(cashStatus.suggestedSgovAmount);
    const quote = liveQuotes.SGOV;
    const quantity =
      quote && usdKrwRate ? Number((amount / (quote.price * usdKrwRate)).toFixed(4)) : 0;
    setDraft({
      ...draft,
      entry_type: "buy",
      symbol: "SGOV",
      amount,
      quantity,
      price: quote?.price ?? 0,
      reason: "분할매수 대기 현금 SGOV 운용",
      note: "TQQQ 추가 분할매수 조건이 오기 전까지 대기 현금 일부를 초단기 국채 ETF로 운용하기 위한 기록입니다. 실제 주문 후 체결가와 수량을 확인하세요."
    });
    setActiveTab("journal");
    setStatus(
      "SGOV 대기자금 기록 초안을 만들었습니다. 실제 주문 후 체결가와 수량을 확인하고 저장하세요."
    );
  }

  async function parkSgovNow() {
    if (!selected || cashStatus.suggestedSgovAmount < 10000 || parkingSgov) return;
    const amount = Math.round(cashStatus.suggestedSgovAmount);
    const quote = liveQuotes.SGOV;
    const quantity =
      quote && usdKrwRate ? Number((amount / (quote.price * usdKrwRate)).toFixed(4)) : 0;
    setParkingSgov(true);
    try {
      const updated = await fetchJson<ManagedStrategy>(
        `/managed-strategies/${selected.id}/journal`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            entry_type: "buy",
            symbol: "SGOV",
            amount,

            quantity,
            price: quote?.price ?? 0,
            reason: selected.research_config
              ? "감속 이월분 SGOV 파킹 — 이번 달 매수 예산 초과 현금"
              : "분할매수 대기 현금 SGOV 운용",
            mood: "calm",
            note: `SGOV 파킹 원클릭 기록 (${new Date().toISOString().slice(0, 10)}). 실제 주문 체결가·수량과 다르면 실행 기록에서 수정하세요.`
          })
        }
      );
      setStrategies((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setGuide((current) => (current ? { ...current, strategy: updated } : current));
      setStatus(
        `${formatKrw(amount)}을 SGOV 파킹으로 기록했습니다. 실제 매수 주문을 함께 실행하세요.`
      );
    } catch (error) {
      setStatus(
        error instanceof Error ? `SGOV 파킹 기록 실패: ${error.message}` : "SGOV 파킹 기록 실패"
      );
    } finally {
      setParkingSgov(false);
    }
  }

  async function addJournal() {
    if (!selected) return;
    try {
      const updated = await fetchJson<ManagedStrategy>(
        `/managed-strategies/${selected.id}/journal`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(draft)
        }
      );
      setStrategies((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setGuide((current) => (current ? { ...current, strategy: updated } : current));
      setDraft({ ...draft, amount: 0, quantity: 0, price: 0, reason: "", note: "" });
      setStatus("전략 기록을 저장했습니다.");
      await loadGuide(updated.id);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 기록 저장에 실패했습니다.");
    }
  }

  async function deleteJournal(entryId: string) {
    if (!selected) return;
    if (!window.confirm("이 기록을 삭제할까요?")) return;
    try {
      const updated = await fetchJson<ManagedStrategy>(
        `/managed-strategies/${selected.id}/journal/${entryId}`,
        {
          method: "DELETE"
        }
      );
      setStrategies((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setGuide((current) => (current ? { ...current, strategy: updated } : current));
      setStatus("전략 기록을 삭제했습니다.");
      await loadGuide(updated.id);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 기록 삭제에 실패했습니다.");
    }
  }

  function allocationRatio(strategy: ManagedStrategy, symbol: string) {
    return (
      strategy.plan.allocations.find((allocation) => allocation.symbol === symbol)?.target_ratio ??
      0
    );
  }

  function primaryBacktestStrategy(strategy: ManagedStrategy): BacktestStrategy {
    if (allocationRatio(strategy, "TQQQ") > 0) return "tqqq_200ma";
    if (allocationRatio(strategy, "QLD") > 0) return "qld_200ma";
    return "qqq_buy_hold";
  }

  function sendToTestLab(strategy: ManagedStrategy) {
    localStorage.setItem(
      "tqcoach.managedTestDraft",
      JSON.stringify({
        source: "managed_strategy",
        strategy_id: strategy.id,
        version: strategy.version,
        title: strategy.plan.title,
        summary: strategy.plan.summary,
        initial_capital: strategy.total_capital,
        strategy: primaryBacktestStrategy(strategy),
        tqqq_target_ratio: allocationRatio(strategy, "TQQQ"),
        qld_target_ratio: allocationRatio(strategy, "QLD"),
        cash_yield: 3,
        projection_years: 3,
        allocations: strategy.plan.allocations.map((allocation) => ({
          symbol: allocation.symbol,
          role: allocation.role,
          target_ratio: allocation.target_ratio,
          target_amount: allocation.target_amount
        }))
      })
    );
    navigate("/lab?source=managed");
  }

  return (
    <section className="page-grid">
      <div className="hero-panel manage">
        <div>
          <span className="section-label">Strategy Operations</span>
          <h2>채택한 전략을 계속 관리합니다</h2>
          <p>추천받은 전략을 실제 운용 계획으로 저장하고, 실행 기록과 준수율을 함께 점검합니다.</p>
        </div>
      </div>

      <div className="content-grid">
        <article className="panel span-4">
          <PanelTitle icon={<BookOpenCheck size={18} />} title="내 전략" />
          <p className="muted">{status}</p>
          <div className="strategy-list">
            {strategies.map((strategy) => (
              <button
                className={strategy.id === selected?.id ? "selected" : ""}
                key={strategy.id}
                onClick={() => setSelectedId(strategy.id)}
              >
                <strong>{strategy.plan.title}</strong>
                <small>{formatDate(strategy.created_at)} 채택</small>
              </button>
            ))}
          </div>
        </article>

        <article className="panel span-8">
          <PanelTitle
            icon={<ClipboardCheck size={18} />}
            title={selected?.research_config ? "연구전략 요약" : "오늘의 운용 가이드"}
          />
          {guide && selected && !selected.research_config ? (
            <>
              <div className="manage-head">
                <div>
                  <span className="section-label">{selected.status}</span>
                  <h2>{selected.plan.title}</h2>
                  <small className="version-badge">v{selected.version}</small>
                  <p>{selected.plan.summary}</p>
                  <div className="hero-actions inline-test-actions">
                    <button type="button" onClick={() => refreshMarketSnapshot()}>
                      <RefreshCw size={16} />
                      QQQ 지표 갱신
                    </button>
                    <button type="button" onClick={() => sendToTestLab(selected)}>
                      <FlaskConical size={16} />이 전략으로 테스트
                    </button>
                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => void removeStrategy(selected)}
                    >
                      <Trash2 size={16} />
                      전략 삭제
                    </button>
                  </div>
                  <small className="fx-status">
                    {marketStatus} · 저장 기준 {selected.market.as_of} · QQQ{" "}
                    {formatUsd(selected.market.qqq_close)}
                    {selected.market.qqq_sma20
                      ? ` · 20일선 ${formatUsd(selected.market.qqq_sma20)}`
                      : ""}
                    {selected.market.qqq_sma50
                      ? ` · 50일선 ${formatUsd(selected.market.qqq_sma50)}`
                      : ""}
                    {selected.market.qqq_sma200
                      ? ` · 200일선 ${formatUsd(selected.market.qqq_sma200)}`
                      : ""}
                  </small>
                </div>
                <div
                  className={`compliance-score ${guide.compliance_score < 60 ? "danger" : guide.compliance_score < 80 ? "watch" : ""}`}
                >
                  <span>준수율</span>
                  <strong>{guide.compliance_score}</strong>
                </div>
              </div>
              <div className="action-band">{guide.current_action}</div>
              <div className="issue-grid">
                {guide.issues.map((issue) => (
                  <div className={`issue-card ${issue.level}`} key={issue.title}>
                    <strong>{issue.title}</strong>
                    <small>{issue.detail}</small>
                  </div>
                ))}
              </div>
              <div className="check-grid">
                {guide.checklist.map((item) => (
                  <label key={item}>
                    <input type="checkbox" />
                    {item}
                  </label>
                ))}
              </div>
            </>
          ) : selected?.research_config ? (
            <div className="manage-head">
              <div>
                <span className="section-label">{selected.status}</span>
                <h2>{selected.plan.title}</h2>
                <small className="version-badge">v{selected.version}</small>
                <p>{selected.plan.summary}</p>
                <div className="hero-actions inline-test-actions">
                  <button type="button" onClick={() => refreshMarketSnapshot()}>
                    <RefreshCw size={16} />
                    QQQ 지표 갱신
                  </button>
                  <button type="button" onClick={() => sendToTestLab(selected)}>
                    <FlaskConical size={16} />이 전략으로 테스트
                  </button>
                  <button
                    className="danger-button"
                    type="button"
                    onClick={() => void removeStrategy(selected)}
                  >
                    <Trash2 size={16} />
                    전략 삭제
                  </button>
                </div>
                <small className="fx-status">
                  {marketStatus} · 저장 기준 {selected.market.as_of} · QQQ{" "}
                  {formatUsd(selected.market.qqq_close)}
                  {selected.market.qqq_sma200
                    ? ` · 200일선 ${formatUsd(selected.market.qqq_sma200)}`
                    : ""}
                </small>
              </div>
            </div>
          ) : (
            <p className="muted">채택된 전략이 있으면 이곳에 상세 가이드가 표시됩니다.</p>
          )}
        </article>

        {selected ? (
          <article className="panel span-12 manage-tabs-panel">
            <div className="manage-tabs">
              {[
                ["overview", "오늘의 판단"],
                ["journal", "실행 기록"],
                ["strategy", "내 전략"]
              ].map(([id, label]) => (
                <button
                  className={activeTab === id ? "selected" : ""}
                  key={id}
                  onClick={() => setActiveTab(id as ManageTab)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
          </article>
        ) : null}

        {activeTab === "overview" && selected?.research_config?.strategy === "tqqq_daily_200ma" ? (
          <article className={`panel span-12 today-decision ${todayDecision?.regime ?? "loading"}`}>
            <div className="report-head">
              <div>
                <span className="section-label">Today Decision · 연구 규칙 기준</span>
                <h2 className="panel-title">
                  <ClipboardCheck size={18} />
                  {todayDecision ? todayDecision.headline : "오늘 판단 계산 중"}
                </h2>
                <p>{todayStatus}</p>
              </div>
              <div className="hero-actions">
                <button type="button" onClick={() => selected && loadTodayDecision(selected.id)}>
                  <RefreshCw size={15} /> 다시 계산
                </button>
                {todayDecision ? (
                  <button
                    className="primary"
                    type="button"
                    disabled={todayAlreadyLogged}
                    onClick={() => void logTodayDecision()}
                  >
                    <Save size={15} />{" "}
                    {todayAlreadyLogged ? "오늘 기록 완료" : "오늘 지시 기록하기"}
                  </button>
                ) : null}
              </div>
            </div>
            {todayDecision ? (
              <>
                <div className="cash-metrics">
                  <span>
                    <small>QQQ vs {selected.research_config.moving_average_days}일선</small>
                    <strong>
                      {todayDecision.distance_pct >= 0 ? "+" : ""}
                      {todayDecision.distance_pct.toFixed(2)}%
                    </strong>
                  </span>
                  <span>
                    <small>국면</small>
                    <strong>
                      {todayDecision.regime === "above"
                        ? "기준선 위"
                        : todayDecision.regime === "below_unconfirmed"
                          ? "이탈 1일차"
                          : `방어 (이탈 ${todayDecision.below_ma_days}일차)`}
                    </strong>
                  </span>
                  <span>
                    <small>감속 구간</small>
                    <strong>{todayDecision.tier_label}</strong>
                  </span>
                  <span>
                    <small>오늘 적립</small>
                    <strong>
                      {todayDecision.daily_budget > 0 && todayDecision.regime === "above"
                        ? `TQQQ ${formatKrw(todayDecision.tqqq_buy_amount)} + ${selected.research_config.one_x_symbol} ${formatKrw(todayDecision.one_x_buy_amount)}`
                        : "현금 대기"}
                    </strong>
                  </span>
                </div>
                {monthExecution ? (
                  <p className="muted">
                    이번 달 집행: {formatKrw(monthExecution.bought)} / 예산{" "}
                    {formatKrw(monthExecution.budget)} ({monthExecution.days}일 기록
                    {monthExecution.budget > 0
                      ? ` · ${Math.round((monthExecution.bought / monthExecution.budget) * 100)}%`
                      : ""}
                    )
                  </p>
                ) : null}
                {todayDecision.daily_budget > 0 &&
                todayDecision.regime === "above" &&
                usdKrwRate > 0 ? (
                  <p className="muted">
                    달러 환산 (환율 {usdKrwRate.toLocaleString("ko-KR")}원 기준): TQQQ{" "}
                    {formatUsdFromKrw(todayDecision.tqqq_buy_amount, usdKrwRate)} +{" "}
                    {selected.research_config.one_x_symbol}{" "}
                    {formatUsdFromKrw(todayDecision.one_x_buy_amount, usdKrwRate)}
                    {todayDecision.daily_budget -
                      todayDecision.tqqq_buy_amount -
                      todayDecision.one_x_buy_amount >
                    1
                      ? ` · 현금 대기 ${formatUsdFromKrw(todayDecision.daily_budget - todayDecision.tqqq_buy_amount - todayDecision.one_x_buy_amount, usdKrwRate)}`
                      : ""}
                  </p>
                ) : null}
                <ul className="today-instructions">
                  {todayDecision.instructions.map((instruction) => (
                    <li key={instruction}>{instruction}</li>
                  ))}
                </ul>
                {todayDecision.redeploy_active ? (
                  <p className="muted">
                    방어 현금 재투입 진행 중: {todayDecision.redeploy_day}/21일차
                  </p>
                ) : null}
                {todayAlreadyLogged ? (
                  <p className="muted">
                    ✓ 오늘({todayDecision.as_of}) 지시는 이미 실행 기록에 저장되어 있습니다.
                  </p>
                ) : null}
              </>
            ) : null}
          </article>
        ) : null}

        {activeTab === "overview" && selected ? (
          <article className="panel span-12">
            <PanelTitle icon={<Target size={18} />} title="오늘의 판단과 보유 현황" />
            <details className="secondary-details">
              <summary>데이터 신뢰도 상세</summary>
              <div className="data-reliability-card">
                <div>
                  <span className="section-label">Data Reliability</span>
                  <h3>판단 기준 데이터 점검</h3>
                  <p>
                    TQQQ/QLD 실행 판단은 QQQ 일봉과 20/50/200일선 기준입니다. 현재가와 환율은 주문
                    전 재확인용이며, 최종 체결가는 실행 기록에 직접 남깁니다.
                  </p>
                </div>
                <div className="reliability-grid">
                  {(() => {
                    const freshness = marketDataFreshness(selected.market.as_of);
                    const hasShortSignals = Boolean(
                      selected.market.qqq_sma20 &&
                      selected.market.qqq_sma50 &&
                      selected.market.qqq_high20
                    );
                    const qqqReliability = dataReliability?.items.find(
                      (item) => item.symbol === "QQQ"
                    );
                    return (
                      <>
                        <span className={qqqReliability?.status ?? freshness.level}>
                          <small>QQQ 기준일</small>
                          <strong>{qqqReliability?.latest_date ?? selected.market.as_of}</strong>
                          <em>
                            {qqqReliability
                              ? `${qqqReliability.score}점 · ${qqqReliability.message}`
                              : freshness.label}
                          </em>
                        </span>
                        <span className={selected.market.qqq_sma200 ? "ok" : "danger"}>
                          <small>200일선</small>
                          <strong>{formatUsd(selected.market.qqq_sma200)}</strong>
                          <em>
                            {selected.market.qqq_sma200
                              ? "핵심 기준 사용 가능"
                              : "필수 데이터 없음"}
                          </em>
                        </span>
                        <span className={hasShortSignals ? "ok" : "watch"}>
                          <small>20/50일·20일 고점</small>
                          <strong>{hasShortSignals ? "완료" : "일부 없음"}</strong>
                          <em>
                            {hasShortSignals
                              ? "분할매수 세부 조건 사용 가능"
                              : "보수적 대체 기준 사용"}
                          </em>
                        </span>
                        <span className="watch">
                          <small>현재가/환율</small>
                          <strong>{usdKrwRate.toLocaleString("ko-KR")}</strong>
                          <em>{quoteStatus}</em>
                        </span>
                      </>
                    );
                  })()}
                </div>
                {dataReliability ? (
                  <div className="reliability-assets">
                    {dataReliability.items.map((item) => (
                      <span className={item.status} key={item.symbol}>
                        <strong>{item.symbol}</strong>
                        <small>
                          {item.score}점 · {item.latest_date} · {item.age_days}일 전
                        </small>
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="muted">{dataReliabilityStatus}</p>
                )}
                <button type="button" onClick={loadDataReliability}>
                  <RefreshCw size={16} />
                  데이터 신뢰도 갱신
                </button>
              </div>
            </details>
            <div className="cash-command-card">
              <div>
                <span className="section-label">Cash Command</span>
                <h3>남은 현금과 SGOV 대기자금</h3>
                <p>
                  실제 미사용 현금은 {formatKrw(cashStatus.idleCash)}이고, SGOV/BIL/CASH 같은 현금성
                  보유를 합치면 전체 원금 대비 {cashStatus.cashReserveRatio.toFixed(1)}%입니다.
                </p>
              </div>
              <div className="cash-metrics">
                <span>
                  <small>미사용 현금</small>
                  <strong>{formatKrw(cashStatus.idleCash)}</strong>
                </span>
                <span>
                  <small>현금성 ETF</small>
                  <strong>{formatKrw(cashStatus.cashLikeValue)}</strong>
                </span>
                {selected?.research_config ? (
                  <span>
                    <small>현금 유지 기준 (이번 달 매수 예산)</small>
                    <strong>{formatKrw(cashStatus.minimumCashBuffer)}</strong>
                  </span>
                ) : (
                  <span>
                    <small>남은 분할매수</small>
                    <strong>{formatKrw(cashStatus.pendingSplitAmount)}</strong>
                  </span>
                )}
                <span>
                  <small>SGOV 추천</small>
                  <strong>
                    {cashStatus.suggestedSgovAmount > 0
                      ? formatKrw(cashStatus.suggestedSgovAmount)
                      : "이동 불필요"}
                  </strong>
                </span>
              </div>
              <div className="cash-actions">
                <label>
                  달러 현금 잔액
                  <input
                    type="number"
                    min={0}
                    value={manualCashUsd}
                    onChange={(event) => setManualCashUsd(Number(event.target.value))}
                    placeholder="예: 360"
                  />
                </label>
                <small>
                  입력하지 않으면 기록 기준 자동 현금 {formatKrw(cashStatus.autoIdleCash)}을
                  사용합니다. 입력 시 {formatUsdFromKrw(cashStatus.idleCash, usdKrwRate)} 기준으로
                  CASH 행에 반영됩니다.
                </small>
                {selected?.research_config ? (
                  <p>
                    이번 달 매수 예산({formatKrw(selected.research_config.monthly_contribution)})은
                    현금으로 남기고, 그 초과분(감속 이월분)만 SGOV 대기 후보로 계산합니다. 10만원
                    미만이면 잦은 매매를 피하기 위해 이동을 권하지 않고, 200일선 이탈 방어
                    국면에서는 전액 SGOV 파킹이 곧 방어 포지션입니다. SGOV 매도는 방어 후 회복 시
                    21일 재투입 때만 발생하는 전제입니다.
                  </p>
                ) : (
                  <p>
                    남은 분할매수 예정액과 최소 현금 버퍼를 제외하고 여유가 있는 현금만 SGOV 대기
                    후보로 계산합니다. 매수 조건이 오면 SGOV를 매도해 TQQQ/QLD 분할매수 재원으로
                    쓰는 전제입니다.
                  </p>
                )}
                <div className="hero-actions">
                  <button
                    className="primary"
                    type="button"
                    onClick={() => void parkSgovNow()}
                    disabled={cashStatus.suggestedSgovAmount < 10000 || parkingSgov}
                  >
                    {parkingSgov ? "기록 중..." : "SGOV 파킹 기록하기"}
                  </button>
                  <button
                    type="button"
                    onClick={prepareSgovParking}
                    disabled={cashStatus.suggestedSgovAmount < 10000}
                  >
                    수정해서 기록
                  </button>
                </div>
              </div>
            </div>
            <details className="secondary-details">
              <summary>전략 한도 상세</summary>
              <div className="risk-budget-card">
                <div>
                  <span className="section-label">Risk Budget</span>
                  <h3>전략 한도 점검</h3>
                  <p>
                    공격적인 운용이어도 레버리지 총량, 현금성 대기, 1회 실행 한도는 매수 전 자동으로
                    확인합니다.
                  </p>
                </div>
                <div className="risk-budget-grid">
                  {riskBudget.map((item) => (
                    <span className={item.level} key={item.title}>
                      <small>{item.title}</small>
                      <strong>{item.value}</strong>
                      <em>{item.limit}</em>
                    </span>
                  ))}
                </div>
              </div>
            </details>
            <div className="execution-summary-grid">
              {executionRows.map((row) => (
                <div className="execution-summary-card" key={row.symbol}>
                  <div>
                    <span className="section-label">{row.stage}</span>
                    <h3>
                      {row.symbol}
                      {row.executionSymbol !== row.symbol ? ` (${row.executionSymbol})` : ""}
                    </h3>
                    <small>{row.role}</small>
                  </div>
                  <div className="progress-track">
                    <span style={{ width: `${Math.min(Math.max(row.progressPct, 0), 120)}%` }} />
                  </div>
                  <div className="execution-summary-metrics">
                    <span>
                      <small>목표</small>
                      <strong>{formatKrw(row.targetAmount)}</strong>
                    </span>
                    <span>
                      <small>집행</small>
                      <strong>{formatKrw(row.executedAmount)}</strong>
                    </span>
                    <span>
                      <small>진행률</small>
                      <strong>{row.progressPct.toFixed(1)}%</strong>
                    </span>
                    <span>
                      <small>현재비중</small>
                      <strong>{row.currentWeight.toFixed(1)}%</strong>
                    </span>
                  </div>
                  <p>{row.nextHint}</p>
                </div>
              ))}
            </div>
          </article>
        ) : null}

        {activeTab === "overview" &&
        guide &&
        selected &&
        !selected.research_config &&
        guide.execution_plan.length > 0 ? (
          <article className="panel span-12">
            <PanelTitle icon={<Target size={18} />} title="오늘 실행 기준" />
            <div className="execution-grid">
              {guide.execution_plan.map((step) => (
                <div className={`execution-card ${step.status}`} key={`${step.side}-${step.step}`}>
                  <div>
                    <span className="section-label">
                      {step.side === "buy" ? "분할매수" : "분할매도"}
                    </span>
                    <h3>
                      {step.step} · {step.symbol}
                    </h3>
                    <p>{step.trigger_label || step.trigger}</p>
                  </div>
                  <div className="trigger-grid">
                    <span>
                      <small>현재 QQQ</small>
                      <strong>{formatUsd(step.current_price)}</strong>
                    </span>
                    <span>
                      <small>실행 기준</small>
                      <strong>{formatUsd(step.trigger_price)}</strong>
                    </span>
                    <span>
                      <small>기준가 대비</small>
                      <strong>
                        {step.distance_to_trigger_pct == null
                          ? "-"
                          : formatPct(step.distance_to_trigger_pct)}
                      </strong>
                    </span>
                  </div>
                  <strong>
                    {actionLabelWithCurrency(
                      step.action_label,
                      step.amount,
                      step.symbol,
                      usdKrwRate
                    )}
                  </strong>
                  <small>{step.reason}</small>
                  <button onClick={() => prepareExecution(step)} disabled={step.status !== "ready"}>
                    기록 초안 만들기
                  </button>
                </div>
              ))}
            </div>
          </article>
        ) : null}

        {activeTab === "strategy" && selected?.research_config ? (
          <article className="panel span-12">
            <PanelTitle
              icon={<BookOpenCheck size={18} />}
              title="연구 규칙 (백테스트로 검증된 원본)"
            />
            <p className="muted">
              개인연구에서 채택한 규칙 그대로입니다. 오늘의 판단이 이 규칙으로 계산되며, 규칙 변경은
              개인연구 탭에서 재검증 후 재채택하는 것이 원칙입니다.
            </p>
            <div className="cash-metrics">
              <span>
                <small>적립 비율</small>
                <strong>
                  TQQQ {selected.research_config.daily_base_tqqq_ratio}% :{" "}
                  {selected.research_config.one_x_symbol}{" "}
                  {selected.research_config.daily_base_one_x_ratio}%
                </strong>
              </span>
              <span>
                <small>{selected.research_config.one_x_symbol} 매수 방식</small>
                <strong>
                  {selected.research_config.one_x_upfront_monthly
                    ? "월급날 소수점 일괄 매수"
                    : "매일 분할 매수"}
                </strong>
              </span>
              <span>
                <small>월 적립금</small>
                <strong>
                  {formatKrw(selected.research_config.monthly_contribution)} (일{" "}
                  {formatKrw(selected.research_config.monthly_contribution / 21)})
                </strong>
              </span>
              <span>
                <small>기준선</small>
                <strong>
                  {selected.research_config.moving_average_days}일선{" "}
                  {selected.research_config.ma_exit_band_pct >= 0 ? "+" : ""}
                  {selected.research_config.ma_exit_band_pct}%
                </strong>
              </span>
              <span>
                <small>이탈 시 방어</small>
                <strong>
                  {selected.research_config.defense_mode === "cash"
                    ? "전량 매도 → 현금/SGOV"
                    : selected.research_config.defense_mode === "spym_sgov_half"
                      ? "전량 매도 → SPYM+SGOV 반반"
                      : "TQQQ만 매도, 1x 유지"}
                </strong>
              </span>
            </div>
          </article>
        ) : null}

        {activeTab === "strategy" && selected?.research_config ? (
          <article className="panel span-12 adjustment-coach">
            <PanelTitle icon={<Save size={18} />} title="월급 추가금 입금" />
            <div className="adjustment-form">
              <div>
                <span className="section-label">Salary Deposit</span>
                <h3>매월 {payDay}일 월급이 들어오면 여기서 입금을 기록하세요.</h3>
                <p className="muted">
                  입금액은 전략 현금(총자본)에 즉시 반영되고, 사용처는 규칙이 결정합니다 — 200일선
                  위에서는 하루 1/21씩 분할 매수, 이격 과열 구간에서는 감속, 이탈 시에는 방어
                  실탄으로 대기합니다. 별도의 배분 조언은 필요 없습니다.
                </p>
                {selected.research_config.one_x_upfront_monthly ? (
                  <p className="muted">
                    ✦ 선매수 모드: 입금 기록 후 {selected.research_config.one_x_symbol}{" "}
                    {formatKrw(
                      (selected.research_config.monthly_contribution *
                        selected.research_config.daily_base_one_x_ratio) /
                        100
                    )}
                    을 토스 앱의 금액(소수점) 주문으로 오늘 일괄 매수하세요. TQQQ는 오늘의 판단대로
                    매일 삽니다.
                  </p>
                ) : null}
              </div>
              <div className="cash-actions">
                <label>
                  입금액 (기본: 월 적립 설정액)
                  <input
                    type="number"
                    min={0}
                    step={100000}
                    value={depositAmount || ""}
                    placeholder={`${selected.research_config.monthly_contribution.toLocaleString("ko-KR")}`}
                    onChange={(event) => setDepositAmount(Number(event.target.value))}
                  />
                </label>
                <label>
                  메모 (선택)
                  <input
                    type="text"
                    value={depositNote}
                    placeholder="예: 7월 월급"
                    onChange={(event) => setDepositNote(event.target.value)}
                  />
                </label>
                <button
                  className="primary"
                  type="button"
                  disabled={depositing}
                  onClick={() => void submitDeposit()}
                >
                  <Save size={15} /> {depositing ? "반영 중..." : "입금 기록하기"}
                </button>
              </div>
            </div>
          </article>
        ) : null}

        {activeTab === "strategy" && selected && !selected.research_config ? (
          <article className="panel span-12 adjustment-coach">
            <PanelTitle icon={<BookOpenCheck size={18} />} title="최신 철학 점검" />
            <div className="adjustment-form">
              <div>
                <span className="section-label">Philosophy Upgrade</span>
                <h3>현재 저장된 전략을 최신 TQQQ 200일선 철학으로 다시 점검합니다.</h3>
                <p className="muted">
                  기존 전략은 당시의 판단 기록으로 보존하고, 최신 철학을 적용할 때만 새 버전으로
                  반영합니다.
                </p>
              </div>
              <button className="primary" onClick={requestPhilosophyAdvice}>
                <BookOpenCheck size={16} />
                최신 철학 점검 받기
              </button>
            </div>
            {philosophyAdvice ? (
              <div
                className={`adjustment-result ${philosophyAdvice.verdict === "major_change" ? "watch" : "ok"}`}
              >
                <div>
                  <span className="section-label">{philosophyAdvice.verdict}</span>
                  <h3>{philosophyAdvice.headline}</h3>
                  <p>{philosophyAdvice.summary}</p>
                </div>
                <div className="adjustment-metrics">
                  <span>
                    <small>현재 전략</small>
                    <strong>{philosophyAdvice.current_plan_title}</strong>
                  </span>
                  <span>
                    <small>최신 추천</small>
                    <strong>{philosophyAdvice.suggested_plan_title}</strong>
                  </span>
                  <span>
                    <small>추정 리스크</small>
                    <strong>{philosophyAdvice.inferred_risk_score}점</strong>
                  </span>
                  <span>
                    <small>QQQ 이격</small>
                    <strong>{formatPct(philosophyAdvice.qqq_distance_from_200ma)}</strong>
                  </span>
                </div>
                <p className="muted">{philosophyAdvice.suggested_plan_summary}</p>

                <ListBlock title="반영되는 철학" items={philosophyAdvice.changes} />
                <ListBlock title="주의할 점" items={philosophyAdvice.cautions} />
                <div className="adjustment-table">
                  {philosophyAdvice.allocation_diffs.map((allocation) => (
                    <div key={allocation.symbol}>
                      <strong>{allocation.symbol}</strong>
                      <span>
                        {allocation.current_ratio.toFixed(1)}% →{" "}
                        {allocation.suggested_ratio.toFixed(1)}%
                      </span>
                      <em>
                        {allocation.delta_ratio >= 0 ? "+" : ""}
                        {allocation.delta_ratio.toFixed(1)}%
                      </em>
                      <small>{allocation.reason}</small>
                    </div>
                  ))}
                </div>
                <button className="primary" onClick={applyPhilosophyAdvice}>
                  <Save size={16} />
                  최신 철학을 v{(selected.version ?? 1) + 1}로 적용
                </button>
              </div>
            ) : null}
          </article>
        ) : null}

        {activeTab === "strategy" && selected && !selected.research_config ? (
          <article className="panel span-12 adjustment-coach">
            <PanelTitle icon={<SlidersHorizontal size={18} />} title="현금 비중 조정 코치" />
            <div className="adjustment-form">
              <div>
                <span className="section-label">What-if 조정</span>
                <h3>원 규칙을 유지한 채 현금 비중을 바꾸면 어떤가요?</h3>
                <p className="muted">
                  예: 현금 39.4% 전략을 20%로 낮추고 싶을 때, 현재 QQQ 위치와 TQQQ 규칙을 기준으로
                  위험도를 점검합니다.
                </p>
              </div>
              <label>
                목표 현금 %
                <input
                  type="number"
                  min={0}
                  max={80}
                  value={targetCashRatio}
                  onChange={(event) => setTargetCashRatio(Number(event.target.value))}
                />
              </label>
              <button className="primary" onClick={requestAdjustmentAdvice}>
                <SlidersHorizontal size={16} />
                조정 조언 받기
              </button>
            </div>
            {adjustmentAdvice ? (
              <div className={`adjustment-result ${adjustmentAdvice.verdict}`}>
                <div>
                  <span className="section-label">{adjustmentAdvice.verdict}</span>
                  <h3>{adjustmentAdvice.headline}</h3>
                  <p>{adjustmentAdvice.summary}</p>
                </div>
                <div className="adjustment-metrics">
                  <span>
                    <small>현재 현금</small>
                    <strong>{adjustmentAdvice.current_cash_ratio.toFixed(1)}%</strong>
                  </span>
                  <span>
                    <small>목표 현금</small>
                    <strong>{adjustmentAdvice.target_cash_ratio.toFixed(1)}%</strong>
                  </span>
                  <span>
                    <small>권장 최소</small>
                    <strong>{adjustmentAdvice.minimum_cash_ratio.toFixed(1)}%</strong>
                  </span>
                  <span>
                    <small>QQQ 이격</small>
                    <strong>{formatPct(adjustmentAdvice.qqq_distance_from_200ma)}</strong>
                  </span>
                </div>
                {adjustmentAdvice.issues.length ? (
                  <ListBlock title="주의할 점" items={adjustmentAdvice.issues} />
                ) : null}
                <ListBlock title="권장 액션" items={adjustmentAdvice.actions} />
                <div className="adjustment-table">
                  {adjustmentAdvice.suggested_allocations.map((allocation) => (
                    <div key={allocation.symbol}>
                      <strong>{allocation.symbol}</strong>
                      <span>
                        {allocation.current_ratio.toFixed(1)}% →{" "}
                        {allocation.suggested_ratio.toFixed(1)}%
                      </span>
                      <em>
                        {allocation.delta_ratio >= 0 ? "+" : ""}
                        {allocation.delta_ratio.toFixed(1)}%
                      </em>
                      <small>{allocation.reason}</small>
                    </div>
                  ))}
                </div>
                <button className="primary" onClick={applyAdjustmentAdvice}>
                  <Save size={16} />이 조정안 적용해서 v{(selected.version ?? 1) + 1}로 관리
                </button>
              </div>
            ) : null}
          </article>
        ) : null}

        {activeTab === "strategy" && selected && !selected.research_config ? (
          <article className="panel span-12 adjustment-coach">
            <PanelTitle icon={<Save size={18} />} title="월급 추가금 코치" />
            <div className="adjustment-form">
              <div>
                <span className="section-label">Monthly Contribution</span>
                <h3>매달 들어오는 추가금을 새 원금으로 반영합니다.</h3>
                <p className="muted">
                  추가금은 먼저 미사용 현금으로 잡고, 새 총자본 기준 목표금액과 현재 실행액의 차이를
                  계산합니다.
                </p>
              </div>
              <label>
                매월 입금일
                <input
                  type="number"
                  min={1}
                  max={31}
                  value={payDay}
                  onChange={(event) => setPayDay(Number(event.target.value))}
                />
              </label>
              <label>
                추가 투입금
                <input
                  type="number"
                  min={0}
                  step={100000}
                  value={monthlyContribution}
                  onChange={(event) => setMonthlyContribution(Number(event.target.value))}
                />
              </label>
              <button className="primary" onClick={requestContributionAdvice}>
                <SlidersHorizontal size={16} />
                추가금 코칭 받기
              </button>
            </div>
            {contributionAdvice
              ? (() => {
                  const selectedPlan =
                    contributionAdvice.plans.find(
                      (plan) => plan.id === selectedContributionPlanId
                    ) ??
                    contributionAdvice.plans.find(
                      (plan) => plan.id === contributionAdvice.recommended_plan_id
                    ) ??
                    contributionAdvice.plans[0];
                  return selectedPlan ? (
                    <div className="adjustment-result ok">
                      <div>
                        <span className="section-label">Contribution Options</span>
                        <h3>{selectedPlan.headline}</h3>
                        <p>{selectedPlan.summary}</p>
                      </div>
                      <div className="strategy-toggle-list">
                        {contributionAdvice.plans.map((plan) => (
                          <button
                            className={selectedPlan.id === plan.id ? "selected" : ""}
                            key={plan.id}
                            onClick={() => setSelectedContributionPlanId(plan.id)}
                            type="button"
                          >
                            <strong>{plan.title}</strong>
                            <small>
                              {plan.risk_level} · 추천도 {plan.recommendation_score}
                            </small>
                            {plan.id === contributionAdvice.recommended_plan_id ? (
                              <em>추천</em>
                            ) : null}
                          </button>
                        ))}
                      </div>
                      <div className="adjustment-metrics">
                        <span>
                          <small>현재 원금</small>
                          <strong>{formatKrw(selectedPlan.current_total_capital)}</strong>
                        </span>
                        <span>
                          <small>추가금</small>
                          <strong>{formatKrw(selectedPlan.contribution_amount)}</strong>
                        </span>
                        <span>
                          <small>새 원금</small>
                          <strong>{formatKrw(selectedPlan.new_total_capital)}</strong>
                        </span>
                        <span>
                          <small>입금 후 현금</small>
                          <strong>{formatKrw(selectedPlan.available_cash_after_deposit)}</strong>
                        </span>
                      </div>
                      <ListBlock title="운용 원칙" items={selectedPlan.actions} />
                      <div className="adjustment-table">
                        {selectedPlan.allocations.map((allocation) => (
                          <div key={`${selectedPlan.id}-${allocation.symbol}-${allocation.role}`}>
                            <strong>{allocation.symbol}</strong>
                            <span>
                              {formatKrw(allocation.current_amount)} → 목표{" "}
                              {formatKrw(allocation.target_amount_after)}
                            </span>
                            <em>
                              {allocation.action === "buy"
                                ? "매수"
                                : allocation.action === "wait"
                                  ? "대기"
                                  : allocation.action === "rebalance"
                                    ? "조정"
                                    : "유지"}{" "}
                              {formatKrw(allocation.suggested_amount)}
                            </em>
                            <small>{allocation.reason}</small>
                          </div>
                        ))}
                      </div>
                      <button className="primary" onClick={applyContributionAdvice}>
                        <Save size={16} />
                        선택한 추가금 운용안을 v{(selected.version ?? 1) + 1} 전략에 반영
                      </button>
                    </div>
                  ) : null;
                })()
              : null}
          </article>
        ) : null}

        {activeTab === "strategy" && selected?.version_history?.length ? (
          <article className="panel span-12">
            <PanelTitle icon={<History size={18} />} title="전략 버전 이력" />
            <div className="version-list">
              {[...selected.version_history].reverse().map((entry) => (
                <div className="version-row" key={`${entry.version}-${entry.created_at}`}>
                  <div>
                    <strong>
                      v{entry.version} · {entry.title}
                    </strong>
                    <small>
                      {formatDate(entry.created_at)} · {entry.change_type}
                    </small>
                    {entry.note ? <p>{entry.note}</p> : null}
                  </div>
                  <div className="version-ratios">
                    {entry.after_allocations.map((allocation) => (
                      <span key={`${entry.version}-${allocation.symbol}`}>
                        {allocation.symbol} {allocation.ratio.toFixed(1)}%
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </article>
        ) : null}

        {(activeTab === "strategy" || activeTab === "journal") && selected ? (
          <>
            {activeTab === "strategy" && !selected.research_config ? (
              <article className="panel span-6">
                <PanelTitle icon={<ListChecks size={18} />} title="목표 비중과 원 규칙" />
                <div className="currency-control">
                  <div>
                    <span>
                      미국 ETF 금액은 달러 기준으로 보고, 괄호 안에 원화 환산을 함께 표시합니다.
                    </span>
                    <small className="fx-status">{fxStatus}</small>
                  </div>
                  <label>
                    USD/KRW
                    <input
                      type="number"
                      value={usdKrwRate}
                      onChange={(event) => setUsdKrwRate(Number(event.target.value))}
                    />
                  </label>
                  <button type="button" onClick={loadFxRate}>
                    <RefreshCw size={16} />
                    환율 갱신
                  </button>
                  <button type="button" onClick={() => selected && loadLiveQuotes(selected)}>
                    <RefreshCw size={16} />
                    현재가 갱신
                  </button>
                </div>
                <div className="refresh-status">
                  <strong>{quoteStatus}</strong>
                  <small>
                    QQQ는 전략 기준 자산으로 유지하되, 목표금액이 QQQ 1주보다 작으면 QQQM을 실행
                    대체 후보로 제시합니다.
                  </small>
                </div>
                <table>
                  <tbody>
                    {selected.plan.allocations.map((allocation) => (
                      <tr key={allocation.symbol}>
                        <td>
                          <strong>{allocation.symbol}</strong>
                          <small>{allocation.role}</small>
                          <small className="policy-note">
                            {allocationPolicy(allocation.symbol)} ·{" "}
                            {allocationPolicyDetail(allocation.symbol)}
                          </small>
                          <small className="execution-note">
                            {allocationExecutionDetail(allocation, liveQuotes, usdKrwRate)}
                          </small>
                        </td>
                        <td>{allocation.target_ratio.toFixed(1)}%</td>
                        <td>
                          {formatDualCurrency(
                            allocation.target_amount,
                            allocation.symbol,
                            usdKrwRate
                          )}
                          {isUsdAsset(allocation.symbol) ? (
                            <small>
                              실행 후보 {executableSymbol(allocation, liveQuotes, usdKrwRate)}
                              {liveQuotes[executableSymbol(allocation, liveQuotes, usdKrwRate)]
                                ? ` · ${formatUsd(liveQuotes[executableSymbol(allocation, liveQuotes, usdKrwRate)].price)}`
                                : ""}
                            </small>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <RuleList title="분할매수 원칙" items={selected.plan.buy_plan} />
                <RuleList title="분할매도 원칙" items={selected.plan.sell_plan} />
              </article>
            ) : null}

            {activeTab === "journal" ? (
              <>
                <article className="panel span-12 execution-review-card">
                  <div>
                    <span className="section-label">Execution Review</span>
                    <h3>최근 실행 리뷰</h3>
                    <p>{executionReview.summary}</p>
                  </div>
                  <div
                    className={`review-score ${executionReview.score < 60 ? "danger" : executionReview.score < 85 ? "watch" : "ok"}`}
                  >
                    <span>리뷰 점수</span>
                    <strong>{executionReview.score}</strong>
                  </div>
                  {executionReview.entries.length ? (
                    <div className="review-entry-grid">
                      {executionReview.entries.map(({ entry, review }) => (
                        <div className={`review-entry ${review.level}`} key={entry.id}>
                          <div>
                            <strong>
                              {journalTypeLabel(entry.entry_type)} · {entry.symbol}
                            </strong>
                            <small>
                              {formatDate(entry.created_at)} · QQQ 200일선 대비{" "}
                              {formatPct(entry.qqq_distance_from_200ma)}
                            </small>
                          </div>
                          <span>{review.label}</span>
                          <p>{review.note}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">
                      매수/매도/리밸런싱 기록을 남기면 자동 리뷰가 생성됩니다.
                    </p>
                  )}
                </article>

                <article className="panel span-6">
                  <PanelTitle icon={<Save size={18} />} title="실행/판단 기록" />
                  <div className="journal-form">
                    <label>
                      유형
                      <select
                        value={draft.entry_type}
                        onChange={(event) =>
                          setDraft({
                            ...draft,
                            entry_type: event.target.value as JournalEntry["entry_type"]
                          })
                        }
                      >
                        <option value="note">메모</option>
                        <option value="deposit">입금</option>
                        <option value="fx">환전</option>
                        <option value="cash_transfer">현금 이동</option>
                        <option value="buy">매수</option>
                        <option value="sell">매도</option>
                        <option value="rebalance">리밸런싱</option>
                        <option value="rule_check">규칙 점검</option>
                        <option value="review">리뷰</option>
                      </select>
                    </label>
                    <label>
                      종목
                      <input
                        value={draft.symbol}
                        onChange={(event) =>
                          updateExecutionPrice({ symbol: event.target.value.toUpperCase() })
                        }
                      />
                    </label>
                    <label>
                      원화 금액
                      <input
                        type="number"
                        value={draft.amount}
                        onChange={(event) =>
                          setDraft({ ...draft, amount: Number(event.target.value) })
                        }
                      />
                    </label>
                    <label>
                      체결가(USD)
                      <input
                        type="number"
                        value={draft.price}
                        onChange={(event) =>
                          updateExecutionPrice({ price: Number(event.target.value) })
                        }
                      />
                    </label>
                    <label>
                      수량
                      <input
                        type="number"
                        value={draft.quantity}
                        onChange={(event) =>
                          updateExecutionPrice({ quantity: Number(event.target.value) })
                        }
                      />
                    </label>
                    <div className="execution-fill span-2">
                      <span>
                        체결가와 수량을 입력하면 환율 {usdKrwRate.toLocaleString("ko-KR")}원
                        기준으로 원화 금액이 자동 계산됩니다.
                      </span>
                      {liveQuotes[draft.symbol] ? (
                        <button
                          type="button"
                          onClick={() =>
                            updateExecutionPrice({ price: liveQuotes[draft.symbol].price })
                          }
                        >
                          현재가를 체결가로 입력
                        </button>
                      ) : null}
                    </div>
                    <label className="span-2">
                      이유
                      <input
                        value={draft.reason}
                        onChange={(event) => setDraft({ ...draft, reason: event.target.value })}
                        placeholder="예: QQQ 200일선 위, 1차 분할 조건"
                      />
                    </label>
                    <label className="span-2">
                      메모
                      <textarea
                        value={draft.note}
                        onChange={(event) => setDraft({ ...draft, note: event.target.value })}
                      />
                    </label>
                    <button className="primary span-2" onClick={addJournal}>
                      <Save size={16} />
                      기록 저장
                    </button>
                  </div>
                </article>

                <article className="panel span-12">
                  <PanelTitle icon={<ListChecks size={18} />} title="현금 흐름 원장" />
                  <div className="cash-ledger-summary">
                    <span>
                      <small>총 입금 기록</small>
                      <strong>{formatKrw(cashLedger.deposits)}</strong>
                    </span>
                    <span>
                      <small>환전 기록</small>
                      <strong>{formatKrw(cashLedger.fx)}</strong>
                    </span>
                    <span>
                      <small>SGOV/BIL 대기 매수</small>
                      <strong>{formatKrw(cashLedger.cashLikeBuys)}</strong>
                    </span>
                    <span>
                      <small>현금성 대기 매도</small>
                      <strong>{formatKrw(cashLedger.cashLikeSells)}</strong>
                    </span>
                    <span>
                      <small>현재 미집행 현금</small>
                      <strong>{formatKrw(cashStatus.idleCash)}</strong>
                    </span>
                  </div>
                  {cashLedger.entries.length ? (
                    <div className="cash-ledger-list">
                      {[...cashLedger.entries].reverse().map((entry) => (
                        <div className="cash-ledger-row" key={entry.id}>
                          <div>
                            <strong>
                              {journalTypeLabel(entry.entry_type)} · {entry.symbol || "CASH"}
                            </strong>
                            <small>{formatDate(entry.created_at)}</small>
                          </div>
                          <span>{entry.amount ? formatKrw(entry.amount) : "-"}</span>
                          <p>{entry.reason || entry.note || "현금 흐름 기록"}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">아직 입금, 환전, 현금성 대기자산 이동 기록이 없습니다.</p>
                  )}
                </article>

                <article className="panel span-12">
                  <PanelTitle icon={<History size={18} />} title="전략 기록장" />
                  {selected.journal.length ? (
                    <table>
                      <tbody>
                        {[...selected.journal].reverse().map((entry) => (
                          <tr key={entry.id}>
                            <td>
                              <strong>{journalTypeLabel(entry.entry_type)}</strong>
                              <small>{formatDate(entry.created_at)}</small>
                            </td>
                            <td>{entry.symbol || "-"}</td>
                            <td>
                              {entry.amount ? formatKrw(entry.amount) : "-"}
                              {entry.price ? (
                                <small>
                                  {formatUsd(entry.price)} · {entry.quantity || 0}주
                                </small>
                              ) : null}
                            </td>
                            <td>{entry.reason || entry.note || "-"}</td>
                            <td>{formatPct(entry.qqq_distance_from_200ma)}</td>
                            <td>
                              <button
                                className="icon-danger"
                                type="button"
                                onClick={() => deleteJournal(entry.id)}
                                title="기록 삭제"
                              >
                                <Trash2 size={16} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p className="muted">
                      아직 기록이 없습니다. 매수/매도 전 판단 이유부터 남기면 전략 관리 품질이
                      좋아집니다.
                    </p>
                  )}
                </article>
              </>
            ) : null}
          </>
        ) : null}
      </div>
    </section>
  );
}
