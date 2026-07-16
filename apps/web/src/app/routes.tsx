import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { RouteLoading } from "../components/RouteLoading";

const ComparePage = lazy(() => import("../pages/ComparePage").then((module) => ({ default: module.ComparePage })));
const HomePage = lazy(() => import("../pages/HomePage").then((module) => ({ default: module.HomePage })));
const InfoPage = lazy(() => import("../pages/InfoPage").then((module) => ({ default: module.InfoPage })));
const ManagementPage = lazy(() => import("../pages/ManagementPage").then((module) => ({ default: module.ManagementPage })));
const RulesPage = lazy(() => import("../pages/RulesPage").then((module) => ({ default: module.RulesPage })));
const StrategyPage = lazy(() => import("../pages/StrategyPage").then((module) => ({ default: module.StrategyPage })));
const UniversePage = lazy(() => import("../pages/UniversePage").then((module) => ({ default: module.UniversePage })));
const NotFoundPage = lazy(() => import("../pages/NotFoundPage").then((module) => ({ default: module.NotFoundPage })));

export function AppRoutes() {
  return (
    <Suspense fallback={<RouteLoading label="화면을 불러오는 중입니다" />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/strategy" element={<StrategyPage />} />
        <Route path="/lab" element={<ComparePage />} />
        <Route path="/info" element={<InfoPage />} />
        <Route path="/compare" element={<Navigate to="/lab" replace />} />
        <Route path="/manage" element={<ManagementPage />} />
        <Route path="/universe" element={<UniversePage />} />
        <Route path="/rules" element={<RulesPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
