import { formatInr } from "../../lib/format.js";

export const initialWizardState = {
  age: "",
  dependentsCount: "0",
  riskTolerance: "moderate",
  investmentHorizonYears: "",
  monthlyIncome: "",
  monthlyExpenses: "",
  currentSavings: "",
  debts: [],
  existingTermCoverAmount: "0",
  personalHealthCoverAmount: "0",
  employerHealthCoverAmount: "0",
  consentGiven: false,
};

function Field({ label, error, children }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{label}</span>
      <div className="mt-1.5">{children}</div>
      {error && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </label>
  );
}

const inputClass =
  "w-full rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm text-zinc-900 outline-none focus:border-accent focus:ring-1 focus:ring-accent dark:border-zinc-700 dark:text-zinc-50";

export function validateScreen2(s) {
  const errors = {};
  const age = Number(s.age);
  if (!s.age || age < 18 || age > 100) errors.age = "Enter an age between 18 and 100.";
  if (Number(s.dependentsCount) < 0) errors.dependentsCount = "Cannot be negative.";
  const horizon = Number(s.investmentHorizonYears);
  if (!s.investmentHorizonYears || horizon < 1) errors.investmentHorizonYears = "Enter at least 1 year.";
  return errors;
}

export function validateScreen3(s) {
  const errors = {};
  if (!s.monthlyIncome || Number(s.monthlyIncome) < 0) errors.monthlyIncome = "Enter a non-negative amount.";
  if (!s.monthlyExpenses || Number(s.monthlyExpenses) < 0) errors.monthlyExpenses = "Enter a non-negative amount.";
  if (!s.currentSavings || Number(s.currentSavings) < 0) errors.currentSavings = "Enter a non-negative amount.";
  return errors;
}

export function validateScreen4(s) {
  const errors = {};
  s.debts.forEach((debt) => {
    if (!debt.label.trim()) errors[`${debt.key}-label`] = "Enter a label.";
    if (Number(debt.outstandingAmount) < 0) errors[`${debt.key}-amount`] = "Cannot be negative.";
    if (Number(debt.interestRatePct) < 0) errors[`${debt.key}-rate`] = "Cannot be negative.";
    if (Number(debt.tenureMonths) < 1) errors[`${debt.key}-tenure`] = "Enter at least 1 month.";
  });
  return errors;
}

export function validateScreen5(s) {
  const errors = {};
  if (Number(s.existingTermCoverAmount) < 0) errors.existingTermCoverAmount = "Cannot be negative.";
  if (Number(s.personalHealthCoverAmount) < 0) errors.personalHealthCoverAmount = "Cannot be negative.";
  if (Number(s.employerHealthCoverAmount) < 0) errors.employerHealthCoverAmount = "Cannot be negative.";
  return errors;
}

export function ScreenPersonalBasics({ state, errors, onChange }) {
  return (
    <div className="space-y-5">
      <Field label="Age" error={errors.age}>
        <input type="number" className={inputClass} value={state.age} onChange={(e) => onChange({ age: e.target.value })} />
      </Field>
      <Field label="Number of dependents" error={errors.dependentsCount}>
        <input type="number" className={inputClass} value={state.dependentsCount} onChange={(e) => onChange({ dependentsCount: e.target.value })} />
      </Field>
      <Field label="Risk tolerance">
        <div className="flex gap-4">
          {["conservative", "moderate", "aggressive"].map((option) => (
            <label key={option} className="flex items-center gap-2 text-sm capitalize">
              <input
                type="radio"
                name="riskTolerance"
                checked={state.riskTolerance === option}
                onChange={() => onChange({ riskTolerance: option })}
              />
              {option}
            </label>
          ))}
        </div>
      </Field>
      <Field label="Investment horizon (years)" error={errors.investmentHorizonYears}>
        <input type="number" className={inputClass} value={state.investmentHorizonYears} onChange={(e) => onChange({ investmentHorizonYears: e.target.value })} />
      </Field>
    </div>
  );
}

export function ScreenIncomeSavings({ state, errors, onChange }) {
  return (
    <div className="space-y-5">
      <Field label="Monthly income (₹)" error={errors.monthlyIncome}>
        <input type="number" className={inputClass} value={state.monthlyIncome} onChange={(e) => onChange({ monthlyIncome: e.target.value })} />
      </Field>
      <Field label="Monthly expenses (₹)" error={errors.monthlyExpenses}>
        <input type="number" className={inputClass} value={state.monthlyExpenses} onChange={(e) => onChange({ monthlyExpenses: e.target.value })} />
      </Field>
      <Field label="Current savings (₹)" error={errors.currentSavings}>
        <input type="number" className={inputClass} value={state.currentSavings} onChange={(e) => onChange({ currentSavings: e.target.value })} />
      </Field>
    </div>
  );
}

let debtKeyCounter = 0;
function newDebtRow() {
  debtKeyCounter += 1;
  return { key: `debt-${debtKeyCounter}`, label: "", outstandingAmount: "", interestRatePct: "", tenureMonths: "" };
}

export function ScreenDebts({ state, errors, onChange }) {
  const updateDebt = (key, patch) => {
    onChange({ debts: state.debts.map((d) => (d.key === key ? { ...d, ...patch } : d)) });
  };
  const removeDebt = (key) => {
    onChange({ debts: state.debts.filter((d) => d.key !== key) });
  };

  return (
    <div className="space-y-6">
      {state.debts.length === 0 && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">No debts added — that's valid.</p>
      )}
      {state.debts.map((debt) => (
        <div key={debt.key} className="space-y-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
          <Field label="Label" error={errors[`${debt.key}-label`]}>
            <input type="text" className={inputClass} value={debt.label} onChange={(e) => updateDebt(debt.key, { label: e.target.value })} placeholder="e.g. Car loan" />
          </Field>
          <Field label="Outstanding amount (₹)" error={errors[`${debt.key}-amount`]}>
            <input type="number" className={inputClass} value={debt.outstandingAmount} onChange={(e) => updateDebt(debt.key, { outstandingAmount: e.target.value })} />
          </Field>
          <Field label="Interest rate (%)" error={errors[`${debt.key}-rate`]}>
            <input type="number" className={inputClass} value={debt.interestRatePct} onChange={(e) => updateDebt(debt.key, { interestRatePct: e.target.value })} />
          </Field>
          <Field label="Tenure (months)" error={errors[`${debt.key}-tenure`]}>
            <input type="number" className={inputClass} value={debt.tenureMonths} onChange={(e) => updateDebt(debt.key, { tenureMonths: e.target.value })} />
          </Field>
          <button type="button" onClick={() => removeDebt(debt.key)} className="text-xs font-medium text-red-600 underline underline-offset-4 dark:text-red-400">
            Remove
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange({ debts: [...state.debts, newDebtRow()] })} className="text-sm font-medium text-accent underline underline-offset-4">
        + Add a debt
      </button>
    </div>
  );
}

export function ScreenInsuranceCover({ state, errors, onChange }) {
  return (
    <div className="space-y-5">
      <Field label="Existing term cover amount (₹)" error={errors.existingTermCoverAmount}>
        <input type="number" className={inputClass} value={state.existingTermCoverAmount} onChange={(e) => onChange({ existingTermCoverAmount: e.target.value })} />
      </Field>
      <Field label="Personal health cover amount (₹)" error={errors.personalHealthCoverAmount}>
        <input type="number" className={inputClass} value={state.personalHealthCoverAmount} onChange={(e) => onChange({ personalHealthCoverAmount: e.target.value })} />
      </Field>
      <Field label="Employer health cover amount (₹)" error={errors.employerHealthCoverAmount}>
        <input type="number" className={inputClass} value={state.employerHealthCoverAmount} onChange={(e) => onChange({ employerHealthCoverAmount: e.target.value })} />
      </Field>
    </div>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div className="flex justify-between border-t border-zinc-100 py-2 text-sm first:border-t-0 dark:border-zinc-800">
      <span className="text-zinc-500 dark:text-zinc-400">{label}</span>
      <span className="font-medium text-zinc-900 dark:text-zinc-50">{value}</span>
    </div>
  );
}

export function ScreenReviewConsent({ state, consentError, onChange }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">Personal basics</h3>
        <SummaryRow label="Age" value={state.age} />
        <SummaryRow label="Dependents" value={state.dependentsCount} />
        <SummaryRow label="Risk tolerance" value={state.riskTolerance} />
        <SummaryRow label="Investment horizon" value={`${state.investmentHorizonYears} years`} />
      </div>
      <div>
        <h3 className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">Income & savings</h3>
        <SummaryRow label="Monthly income" value={formatInr(Number(state.monthlyIncome) || 0)} />
        <SummaryRow label="Monthly expenses" value={formatInr(Number(state.monthlyExpenses) || 0)} />
        <SummaryRow label="Current savings" value={formatInr(Number(state.currentSavings) || 0)} />
      </div>
      <div>
        <h3 className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">Debts</h3>
        {state.debts.length === 0 ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">None</p>
        ) : (
          state.debts.map((d) => (
            <SummaryRow
              key={d.key}
              label={d.label || "(unlabeled)"}
              value={`${formatInr(Number(d.outstandingAmount) || 0)} @ ${d.interestRatePct}%`}
            />
          ))
        )}
      </div>
      <div>
        <h3 className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">Insurance cover</h3>
        <SummaryRow label="Term cover" value={formatInr(Number(state.existingTermCoverAmount) || 0)} />
        <SummaryRow label="Personal health cover" value={formatInr(Number(state.personalHealthCoverAmount) || 0)} />
        <SummaryRow label="Employer health cover" value={formatInr(Number(state.employerHealthCoverAmount) || 0)} />
      </div>
      <label className="flex cursor-pointer gap-3 border-t border-zinc-200 pt-6 text-sm leading-6 text-zinc-700 dark:border-zinc-800 dark:text-zinc-300">
        <input type="checkbox" checked={state.consentGiven} onChange={(e) => onChange({ consentGiven: e.target.checked })} className="mt-0.5 size-4 shrink-0" />
        I consent to this data being used to generate my gap analysis and allocation results, per the DPDP notice.
      </label>
      {consentError && <p className="text-xs text-red-600 dark:text-red-400">{consentError}</p>}
    </div>
  );
}
