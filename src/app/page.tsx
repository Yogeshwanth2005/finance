import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center justify-center gap-6 px-6 py-24 text-center sm:py-32">
      <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-4xl">
        Financial Planning Demo
      </h1>
      <p className="text-base leading-7 text-zinc-600 dark:text-zinc-400">
        A personal/portfolio demo project that walks through emergency fund
        coverage, debt prioritization, insurance gaps, and asset allocation
        based on the information you provide.
      </p>
      <Link
        href="/onboarding"
        className="mt-2 rounded-md bg-accent px-5 py-2.5 text-sm font-medium text-accent-contrast"
      >
        Start
      </Link>
    </div>
  );
}
