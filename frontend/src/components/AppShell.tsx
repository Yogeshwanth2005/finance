import { Link, useLocation } from "react-router-dom";
import { BarChart3, HeartHandshake, Languages, LockKeyhole, LogOut, ShieldCheck, Sparkles, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

const navItems = [
  { to: "/", label: "Profile", icon: Sparkles, testId: "nav-profile-wizard-link" },
  { to: "/dashboard", label: "Dashboard", icon: BarChart3, testId: "nav-dashboard-link" },
  { to: "/insurance", label: "Insurance", icon: ShieldCheck, testId: "nav-insurance-plans-link" },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { language, languageOptions, setLanguage, t } = useI18n();
  const visibleNavItems = user?.role === "admin" ? [] : user?.profile_complete ? navItems : navItems.filter((item) => item.to === "/");

  const signOut = async () => {
    try {
      await logout();
      toast.success("You are signed out");
    } catch {
      toast.error("Could not sign out. Please try again.");
    }
  };

  return (
    <div className="min-h-svh bg-[#f8f7f4] text-[#17181c]">
      <header className="sticky top-0 z-30 border-b border-[#e4e1d8]/90 bg-[#f8f7f4]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <Link to={user?.role === "admin" ? "/admin/documents" : "/"} className="flex items-center gap-3" data-testid="header-brand-logo">
            <span className="flex size-9 items-center justify-center rounded-xl bg-[#0d7a5f] text-white shadow-[0_8px_18px_rgba(13,122,95,0.2)]">
              <HeartHandshake className="size-5" />
            </span>
            <span className="hidden sm:block">
              <span className="block font-heading text-sm font-bold tracking-tight">SurakshaCFO</span>
              <span className="block text-[10px] font-medium uppercase tracking-[0.18em] text-[#8a8f99]">{t("familyEngine")}</span>
            </span>
          </Link>

          <nav className="flex items-center gap-1 rounded-xl border border-[#e4e1d8] bg-white/70 p-1" data-testid="main-navigation">
            {visibleNavItems.map(({ to, label, icon: Icon, testId }) => (
              <Link
                key={to}
                to={to}
                data-testid={testId}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${location.pathname === to ? "bg-[#17181c] text-white" : "text-[#5c5f66] hover:bg-[#f1efe9] hover:text-[#17181c]"}`}
              >
                <Icon className="size-3.5" />
                <span className="hidden md:inline">{t(label.toLowerCase())}</span>
              </Link>
            ))}
            {user?.role === "admin" && <Link to="/admin/documents" data-testid="nav-admin-documents-link" className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${location.pathname === "/admin/documents" ? "bg-[#17181c] text-white" : "text-[#5c5f66] hover:bg-[#f1efe9] hover:text-[#17181c]"}`}><LockKeyhole className="size-3.5" /><span className="hidden md:inline">Admin</span></Link>}
          </nav>

          <div className="flex items-center gap-2" data-testid="header-status-cluster">
            <span className="hidden rounded-full border border-[#d7ebe4] bg-[#eaf6f1] px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[#0d7a5f] sm:inline">{t("indiaInr")}</span>
            <span className="hidden text-xs font-semibold text-[#5c5f66] lg:inline" data-testid="header-user-name">{user?.name}</span>
            <label className="relative flex h-8 items-center rounded-lg border border-[#e4e1d8] bg-white pl-7 pr-1 text-[#5c5f66]" data-testid="header-language-control"><Languages className="pointer-events-none absolute left-2 size-3.5" /><select value={language} onChange={(event) => void setLanguage(event.target.value as typeof language)} className="h-full bg-transparent text-[10px] font-bold outline-none" aria-label={t("language")} data-testid="header-language-select">{languageOptions.map((option) => <option key={option.value} value={option.value}>{option.short}</option>)}</select></label>
            {user?.role !== "admin" && <Link to="/account" className={`flex size-8 items-center justify-center rounded-lg border border-[#e4e1d8] bg-white transition-colors hover:bg-[#f1efe9] ${location.pathname === "/account" ? "text-[#0d7a5f]" : "text-[#5c5f66]"}`} aria-label={t("settings")} data-testid="user-profile-settings-button"><UserRound className="size-3.5" /></Link>}
            <button type="button" onClick={signOut} className="flex size-8 items-center justify-center rounded-lg border border-[#e4e1d8] bg-white text-[#5c5f66] transition-colors hover:bg-[#f1efe9] hover:text-[#17181c]" aria-label={t("signOut")} data-testid="logout-button"><LogOut className="size-3.5" /></button>
          </div>
        </div>
      </header>
      <main>{children}</main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 pt-4 text-center text-[11px] text-[#8a8f99] sm:px-6 lg:px-8" data-testid="app-disclaimer-footer">
        {t("footer")}
      </footer>
    </div>
  );
}