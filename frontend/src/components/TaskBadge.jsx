import React from "react";

export default function TaskBadge({ task }) {
  if (!task) return <span className="task-badge task-badge-done">Done</span>;
  return (
    <span className={task.overdue ? "task-badge task-badge-overdue" : "task-badge task-badge-upcoming"}>
      {task.overdue ? "Overdue: " : "Due "}
      {task.label} ({task.due_date})
    </span>
  );
}
