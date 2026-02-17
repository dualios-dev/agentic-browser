"""Task management system for the browser agent.

Tracks multi-step goals, their progress, and history.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .agent import AgentResult


class TaskStatus(Enum):
    """Status of a task."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A user-submitted task for the agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    status: TaskStatus = TaskStatus.QUEUED
    result: AgentResult | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": (
                round((self.completed_at or time.time()) - (self.started_at or self.created_at), 2)
                if self.started_at else None
            ),
            "error": self.error,
        }


class TaskManager:
    """Manages a queue of tasks for the agent.

    Stores task history, handles queuing, and provides
    status updates for the dashboard.
    """

    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        self.history: list[str] = []  # Task IDs in order
        self._current_task_id: str | None = None

    def create_task(self, goal: str) -> Task:
        """Create a new task and add it to the queue."""
        task = Task(goal=goal)
        self.tasks[task.id] = task
        self.history.append(task.id)
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    @property
    def current_task(self) -> Task | None:
        """Get the currently running task."""
        if self._current_task_id:
            return self.tasks.get(self._current_task_id)
        return None

    def start_task(self, task_id: str) -> None:
        """Mark a task as running."""
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            self._current_task_id = task_id

    def complete_task(self, task_id: str, result: AgentResult) -> None:
        """Mark a task as completed with results."""
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
            task.result = result
            task.completed_at = time.time()
            if not result.success:
                task.error = result.summary
            self._current_task_id = None

    def cancel_task(self, task_id: str) -> None:
        """Cancel a task."""
        task = self.tasks.get(task_id)
        if task and task.status in (TaskStatus.QUEUED, TaskStatus.RUNNING):
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            if self._current_task_id == task_id:
                self._current_task_id = None

    def get_all_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get all tasks as dicts, newest first."""
        task_ids = list(reversed(self.history))[:limit]
        return [self.tasks[tid].to_dict() for tid in task_ids if tid in self.tasks]

    def get_status(self) -> dict[str, Any]:
        """Get overall status summary."""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "current_task": self.current_task.to_dict() if self.current_task else None,
        }
