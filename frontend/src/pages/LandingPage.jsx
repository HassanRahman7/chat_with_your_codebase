import { AppShell } from "../components/layout/AppShell";
import { FeatureHighlights } from "../components/landing/FeatureHighlights";
import { Hero } from "../components/landing/Hero";
import { SupportedLanguages } from "../components/landing/SupportedLanguages";
import { SystemStatus } from "../components/landing/SystemStatus";
import { WorkflowSteps } from "../components/landing/WorkflowSteps";
import { useSystemHealth } from "../hooks/useSystemHealth";

export function LandingPage() {
  const health = useSystemHealth();

  return (
    <AppShell health={health}>
      <Hero />
      <WorkflowSteps />
      <FeatureHighlights />
      <SupportedLanguages />
      <SystemStatus health={health} />
    </AppShell>
  );
}
