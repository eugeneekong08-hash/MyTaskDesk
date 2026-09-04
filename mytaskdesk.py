import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import sqlite3
import hashlib  # For password hashing
import os
import winsound  # For Windows beep; use playsound for cross-platform with .wav files
from tkcalendar import DateEntry

# Database setup with migration for users and tasks tables
def init_db():
    try:
        conn = sqlite3.connect("mytaskdesk.db")
        c = conn.cursor()
        # Create users table with new schema
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            date_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # Migrate existing users table if necessary
        c.execute('''PRAGMA table_info(users)''')
        columns = [col[1] for col in c.fetchall()]
        if 'username' in columns and 'email' not in columns:  # Old schema detected
            c.execute("ALTER TABLE users RENAME TO temp_users")
            c.execute('''CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                date_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            c.execute("INSERT INTO users (full_name, email, password, date_registered) SELECT username, username || '@default.com', password, CURRENT_TIMESTAMP FROM temp_users")
            c.execute("DROP TABLE temp_users")
            conn.commit()
        # Create tasks table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, title TEXT, due_date TEXT, due_time TEXT, 
                      category TEXT, priority TEXT, details TEXT, status TEXT, reminder_set INTEGER DEFAULT 0)''')
        # Migrate tasks table to add reminder_set and due_time if missing
        c.execute('''PRAGMA table_info(tasks)''')
        columns = [col[1] for col in c.fetchall()]
        if 'reminder_set' not in columns:
            c.execute('''ALTER TABLE tasks ADD COLUMN reminder_set INTEGER DEFAULT 0''')
        if 'due_time' not in columns:
            c.execute('''ALTER TABLE tasks ADD COLUMN due_time TEXT DEFAULT '00:00' ''')
        # Create or verify expenses table
        c.execute('''PRAGMA table_info(expenses)''')
        columns = [col[1] for col in c.fetchall()]
        if not columns or 'category' not in columns:  # Recreate if missing category
            c.execute("DROP TABLE IF EXISTS expenses")  # Warning: This deletes existing expense data
            c.execute('''CREATE TABLE expenses 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, amount REAL, category TEXT, date TEXT)''')
        conn.commit()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to initialize database: {e}")
    finally:
        conn.close()

init_db()

# Load user settings (simplified since sound settings are removed)
def get_user_settings(email):
    try:
        conn = sqlite3.connect("mytaskdesk.db")
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE email = ?", (email,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None  # Return password (hashed) or None
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch user settings: {e}")
        return None

# Save user or task
def save_data(table, data):
    try:
        conn = sqlite3.connect("mytaskdesk.db")
        c = conn.cursor()
        c.execute(f"INSERT INTO {table} VALUES ({','.join(['?' for _ in data])})", data)
        conn.commit()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to save data: {e}")
    finally:
        conn.close()

# Fetch tasks with sorting option
def fetch_tasks(username, category_filter="all", status_filter="all", sort_by="due_date_asc"):
    try:
        conn = sqlite3.connect("mytaskdesk.db")
        c = conn.cursor()
        query = f"SELECT * FROM tasks WHERE username = ?"
        params = [username]
        if category_filter != "all":
            query += " AND category = ?"
            params.append(category_filter)
        if status_filter != "all":
            query += " AND status = ?"
            params.append(status_filter)
        sort_col = sort_by.split('_')[0]
        sort_order = sort_by.split('_')[1].upper()
        if sort_col == "due_date":
            query += f" ORDER BY due_date {sort_order}, due_time {sort_order}"
        elif sort_col == "title":
            query += f" ORDER BY title {sort_order}"
        elif sort_col == "priority":
            query += f" ORDER BY priority {sort_order}"
        c.execute(query, params)
        tasks = c.fetchall()
        conn.close()
        return tasks
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch tasks: {e}")
        return []

# Fetch expenses with totals by category
def fetch_expenses(username):
    try:
        start_date = expense_start_date_var.get()
        end_date = expense_end_date_var.get()
        if not is_valid_date(start_date) or not is_valid_date(end_date):
            return []
        conn = sqlite3.connect("mytaskdesk.db")
        c = conn.cursor()
        c.execute("SELECT category, SUM(amount) as total FROM expenses WHERE username = ? AND date >= ? AND date <= ? GROUP BY category", 
                  (username, start_date, end_date))
        expenses = c.fetchall()
        conn.close()
        return expenses
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch expenses: {e}")
        return []

# Function to switch between frames
def show_frame(frame):
    for child in root.winfo_children():
        if isinstance(child, tk.Frame):
            child.pack_forget()
    frame.pack(fill="both", expand=True)

# Root window setup
root = tk.Tk()
root.title("MyTaskDesk")
root.geometry("650x580")
root.configure(bg="#0a0a0a")

# Fonts and colors
label_font = ("Consolas", 11)
entry_font = ("Consolas", 10)
bg_color = "#0f0f0f"
fg_color = "#ffffff"
accent_color = "#1e90ff"

# Helper functions for date and time
def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def is_valid_time(hour, minute, period):
    try:
        hour = int(hour)
        minute = int(minute)
        if period == "PM" and hour != 12:
            hour += 12
        elif period == "AM" and hour == 12:
            hour = 0
        time_str = f"{hour:02d}:{minute:02d}"
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def convert_to_24_hour(hour, minute, period):
    hour = int(hour)
    minute = int(minute)
    if period == "PM" and hour != 12:
        hour += 12
    elif period == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"

def convert_to_12_hour(time_str):
    try:
        if not time_str or not isinstance(time_str, str) or ':' not in time_str:
            return 12, 0, "AM"
        hour, minute = map(int, time_str.split(":"))
        period = "AM"
        if hour >= 12:
            period = "PM"
            if hour > 12:
                hour -= 12
        elif hour == 0:
            hour = 12
        return hour, minute, period
    except ValueError:
        return 12, 0, "AM"

# Schedule and manage reminders (simplified without sound settings)
def schedule_reminder(task_id, title, due_date, due_time):
    try:
        due_datetime = datetime.strptime(f"{due_date} {due_time}", "%Y-%m-%d %H:%M")
        now = datetime.now()
        time_diff_ms = int((due_datetime - now).total_seconds() * 1000)
        if time_diff_ms > 0:
            root.after(time_diff_ms, lambda: show_reminder(task_id, title, due_datetime))
    except ValueError as e:
        print(f"Error scheduling reminder for task {task_id}: {e}")

def show_reminder(task_id, title, due_datetime):
    now = datetime.now()
    if now >= due_datetime:
        messagebox.showinfo("Reminder", f"Task '{title}' is due now!\n[Press Snooze or OK]", parent=root)
        winsound.Beep(1000, 500)  # Default beep sound
        snooze_window = tk.Toplevel(root)
        snooze_window.title("Snooze")
        snooze_window.geometry("200x100")
        tk.Label(snooze_window, text="Snooze for 5 minutes?", font=entry_font, bg=bg_color, fg=fg_color).pack(pady=10)
        tk.Button(snooze_window, text="Snooze", command=lambda: snooze_reminder(task_id, title, due_datetime, snooze_window), bg=accent_color, fg="white", font=("Consolas", 10, "bold"), relief="flat", bd=0).pack(pady=5)
        tk.Button(snooze_window, text="OK", command=snooze_window.destroy, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), relief="flat", bd=0).pack(pady=5)
    else:
        time_diff_ms = int((due_datetime - now).total_seconds() * 1000)
        if time_diff_ms > 0:
            root.after(time_diff_ms, lambda: show_reminder(task_id, title, due_datetime))

def snooze_reminder(task_id, title, due_datetime, window):
    window.destroy()
    snooze_time = due_datetime + timedelta(minutes=5)
    schedule_reminder(task_id, title, snooze_time.strftime("%Y-%m-%d"), snooze_time.strftime("%H:%M"))

# Load and schedule reminders
def load_reminders():
    try:
        conn = sqlite3.connect("mytaskdesk.db")
        c = conn.cursor()
        c.execute("SELECT id, title, due_date, due_time, reminder_set FROM tasks WHERE username = ? AND reminder_set = 1", (current_user.get(),))
        tasks = c.fetchall()
        for task in tasks:
            schedule_reminder(task[0], task[1], task[2], task[3] if task[3] else "00:00")
        conn.close()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to load reminders: {e}")

# Login/Signup Page with Demo
login_frame = tk.Frame(root, bg=bg_color)
login_frame.pack(fill="both", expand=True)

header_label = tk.Label(login_frame, text="MyTaskDesk", font=("Consolas", 20, "bold"), fg=accent_color, bg=bg_color)
header_label.pack(pady=20)

auth_frame = tk.Frame(login_frame, bg=bg_color, padx=30, pady=30, relief="flat", bd=2, highlightbackground=accent_color, highlightthickness=2)
auth_frame.pack(pady=20)

tk.Label(auth_frame, text="LOGIN", font=("Consolas", 14, "bold"), fg=accent_color, bg=bg_color).grid(row=0, column=0, columnspan=2, pady=10)
tk.Label(auth_frame, text="Email:", font=label_font, bg=bg_color, fg=fg_color).grid(row=1, column=0, sticky="w", pady=5)
email_login_var = tk.StringVar()
tk.Entry(auth_frame, textvariable=email_login_var, width=30, font=entry_font, bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=1, column=1, pady=5)
tk.Label(auth_frame, text="Password:", font=label_font, bg=bg_color, fg=fg_color).grid(row=2, column=0, sticky="w", pady=5)
password_login_var = tk.StringVar()
tk.Entry(auth_frame, textvariable=password_login_var, width=30, font=entry_font, show="*", bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=2, column=1, pady=5)

tk.Label(auth_frame, text="SIGN UP", font=("Consolas", 14, "bold"), fg=accent_color, bg=bg_color).grid(row=3, column=0, columnspan=2, pady=10)
tk.Label(auth_frame, text="Full Name:", font=label_font, bg=bg_color, fg=fg_color).grid(row=4, column=0, sticky="w", pady=5)
full_name_signup_var = tk.StringVar()
tk.Entry(auth_frame, textvariable=full_name_signup_var, width=30, font=entry_font, bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=4, column=1, pady=5)
tk.Label(auth_frame, text="Email:", font=label_font, bg=bg_color, fg=fg_color).grid(row=5, column=0, sticky="w", pady=5)
email_signup_var = tk.StringVar()
tk.Entry(auth_frame, textvariable=email_signup_var, width=30, font=entry_font, bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=5, column=1, pady=5)
tk.Label(auth_frame, text="Password:", font=label_font, bg=bg_color, fg=fg_color).grid(row=6, column=0, sticky="w", pady=5)
password_signup_var = tk.StringVar()
tk.Entry(auth_frame, textvariable=password_signup_var, width=30, font=entry_font, show="*", bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=6, column=1, pady=5)

btn_auth_frame = tk.Frame(auth_frame, bg=bg_color)
btn_auth_frame.grid(row=7, column=0, columnspan=2, pady=20)

def login():
    email = email_login_var.get().strip()
    password = password_login_var.get().strip()
    if not email or not password:
        messagebox.showwarning("Input Error", "Please enter both email and password.")
        return
    stored_password = get_user_settings(email)
    if stored_password and hashlib.sha256(password.encode()).hexdigest() == stored_password:
        current_user.set(email.split('@')[0])  # Use email prefix as username for tasks
        load_reminders()
        update_task_list()  # Update task list immediately after login
        show_frame(profile_frame)
    else:
        messagebox.showerror("Login Failed", "Invalid email or password.")

def signup():
    full_name = full_name_signup_var.get().strip()
    email = email_signup_var.get().strip()
    password = password_signup_var.get().strip()
    if not full_name or not email or not password:
        messagebox.showwarning("Input Error", "Please enter all required fields.")
        return
    conn = sqlite3.connect("mytaskdesk.db")
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE email = ?", (email,))
    if c.fetchone():
        messagebox.showerror("Signup Failed", "Email already exists.")
        conn.close()
        return
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    c.execute("INSERT INTO users (full_name, email, password, date_registered) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", 
              (full_name, email, hashed_password))
    conn.commit()
    conn.close()
    messagebox.showinfo("Success", "Account created! Please log in.")
    full_name_signup_var.set("")
    email_signup_var.set("")
    password_signup_var.set("")

def show_demo():
    show_frame(demo_frame)

tk.Button(btn_auth_frame, text="Login", width=15, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=login, relief="flat", bd=0).pack(side="left", padx=10)
tk.Button(btn_auth_frame, text="Sign Up", width=15, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=signup, relief="flat", bd=0).pack(side="left", padx=10)
tk.Button(btn_auth_frame, text="Try Demo", width=15, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), command=show_demo, relief="flat", bd=0).pack(side="left", padx=10)

# Profile Page
profile_frame = tk.Frame(root, bg=bg_color)
current_user = tk.StringVar()

tk.Label(profile_frame, text="MyTaskDesk", font=("Consolas", 20, "bold"), fg=accent_color, bg=bg_color).pack(pady=20)
profile_inner_frame = tk.Frame(profile_frame, bg=bg_color, padx=30, pady=30, relief="flat", bd=2, highlightbackground=accent_color, highlightthickness=2)
profile_inner_frame.pack(pady=20)

tk.Label(profile_inner_frame, text="Profile", font=("Consolas", 16, "bold"), fg=accent_color, bg=bg_color).pack(pady=10)
tk.Label(profile_inner_frame, textvariable=current_user, font=("Consolas", 14), fg=fg_color, bg=bg_color).pack(pady=10)
tk.Button(profile_inner_frame, text="Go to Add Task", width=20, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=lambda: show_frame(add_task_frame), relief="flat", bd=0).pack(pady=10)
tk.Button(profile_inner_frame, text="Go to Task List", width=20, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=lambda: show_frame(task_list_frame), relief="flat", bd=0).pack(pady=10)
tk.Button(profile_inner_frame, text="Go to Expenses", width=20, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=lambda: show_frame(expense_frame), relief="flat", bd=0).pack(pady=10)
tk.Button(profile_inner_frame, text="Logout", width=20, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), command=lambda: show_frame(login_frame), relief="flat", bd=0).pack(pady=10)

# Add Task Page
add_task_frame = tk.Frame(root, bg=bg_color)

title_var = tk.StringVar()
due_date_var = tk.StringVar()
due_time_hour_var = tk.StringVar(value="12")
due_time_minute_var = tk.StringVar(value="00")
due_time_period_var = tk.StringVar(value="AM")
category_var = tk.StringVar(value="Academic")
priority_var = tk.StringVar(value="Medium")
details_var = tk.StringVar()
status_var = tk.StringVar(value="Pending")
reminder_var = tk.BooleanVar()

def add_task():
    title = title_var.get().strip()
    due_date = due_date_var.get().strip()
    due_time = convert_to_24_hour(due_time_hour_var.get(), due_time_minute_var.get(), due_time_period_var.get())
    category = category_var.get()
    priority = priority_var.get()
    details = details_var.get().strip()
    status = status_var.get()
    reminder = 1 if reminder_var.get() else 0

    if not title:
        messagebox.showwarning("Validation Error", "Task Title is required.")
        return
    if len(title) > 100:
        messagebox.showwarning("Validation Error", "Task Title must be under 100 characters.")
        return
    if not is_valid_date(due_date):
        messagebox.showwarning("Validation Error", "Due Date must be in YYYY-MM-DD format.")
        return
    if not is_valid_time(due_time_hour_var.get(), due_time_minute_var.get(), due_time_period_var.get()):
        messagebox.showwarning("Validation Error", "Due Time must be valid.")
        return

    save_data("tasks", (None, current_user.get(), title, due_date, due_time, category, priority, details, status, reminder))
    conn = sqlite3.connect("mytaskdesk.db")
    c = conn.cursor()
    c.execute("SELECT last_insert_rowid()")
    task_id = c.fetchone()[0]
    conn.close()
    if reminder:
        schedule_reminder(task_id, title, due_date, due_time)
    messagebox.showinfo("Success", f"Task '{title}' added!")
    update_task_list()
    show_frame(task_list_frame)
    cancel_task()

def edit_task(task_id):
    conn = sqlite3.connect("mytaskdesk.db")
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = c.fetchone()
    title_var.set(task[2])
    due_date_var.set(task[3])
    hour, minute, period = convert_to_12_hour(task[4] if task[4] else "00:00")
    due_time_hour_var.set(f"{hour:02d}")
    due_time_minute_var.set(f"{minute:02d}")
    due_time_period_var.set(period)
    category_var.set(task[5])
    priority_var.set(task[6])
    details_var.set(task[7])
    status_var.set(task[8])
    reminder_var.set(bool(task[9]))
    conn.close()
    show_frame(edit_task_frame)
    edit_task_id.set(task_id)

def delete_task(task_id):
    conn = sqlite3.connect("mytaskdesk.db")
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    update_task_list()

def mark_complete(task_id):
    conn = sqlite3.connect("mytaskdesk.db")
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = 'Completed' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    update_task_list()

def cancel_task():
    title_var.set("")
    due_date_var.set("")
    due_time_hour_var.set("12")
    due_time_minute_var.set("00")
    due_time_period_var.set("AM")
    category_var.set("Academic")
    priority_var.set("Medium")
    details_var.set("")
    status_var.set("Pending")
    reminder_var.set(False)

tk.Label(add_task_frame, text="MyTaskDesk", font=("Consolas", 20, "bold"), fg=accent_color, bg=bg_color).pack(pady=10)
frame = tk.Frame(add_task_frame, bg=bg_color, padx=25, pady=25, relief="flat", bd=2, highlightbackground=accent_color, highlightthickness=2)
frame.pack(pady=20, fill="both", expand=True)

tk.Label(frame, text="Create New Task", font=("Consolas", 16, "bold"), bg=bg_color, fg=accent_color).grid(row=0, column=0, columnspan=2, pady=15)
tk.Label(frame, text="Task Title:", font=label_font, bg=bg_color, fg=fg_color).grid(row=1, column=0, sticky="w", pady=5)
tk.Entry(frame, textvariable=title_var, width=40, font=entry_font, bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=1, column=1, pady=5)
tk.Label(frame, text="Due Date:", font=label_font, bg=bg_color, fg=fg_color).grid(row=2, column=0, sticky="w", pady=5)
DateEntry(frame, textvariable=due_date_var, width=37, date_pattern="yyyy-mm-dd", font=entry_font, background="#1a1a1a", foreground=fg_color, selectbackground=accent_color).grid(row=2, column=1, pady=5)
tk.Label(frame, text="Due Time:", font=label_font, bg=bg_color, fg=fg_color).grid(row=3, column=0, sticky="w", pady=5)
time_frame = tk.Frame(frame, bg=bg_color)
time_frame.grid(row=3, column=1, pady=5, sticky="w")
ttk.Combobox(time_frame, values=[f"{h:02d}" for h in range(1, 13)], textvariable=due_time_hour_var, state="readonly", width=5).pack(side="left", padx=5)
tk.Label(time_frame, text=":", font=label_font, bg=bg_color, fg=fg_color).pack(side="left")
ttk.Combobox(time_frame, values=[f"{m:02d}" for m in range(60)], textvariable=due_time_minute_var, state="readonly", width=5).pack(side="left", padx=5)
ttk.Combobox(time_frame, values=["AM", "PM"], textvariable=due_time_period_var, state="readonly", width=5).pack(side="left", padx=5)
tk.Label(frame, text="Category:", font=label_font, bg=bg_color, fg=fg_color).grid(row=4, column=0, sticky="w", pady=5)
category_dropdown = ttk.Combobox(frame, values=["Academic", "Work", "Personal"], textvariable=category_var, state="readonly", width=37)
category_dropdown.grid(row=4, column=1, pady=5)
tk.Label(frame, text="Priority:", font=label_font, bg=bg_color, fg=fg_color).grid(row=5, column=0, sticky="w", pady=5)
priority_dropdown = ttk.Combobox(frame, values=["Low", "Medium", "High"], textvariable=priority_var, state="readonly", width=37)
priority_dropdown.grid(row=5, column=1, pady=5)
tk.Label(frame, text="Details:", font=label_font, bg=bg_color, fg=fg_color).grid(row=6, column=0, sticky="nw", pady=5)
tk.Entry(frame, textvariable=details_var, width=40, font=entry_font, bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=6, column=1, pady=5)
tk.Label(frame, text="Status:", font=label_font, bg=bg_color, fg=fg_color).grid(row=7, column=0, sticky="w", pady=5)
status_frame = tk.Frame(frame, bg=bg_color)
status_frame.grid(row=7, column=1, pady=5, sticky="w")
for s in ["Pending", "In Progress", "Completed"]:
    tk.Radiobutton(status_frame, text=s, value=s, variable=status_var, bg=bg_color, fg=fg_color, selectcolor="#1a1a1a", font=entry_font, activebackground=bg_color, activeforeground=accent_color).pack(side="left", padx=5)
tk.Checkbutton(frame, text="Set Reminder", variable=reminder_var, bg=bg_color, fg=fg_color, font=entry_font, activebackground=bg_color, activeforeground=accent_color, selectcolor="#1a1a1a").grid(row=8, column=1, pady=5, sticky="w")
btn_frame = tk.Frame(frame, bg=bg_color)
btn_frame.grid(row=9, column=0, columnspan=2, pady=20)
tk.Button(btn_frame, text="Add Task", width=15, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=add_task, relief="flat", bd=0).pack(side="left", padx=10)
tk.Button(btn_frame, text="Cancel", width=15, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), command=cancel_task, relief="flat", bd=0).pack(side="left", padx=10)
tk.Button(btn_frame, text="Back to Profile", width=15, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), command=lambda: show_frame(profile_frame), relief="flat", bd=0).pack(side="left", padx=10)

# Edit Task Page
edit_task_frame = tk.Frame(root, bg=bg_color)
edit_task_id = tk.IntVar()

def save_edited_task():
    task_id = edit_task_id.get()
    title = title_var.get().strip()
    due_date = due_date_var.get().strip()
    due_time = convert_to_24_hour(due_time_hour_var.get(), due_time_minute_var.get(), due_time_period_var.get())
    category = category_var.get()
    priority = priority_var.get()
    details = details_var.get().strip()
    status = status_var.get()
    reminder = 1 if reminder_var.get() else 0

    if not title or not is_valid_date(due_date):
        messagebox.showwarning("Validation Error", "Title and valid due date are required.")
        return

    conn = sqlite3.connect("mytaskdesk.db")
    c = conn.cursor()
    c.execute("UPDATE tasks SET title = ?, due_date = ?, due_time = ?, category = ?, priority = ?, details = ?, status = ?, reminder_set = ? WHERE id = ?", 
              (title, due_date, due_time, category, priority, details, status, reminder, task_id))
    conn.commit()
    conn.close()
    if reminder:
        schedule_reminder(task_id, title, due_date, due_time)
    messagebox.showinfo("Success", f"Task '{title}' updated!")
    update_task_list()
    show_frame(task_list_frame)

tk.Label(edit_task_frame, text="MyTaskDesk", font=("Consolas", 20, "bold"), fg=accent_color, bg=bg_color).pack(pady=10)
edit_frame = tk.Frame(edit_task_frame, bg=bg_color, padx=25, pady=25, relief="flat", bd=2, highlightbackground=accent_color, highlightthickness=2)
edit_frame.pack(pady=20, fill="both", expand=True)

tk.Label(edit_frame, text="Edit Task", font=("Consolas", 16, "bold"), bg=bg_color, fg=accent_color).grid(row=0, column=0, columnspan=2, pady=15)
tk.Label(edit_frame, text="Task Title:", font=label_font, bg=bg_color, fg=fg_color).grid(row=1, column=0, sticky="w", pady=5)
tk.Entry(edit_frame, textvariable=title_var, width=40, font=entry_font, bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=1, column=1, pady=5)
tk.Label(edit_frame, text="Due Date:", font=label_font, bg=bg_color, fg=fg_color).grid(row=2, column=0, sticky="w", pady=5)
DateEntry(edit_frame, textvariable=due_date_var, width=37, date_pattern="yyyy-mm-dd", font=entry_font, background="#1a1a1a", foreground=fg_color, selectbackground=accent_color).grid(row=2, column=1, pady=5)
tk.Label(edit_frame, text="Due Time:", font=label_font, bg=bg_color, fg=fg_color).grid(row=3, column=0, sticky="w", pady=5)
edit_time_frame = tk.Frame(edit_frame, bg=bg_color)
edit_time_frame.grid(row=3, column=1, pady=5, sticky="w")
ttk.Combobox(edit_time_frame, values=[f"{h:02d}" for h in range(1, 13)], textvariable=due_time_hour_var, state="readonly", width=5).pack(side="left", padx=5)
tk.Label(edit_time_frame, text=":", font=label_font, bg=bg_color, fg=fg_color).pack(side="left")
ttk.Combobox(edit_time_frame, values=[f"{m:02d}" for m in range(60)], textvariable=due_time_minute_var, state="readonly", width=5).pack(side="left", padx=5)
ttk.Combobox(edit_time_frame, values=["AM", "PM"], textvariable=due_time_period_var, state="readonly", width=5).pack(side="left", padx=5)
tk.Label(edit_frame, text="Category:", font=label_font, bg=bg_color, fg=fg_color).grid(row=4, column=0, sticky="w", pady=5)
ttk.Combobox(edit_frame, values=["Academic", "Work", "Personal"], textvariable=category_var, state="readonly", width=37).grid(row=4, column=1, pady=5)
tk.Label(edit_frame, text="Priority:", font=label_font, bg=bg_color, fg=fg_color).grid(row=5, column=0, sticky="w", pady=5)
ttk.Combobox(edit_frame, values=["Low", "Medium", "High"], textvariable=priority_var, state="readonly", width=37).grid(row=5, column=1, pady=5)
tk.Label(edit_frame, text="Details:", font=label_font, bg=bg_color, fg=fg_color).grid(row=6, column=0, sticky="nw", pady=5)
tk.Entry(edit_frame, textvariable=details_var, width=40, font=entry_font, bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=6, column=1, pady=5)
tk.Label(edit_frame, text="Status:", font=label_font, bg=bg_color, fg=fg_color).grid(row=7, column=0, sticky="w", pady=5)
status_edit_frame = tk.Frame(edit_frame, bg=bg_color)
status_edit_frame.grid(row=7, column=1, pady=5, sticky="w")
for s in ["Pending", "In Progress", "Completed"]:
    tk.Radiobutton(status_edit_frame, text=s, value=s, variable=status_var, bg=bg_color, fg=fg_color, selectcolor="#1a1a1a", font=entry_font, activebackground=bg_color, activeforeground=accent_color).pack(side="left", padx=5)
tk.Checkbutton(edit_frame, text="Set Reminder", variable=reminder_var, bg=bg_color, fg=fg_color, font=entry_font, activebackground=bg_color, activeforeground=accent_color, selectcolor="#1a1a1a").grid(row=8, column=1, pady=5, sticky="w")
btn_edit_frame = tk.Frame(edit_frame, bg=bg_color)
btn_edit_frame.grid(row=9, column=0, columnspan=2, pady=20)
tk.Button(btn_edit_frame, text="Save Changes", width=15, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=save_edited_task, relief="flat", bd=0).pack(side="left", padx=10)
tk.Button(btn_edit_frame, text="Cancel", width=15, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), command=lambda: show_frame(task_list_frame), relief="flat", bd=0).pack(side="left", padx=10)

# Task List Page
task_list_frame = tk.Frame(root, bg=bg_color)

task_list = tk.Listbox(task_list_frame, width=80, height=15, font=entry_font, bg="#1a1a1a", fg=fg_color)
category_filter_var = tk.StringVar(value="all")
status_filter_var = tk.StringVar(value="all")
sort_var = tk.StringVar(value="due_date_asc")

def update_task_list():
    task_list.delete(0, tk.END)
    tasks = fetch_tasks(current_user.get(), category_filter_var.get(), status_filter_var.get(), sort_var.get())
    for task in tasks:
        try:
            hour, minute, period = convert_to_12_hour(task[4] if task[4] else "00:00")
            task_str = f"ID: {task[0]} | Title: {task[2]} | Due: {task[3]} {hour:02d}:{minute:02d} {period} | Cat: {task[5]} | Pri: {task[6]} | Stat: {task[8]}"
        except ValueError:
            task_str = f"ID: {task[0]} | Title: {task[2]} | Due: {task[3]} (Invalid Time) | Cat: {task[5]} | Pri: {task[6]} | Stat: {task[8]}"
        task_list.insert(tk.END, task_str)

def filter_tasks():
    update_task_list()

def edit_task_wrapper():
    if not task_list.curselection():
        messagebox.showwarning("Selection Error", "Please select a task to edit.")
        return
    task_id = task_list.get(task_list.curselection()).split("|")[0].split(":")[1].strip()
    edit_task(task_id)

def delete_task_wrapper():
    if not task_list.curselection():
        messagebox.showwarning("Selection Error", "Please select a task to delete.")
        return
    task_id = task_list.get(task_list.curselection()).split("|")[0].split(":")[1].strip()
    delete_task(task_id)

def mark_complete_wrapper():
    if not task_list.curselection():
        messagebox.showwarning("Selection Error", "Please select a task to mark as complete.")
        return
    task_id = task_list.get(task_list.curselection()).split("|")[0].split(":")[1].strip()
    mark_complete(task_id)

tk.Label(task_list_frame, text="MyTaskDesk", font=("Consolas", 20, "bold"), fg=accent_color, bg=bg_color).grid(row=0, column=0, columnspan=3, pady=10)
tk.Label(task_list_frame, text="Task List", font=("Consolas", 16, "bold"), bg=bg_color, fg=accent_color).grid(row=1, column=0, columnspan=3, pady=10)
task_list.grid(row=2, column=0, columnspan=3, pady=10)
tk.Label(task_list_frame, text="Filter by Category:", font=label_font, bg=bg_color, fg=fg_color).grid(row=3, column=0, sticky="w", pady=5)
ttk.Combobox(task_list_frame, values=["all", "Academic", "Work", "Personal"], textvariable=category_filter_var, state="readonly", width=15).grid(row=3, column=1, pady=5)
tk.Label(task_list_frame, text="Filter by Status:", font=label_font, bg=bg_color, fg=fg_color).grid(row=4, column=0, sticky="w", pady=5)
ttk.Combobox(task_list_frame, values=["all", "Pending", "In Progress", "Completed"], textvariable=status_filter_var, state="readonly", width=15).grid(row=4, column=1, pady=5)
tk.Label(task_list_frame, text="Sort by:", font=label_font, bg=bg_color, fg=fg_color).grid(row=5, column=0, sticky="w", pady=5)
ttk.Combobox(task_list_frame, values=["due_date_asc", "due_date_desc", "title_asc", "title_desc", "priority_asc", "priority_desc"], textvariable=sort_var, state="readonly", width=15).grid(row=5, column=1, pady=5)
tk.Button(task_list_frame, text="Apply Filters", width=15, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=filter_tasks, relief="flat", bd=0).grid(row=6, column=1, pady=5)
tk.Button(task_list_frame, text="Edit", width=10, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=edit_task_wrapper, relief="flat", bd=0).grid(row=7, column=0, pady=5)
tk.Button(task_list_frame, text="Delete", width=10, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), command=delete_task_wrapper, relief="flat", bd=0).grid(row=7, column=1, pady=5)
tk.Button(task_list_frame, text="Mark Complete", width=10, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=mark_complete_wrapper, relief="flat", bd=0).grid(row=7, column=2, pady=5)
tk.Button(task_list_frame, text="Back to Profile", width=15, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), command=lambda: show_frame(profile_frame), relief="flat", bd=0).grid(row=8, column=1, pady=10)

# Demo Page
demo_frame = tk.Frame(root, bg=bg_color)

demo_list = tk.Listbox(demo_frame, width=80, height=15, font=entry_font, bg="#1a1a1a", fg=fg_color)

def show_demo_tasks():
    demo_list.delete(0, tk.END)
    sample_tasks = [
        "ID: 1 | Title: Sample Task 1 | Due: 2025-05-13 09:00 AM | Cat: Work | Pri: Medium | Stat: Pending",
        "ID: 2 | Title: Sample Task 2 | Due: 2025-05-14 10:00 AM | Cat: Personal | Pri: High | Stat: In Progress"
    ]
    for task in sample_tasks:
        demo_list.insert(tk.END, task)

tk.Label(demo_frame, text="MyTaskDesk Demo", font=("Consolas", 20, "bold"), fg=accent_color, bg=bg_color).pack(pady=10)
tk.Label(demo_frame, text="Sample Task List", font=("Consolas", 16, "bold"), bg=bg_color, fg=accent_color).pack(pady=10)
demo_list.pack(pady=10)
tk.Button(demo_frame, text="Back to Login", width=15, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), command=lambda: show_frame(login_frame), relief="flat", bd=0).pack(pady=10)

show_demo_tasks()

# Expense Tracking Page
expense_frame = tk.Frame(root, bg=bg_color)
amount_var = tk.StringVar()
expense_category_var = tk.StringVar(value="General")
expense_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
expense_start_date_var = tk.StringVar(value="2025-01-01")
expense_end_date_var = tk.StringVar(value="2025-12-31")
exp_frame = tk.Frame(expense_frame, bg=bg_color, padx=25, pady=25, relief="flat", bd=2, highlightbackground=accent_color, highlightthickness=2)
expense_list = tk.Listbox(exp_frame, width=80, height=10, font=entry_font, bg="#1a1a1a", fg=fg_color)
total_labels = {}

def add_expense():
    amount = amount_var.get().strip()
    category = expense_category_var.get()
    date = expense_date_var.get().strip()
    if not amount or not date or not is_valid_date(date):
        messagebox.showwarning("Validation Error", "Please enter a valid amount and date.")
        return
    save_data("expenses", (None, current_user.get(), float(amount), category, date))
    messagebox.showinfo("Success", "Expense added!")
    amount_var.set("")
    expense_category_var.set("General")
    update_expense_list()

def update_expense_list():
    start_date = expense_start_date_var.get()
    end_date = expense_end_date_var.get()
    if not is_valid_date(start_date) or not is_valid_date(end_date):
        messagebox.showwarning("Validation Error", "Please enter valid start and end dates.")
        return
    expense_list.delete(0, tk.END)
    conn = sqlite3.connect("mytaskdesk.db")
    c = conn.cursor()
    c.execute("SELECT date, amount, category FROM expenses WHERE username = ? AND date >= ? AND date <= ? ORDER BY date DESC", 
              (current_user.get(), start_date, end_date))
    expenses = c.fetchall()
    for expense in expenses:
        expense_str = f"Date: {expense[0]} | Amount: ${expense[1]:.2f} | Category: {expense[2]}"
        expense_list.insert(tk.END, expense_str)
    conn.close()
    update_totals()

def update_totals():
    for label in total_labels.values():
        label.destroy()
    totals = fetch_expenses(current_user.get())
    row = 8
    for category, total in totals:
        label_text = f"Total for {category}: ${total:.2f}"
        label = tk.Label(exp_frame, text=label_text, font=label_font, bg=bg_color, fg=fg_color)
        label.grid(row=row, column=0, columnspan=2, pady=2)
        total_labels[category] = label
        row += 1

tk.Label(expense_frame, text="MyTaskDesk", font=("Consolas", 20, "bold"), fg=accent_color, bg=bg_color).pack(pady=10)
exp_frame.pack(pady=20, fill="both", expand=True)

tk.Label(exp_frame, text="Expense Tracker", font=("Consolas", 16, "bold"), bg=bg_color, fg=accent_color).grid(row=0, column=0, columnspan=2, pady=15)
tk.Label(exp_frame, text="Amount:", font=label_font, bg=bg_color, fg=fg_color).grid(row=1, column=0, sticky="w", pady=5)
tk.Entry(exp_frame, textvariable=amount_var, width=40, font=entry_font, bg="#1a1a1a", fg=fg_color, insertbackground=accent_color, bd=1, relief="solid", highlightbackground=accent_color, highlightthickness=1).grid(row=1, column=1, pady=5)
tk.Label(exp_frame, text="Category:", font=label_font, bg=bg_color, fg=fg_color).grid(row=2, column=0, sticky="w", pady=5)
ttk.Combobox(exp_frame, values=["General", "Food", "Travel", "Other"], textvariable=expense_category_var, state="readonly", width=37).grid(row=2, column=1, pady=5)
tk.Label(exp_frame, text="Date:", font=label_font, bg=bg_color, fg=fg_color).grid(row=3, column=0, sticky="w", pady=5)
DateEntry(exp_frame, textvariable=expense_date_var, width=37, date_pattern="yyyy-mm-dd", font=entry_font, background="#1a1a1a", foreground=fg_color, selectbackground=accent_color).grid(row=3, column=1, pady=5)
tk.Label(exp_frame, text="Start Date:", font=label_font, bg=bg_color, fg=fg_color).grid(row=4, column=0, sticky="w", pady=5)
DateEntry(exp_frame, textvariable=expense_start_date_var, width=37, date_pattern="yyyy-mm-dd", font=entry_font, background="#1a1a1a", foreground=fg_color, selectbackground=accent_color).grid(row=4, column=1, pady=5)
tk.Label(exp_frame, text="End Date:", font=label_font, bg=bg_color, fg=fg_color).grid(row=5, column=0, sticky="w", pady=5)
DateEntry(exp_frame, textvariable=expense_end_date_var, width=37, date_pattern="yyyy-mm-dd", font=entry_font, background="#1a1a1a", foreground=fg_color, selectbackground=accent_color).grid(row=5, column=1, pady=5)
btn_exp_frame = tk.Frame(exp_frame, bg=bg_color)
btn_exp_frame.grid(row=6, column=0, columnspan=2, pady=10)
tk.Button(btn_exp_frame, text="Add Expense", width=15, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=add_expense, relief="flat", bd=0).pack(side="left", padx=10)
tk.Button(btn_exp_frame, text="Apply Date Filter", width=15, bg=accent_color, fg="white", font=("Consolas", 10, "bold"), command=update_expense_list, relief="flat", bd=0).pack(side="left", padx=10)
tk.Button(btn_exp_frame, text="Back to Profile", width=15, bg="#1a1a1a", fg="white", font=("Consolas", 10, "bold"), command=lambda: show_frame(profile_frame), relief="flat", bd=0).pack(side="left", padx=10)
expense_list.grid(row=7, column=0, columnspan=2, pady=10)
update_expense_list()

# Start with the login frame
show_frame(login_frame)

# Run the application
root.mainloop()