import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("http://localhost:8000/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/managed-strategies")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
      return;
    }
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "E2E offline fixture" })
    });
  });
});

test("primary workflow pages remain reachable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "전략 수립" })).toBeVisible();
  await expect(page.getByPlaceholder("보유 종목과 금액을 입력하세요")).toBeVisible();

  await page.getByRole("link", { name: "오늘 판단" }).click();
  await expect(page.getByRole("heading", { name: /오늘의 행동부터 확인/ })).toBeVisible();

  await page.getByRole("link", { name: "개인연구" }).click();
  await expect(page.getByText("현재 보유와 적립 조건")).toBeVisible();

  await page.getByRole("link", { name: "추가정보" }).click();
  await expect(
    page.getByRole("heading", { name: /핵심 판단에 필요하지 않은 연구 정보/ })
  ).toBeVisible();
});

test("layout has no horizontal overflow", async ({ page }) => {
  for (const path of ["/", "/manage", "/lab", "/info"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(overflow, `${path} horizontal overflow`).toBeLessThanOrEqual(1);
  }
});

test("daily research rule is suggested for matching preferences", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "현금만으로 시작" }).click();
  await page.locator('input[type="number"]').first().fill("1000000");
  await page.getByRole("button", { name: "다음: 위험 성향 정하기" }).click();
  await page.getByRole("button", { name: "큰 변동 감내" }).click();
  await page.getByRole("button", { name: "충분함" }).click();
  await expect(page.getByText("추천 · 7:3 레버리지 일일 · 코어 일괄")).toBeVisible();
});

test("portfolio input produces a rendered strategy recommendation", async ({ page }) => {
  await page.route("http://localhost:8000/strategy/recommend", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_capital: 2_500_000,
        market_regime: "reduced_entry",
        qqq_distance_from_200ma: 12.46,
        current_diagnosis: ["레버리지와 반도체 비중을 함께 점검해야 합니다."],
        candidate_opinions: [],
        plans: [
          {
            id: "e2e-plan",
            title: "테스트 추천 전략",
            summary: "QQQ 200일선 기준으로 레버리지와 대기자금을 관리합니다.",
            allocations: [
              {
                symbol: "TQQQ",
                name: "TQQQ",
                target_ratio: 30,
                target_amount: 750_000,
                role: "공격 엔진"
              },
              {
                symbol: "QQQM",
                name: "QQQM",
                target_ratio: 50,
                target_amount: 1_250_000,
                role: "1x 코어"
              },
              {
                symbol: "CASH",
                name: "현금",
                target_ratio: 20,
                target_amount: 500_000,
                role: "분할매수 대기"
              }
            ],
            actions: [],
            buy_plan: [
              {
                step: "1차 매수",
                trigger: "QQQ 200일선 위",
                ratio_of_target: 30,
                amount: 225_000,
                note: "조건 확인"
              }
            ],
            sell_plan: [
              {
                step: "방어 전환",
                trigger: "QQQ 200일선 이탈",
                ratio_of_target: 100,
                amount: 750_000,
                note: "규칙 준수"
              }
            ],
            risk_metrics: [{ label: "예상 낙폭", value: "높음", level: "high" }],
            scores: {
              confidence_score: 82,
              risk_score: 78,
              fit_score: 86,
              expected_return_score: 84,
              execution_difficulty: "medium",
              confidence_breakdown: {
                rule_clarity: 90,
                market_fit: 80,
                cash_defense: 75,
                drawdown_control: 72,
                overfit_resistance: 76,
                execution_quality: 84,
                user_fit: 88
              },
              confidence_notes: ["결정론적 규칙 기반 추천입니다."]
            },
            pros: ["규칙이 명확합니다."],
            cons: ["레버리지 변동성이 큽니다."],
            execution_style: "daily"
          }
        ],
        coach_report: {
          headline: "과열 추격보다 규칙 기반 진입이 우선입니다.",
          diagnosis: "현재 자산과 위험 허용도를 함께 반영했습니다.",
          recommended_plan_id: "e2e-plan",
          why: ["현금 20%를 유지합니다."],
          next_actions: ["분할매수 조건을 확인하세요."],
          warnings: ["수익을 보장하지 않습니다."],
          monitoring_rules: ["QQQ 200일선을 확인하세요."]
        },
        ai_used: false
      })
    });
  });

  await page.goto("/");
  await page
    .getByPlaceholder("보유 종목과 금액을 입력하세요")
    .fill("QLD 150만원, ACE K반도체TOP2 100만원");
  await page.getByRole("button", { name: "반영" }).click();
  await page.getByRole("button", { name: "다음: 위험 성향 정하기" }).click();
  await expect(page.getByText("3가지만 고르면 됩니다")).toBeVisible();
  await page.getByRole("button", { name: "답변으로 위험 한도 적용" }).click();
  await expect(page.getByText("45 / 100")).toBeVisible();
  await page.getByRole("button", { name: "레버리지 일일 · 코어 일괄 3개 비교" }).click();

  await expect(page.getByText("테스트 추천 전략").first()).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "과열 추격보다 규칙 기반 진입이 우선입니다." }).first()
  ).toBeVisible();
  await expect(page.getByText("TQQQ").first()).toBeVisible();
  await expect(page.getByText("30.0%").first()).toBeVisible();
  await expect(page.getByText("1·2·3차 매수 없음")).toBeVisible();
  await expect(page.getByLabel("QQQ 200일선 대비 시장 위치")).toBeVisible();
  await expect(page.getByText("데이터·검증·한계 확인")).toBeVisible();
  const adoptionCheckbox = page.getByRole("checkbox");
  const adoptionButton = page.getByRole("button", { name: "이 전략 채택", exact: true });
  await expect(adoptionCheckbox).toBeVisible();
  await expect(adoptionButton).toBeDisabled();
  await adoptionCheckbox.check();
  await expect(adoptionButton).toBeEnabled();
  await page.getByRole("button", { name: "연구실에서 검증" }).click();
  await expect(page.getByText("추천안에서 불러옴")).toBeVisible();
await expect(page.getByText("테스트 추천 전략", { exact: true })).toBeVisible();
});
