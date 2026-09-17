import { Routes, Route } from "react-router-dom";
import { DisclaimerBanner } from "./components/DisclaimerBanner.jsx";
import Home from "./pages/Home.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import OnboardingWizard from "./pages/onboarding/OnboardingWizard.jsx";
import Dashboard from "./pages/Dashboard.jsx";

export default function App() {
  return (
    <div className="flex min-h-full flex-col">
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/onboarding/profile" element={<OnboardingWizard />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
      <DisclaimerBanner />
    </div>
  );
}
