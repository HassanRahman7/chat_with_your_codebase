import { BrowserRouter, Route, Routes } from "react-router-dom";

import { DashboardPage } from "./pages/DashboardPage";
import { LandingPage } from "./pages/LandingPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { RepositoryPage } from "./pages/RepositoryPage";
import { RepositoryWorkspacePage } from "./pages/RepositoryWorkspacePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/repositories/:repositoryId" element={<RepositoryPage />} />
        <Route path="/repositories/:repositoryId/workspace" element={<RepositoryWorkspacePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
