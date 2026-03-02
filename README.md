# GMS Employee Tracker
## Geometry Measurement Service — Internal Tracking System

### Setup & Run

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the app:
   ```
   python app.py
   ```

3. Open browser: http://localhost:5050

---

### Login Credentials

| Role     | ID      | Password  |
|----------|---------|-----------|
| Admin    | ADM001  | admin123  |
| Engineer | EMP001  | emp123    |
| Finance  | EMP002  | emp123    |
| Tech     | EMP003  | emp123    |

---

### Features

**Employee (Limited Access)**
- Create Job Cards with all details (customer, timing, vehicle, machine, bills)
- View personal job card history

**Admin (Full Access)**
- Dashboard with stats and finance summary
- View & manage all job cards
- Update job card status (Pending / In Progress / Completed)
- Split batch hours (e.g. 6 shifts → 5.5 + 0.5)
- Finance module with GST & TDS auto-calculation
- Stock tracking by job card & customer
- Master List management (customers, employees, vehicles, drivers, machines)

---

### File Structure
```
gms_tracker/
├── app.py              ← Main Flask app
├── data.json           ← Auto-created JSON database
├── requirements.txt
└── templates/
    ├── base.html       ← Shared layout with sidebar
    ├── login.html      ← Login page
    ├── emp_dash.html   ← Employee dashboard
    ├── new_job.html    ← Create job card form
    ├── admin_dash.html ← Admin dashboard
    ├── admin_jobs.html ← All job cards list
    ├── view_job.html   ← Job card detail + split + status
    ├── finance.html    ← Finance records
    ├── master.html     ← Master list management
    └── stock.html      ← Stock overview
```
