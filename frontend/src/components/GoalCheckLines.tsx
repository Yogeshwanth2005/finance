import { crashLine, goalLine } from "@/lib/goalText";
import type { GoalCheck } from "@/lib/types";

export default function GoalCheckLines({ goal }: { goal: GoalCheck }) {
  return (
    <div className="mt-4 space-y-1.5 border-t border-[#eddcbb] pt-4 text-[11px] leading-5 text-[#5c5f66]">
      <p data-testid="investment-goal-line">{goalLine(goal)}</p>
      <p data-testid="investment-crash-line">{crashLine(goal)}</p>
    </div>
  );
}
