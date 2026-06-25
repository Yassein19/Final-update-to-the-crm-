# TEAM Engineering CRM

A professional, self-contained **Sales Pipeline CRM** built for TEAM Engineering to manage engineering inquiries, track their commercial outcomes, and synchronise all data back to the existing `STATUS 2025-2026.xlsx` Excel file.

---

## 📋 What It Does

Your existing Excel workbook has 7 sheets that form a classic B2B sales funnel:

```
Inquiries ──→ Won Orders
          ──→ Lost Inquiries
          ──→ Declined Inquiries
```

This CRM replaces manual Excel editing with a beautiful, browser-based interface — while keeping Excel as your source of truth through a two-way sync feature.

---

## ✨ Features

| Feature                    | Description                                                                             |
| -------------------------- | --------------------------------------------------------------------------------------- |
| **Dashboard**              | Live pipeline counts, total active & won values, chart, and urgent alerts               |
| **Inquiries Pipeline**     | Full CRUD with filters for stage, client, and principal                                 |
| **Status Transitions**     | One-click transitions: Active → Won / Lost / Declined (with business rules enforcement) |
| **Won Orders Form**        | Detailed order form auto-triggered on winning an inquiry                                |
| **Comment Timeline**       | Chronological remarks log per inquiry (imported from Excel)                             |
| **Activity Audit Log**     | System-tracked log of every status change and update                                    |
| **Soft Delete + Recovery** | Deleted items go to Trash Bin and can be fully restored                                 |
| **Global Search**          | Instant search across client, principal, references, order numbers                      |
| **Excel Sync**             | One-click export writes the live database state back to `STATUS 2025-2026.xlsx`         |
| **Auto-Import**            | On first launch, all 7 Excel sheets are automatically imported into the database        |

---

## 🗂 Project Structure

```
Team Eng/
│
├── app/                        # Python backend
│   ├── __init__.py
│   ├── database.py             # SQLAlchemy engine & session (SQLite)
│   ├── models.py               # ORM tables: Inquiry, Order, Client, Principal, Comment, ActivityLog
│   ├── schemas.py              # Pydantic validation schemas
│   ├── main.py                 # FastAPI routes & API endpoints
│   └── sync.py                 # Excel import/export logic (openpyxl + pandas)
│
├── static/                     # Frontend (served by FastAPI)
│   ├── index.html              # Single Page App UI
│   ├── style.css               # Premium dark-mode design system
│   └── app.js                  # UI logic, API calls, state management
│
├── crm.db                      # SQLite database (auto-created on first run)
├── run.py                      # Launcher: installs deps, imports data, starts server
├── run.bat                     # Windows double-click launcher
├── requirements.txt            # Python package dependencies
├── STATUS 2025-2026.xlsx       # Your existing Excel file (read + written back to)
└── plan.text                   # Original specification
```

---

## 🚀 Quick Start

### Option A — Double-click (Windows)

Simply double-click **`run.bat`** in the `Team Eng` folder.

### Option B — Command Line

```powershell
cd "c:\Users\yassein ahmed\OneDrive\Desktop\Team Eng"
python run.py
```

The launcher will:

1. Check and auto-install any missing Python packages
2. Auto-create the SQLite database `crm.db` if it doesn't exist
3. Import all 7 Excel sheets into the database on first run
4. Open your browser automatically at `http://127.0.0.1:8000`

### Manual Installation (Optional)

If you prefer installing dependencies yourself first:

```powershell
pip install -r requirements.txt
python run.py
```

---

## 🔌 API Reference

The backend exposes a REST API at `http://127.0.0.1:8000/`. You can explore it interactively at:

```
http://127.0.0.1:8000/docs      ← Swagger UI (auto-generated)
http://127.0.0.1:8000/redoc     ← ReDoc UI
```

| Method   | Endpoint                         | Description                                                             |
| -------- | -------------------------------- | ----------------------------------------------------------------------- |
| `GET`    | `/api/dashboard`                 | Pipeline stats, alerts, and totals                                      |
| `GET`    | `/api/inquiries`                 | List inquiries (filter by status, search term)                          |
| `POST`   | `/api/inquiries`                 | Create new inquiry                                                      |
| `PUT`    | `/api/inquiries/{id}`            | Update inquiry fields                                                   |
| `DELETE` | `/api/inquiries/{id}`            | Soft delete inquiry                                                     |
| `POST`   | `/api/inquiries/{id}/restore`    | Restore from trash                                                      |
| `POST`   | `/api/inquiries/{id}/transition` | Transition status (pass `status` query param + order JSON body for Won) |
| `GET`    | `/api/inquiries/{id}/comments`   | Get comments for inquiry                                                |
| `POST`   | `/api/inquiries/{id}/comments`   | Add a comment                                                           |
| `GET`    | `/api/activity-logs`             | Last 100 audit log entries                                              |
| `GET`    | `/api/clients`                   | List all client names                                                   |
| `GET`    | `/api/principals`                | List all principal names                                                |
| `POST`   | `/api/sync/export`               | Write database → Excel file                                             |
| `POST`   | `/api/sync/import`               | Re-import Excel → database (overwrites DB)                              |

---

## 🗄 Database Schema

```
clients           principals
  └─────────────────────────┐
                            ↓
                        inquiries  (status: Active / Won / Lost / Declined)
                            │
              ┌─────────────┼──────────────┐
              ↓             ↓              ↓
           orders        comments    activity_logs
     (extended data    (timeline     (audit trail)
      for won deals)    history)
```

- **`inquiries`** — master table for all pipeline records; `is_deleted` enables soft-delete
- **`orders`** — one-to-one extension of a won inquiry with delivery/payment fields
- **`comments`** — multi-line remarks and updates timeline per inquiry
- **`activity_logs`** — immutable system log of every change (who changed what and when)

---

## 📊 Excel Sync Details

### Import (first launch or `/api/sync/import`)

| Excel Sheet           | Maps To                       | Status   |
| --------------------- | ----------------------------- | -------- |
| `Inquires`            | `inquiries`                   | Active   |
| `Declined Inquiries`  | `inquiries`                   | Declined |
| `Lost Inquiries`      | `inquiries`                   | Lost     |
| `Orders`              | `orders` + linked `inquiries` | Won      |
| `LESER's Orders`      | `orders` + linked `inquiries` | Won      |
| ` Bartec Orders`      | `orders` + linked `inquiries` | Won      |
| ` Bartec Orders 2025` | `orders` + linked `inquiries` | Won      |

### Export (Sync to Excel button)

Writes the live DB state back to `STATUS 2025-2026.xlsx`, preserving the original header rows and formatting. Only the data rows (row 9+ for inquiry sheets, row 8+ for order sheets) are replaced.

---

## 📌 Business Rules

- **Status transitions** follow a controlled flow:
  - Any active inquiry can go → Won / Lost / Declined
  - Declined or Lost inquiries must be reset to **Active** before being marked **Won**
- **Soft delete**: Records are never permanently removed unless you manually clear the database. Deleted records appear in the Trash Bin and can be restored.
- **Required fields**: Client, Principal, and Inquiry Reference are mandatory when creating a new inquiry.
- **Won transition**: Requires filling in the Order form (Order Number, Date, Value, Delivery).

---

## ⚙️ Requirements

- **Python 3.10+** (3.13 tested and working)
- **Windows 10/11** (the `run.bat` launcher targets Windows; `run.py` works cross-platform)
- No database server required — uses SQLite (file-based, zero-config)
- Internet connection only needed on first run to download Python packages

---

## 🛑 Stopping the Server

Press **`Ctrl + C`** in the terminal window running `run.py` (or close the terminal).  
Your data is safely persisted in `crm.db` — the next launch will continue from where you left off.

---

## 🔄 Resetting the Database

To wipe and re-import from Excel from scratch:

```powershell
Remove-Item crm.db
python run.py
```

Or use the API endpoint:

```
POST http://127.0.0.1:8000/api/sync/import
```

> ⚠️ **Warning:** This overwrites all CRM data (including any new entries or comments added via the UI that have not been exported back to Excel first).
