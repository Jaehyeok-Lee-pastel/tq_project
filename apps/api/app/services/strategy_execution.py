from app.schemas.managed_strategy import ManagedStrategy, SplitExecutionStep
from app.services.managed_strategy_model import (
    _allocation_amount,
    _allocation_map,
    _allocation_ratio,
    _cash_like_ratio,
    _executed_amounts,
)


def build_execution_plan(strategy: ManagedStrategy, distance: float) -> list[SplitExecutionStep]:
    if strategy.research_config is not None and strategy.research_config.strategy == "tqqq_daily_200ma":
        # Daily-accumulation strategies don't follow the staged 1/2/3-step
        # ladder; the today-decision endpoint drives their execution instead.
        return []
    target_symbol = "TQQQ" if _allocation_ratio(strategy, "TQQQ") else "QLD"
    plan: list[SplitExecutionStep] = []
    for index, step in enumerate(strategy.plan.buy_plan):
        status, reason = _buy_step_status(strategy, index, step.step, distance)
        trigger = _buy_trigger_detail(strategy, index)
        amount = _buy_step_amount(strategy, index, step.amount, distance, status)
        plan.append(
            SplitExecutionStep(
                side="buy",
                step=step.step,
                symbol=target_symbol,
                status=status,
                trigger=step.trigger,
                trigger_price=trigger["price"],
                trigger_label=trigger["label"],
                current_price=strategy.market.qqq_close,
                distance_to_trigger_pct=trigger["distance"],
                amount=round(amount),
                ratio_of_target=round(amount / _allocation_amount(strategy, target_symbol) * 100, 1)
                if _allocation_amount(strategy, target_symbol)
                else step.ratio_of_target,
                reason=f"{reason} {_funding_hint(strategy, 'buy', target_symbol, status)}".strip(),
                action_label=_action_label("buy", status, amount),
            )
        )
    for index, step in enumerate(strategy.plan.sell_plan):
        status, reason = _sell_step_status(strategy, index, step.step, distance)
        trigger = _sell_trigger_detail(strategy, index)
        plan.append(
            SplitExecutionStep(
                side="sell",
                step=step.step,
                symbol=target_symbol,
                status=status,
                trigger=step.trigger,
                trigger_price=trigger["price"],
                trigger_label=trigger["label"],
                current_price=strategy.market.qqq_close,
                distance_to_trigger_pct=trigger["distance"],
                amount=step.amount,
                ratio_of_target=step.ratio_of_target,
                reason=f"{reason} {_funding_hint(strategy, 'sell', target_symbol, status)}".strip(),
                action_label=_action_label("sell", status, step.amount),
            )
        )
    return plan


def _price_distance(current: float, trigger_price: float | None) -> float | None:
    if not trigger_price:
        return None
    return round((current / trigger_price - 1) * 100, 2)


def _funding_hint(strategy: ManagedStrategy, side: str, target_symbol: str, status: str) -> str:
    if status == "blocked":
        return "재원 전환 금지: SGOV/CASH는 방어 또는 다음 조건까지 유지합니다."
    if status != "ready":
        return "재원 대기: TQQQ 매수 재원과 1x 완충 재원을 분리해 둡니다."
    if side == "buy":
        cash_like = _cash_like_ratio(_allocation_map(strategy))
        if target_symbol in {"TQQQ", "QLD"}:
            if cash_like > 0:
                return "실행 재원: 미사용 현금 또는 SGOV 일부를 매도해 레버리지 분할매수 재원으로만 사용합니다."
            return "실행 재원: 신규 입금 또는 미집행 현금이 있을 때만 집행합니다."
        return "실행 재원: 레버리지 추격매수가 아니라 1x 완충 비중 보완으로 처리합니다."
    return "매도금 처리: 200일선 위 감속이면 QQQM/SPYM, 200일선 아래 방어면 SGOV/CASH로 이동합니다."


def _buy_trigger_detail(strategy: ManagedStrategy, index: int) -> dict[str, float | str | None]:
    current = strategy.market.qqq_close
    sma20 = getattr(strategy.market, "qqq_sma20", None)
    sma50 = strategy.market.qqq_sma50
    sma200 = strategy.market.qqq_sma200
    if index == 0:
        price = sma200
        label = f"QQQ가 200일선 ${sma200:,.2f} 위에서 마감 유지"
    elif index == 1:
        if sma20:
            price = sma20 * 1.01
            label = f"2차 매수: QQQ가 20일선 ${sma20:,.2f} 기준 +1% 이내(${price:,.2f} 이하)로 조정"
        else:
            price = sma200 * 1.08
            label = f"2차 매수: 20일선 데이터가 없으므로 QQQ 200일선 대비 +8% 이하(${price:,.2f})로 이격 완화"
    else:
        if sma50:
            base = sma50
            price = sma50 * 1.02
            defense_price = sma50 * 1.01
            label = (
                f"3차 매수: QQQ가 50일선 ${base:,.2f} 기준 +1~+2% 방어 구간"
                f"(${defense_price:,.2f} 초과 ~ ${price:,.2f} 이하)에 있을 때만 검토"
            )
        else:
            price = sma200 * 1.05
            label = f"3차 매수: QQQ 200일선 대비 +5% 이하(${price:,.2f})로 이격 완화"
    return {"price": price, "label": label, "distance": _price_distance(current, price)}


def _reload_execution_step(strategy: ManagedStrategy, target_symbol: str, distance: float) -> SplitExecutionStep | None:
    if target_symbol != "TQQQ":
        return None
    target_amount = _allocation_amount(strategy, "TQQQ")
    if target_amount <= 0:
        return None
    executed = _executed_amounts(strategy).get("TQQQ", 0)
    progress = executed / target_amount * 100
    target_gap = max(target_amount - executed, 0)
    status, reason = _reload_status(strategy, distance, progress, target_gap)
    amount = 0 if status in {"blocked", "wait", "done"} else min(target_gap, strategy.total_capital * 0.05)
    trigger_price = min(
        strategy.market.qqq_sma50 * 1.01 if strategy.market.qqq_sma50 else strategy.market.qqq_sma200 * 1.05,
        strategy.market.qqq_sma200 * 1.05,
    )
    label = (
        "3차 이후 재장전: 새 추가금 또는 전략 변경이 있고, QQQ가 200일선 대비 +5% 이하로 이격 완화되며, "
        "50일선이 무너지지 않았고 TQQQ 목표 미달이 원금 2% 이상일 때만 검토"
    )
    return SplitExecutionStep(
        side="buy",
        step="재장전 검토",
        symbol="TQQQ",
        status=status,  # type: ignore[arg-type]
        trigger="3차 완료 후 엄격한 재장전 조건",
        trigger_price=trigger_price,
        trigger_label=label,
        current_price=strategy.market.qqq_close,
        distance_to_trigger_pct=_price_distance(strategy.market.qqq_close, trigger_price),
        amount=round(amount),
        ratio_of_target=round(amount / target_amount * 100, 1) if target_amount else 0,
        reason=reason,
        action_label=_action_label("buy", status, amount),
    )


def _reload_status(
    strategy: ManagedStrategy,
    distance: float,
    progress: float,
    target_gap: float,
) -> tuple[str, str]:
    if _has_journal_marker(strategy, "buy", "재장전"):
        return "done", "이미 기록장에 재장전 매수 기록이 있습니다. 다음 재장전은 새 추가금 또는 전략 버전 변경 후 다시 검토합니다."
    if progress < 95:
        return "wait", "아직 1~3차 기존 분할매수 사이클이 끝나지 않았습니다. 재장전보다 원래 분할 규칙과 1x 완충 운용을 먼저 따릅니다."
    if distance <= 0:
        return "blocked", "QQQ가 200일선 아래입니다. SGOV/CASH를 TQQQ 매수 재원으로 전환하지 않습니다."
    if strategy.market.qqq_sma50 and strategy.market.qqq_close < strategy.market.qqq_sma50:
        return "blocked", "QQQ가 50일선 아래라 리스크 축소 조건이 우선입니다. 추가 TQQQ 매수는 금지합니다."
    if distance > 5:
        return "blocked", "3차 이후 재장전은 과최적화를 막기 위해 QQQ 200일선 대비 +5% 이하로 이격이 완화될 때만 허용합니다."
    if target_gap < strategy.total_capital * 0.02:
        return "wait", "TQQQ 목표 미달분이 원금의 2% 미만입니다. 새 추가금이나 전략 변경 전까지 추가매수하지 않습니다."
    return "ready", "3차 완료, 200일선 위, 50일선 방어, 이격 +5% 이하, 목표 미달 2% 이상을 모두 충족했습니다. 1회 재장전은 원금 5% 이내로 제한합니다."


def _sell_trigger_detail(strategy: ManagedStrategy, index: int) -> dict[str, float | str | None]:
    current = strategy.market.qqq_close
    sma50 = strategy.market.qqq_sma50
    sma200 = strategy.market.qqq_sma200
    if index == 0:
        price = sma50 * 0.99 if sma50 else None
        label = (
            f"리스크 축소: QQQ가 50일선 ${sma50:,.2f} 대비 -1% 이하(${price:,.2f})로 이탈하거나 "
            "50일선 아래 2거래일 연속 마감할 때 일부 매도"
            if sma50
            else "50일선 데이터가 필요합니다"
        )
    elif index == 1:
        price = sma200
        label = f"방어 전환: QQQ가 200일선 ${sma200:,.2f} 아래로 2거래일 연속 마감"
    else:
        price = sma200 * 1.25
        label = f"수익 회수: QQQ가 200일선 대비 +25% 수준 ${price:,.2f} 이상"
    return {"price": price, "label": label, "distance": _price_distance(current, price)}


def _buy_step_status(strategy: ManagedStrategy, index: int, step: str, distance: float) -> tuple[str, str]:
    close = strategy.market.qqq_close
    sma20 = getattr(strategy.market, "qqq_sma20", None)
    sma50 = strategy.market.qqq_sma50
    target_symbol = "TQQQ" if _allocation_ratio(strategy, "TQQQ") else "QLD"
    target_amount = _allocation_amount(strategy, target_symbol)
    executed_amount = _executed_amounts(strategy).get(target_symbol, 0)
    progress = executed_amount / target_amount * 100 if target_amount else 0
    if _has_journal_marker(strategy, "buy", step):
        return "done", "이미 기록장에 실행 기록이 있습니다."
    if distance <= 0:
        return "blocked", "QQQ가 200일선 아래라 신규 레버리지 매수는 금지합니다."
    if distance >= 15:
        return "blocked", "QQQ 200일선 대비 +15% 이상에서는 신규 TQQQ/QLD 분할매수를 금지합니다. QQQM/SPYM 1x 완충과 기존 보유 관리가 우선입니다."
    if index == 0:
        if distance > 8:
            return "ready", "QQQ가 200일선 위지만 이격이 +8%를 넘어 1차는 축소 진입만 허용합니다."
        return "ready", "QQQ가 200일선 위이고 이격이 +8% 이하라 1차 분할매수 조건을 검토할 수 있습니다."
    if index == 1:
        if progress < 10:
            return "wait", "2차는 1차가 최소 10% 이상 집행된 뒤에만 검토합니다. 순서를 건너뛰지 않습니다."
        if sma20 and close <= sma20 * 1.01:
            return "ready", "QQQ가 20일선 근처로 눌려 2차 분할매수 후보입니다."
        if distance <= 8:
            return "ready", "QQQ 200일선 이격도가 완화되어 2차 분할매수 후보입니다."
        return "wait", "2차 TQQQ는 조건 전까지 보류합니다. 미집행분은 무기한 현금 대기가 아니라 1x 완충 또는 SGOV/CASH 역할로 관리합니다."
    if progress < 45:
        return "wait", "3차는 1차와 2차가 합쳐 최소 45% 이상 집행된 뒤에만 검토합니다. 깊은 눌림 전 예비 현금을 보존합니다."
    if sma50 and close < sma50:
        return "blocked", "QQQ가 50일선 아래라 3차 매수보다 리스크 축소 판단이 우선입니다."
    if sma50 and close <= sma50 * 1.01:
        return "wait", "QQQ가 50일선 바로 위 1% 이내라 3차 매수와 리스크 축소 신호가 충돌할 수 있습니다. 50일선 방어 확인 전까지 보류합니다."
    if distance <= 5:
        return "ready", "QQQ가 200일선에 가까워져 마지막 분할매수 조건을 검토할 수 있습니다."
    if sma50 and close <= sma50 * 1.02:
        return "ready", "QQQ가 50일선을 아직 방어한 +1~+2% 깊은 눌림 구간이라 마지막 분할매수 후보입니다."
    return "wait", "3차 TQQQ는 깊은 눌림 또는 이격 완화 때만 검토합니다. 조건이 없으면 추가 레버리지보다 1x 완충 유지가 원칙입니다."


def _buy_step_amount(strategy: ManagedStrategy, index: int, planned_amount: float, distance: float, status: str) -> float:
    if status != "ready":
        return 0
    target_symbol = "TQQQ" if _allocation_ratio(strategy, "TQQQ") else "QLD"
    target_amount = _allocation_amount(strategy, target_symbol)
    if index == 0 and distance > 8:
        return min(planned_amount, target_amount * 0.15)
    return planned_amount


def _sell_step_status(strategy: ManagedStrategy, index: int, step: str, distance: float) -> tuple[str, str]:
    if _has_journal_marker(strategy, "sell", step):
        return "done", "이미 기록장에 실행 기록이 있습니다."
    if index == 0 and strategy.market.qqq_sma50:
        if strategy.market.qqq_close <= strategy.market.qqq_sma50 * 0.99:
            return "ready", "QQQ가 50일선 대비 -1% 이하로 이탈해 일부 감축을 검토합니다."
        if strategy.market.qqq_close < strategy.market.qqq_sma50:
            return "wait", "QQQ가 50일선 아래지만 -1% 이탈은 아닙니다. 2거래일 연속 이탈 확인 전까지 성급한 매도를 피합니다."
    if index == 1 and distance <= 0:
        return "ready", "QQQ가 200일선 아래라 방어 전환을 검토합니다. 2거래일 확인이면 강제 실행입니다."
    if index >= 2 and distance >= 25:
        return "ready", "QQQ가 200일선 대비 +25% 이상이라 일부 이익실현을 검토합니다."
    return "wait", "현재는 해당 매도 조건이 충족되지 않았습니다."


def _has_journal_marker(strategy: ManagedStrategy, action: str, step: str) -> bool:
    marker = step.lower()
    return any(
        entry.entry_type == action and (marker in entry.reason.lower() or marker in entry.note.lower())
        for entry in strategy.journal
    )


def _action_label(side: str, status: str, amount: float) -> str:
    if status == "ready":
        action = "매수" if side == "buy" else "매도"
        return f"{action} 후보 {amount:,.0f}원"
    if status == "done":
        return "실행 완료"
    if status == "blocked":
        return "실행 금지"
    return "대기"






