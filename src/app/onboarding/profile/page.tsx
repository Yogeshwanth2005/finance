"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  initialWizardState,
  validateScreen2,
  validateScreen3,
  validateScreen4,
  validateScreen5,
  ScreenPersonalBasics,
  ScreenIncomeSavings,
  ScreenDebts,
  ScreenInsuranceCover,
  ScreenReviewConsent,
  type WizardState,
  type FieldErrors,
} from "./screens";

const STEP_TITLES = [
  "Personal basics",
  "Income & savings",
  "Existing debts",
  "Insurance cover",
  "Review & consent",
];

export default function OnboardingProfilePage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [state, setState] = useState<WizardState>(initialWizardState);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onChange = (patch: Partial<WizardState>) => setState((s) => ({ ...s, ...patch }));

  const validators: Array<(s: WizardState) => FieldErrors> = [
    validateScreen2,
    validateScreen3,
    validateScreen4,
    validateScreen5,
    () => ({}),
  ];

  function goNext() {
    const stepErrors = validators[step](state);
    setErrors(stepErrors);
    if (Object.keys(stepErrors).length > 0) return;
    setStep((s) => Math.min(s + 1, STEP_TITLES.length - 1));
  }

  function goBack() {
    setErrors({});
    setStep((s) => Math.max(s - 1, 0));
  }

  async function submit() {
    if (!state.consentGiven) {
      setErrors({ consent: "Consent is required to continue." });
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await fetch("/api/onboarding/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          age: Number(state.age),
          dependentsCount: Number(state.dependentsCount),
          riskTolerance: state.riskTolerance,
          investmentHorizonYears: Number(state.investmentHorizonYears),
          monthlyIncome: Number(state.monthlyIncome),
          monthlyExpenses: Number(state.monthlyExpenses),
          currentSavings: Number(state.currentSavings),
          debts: state.debts.map((d) => ({
            label: d.label,
            outstandingAmount: Number(d.outstandingAmount),
            interestRatePct: Number(d.interestRatePct),
            tenureMonths: Number(d.tenureMonths),
          })),
          existingTermCoverAmount: Number(state.existingTermCoverAmount),
          personalHealthCoverAmount: Number(state.personalHealthCoverAmount),
          employerHealthCoverAmount: Number(state.employerHealthCoverAmount),
        }),
      });
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      router.push("/dashboard");
    } catch {
      setSubmitError("Something went wrong submitting your profile. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl px-6 py-20 sm:py-28">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">
        fin — profile ({step + 1} of {STEP_TITLES.length})
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        {STEP_TITLES[step]}
      </h1>

      <div className="mt-8">
        {step === 0 && <ScreenPersonalBasics state={state} errors={errors} onChange={onChange} />}
        {step === 1 && <ScreenIncomeSavings state={state} errors={errors} onChange={onChange} />}
        {step === 2 && <ScreenDebts state={state} errors={errors} onChange={onChange} />}
        {step === 3 && <ScreenInsuranceCover state={state} errors={errors} onChange={onChange} />}
        {step === 4 && (
          <ScreenReviewConsent state={state} consentError={errors.consent} onChange={onChange} />
        )}
      </div>

      {submitError && (
        <p className="mt-4 text-sm text-red-600 dark:text-red-400">{submitError}</p>
      )}

      <div className="mt-10 flex gap-3">
        {step > 0 && (
          <button
            type="button"
            onClick={goBack}
            disabled={submitting}
            className="flex-1 rounded-md border border-zinc-300 px-4 py-3 text-sm font-medium text-zinc-700 dark:border-zinc-700 dark:text-zinc-300"
          >
            Back
          </button>
        )}
        {step < STEP_TITLES.length - 1 ? (
          <button
            type="button"
            onClick={goNext}
            className="flex-1 rounded-md bg-accent px-4 py-3 text-sm font-medium text-accent-contrast"
          >
            Next
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={submitting}
            className="flex-1 rounded-md bg-accent px-4 py-3 text-sm font-medium text-accent-contrast disabled:opacity-60"
          >
            {submitting ? "Submitting..." : "Submit"}
          </button>
        )}
      </div>
    </div>
  );
}
