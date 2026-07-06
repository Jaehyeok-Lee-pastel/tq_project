import { ComparePage } from "../pages/ComparePage";
import { InfoPage } from "../pages/InfoPage";
import { ManagementPage } from "../pages/ManagementPage";
import { Route, Routes } from "react-router-dom";
import { RulesPage } from "../pages/RulesPage";
import { SimulationPage } from "../pages/SimulationPage";
import { StrategyPage } from "../pages/StrategyPage";
import { UniversePage } from "../pages/UniversePage";
import { NotFoundPage } from "../pages/NotFoundPage";

export function AppRoutes() {
  return (
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
  );
}
