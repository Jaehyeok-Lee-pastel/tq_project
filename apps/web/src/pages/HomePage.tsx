import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { fetchJson } from "../features/management/api";
import type { ManagedStrategy } from "../features/management/types";

export function HomePage() {
  const [destination, setDestination] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetchJson<ManagedStrategy[]>("/managed-strategies")
      .then((strategies) => {
        const hasActiveStrategy = strategies.some((strategy) => strategy.status === "active");
        if (active) setDestination(hasActiveStrategy ? "/manage" : "/strategy");
      })
      .catch(() => {
        if (active) setDestination("/strategy");
      });
    return () => {
      active = false;
    };
  }, []);

  if (destination) return <Navigate to={destination} replace />;
  return <div className="route-loading">내 투자 화면을 준비하고 있습니다.</div>;
}
