import Link from "next/link";

export default function OnboardingProfilePage() {
  return (
    <div className="mx-auto max-w-xl px-6 py-20 sm:py-28">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">
        fin — profile
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Not built yet
      </h1>
      <p className="mt-4 max-w-[58ch] text-sm leading-7 text-zinc-600 dark:text-zinc-400">
        The income, expenses, debt, and insurance questions that feed the
        gap analysis live here next.
      </p>
      <Link
        href="/onboarding"
        className="mt-8 inline-block text-sm font-medium text-accent underline underline-offset-4"
      >
        Back
      </Link>
    </div>
  );
}
