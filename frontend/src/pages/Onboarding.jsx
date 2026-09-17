import { useId, useState } from "react";
import { useNavigate } from "react-router-dom";

function Clause({ id, part, checked, onChange, children }) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer gap-4 border-t border-black/10 py-6 first:border-t-0 dark:border-white/10"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 size-4 shrink-0 cursor-pointer appearance-none rounded-[3px] border border-zinc-400 checked:border-accent checked:bg-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent dark:border-zinc-600"
        style={{
          backgroundImage: checked
            ? "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='none' stroke='white' stroke-width='2'%3E%3Cpath d='M3.5 8.5l3 3 6-7' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E\")"
            : undefined,
          backgroundSize: "12px 12px",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
        }}
      />
      <span className="text-sm leading-7 text-zinc-700 dark:text-zinc-300">
        <span className="mb-1 block font-mono text-xs text-zinc-400 dark:text-zinc-500">
          {part}
        </span>
        {children}
      </span>
    </label>
  );
}

export default function Onboarding() {
  const navigate = useNavigate();
  const idPrefix = useId();
  const [ackEducational, setAckEducational] = useState(false);
  const [ackDemo, setAckDemo] = useState(false);
  const bothAcknowledged = ackEducational && ackDemo;

  return (
    <div className="mx-auto max-w-xl px-6 pt-20 pb-32 sm:pt-28">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">
        fin — before you start
      </p>
      <h1 className="mt-3 max-w-[20ch] text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Two things to read before you enter any financial details
      </h1>
      <p className="mt-4 max-w-[58ch] text-sm leading-7 text-zinc-600 dark:text-zinc-400">
        Both apply to everything that follows. Check each one once you've read it.
      </p>

      <div className="mt-8">
        <Clause
          id={`${idPrefix}-educational`}
          part="Part A — educational scope"
          checked={ackEducational}
          onChange={setAckEducational}
        >
          This tool provides educational guidance based on information you
          provide. It is not personalized financial or insurance advice.
        </Clause>
        <Clause
          id={`${idPrefix}-demo`}
          part="Part B — project status"
          checked={ackDemo}
          onChange={setAckDemo}
        >
          This is a personal/portfolio demo project, not a live financial or
          insurance service. Any fund or insurance plan examples shown are
          for illustration and are not offers, recommendations, or
          solicitations to buy.
        </Clause>
      </div>

      <button
        type="button"
        disabled={!bothAcknowledged}
        onClick={() => navigate("/onboarding/profile")}
        className="mt-10 w-full rounded-md bg-accent px-4 py-3 text-sm font-medium text-accent-contrast transition-colors disabled:cursor-not-allowed disabled:bg-zinc-200 disabled:text-zinc-400 dark:disabled:bg-zinc-800 dark:disabled:text-zinc-600"
      >
        Continue
      </button>
    </div>
  );
}
