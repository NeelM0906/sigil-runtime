"""
Task Board Integration — log_task() utility.

Any script or agent can call log_task() to add/update tasks on the
Mission Control task board. Tasks persist to the shared JSON file
that the dashboard reads.

Usage:
    from bomba_sr.tools.taskboard import log_task, update_task, get_tasks

    # Create a new task
    task = log_task(
        title="Implement feature X",
        description="Details here...",
        priority="high",
        assignees=["prime", "callie"],
        status="backlog",
    )

    # Update existing task
    update_task("task-abc123", status="in_progress")

    # Get all tasks
    tasks = get_tasks()
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

# Default task board data file location (relative to project root)
_DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'mission-control', 'data', 'tasks.json'
)
_DATA_PATH = os.environ.get('BOMBA_TASKBOARD_PATH', _DEFAULT_DATA_PATH)
_lock = Lock()


def _resolve_path():
    """Resolve the task board data file path."""
    return Path(_DATA_PATH).resolve()


def _load():
    """Load task board data from JSON file."""
    path = _resolve_path()
    if not path.exists():
        return {"tasks": [], "history": []}
    with open(path, 'r') as f:
        return json.load(f)


def _save(data):
    """Save task board data to JSON file."""
    path = _resolve_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def _log_history(data, task_id, action, details=None):
    """Append a history entry."""
    data.setdefault("history", []).append({
        "id": uuid.uuid4().hex[:8],
        "taskId": task_id,
        "action": action,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Keep last 500
    if len(data["history"]) > 500:
        data["history"] = data["history"][-500:]


def log_task(
    title,
    description="",
    priority="medium",
    assignees=None,
    status="backlog",
):
    """
    Create a new task on the Mission Control task board.

    Args:
        title: Task title (required)
        description: Task description
        priority: One of 'critical', 'high', 'medium', 'low'
        assignees: List of being IDs (e.g. ['prime', 'callie'])
        status: One of 'backlog', 'in_progress', 'in_review', 'done'

    Returns:
        dict: The created task object with generated id and timestamps
    """
    if assignees is None:
        assignees = []

    now = datetime.now(timezone.utc).isoformat()
    task = {
        "id": f"task-{uuid.uuid4().hex[:8]}",
        "title": title,
        "description": description,
        "status": status,
        "priority": priority,
        "assignees": assignees,
        "created": now,
        "updated": now,
    }

    with _lock:
        data = _load()
        data["tasks"].append(task)
        _log_history(data, task["id"], "created", {"title": title, "priority": priority})
        _save(data)

    return task


def update_task(task_id, **changes):
    """
    Update an existing task on the board.

    Args:
        task_id: The task ID to update
        **changes: Fields to update (title, description, status, priority, assignees)

    Returns:
        dict: The updated task object, or None if not found
    """
    allowed = {'title', 'description', 'status', 'priority', 'assignees'}
    updates = {k: v for k, v in changes.items() if k in allowed}
    if not updates:
        return None

    with _lock:
        data = _load()
        for task in data["tasks"]:
            if task["id"] == task_id:
                change_details = {}
                for key, new_val in updates.items():
                    old_val = task.get(key)
                    if json.dumps(old_val) != json.dumps(new_val):
                        change_details[key] = {"from": old_val, "to": new_val}
                        task[key] = new_val

                task["updated"] = datetime.now(timezone.utc).isoformat()

                if change_details:
                    action = "status_change" if "status" in change_details else "updated"
                    _log_history(data, task_id, action, change_details)

                _save(data)
                return task

    return None


def delete_task(task_id):
    """
    Delete a task from the board.

    Args:
        task_id: The task ID to delete

    Returns:
        bool: True if deleted, False if not found
    """
    with _lock:
        data = _load()
        for i, task in enumerate(data["tasks"]):
            if task["id"] == task_id:
                removed = data["tasks"].pop(i)
                _log_history(data, task_id, "deleted", {"title": removed["title"]})
                _save(data)
                return True
    return False


def get_tasks(status=None, assignee=None, priority=None):
    """
    Get tasks from the board with optional filters.

    Args:
        status: Filter by status
        assignee: Filter by being ID
        priority: Filter by priority

    Returns:
        list: List of task dicts
    """
    data = _load()
    tasks = data.get("tasks", [])

    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if assignee:
        tasks = [t for t in tasks if assignee in t.get("assignees", [])]
    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]

    return tasks


def get_task_history(task_id=None):
    """
    Get task history entries.

    Args:
        task_id: Optional task ID to filter by

    Returns:
        list: List of history entry dicts
    """
    data = _load()
    history = data.get("history", [])
    if task_id:
        history = [h for h in history if h["taskId"] == task_id]
    return history
