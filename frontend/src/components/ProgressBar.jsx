import React from "react";

/** Seed-to-harvest progress: a calm red-to-green gradient bar. Overdue task
 * alerts are shown separately (a badge) so the two kinds of "red" never
 * mean the same thing on screen at once. */
export default function ProgressBar({ percent, color }) {
  return (
    <div className="progress-track" title={`${percent}% of the way to expected harvest`}>
      <div className="progress-fill" style={{ width: `${percent}%`, backgroundColor: color }} />
    </div>
  );
}
