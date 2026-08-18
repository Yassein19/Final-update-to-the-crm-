# TEAM Engineering CRM

A professional, self-contained **Sales Pipeline CRM** built for TEAM Engineering to manage engineering inquiries, track commercial outcomes, and synchronise all data back to the existing `STATUS 2025-2026.xlsx` Excel file.

---

## 📖 Non-Technical User Guide (How to Use)

This guide explains how to start, use, and sync the CRM without needing technical knowledge.

### 1. How to Start the CRM
To launch the CRM, you do not need to write code or open terminals:
1. Locate the **`Team-engineering-CRM`** folder on your computer.
2. Double-click the file named **`run.bat`** (the Windows Batch file).
3. A black command window will open. It will automatically check for required software components, install them if missing, setup the database, and run the server.
4. Your default web browser will open automatically and navigate to the CRM at **`http://127.0.0.1:8000`**.

> [!IMPORTANT]
> **Do not close the black window while using the CRM.** That window is running the CRM server in the background. When you are finished, simply close the black window to shut down the server. Your data is safely saved.

---

### 2. Dashboard & Alerts
When the CRM opens, you will see the **Dashboard**:
- **Pipeline Statistics:** Instant counts of how many inquiries are *Active*, *Won*, *Lost*, or *Declined*.
- **Financial Status:** Sums of active pipeline inquiry values and won order values.
- **Urgent Alerts:** List of inquiries due this week and orders nearing expected delivery.

---

### 3. Managing the Sales Pipeline (Funnel)
The CRM matches your sales funnel stages:
- **Adding Inquiries:** Click the **`+ New Inquiry`** button. Fill in the client, principal, reference, values, and deadlines.
- **Adding Update Comments:** Scroll to the bottom of any inquiry page to add comments. These are preserved chronologically as a history timeline.
- **Moving Inquiries:**
  - **Winning a Deal:** Click **`Mark as Won`**. This automatically brings up the **Order Form** to enter order numbers, confirmations, delivery dates, and payment status.
  - **Lost or Declined:** Click **`Mark as Lost`** or **`Mark as Declined`**.
  - **Resetting status:** If you want to change a *Lost* or *Declined* inquiry back to *Won*, you must first change it back to **`Active`** (an active pipeline state) before transition.

---

### 4. Trash Bin (Soft Delete)
- Deleting an item does not permanently erase it. It goes to the **Trash Bin**.
- You can access the Trash Bin at any time to **Restore** the record if it was deleted by mistake.

---

### 5. Syncing Data with Excel
The CRM works hand-in-hand with your existing `STATUS 2025-2026.xlsx` spreadsheet:
- **Auto-Import:** The first time you launch, the CRM imports all columns and rows from your existing Excel sheet.
- **Sync back to Excel:** After editing, adding comments, or moving items in the CRM, click the **`Sync to Excel`** button at the top-right of the dashboard. This writes the live CRM database back to the spreadsheet, preserving all formatting and formulas.

---

## 🚀 Quick Start (Technical Version)

### Option A — Double-click (Windows)
Double-click **`run.bat`** in the workspace directory.

### Option B — Command Line
Run the launcher using python:
```powershell
python run.py
```

The launcher will:
1. Auto-install missing packages in `requirements.txt`.
2. Initialize `crm.db` (SQLite) if not present.
3. Automatically load initial data from Excel.
4. Start the FastAPI server on `127.0.0.1:8000` and open the browser.

---

## ✨ Application Features

| Feature | Description |
| :--- | :--- |
| **Dashboard** | Live pipeline counts, active/won values, and deadline alerts. |
| **Inquiries Pipeline** | List, filter, search, create, and update inquiries. |
| **Status Transitions** | Moves inquiries between Active, Won, Lost, and Declined stages. |
| **Won Orders Form** | Activates delivery terms, expected delivery date, cargo-X tracking, and payment terms. |
| **Comment Timeline** | Full chronological log of history comments per inquiry. |
| **Audit Trails** | Immutably records status changes and updates in the Activity Log. |
| **Soft Delete** | Trash bin recovery system. |
| **Instant Export** | Syncs live data back to the excel file in less than 1 second. |

---

## 🗂 Project Structure

```
CRM-Workspace/
│
├── app/                        # Python FastAPI Backend
│   ├── __init__.py
│   ├── database.py             # Database engine setup (SQLite)
│   ├── models.py               # ORM Tables (Client, Principal, Inquiry, Order, Comment, Log)
│   ├── schemas.py              # Pydantic schemas
│   ├── main.py                 # API controllers/routes
│   └── sync.py                 # Optimized Excel import/export code (pandas + openpyxl)
│
├── static/                     # SPA Frontend
│   ├── index.html              # HTML structure
│   ├── style.css               # Clean dark-mode styles
│   └── app.js                  # Frontend client engine (AJAX API calls)
│
├── crm.db                      # Local SQLite file database
├── run.py                      # Python startup launcher
├── run.bat                     # Windows shortcut launcher
├── requirements.txt            # Python dependencies
└── STATUS 2025-2026.xlsx   # The master Excel file
```

---

## 🔌 API Reference

Explore the interactive API docs at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Core Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/dashboard` | Fetches dashboard statistics & alerts |
| `GET` | `/api/inquiries` | Lists inquiries (filter by search and status) |
| `POST` | `/api/inquiries` | Adds a new pipeline inquiry |
| `PUT` | `/api/inquiries/{id}` | Updates existing inquiry fields |
| `DELETE`| `/api/inquiries/{id}` | Moves an inquiry to the trash bin |
| `POST` | `/api/inquiries/{id}/restore` | Restores a soft-deleted inquiry |
| `POST` | `/api/inquiries/{id}/transition` | Transitions inquiry status (Required for marking Won) |
| `POST` | `/api/sync/export` | Export database changes back to the Excel file |
| `POST` | `/api/sync/import` | Force re-import data from the Excel file (clears database) |

---

## 📌 Business & Transition Rules

1. **Status Flow Enforcement:**
   - Active $\rightarrow$ Won / Lost / Declined (Allowed)
   - Declined / Lost $\rightarrow$ Won (Forbidden directly; must transition to **Active** first)
2. **Mandatory Fields:** Client, Principal, and Inquiry Reference must be provided.
3. **Required Won details:** Transitioning to Won requires order confirmations, expected delivery dates, and total order value.

---

## ⚙️ System Requirements

- **Python 3.10+** (Tested on Python 3.13)
- **Windows 10/11**
- Zero server database configuration required (fully database-portable SQLite).

---

## 🛑 Stopping the Server

Press **`Ctrl + C`** in the command prompt launcher window or close the window.

---

## 🔄 Resetting the Database

If you want to clear the CRM and fully re-load all data from the spreadsheet:
1. Close the CRM launcher window.
2. Delete the `crm.db` file from the directory.
3. Restart using `run.bat` or `python run.py`.

> [!WARNING]
> Resetting the database will overwrite any new records, status updates, or comments added in the CRM that have **not** been exported back to the Excel spreadsheet. Always run the **Sync to Excel** function before executing a reset.
se the API endpoint:

```
POST http://127.0.0.1:8000/api/sync/import
```

# ⚠️ **Warning:** This overwrites all CRM data (including any new entries or comments added via the UI that have not been exported back to Excel first).

# Team-engineering-CRM

This repository contains my projects for the company team engineering
