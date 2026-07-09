import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

const ComparePage = lazy(() => import("../pages/ComparePage").then((module) => ({ default: module.ComparePage })));
const InfoPage = lazy(() => import("../pages/InfoPage").then((module) => ({ default: module.InfoPage })));
const ManagementPage = lazy(() => import("../pages/ManagementPage").then((module) => ({ default: module.ManagementPage })));
const RulesPage = lazy(() => import("../pages/RulesPage").then((module) => ({ default: module.RulesPage })));
const SimulationPage = lazy(() => import("../pages/SimulationPage").then((module) => ({ default: module.SimulationPage })));
const StrategyPage = lazy(() => import("../pages/StrategyPage").then((module) => ({ default: module.StrategyPage })));
const UniversePage = lazy(() => import("../pages/UniversePage").then((module) => ({ default: module.UniversePage })));
const NotFoundPage = lazy(() => import("../pages/NotFoundPage").then((module) => ({ default: module.NotFoundPage })));

export function AppRoutes() {
  return (
    <Suspense fallback={<div className="route-loading">화면을 불러오는 중입니다.</div>}>
      <Routes>
        <Route path="/" element={<StrategyPage />} />
        <Route path="/lab" element={<SimulationPage />} />
        <Route path="/info" element={<InfoPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/manage" element={<ManagementPage />} />
        <Route path="/universe" element={<UniversePage />} />
        <Route path="/rules" element={<RulesPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
