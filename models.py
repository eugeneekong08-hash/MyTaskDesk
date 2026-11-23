from datetime import datetime
from typing import Optional, List
import sqlite3

class Task:
    """Models a single task (academic, work, or personal)."""
    
    def __init__(
        self,
        title: str,
        due_date: str,
        due_time: str = "00:00",
        category: str = "Academic",
        priority: str = "Medium",
        details: str = "",
        status: str = "Pending",
        reminder_set: bool = False,
        task_id: Optional[int] = None,
        username: str = ""
    ):
        self.id = task_id
        self.username = username
        self.title = title
        self.due_date = due_date
        self.due_time = due_time
        self.category = category
        self.priority = priority
        self.details = details
        self.status = status
        self.reminder_set = reminder_set

    def mark_complete(self):
        self.status = "Completed"

    def __str__(self):
        return f"{self.title} | Due: {self.due_date} {self.due_time} | {self.priority} | {self.status}"


class Expense:
    """Models a single expense record."""
    
    def __init__(
        self,
        amount: float,
        category: str,
        date: str,
        username: str = "",
        expense_id: Optional[int] = None
    ):
        self.id = expense_id
        self.username = username
        self.amount = amount
        self.category = category
        self.date = date

    def __str__(self):
        return f"{self.date} | ₦{self.amount:.2f} | {self.category}"


class TaskService:
    """
    Uses composition: it works with Task objects and handles
    database operations, instead of Task inheriting database logic.
    """
    
    def __init__(self, db_path: str = "mytaskdesk.db"):
        self.db_path = db_path

    def save(self, task: Task) -> int:
        """Save a Task object and return its new ID."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO tasks 
               (username, title, due_date, due_time, category, priority, details, status, reminder_set)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task.username, task.title, task.due_date, task.due_time,
             task.category, task.priority, task.details, task.status, int(task.reminder_set))
        )
        task_id = c.lastrowid
        conn.commit()
        conn.close()
        return task_id

    def get_tasks(self, username: str, status: str = "all") -> List[Task]:
        """Return a list of Task objects."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if status == "all":
            c.execute("SELECT * FROM tasks WHERE username = ?", (username,))
        else:
            c.execute("SELECT * FROM tasks WHERE username = ? AND status = ?", (username, status))
        
        rows = c.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            tasks.append(Task(
                task_id=row[0],
                username=row[1],
                title=row[2],
                due_date=row[3],
                due_time=row[4] or "00:00",
                category=row[5],
                priority=row[6],
                details=row[7],
                status=row[8],
                reminder_set=bool(row[9])
            ))
        return tasks