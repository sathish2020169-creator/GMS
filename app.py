"""
Geometry Measurement Service - Employee Tracking System
Run:   python app.py
Open:  http://localhost:5000
Admin: admin / admin123  |  Employee: emp1 / emp123
"""

from flask import (Flask, render_template_string, request, redirect,
                   url_for, session, flash, send_from_directory)
import sqlite3, os, hashlib, uuid
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'gms-secure-2025'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED = {'pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'xls', 'doc', 'docx'}
DB = 'gms.db'

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

def save_file(f):
    if f and f.filename and f.filename.rsplit('.', 1)[-1].lower() in ALLOWED:
        n = f"{uuid.uuid4().hex}.{f.filename.rsplit('.', 1)[-1].lower()}"
        f.save(os.path.join(UPLOAD_FOLDER, n))
        return n
    return None

def now_str():
    return datetime.now().strftime('%Y%m%d%H%M%S')

def gen_job():
    return f"J-{now_str()}"

def gen_batch():
    return f"B-{now_str()}"

def login_req(f):
    @wraps(f)
    def w(*a, **k):
        if 'uid' not in session:
            return redirect(url_for('login'))
        return f(*a, **k)
    return w

def admin_req(f):
    @wraps(f)
    def w(*a, **k):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'al-err')
            return redirect(url_for('dashboard'))
        return f(*a, **k)
    return w

def db_fetch(sql, params=(), one=False):
    c = get_db()
    r = c.execute(sql, params)
    return r.fetchone() if one else r.fetchall()

def db_run(sql, params=()):
    c = get_db()
    c.execute(sql, params)
    c.commit()
    c.close()

# ── DB Init ───────────────────────────────────────────────────────────────────
def init_db():
    c = get_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        name TEXT NOT NULL, role TEXT DEFAULT 'employee',
        designation TEXT, department TEXT, phone TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP);

    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, nickname TEXT, code TEXT UNIQUE NOT NULL,
        address TEXT, gst TEXT, tds_percent REAL DEFAULT 0, active INTEGER DEFAULT 1);

    CREATE TABLE IF NOT EXISTS drivers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT, license_no TEXT,
        license_expiry TEXT, blood_group TEXT,
        emergency_contact TEXT, emergency_phone TEXT,
        photo TEXT, active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP);

    CREATE TABLE IF NOT EXISTS vehicles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_no TEXT NOT NULL, type TEXT, model TEXT,
        driver_id INTEGER, insurance_expiry TEXT,
        fitness_expiry TEXT, active INTEGER DEFAULT 1,
        FOREIGN KEY(driver_id) REFERENCES drivers(id));

    CREATE TABLE IF NOT EXISTS machines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, model TEXT, serial_no TEXT,
        manufacturer TEXT, purchase_date TEXT,
        last_service TEXT, next_service TEXT,
        calibration_due TEXT, specs TEXT,
        photo TEXT, active INTEGER DEFAULT 1);

    CREATE TABLE IF NOT EXISTS job_cards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_no TEXT UNIQUE NOT NULL, batch_no TEXT,
        employee_id INTEGER, customer_id INTEGER,
        designation TEXT, start_date TEXT, start_time TEXT,
        end_date TEXT, end_time TEXT,
        latitude REAL, longitude REAL,
        location_address TEXT, location_district TEXT, location_state TEXT,
        vehicle_id INTEGER, driver_id INTEGER,
        machine_id INTEGER, laptop TEXT,
        fuel_amount REAL, v_probe_used INTEGER DEFAULT 0,
        other_repairs TEXT, status TEXT DEFAULT 'open',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES users(id),
        FOREIGN KEY(customer_id) REFERENCES customers(id),
        FOREIGN KEY(vehicle_id) REFERENCES vehicles(id),
        FOREIGN KEY(driver_id) REFERENCES drivers(id),
        FOREIGN KEY(machine_id) REFERENCES machines(id));

    CREATE TABLE IF NOT EXISTS job_docs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_card_id INTEGER, doc_type TEXT, description TEXT,
        filename TEXT, uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(job_card_id) REFERENCES job_cards(id));

    CREATE TABLE IF NOT EXISTS finance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_card_id INTEGER, po_number TEXT, quotation_no TEXT,
        bill_amount REAL, gst_percent REAL DEFAULT 18,
        gst_amount REAL, total_amount REAL, tds_amount REAL,
        received_amount REAL DEFAULT 0, balance REAL,
        invoice_date TEXT, due_date TEXT, status TEXT DEFAULT 'pending',
        FOREIGN KEY(job_card_id) REFERENCES job_cards(id));

    CREATE TABLE IF NOT EXISTS finance_docs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finance_id INTEGER, doc_type TEXT, description TEXT,
        filename TEXT, version INTEGER DEFAULT 1,
        uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(finance_id) REFERENCES finance(id));

    CREATE TABLE IF NOT EXISTS job_shifts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_card_id INTEGER, batch_no TEXT,
        shift_date TEXT, shift_hrs REAL, stock INTEGER DEFAULT 0,
        is_split INTEGER DEFAULT 0, parent_batch TEXT,
        FOREIGN KEY(job_card_id) REFERENCES job_cards(id));
    """)
    # Default users only — no demo drivers/vehicles/machines
    for u, p, n, r, d in [
        ('admin', 'admin123', 'Administrator', 'admin', 'Admin'),
        ('emp1',  'emp123',   'Rajesh Kumar',  'employee', 'Engineer')
    ]:
        c.execute(
            "INSERT OR IGNORE INTO users(username,password,name,role,designation) VALUES(?,?,?,?,?)",
            (u, hash_pw(p), n, r, d)
        )
    c.commit()
    c.close()

# ── Design ────────────────────────────────────────────────────────────────────
CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#f1f5fb; --card:#fff; --border:#e2e8f5;
  --acc:#2563eb; --acc-l:#eff6ff;
  --sb:#1e3a5f; --sb-a:#3b82f6;
  --txt:#1e293b; --mut:#64748b;
  --grn:#059669; --grn-l:#ecfdf5;
  --amb:#d97706; --amb-l:#fffbeb;
  --red:#dc2626; --red-l:#fef2f2;
  --cyn:#0891b2; --cyn-l:#ecfeff;
  --sh:0 1px 3px rgba(0,0,0,.05),0 4px 16px rgba(30,58,95,.07);
  --r:10px; --sw:238px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--txt);display:flex;min-height:100vh;font-size:14px}
h1,h2,h3{font-family:'Poppins',sans-serif}
a{color:inherit;text-decoration:none}

/* Sidebar */
.sb{width:var(--sw);background:var(--sb);display:flex;flex-direction:column;
    position:fixed;top:0;left:0;height:100vh;z-index:100;
    box-shadow:2px 0 16px rgba(0,0,0,.14)}
.sb-logo{padding:18px 15px;border-bottom:1px solid rgba(255,255,255,.07);
         display:flex;align-items:center;gap:10px}
.sb-ico{width:37px;height:37px;border-radius:9px;
        background:linear-gradient(135deg,#3b82f6,#06b6d4);
        display:flex;align-items:center;justify-content:center;
        font-weight:700;font-size:17px;color:#fff;flex-shrink:0;
        font-family:'Poppins',sans-serif;box-shadow:0 3px 10px rgba(59,130,246,.38)}
.sb-brand{font-size:14.5px;font-weight:700;color:#fff;line-height:1.2}
.sb-brand small{display:block;font-size:9.5px;color:rgba(255,255,255,.33);
                font-weight:400;letter-spacing:1.1px;margin-top:1px}
.nav{flex:1;overflow-y:auto;padding:10px 0}
.nsec{padding:9px 15px 3px;font-size:9.5px;color:rgba(255,255,255,.26);
      text-transform:uppercase;letter-spacing:1.7px}
.nav a{display:flex;align-items:center;gap:8px;padding:9px 12px;margin:1px 7px;
       border-radius:7px;color:rgba(255,255,255,.58);font-size:13px;font-weight:500;transition:.16s}
.nav a:hover{color:#fff;background:rgba(255,255,255,.07)}
.nav a.on{color:#fff;background:var(--sb-a);box-shadow:0 2px 9px rgba(59,130,246,.38)}
.nav a svg{width:14px;height:14px;flex-shrink:0;opacity:.75}
.nav a.on svg{opacity:1}
svg{max-width:100%;max-height:100%}
.chd svg{width:16px;height:16px;flex-shrink:0}
.sb-u{padding:13px 15px;border-top:1px solid rgba(255,255,255,.07);
      font-size:11.5px;color:rgba(255,255,255,.42)}
.sb-u strong{display:block;color:#fff;font-size:13px;font-weight:600;margin-bottom:2px}
.rtag{display:inline-block;padding:1px 8px;border-radius:20px;font-size:9.5px;font-weight:600}
.r-admin{background:rgba(251,191,36,.17);color:#fbbf24}
.r-emp{background:rgba(96,165,250,.17);color:#93c5fd}

/* Main layout */
.main{margin-left:var(--sw);flex:1;display:flex;flex-direction:column;min-height:100vh}
.tb{background:#fff;border-bottom:1px solid var(--border);padding:0 22px;height:56px;
    display:flex;align-items:center;justify-content:space-between;
    position:sticky;top:0;z-index:50;box-shadow:0 1px 5px rgba(30,58,95,.06)}
.tb h2{font-size:19px;font-weight:700;color:var(--txt)}
.tb-r{display:flex;align-items:center;gap:9px}
.page{padding:22px}

/* Cards */
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);
      padding:18px;margin-bottom:16px;box-shadow:var(--sh)}
.chd{font-size:15px;font-weight:700;color:var(--acc);padding-bottom:11px;
     margin-bottom:14px;border-bottom:2px solid var(--border);
     display:flex;align-items:center;gap:7px}

/* Stats */
.stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:13px;margin-bottom:18px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:var(--r);
      padding:16px;position:relative;overflow:hidden;box-shadow:var(--sh);
      transition:.14s;cursor:pointer}
.stat:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(30,58,95,.1)}
.sbar{position:absolute;top:0;left:0;right:0;height:3px;border-radius:var(--r) var(--r) 0 0}
.s-b{background:linear-gradient(90deg,#2563eb,#06b6d4)}
.s-a{background:linear-gradient(90deg,#d97706,#f59e0b)}
.s-g{background:linear-gradient(90deg,#059669,#10b981)}
.s-r{background:linear-gradient(90deg,#dc2626,#f87171)}
.s-c{background:linear-gradient(90deg,#0891b2,#22d3ee)}
.sn{font-size:34px;font-weight:700;color:var(--txt);font-family:'Poppins',sans-serif;
    line-height:1;margin-top:7px}
.sl{font-size:10.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.7px;margin-top:5px}

/* Tables */
.tw{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:#f8faff;padding:9px 12px;text-align:left;font-size:10.5px;
   font-weight:600;color:var(--mut);text-transform:uppercase;
   letter-spacing:.6px;border-bottom:2px solid var(--border)}
td{padding:11px 12px;border-bottom:1px solid #f0f4fb;vertical-align:middle}
tr:last-child td{border:none}
tr:hover td{background:#fafbff}

/* Tags */
.tag{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10.5px;font-weight:600}
.t-open{background:var(--acc-l);color:var(--acc)}
.t-closed{background:var(--grn-l);color:var(--grn)}
.t-pending{background:var(--amb-l);color:var(--amb)}
.t-completed{background:var(--grn-l);color:var(--grn)}
.t-overdue{background:var(--red-l);color:var(--red)}
.t-admin{background:var(--amb-l);color:var(--amb)}
.t-employee{background:var(--acc-l);color:var(--acc)}
.t-info{background:var(--cyn-l);color:var(--cyn)}

/* Forms */
.fg{display:flex;flex-direction:column;gap:4px}
.fg label{font-size:10.5px;font-weight:600;color:var(--mut);
          text-transform:uppercase;letter-spacing:.6px}
.fg input,.fg select,.fg textarea{
  background:#fff;border:1.5px solid var(--border);border-radius:7px;
  color:var(--txt);padding:8px 11px;font-size:13px;
  font-family:inherit;width:100%;transition:.16s}
.fg input:focus,.fg select:focus,.fg textarea:focus{
  outline:none;border-color:var(--acc);box-shadow:0 0 0 3px rgba(37,99,235,.08)}
.fg input[readonly]{background:#f8faff;color:var(--mut)}
.fg textarea{resize:vertical;min-height:68px}
.fgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:13px}
.fgrid .full{grid-column:1/-1}
.flbl{border:2px dashed #c7d7f5;border-radius:7px;padding:9px 13px;text-align:center;
      cursor:pointer;color:var(--mut);font-size:12px;background:#f8faff;
      transition:.16s;display:block}
.flbl:hover{border-color:var(--acc);color:var(--acc);background:var(--acc-l)}
input[type=file]{display:none}
.stitle{font-size:12px;font-weight:700;color:var(--acc);margin:16px 0 10px;
        display:flex;align-items:center;gap:7px;
        text-transform:uppercase;letter-spacing:.4px}
.stitle::after{content:'';flex:1;height:2px;background:var(--border);border-radius:2px}

/* Buttons */
.btn{display:inline-flex;align-items:center;gap:5px;padding:7px 15px;
     border-radius:7px;border:none;font-size:13px;font-weight:600;
     cursor:pointer;text-decoration:none;transition:.16s;font-family:'Inter',sans-serif}
.bp{background:linear-gradient(135deg,#2563eb,#3b82f6);color:#fff;
    box-shadow:0 2px 7px rgba(37,99,235,.26)}
.bp:hover{background:linear-gradient(135deg,#1d4ed8,#2563eb);
          transform:translateY(-1px);box-shadow:0 3px 12px rgba(37,99,235,.36)}
.bs{background:#fff;border:1.5px solid var(--border);color:var(--txt)}
.bs:hover{border-color:var(--acc);color:var(--acc);background:var(--acc-l)}
.bg{background:linear-gradient(135deg,#d97706,#f59e0b);color:#fff;
    box-shadow:0 2px 7px rgba(217,119,6,.2)}
.bg:hover{transform:translateY(-1px)}
.br{background:linear-gradient(135deg,#dc2626,#ef4444);color:#fff}
.bsm{padding:4px 10px;font-size:11.5px;border-radius:6px}
.brow{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}

/* Alerts */
.alert{padding:10px 14px;border-radius:7px;margin-bottom:12px;
       font-size:13px;font-weight:500;display:flex;align-items:center;gap:8px}
.al-ok{background:var(--grn-l);border:1px solid #a7f3d0;color:#065f46}
.al-err{background:var(--red-l);border:1px solid #fca5a5;color:#991b1b}
.al-inf{background:var(--acc-l);border:1px solid #bfdbfe;color:#1d4ed8}

/* Location */
.locbox{background:var(--acc-l);border:1.5px solid #bfdbfe;border-radius:8px;
        padding:11px 13px;display:flex;align-items:center;gap:11px;margin-top:5px}
.locdot{width:9px;height:9px;border-radius:50%;background:var(--acc);
        flex-shrink:0;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.55;transform:scale(1.35)}}
.loctxt{flex:1;font-size:12.5px;color:var(--acc);font-weight:500}
.locco{font-size:10.5px;color:var(--mut);margin-top:1px}

/* Detail table */
.dtbl{width:100%}
.dtbl td{padding:6px 0;border-bottom:1px solid var(--border);font-size:13px}
.dtbl td:first-child{width:40%;color:var(--mut);font-weight:500;
                     font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.dtbl tr:last-child td{border:none}

/* Photos */
.ph-circ{width:68px;height:68px;border-radius:50%;object-fit:cover;border:3px solid var(--border)}
.ph-sq{width:75px;height:55px;border-radius:7px;object-fit:cover;border:2px solid var(--border)}
.docrow{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--border)}
.docrow:last-child{border:none}

/* Utility */
.tc{color:var(--acc)} .tm{color:var(--mut)} .tg{color:var(--grn)}
.tr{color:var(--red)} .ta{color:var(--amb)}
.mt14{margin-top:14px}
</style>
"""

def _ico(d):
    return f'<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;vertical-align:middle">{d}</svg>'

ICO = {
    'd':  _ico('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>'),
    'j':  _ico('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>'),
    'f':  _ico('<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'),
    'ml': _ico('<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>'),
    'e':  _ico('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'),
    'dr': _ico('<circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>'),
    'm':  _ico('<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'),
}

def page(title, body, path=''):
    role = session.get('role', '')
    name = session.get('name', '')

    def na(href, lbl, ic):
        cls = 'on' if (href == path or (len(href) > 1 and href in path)) else ''
        return f'<a href="{href}" class="{cls}">{ic} {lbl}</a>'

    admin_nav = f"""
      <div class="nsec">Admin</div>
      {na('/finance',   'Finance',     ICO['f'])}
      {na('/drivers',   'Drivers',     ICO['dr'])}
      {na('/machines',  'Machines',    ICO['m'])}
      {na('/master',    'Master List', ICO['ml'])}
      {na('/employees', 'Employees',   ICO['e'])}
    """ if role == 'admin' else ''

    rtag = f'<span class="rtag r-{"admin" if role=="admin" else "emp"}">{role.upper()}</span>'
    new_btn = '<a href="/job-cards/new" class="btn bp bsm">+ New Job Card</a>' if role == 'employee' else ''
    alerts = '{% for c,m in get_flashed_messages(with_categories=True) %}<div class="alert {{c}}">{{m}}</div>{% endfor %}'

    tpl = f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GMS - {title}</title>{CSS}</head><body>
<nav class="sb">
  <div class="sb-logo">
    <div class="sb-ico">G</div>
    <div class="sb-brand">GMS<small>Measurement Service</small></div>
  </div>
  <div class="nav">
    <div class="nsec">Main</div>
    {na('/dashboard', 'Dashboard', ICO['d'])}
    {na('/job-cards', 'Job Cards', ICO['j'])}
    {admin_nav}
  </div>
  <div class="sb-u">
    <strong>{name}</strong>{rtag}
    <a href="/logout" style="display:block;margin-top:7px;font-size:11px;color:#f87171">Logout</a>
  </div>
</nav>
<div class="main">
  <div class="tb">
    <h2>{title}</h2>
    <div class="tb-r">
      {new_btn}
      <span style="font-size:11.5px;color:var(--mut)">{{{{ now }}}}</span>
    </div>
  </div>
  <div class="page">{alerts}{body}</div>
</div>
</body></html>"""
    from flask import render_template_string
    return render_template_string(tpl, now=datetime.now().strftime('%d %b %Y  %H:%M'))


def login_page(body):
    alerts = '{% for c,m in get_flashed_messages(with_categories=True) %}<div class="alert {{c}}">{{m}}</div>{% endfor %}'
    tpl = f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GMS - Login</title>{CSS}
<style>
html, body {{
  height: 100%;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eff6ff 0%, #f1f5fb 60%, #ecfdf5 100%);
}}
.lb {{
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 40px 38px;
  width: 420px;
  box-shadow: 0 8px 38px rgba(30,58,95,.11);
}}
.ll {{ text-align: center; margin-bottom: 26px; }}
.li {{
  width: 60px; height: 60px; border-radius: 13px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  display: inline-flex; align-items: center; justify-content: center;
  font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 27px;
  color: #fff; box-shadow: 0 7px 20px rgba(37,99,235,.27);
}}
.ll h1 {{
  font-size: 23px; font-weight: 700; color: var(--acc);
  margin-top: 12px; font-family: 'Poppins', sans-serif;
}}
.ll p {{ color: var(--mut); font-size: 12px; margin-top: 3px; }}
.tabs {{
  display: flex; gap: 4px; background: var(--bg);
  padding: 3px; border-radius: 9px; margin-bottom: 20px;
  border: 1px solid var(--border);
}}
.tab {{
  flex: 1; padding: 8px; text-align: center; border: none;
  border-radius: 6px; cursor: pointer; font-size: 13.5px;
  font-weight: 600; transition: .16s; background: transparent;
  color: var(--mut); font-family: 'Inter', sans-serif;
}}
.tab.on {{ background: var(--acc); color: #fff; box-shadow: 0 2px 7px rgba(37,99,235,.26); }}
.hint {{
  font-size: 11px; color: var(--mut); text-align: center;
  margin-top: 13px; padding: 8px 11px;
  background: var(--bg); border-radius: 7px; border: 1px solid var(--border);
}}
</style>
</head><body>
<div class="lb">
  <div class="ll">
    <div class="li">G</div>
    <h1>GMS Portal</h1>
    <p>Geometry Measurement Service</p>
  </div>
  {alerts}
  {body}
</div>
<script>
function setRole(r, b) {{
  document.getElementById('rt').value = r;
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
}}
</script>
</body></html>"""
    from flask import render_template_string
    return render_template_string(tpl)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('login' if 'uid' not in session else 'dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'uid' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        rt = request.form.get('rt', 'employee')
        u = db_fetch(
            "SELECT * FROM users WHERE username=? AND password=?",
            (request.form['username'].strip(), hash_pw(request.form['password'])),
            one=True
        )
        if u:
            if rt == 'admin' and u['role'] != 'admin':
                flash('Not an admin account.', 'al-err')
            else:
                session.update(uid=u['id'], uname=u['username'], name=u['name'],
                               role=u['role'], desig=u['designation'])
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'al-err')
    form = """
    <div class="tabs">
      <button type="button" class="tab on" onclick="setRole('employee',this)">Employee</button>
      <button type="button" class="tab" onclick="setRole('admin',this)">Admin</button>
    </div>
    <form method="POST">
      <input type="hidden" name="rt" id="rt" value="employee">
      <div class="fg" style="margin-bottom:12px">
        <label>Username</label>
        <input type="text" name="username" required placeholder="Enter username">
      </div>
      <div class="fg" style="margin-bottom:18px">
        <label>Password</label>
        <input type="password" name="password" required placeholder="Enter password">
      </div>
      <button type="submit" class="btn bp" style="width:100%;justify-content:center;padding:10px">
        Sign In
      </button>
    </form>
    <div class="hint">Demo: <strong>admin / admin123</strong> &nbsp;|&nbsp; <strong>emp1 / emp123</strong></div>
    """
    return login_page(form)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_req
def dashboard():
    uid, role = session['uid'], session['role']
    s_jobs = db_fetch("SELECT COUNT(*) FROM job_cards", one=True)[0]
    s_open = db_fetch("SELECT COUNT(*) FROM job_cards WHERE status='open'", one=True)[0]
    s_cust = db_fetch("SELECT COUNT(*) FROM customers WHERE active=1", one=True)[0]
    extra = ''
    if role == 'admin':
        s_emp = db_fetch("SELECT COUNT(*) FROM users WHERE role='employee'", one=True)[0]
        s_fin = db_fetch("SELECT COUNT(*) FROM finance WHERE status='pending'", one=True)[0]
        s_drv = db_fetch("SELECT COUNT(*) FROM drivers WHERE active=1", one=True)[0]
        extra = f"""
        <div class="stat" onclick="location='/employees'">
          <div class="sbar s-c"></div><div class="sn">{s_emp}</div><div class="sl">Employees</div>
        </div>
        <div class="stat" onclick="location='/finance'">
          <div class="sbar s-r"></div><div class="sn">{s_fin}</div><div class="sl">Finance Pending</div>
        </div>
        <div class="stat" onclick="location='/drivers'">
          <div class="sbar s-a"></div><div class="sn">{s_drv}</div><div class="sl">Drivers</div>
        </div>"""
        jobs = db_fetch("""SELECT j.*,u.name emp,c.name cust FROM job_cards j
            LEFT JOIN users u ON j.employee_id=u.id
            LEFT JOIN customers c ON j.customer_id=c.id
            ORDER BY j.created_at DESC LIMIT 8""")
    else:
        jobs = db_fetch("""SELECT j.*,u.name emp,c.name cust FROM job_cards j
            LEFT JOIN users u ON j.employee_id=u.id
            LEFT JOIN customers c ON j.customer_id=c.id
            WHERE j.employee_id=? ORDER BY j.created_at DESC LIMIT 8""", (uid,))

    th_e = '<th>Employee</th>' if role == 'admin' else ''
    rows = ''.join(f"""<tr>
        <td class="tc">{j['job_no']}</td>
        <td>{j['cust'] or '-'}</td>
        {'<td>'+j['emp']+'</td>' if role=='admin' else ''}
        <td>{j['start_date'] or '-'} {j['start_time'] or ''}</td>
        <td>{j['location_address'] or '-'}</td>
        <td><span class="tag t-{j['status']}">{j['status'].upper()}</span></td>
        <td>
          <a href="/job-cards/{j['id']}" class="btn bs bsm">View</a>
          {'<a href="/job-cards/'+str(j["id"])+'/finance" class="btn bg bsm">Finance</a>' if role=='admin' else ''}
        </td></tr>""" for j in jobs)

    body = f"""
    <div class="stats">
      <div class="stat" onclick="location='/job-cards'">
        <div class="sbar s-b"></div><div class="sn">{s_jobs}</div><div class="sl">Total Jobs</div>
      </div>
      <div class="stat" onclick="location='/job-cards'">
        <div class="sbar s-a"></div><div class="sn">{s_open}</div><div class="sl">Open Jobs</div>
      </div>
      <div class="stat">
        <div class="sbar s-g"></div><div class="sn">{s_cust}</div><div class="sl">Customers</div>
      </div>
      {extra}
    </div>
    <div class="card">
      <div class="chd">{ICO['j']} Recent Job Cards</div>
      <div class="tw"><table>
        <thead><tr><th>Job No</th><th>Customer</th>{th_e}<th>Start</th><th>Location</th><th>Status</th><th></th></tr></thead>
        <tbody>{rows or '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--mut)">No records yet.</td></tr>'}</tbody>
      </table></div>
    </div>"""
    return page('Dashboard', body, '/dashboard')


# ── Job Cards ─────────────────────────────────────────────────────────────────
@app.route('/job-cards')
@login_req
def job_cards():
    uid, role = session['uid'], session['role']
    if role == 'admin':
        jobs = db_fetch("""SELECT j.*,u.name emp,c.name cust FROM job_cards j
            LEFT JOIN users u ON j.employee_id=u.id
            LEFT JOIN customers c ON j.customer_id=c.id
            ORDER BY j.created_at DESC""")
    else:
        jobs = db_fetch("""SELECT j.*,u.name emp,c.name cust FROM job_cards j
            LEFT JOIN users u ON j.employee_id=u.id
            LEFT JOIN customers c ON j.customer_id=c.id
            WHERE j.employee_id=? ORDER BY j.created_at DESC""", (uid,))

    th_e = '<th>Employee</th>' if role == 'admin' else ''
    rows = ''.join(f"""<tr>
        <td class="tc">{j['job_no']}</td>
        <td><small class="tm">{j['batch_no'] or '-'}</small></td>
        <td>{j['cust'] or '-'}</td>
        {'<td>'+j['emp']+'</td>' if role=='admin' else ''}
        <td>{j['start_date'] or '-'}</td>
        <td>{j['end_date'] or '-'}</td>
        <td>{j['location_address'] or '-'}</td>
        <td><span class="tag t-{j['status']}">{j['status'].upper()}</span></td>
        <td>
          <a href="/job-cards/{j['id']}" class="btn bs bsm">View</a>
          {'<a href="/job-cards/'+str(j["id"])+'/finance" class="btn bg bsm">Finance</a>' if role=='admin' else ''}
        </td></tr>""" for j in jobs)

    body = f"""
    <div style="display:flex;justify-content:flex-end;margin-bottom:13px">
      <a href="/job-cards/new" class="btn bp">+ New Job Card</a>
    </div>
    <div class="card">
      <div class="chd">{ICO['j']} All Job Cards</div>
      <div class="tw"><table>
        <thead><tr><th>Job No</th><th>Batch</th><th>Customer</th>{th_e}<th>Start</th><th>End</th><th>Location</th><th>Status</th><th></th></tr></thead>
        <tbody>{rows or '<tr><td colspan="9" style="text-align:center;padding:24px;color:var(--mut)">No records.</td></tr>'}</tbody>
      </table></div>
    </div>"""
    return page('Job Cards', body, '/job-cards')


@app.route('/job-cards/new', methods=['GET', 'POST'])
@login_req
def new_job_card():
    uid = session['uid']
    custs = db_fetch("SELECT * FROM customers WHERE active=1 ORDER BY name")
    vehs  = db_fetch("SELECT * FROM vehicles WHERE active=1 ORDER BY reg_no")
    drvs  = db_fetch("SELECT * FROM drivers WHERE active=1 ORDER BY name")
    machs = db_fetch("SELECT * FROM machines WHERE active=1")
    user  = db_fetch("SELECT * FROM users WHERE id=?", (uid,), one=True)

    if request.method == 'POST':
        f = request.form
        jno, bno = gen_job(), gen_batch()
        conn = get_db()

        # If employee typed a new customer, create it first
        customer_id = f.get('customer_id')
        if f.get('new_cust_name'):
            # Auto-generate code from name if not provided
            cname = f['new_cust_name'].strip()
            ccode = f.get('new_cust_code', '').strip() or cname[:4].upper().replace(' ', '')
            try:
                conn.execute(
                    "INSERT INTO customers(name,nickname,code,tds_percent,address,gst) VALUES(?,?,?,?,?,?)",
                    (cname, f.get('new_cust_nick', ''), ccode,
                     f.get('new_cust_tds') or 0,
                     f.get('new_cust_addr', ''), f.get('new_cust_gst', '')))
                customer_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            except Exception:
                # Code conflict — append timestamp
                ccode = ccode + now_str()[-4:]
                conn.execute(
                    "INSERT INTO customers(name,nickname,code,tds_percent,address,gst) VALUES(?,?,?,?,?,?)",
                    (cname, f.get('new_cust_nick', ''), ccode,
                     f.get('new_cust_tds') or 0,
                     f.get('new_cust_addr', ''), f.get('new_cust_gst', '')))
                customer_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute("""INSERT INTO job_cards
            (job_no,batch_no,employee_id,customer_id,designation,
             start_date,start_time,end_date,end_time,
             latitude,longitude,location_address,location_district,location_state,
             vehicle_id,driver_id,machine_id,laptop,fuel_amount,v_probe_used,other_repairs)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (jno, bno, uid, customer_id, user['designation'],
             f.get('start_date'), f.get('start_time'), f.get('end_date'), f.get('end_time'),
             f.get('lat') or None, f.get('lng') or None,
             f.get('location_address'), f.get('location_district'), f.get('location_state'),
             f.get('vehicle_id') or None, f.get('driver_id') or None,
             f.get('machine_id') or None, f.get('laptop'),
             f.get('fuel_amount') or None,
             1 if f.get('v_probe') else 0,
             f.get('other_repairs')))
        jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for dt in ['work_timing', 'hotel_bill', 'food_bill', 'taxi_bill', 'other1', 'other2']:
            fn = save_file(request.files.get(dt))
            if fn:
                conn.execute(
                    "INSERT INTO job_docs(job_card_id,doc_type,description,filename) VALUES(?,?,?,?)",
                    (jid, dt, f.get(f'{dt}_desc', dt), fn))
        conn.commit()
        conn.close()
        flash(f'Job Card {jno} created — Batch: {bno}', 'al-ok')
        return redirect(url_for('view_job', jid=jid))

    now = datetime.now()
    # Vehicle and Driver are independent dropdowns
    veh_opts = '<option value="">-- Select Vehicle --</option>' + ''.join(
        f'<option value="{v["id"]}">{v["reg_no"]} - {v["model"] or ""}</option>' for v in vehs)
    drv_opts = '<option value="">-- Select Driver --</option>' + ''.join(
        f'<option value="{d["id"]}">{d["name"]} ({d["phone"] or "no phone"})</option>' for d in drvs)
    cust_opts = '<option value="">-- Select Existing --</option>' + ''.join(
        f'<option value="{c["id"]}">{c["name"]} ({c["nickname"] or c["code"]})</option>' for c in custs)
    mach_opts = '<option value="">-- Select Machine --</option>' + ''.join(
        f'<option value="{m["id"]}">{m["name"]} - {m["model"] or ""}</option>' for m in machs)
    doc_html = ''.join(f"""
        <div class="fg">
          <label>{lbl}</label>
          <input type="text" name="{n}_desc" placeholder="Description (optional)">
          <label class="flbl" for="{n}f">Browse / Upload</label>
          <input type="file" id="{n}f" name="{n}">
        </div>"""
        for n, lbl in [
            ('work_timing', 'Work Timing Sheet'), ('hotel_bill', 'Hotel Bill'),
            ('food_bill', 'Food Bill'), ('taxi_bill', 'Taxi Bill'),
            ('other1', 'Other Doc 1'), ('other2', 'Other Doc 2')
        ])

    body = f"""
    <div class="card">
      <div class="chd">{ICO['j']} Create Job Card</div>
      <form method="POST" enctype="multipart/form-data">

        <div class="stitle">Employee (Auto-filled)</div>
        <div class="fgrid">
          <div class="fg"><label>Name</label><input value="{user['name']}" readonly></div>
          <div class="fg"><label>Designation</label><input value="{user['designation'] or ''}" readonly></div>
        </div>

        <div class="stitle">Customer Details</div>
        <div style="background:var(--acc-l);border:1.5px solid #bfdbfe;border-radius:8px;padding:13px 15px;margin-bottom:13px">
          <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px">
            <label style="font-size:12px;font-weight:600;color:var(--acc)">
              <input type="radio" name="cust_mode" value="existing" checked
                     onchange="toggleCust(this.value)" style="accent-color:var(--acc);width:auto;margin-right:4px">
              Select Existing Customer
            </label>
            <label style="font-size:12px;font-weight:600;color:var(--acc)">
              <input type="radio" name="cust_mode" value="new"
                     onchange="toggleCust(this.value)" style="accent-color:var(--acc);width:auto;margin-right:4px">
              Add New Customer
            </label>
          </div>
          <div id="cust_existing">
            <div class="fg"><label>Select Customer *</label>
              <select name="customer_id" id="cust_sel">{cust_opts}</select></div>
          </div>
          <div id="cust_new" style="display:none">
            <div class="fgrid">
              <div class="fg"><label>Company Name *</label>
                <input name="new_cust_name" id="new_cust_name" placeholder="e.g. Wheels India Ltd"></div>
              <div class="fg"><label>Short Code</label>
                <input name="new_cust_code" placeholder="e.g. WI-001 (auto if blank)"></div>
              <div class="fg"><label>Nickname</label>
                <input name="new_cust_nick" placeholder="Short name"></div>
              <div class="fg"><label>TDS %</label>
                <input name="new_cust_tds" type="number" step="0.1" value="10"></div>
              <div class="fg"><label>Address</label>
                <input name="new_cust_addr" placeholder="Office address"></div>
              <div class="fg"><label>GST Number</label>
                <input name="new_cust_gst" placeholder="GST No"></div>
            </div>
          </div>
        </div>

        <div class="stitle">Timing</div>
        <div class="fgrid">
          <div class="fg"><label>Start Date *</label>
            <input type="date" name="start_date" value="{now.strftime('%Y-%m-%d')}" required></div>
          <div class="fg"><label>Start Time (24hr)</label>
            <input type="time" name="start_time" value="{now.strftime('%H:%M')}"></div>
          <div class="fg"><label>End Date</label>
            <input type="date" name="end_date"></div>
          <div class="fg"><label>End Time (24hr)</label>
            <input type="time" name="end_time"></div>
        </div>

        <div class="stitle">Location (GPS Auto-Capture)</div>
        <div class="locbox" id="locbox">
          <div class="locdot"></div>
          <div style="flex:1">
            <div class="loctxt" id="ltxt">Detecting your location...</div>
            <div class="locco" id="lco"></div>
          </div>
          <button type="button" class="btn bs bsm" onclick="getLoc()">Retry</button>
        </div>
        <input type="hidden" name="lat" id="lat">
        <input type="hidden" name="lng" id="lng">
        <div class="fgrid mt14">
          <div class="fg"><label>Address / Site</label>
            <input type="text" name="location_address" id="ladr" placeholder="Auto-filled from GPS"></div>
          <div class="fg"><label>District</label>
            <input type="text" name="location_district" id="ldist" placeholder="Auto-filled"></div>
          <div class="fg"><label>State</label>
            <input type="text" name="location_state" id="lstate" placeholder="Auto-filled"></div>
        </div>

        <div class="stitle">Vehicle and Driver (Independent)</div>
        <div class="fgrid">
          <div class="fg"><label>Vehicle</label>
            <select name="vehicle_id">{veh_opts}</select></div>
          <div class="fg"><label>Driver</label>
            <select name="driver_id">{drv_opts}</select></div>
          <div class="fg"><label>Fuel Amount (Rs.)</label>
            <input type="number" name="fuel_amount" placeholder="0.00" step="0.01"></div>
        </div>

        <div class="stitle">Machine and Equipment</div>
        <div class="fgrid">
          <div class="fg"><label>Machine</label>
            <select name="machine_id">{mach_opts}</select></div>
          <div class="fg"><label>Laptop</label>
            <input type="text" name="laptop" placeholder="Model / serial"></div>
          <div class="fg" style="padding-top:18px">
            <label style="display:flex;gap:7px;align-items:center;cursor:pointer;
                          text-transform:none;font-size:13px;font-weight:500;color:var(--txt)">
              <input type="checkbox" name="v_probe" style="width:auto;accent-color:var(--acc)">
              V-Probe Used
            </label>
          </div>
        </div>

        <div class="stitle">Other / Repairs</div>
        <div class="fgrid">
          <div class="fg full">
            <textarea name="other_repairs" placeholder="Repair, puncher, misc expenses..."></textarea>
          </div>
        </div>

        <div class="stitle">Documents</div>
        <div class="fgrid">{doc_html}</div>

        <div class="brow">
          <button type="submit" class="btn bp">Create Job Card</button>
          <a href="/job-cards" class="btn bs">Cancel</a>
        </div>
      </form>
    </div>

    <script>
    function toggleCust(mode) {{
      document.getElementById('cust_existing').style.display = mode === 'existing' ? '' : 'none';
      document.getElementById('cust_new').style.display = mode === 'new' ? '' : 'none';
      document.getElementById('cust_sel').required = mode === 'existing';
      document.getElementById('new_cust_name').required = mode === 'new';
    }}
    function getLoc() {{
      document.getElementById('ltxt').textContent = 'Detecting location...';
      if (!navigator.geolocation) {{
        document.getElementById('ltxt').textContent = 'GPS not supported. Enter manually.';
        return;
      }}
      navigator.geolocation.getCurrentPosition(function(p) {{
        var la = p.coords.latitude.toFixed(6), ln = p.coords.longitude.toFixed(6);
        document.getElementById('lat').value = la;
        document.getElementById('lng').value = ln;
        document.getElementById('lco').textContent = la + ', ' + ln;
        document.getElementById('ltxt').textContent = 'Location captured!';
        fetch('https://nominatim.openstreetmap.org/reverse?format=json&lat=' + la + '&lon=' + ln)
          .then(r => r.json()).then(d => {{
            var a = d.address || {{}};
            var site = a.road || a.suburb || a.neighbourhood || a.village || a.town || '';
            var dist = a.county || a.city_district || a.district || a.city || '';
            var state = a.state || '';
            var disp = d.display_name ? d.display_name.split(',').slice(0, 3).join(', ') : site;
            document.getElementById('ladr').value = disp || site;
            document.getElementById('ldist').value = dist;
            document.getElementById('lstate').value = state;
            document.getElementById('ltxt').textContent = 'Location: ' + (a.city || a.town || a.village || dist || 'Captured');
          }}).catch(function() {{
            document.getElementById('ltxt').textContent = 'Coordinates saved (address lookup failed).';
          }});
      }}, function() {{
        document.getElementById('ltxt').textContent = 'Location denied - please enter manually.';
        var b = document.getElementById('locbox');
        b.style.background = 'var(--red-l)';
        b.style.borderColor = '#fca5a5';
      }}, {{timeout: 10000}});
    }}
    window.onload = getLoc;
    </script>"""
    return page('New Job Card', body, '/job-cards')


@app.route('/job-cards/<int:jid>')
@login_req
def view_job(jid):
    j = db_fetch("""SELECT j.*,u.name emp,u.designation empd,
        c.name cust,c.code ccode,c.nickname cnick,
        v.reg_no vreg,v.model vmod,
        d.name dname,d.phone dph,d.license_no dlic,d.blood_group dblood,d.emergency_contact demg,
        m.name mname,m.model mmod,m.serial_no mser,m.calibration_due mcal,m.next_service mnxt
        FROM job_cards j
        LEFT JOIN users u ON j.employee_id=u.id
        LEFT JOIN customers c ON j.customer_id=c.id
        LEFT JOIN vehicles v ON j.vehicle_id=v.id
        LEFT JOIN drivers d ON j.driver_id=d.id
        LEFT JOIN machines m ON j.machine_id=m.id
        WHERE j.id=?""", (jid,), one=True)
    if not j:
        flash('Not found.', 'al-err')
        return redirect(url_for('job_cards'))
    if session['role'] != 'admin' and j['employee_id'] != session['uid']:
        flash('Access denied.', 'al-err')
        return redirect(url_for('job_cards'))

    docs   = db_fetch("SELECT * FROM job_docs WHERE job_card_id=?", (jid,))
    shifts = db_fetch("SELECT * FROM job_shifts WHERE job_card_id=? ORDER BY shift_date", (jid,))
    role   = session['role']

    gps = ''
    if j['latitude']:
        gps = f"""
        <div class="locbox" style="margin-top:7px">
          <div class="locdot"></div>
          <div style="flex:1">
            <div class="loctxt">GPS Location Captured</div>
            <div class="locco">{j['latitude']}, {j['longitude']}</div>
          </div>
          <a href="https://maps.google.com/?q={j['latitude']},{j['longitude']}"
             target="_blank" class="btn bs bsm">Open Maps</a>
        </div>"""

    admin_btns = f"""
      <a href="/job-cards/{jid}/finance" class="btn bg bsm">Finance</a>
      <a href="/job-cards/{jid}/close" class="btn bsm"
         style="background:var(--grn);color:#fff"
         onclick="return confirm('Close this job?')">Close Job</a>
    """ if role == 'admin' else ''

    shift_rows = ''.join(f"""<tr>
        <td class="ta">{s['batch_no']}</td>
        <td>{s['shift_date']}</td>
        <td>{s['shift_hrs']} hrs</td>
        <td>{s['stock']}</td>
        <td>{'Yes (' + s['parent_batch'] + ')' if s['is_split'] else '-'}</td>
        </tr>""" for s in shifts)

    doc_rows = ''.join(f"""
        <div class="docrow">
          <span style="font-size:18px;flex-shrink:0">&#128196;</span>
          <div style="flex:1">
            <div style="font-size:13px">{d['description'] or d['doc_type']}</div>
            <div style="font-size:10.5px;color:var(--mut)">{d['doc_type']} &middot; {d['uploaded_at'][:16]}</div>
          </div>
          <a href="/uploads/{d['filename']}" target="_blank" class="btn bs bsm">Open</a>
        </div>""" for d in docs)

    shift_section = ''
    if role == 'admin':
        shift_section = f"""
        <div class="card mt14">
          <div class="chd">Shift Records</div>
          <form method="POST" action="/job-cards/{jid}/add-shift"
                style="display:flex;gap:9px;flex-wrap:wrap;align-items:flex-end;margin-bottom:12px">
            <div class="fg" style="flex:1;min-width:130px">
              <label>Date</label><input type="date" name="shift_date" required>
            </div>
            <div class="fg" style="flex:1;min-width:90px">
              <label>Shift Hrs</label><input type="number" name="shift_hrs" step="0.5" min="0" required>
            </div>
            <div class="fg" style="flex:1;min-width:75px">
              <label>Stock</label><input type="number" name="stock" value="0">
            </div>
            <button type="submit" class="btn bp bsm">Add Shift</button>
          </form>
          {'<div class="tw"><table><thead><tr><th>Batch</th><th>Date</th><th>Hours</th><th>Stock</th><th>Split</th></tr></thead><tbody>' + shift_rows + '</tbody></table></div>' if shifts else '<p style="color:var(--mut);font-size:13px">No shifts yet.</p>'}
        </div>"""

    body = f"""
    <div class="brow" style="margin-bottom:14px">
      <a href="/job-cards" class="btn bs bsm">Back to List</a>
      {admin_btns}
    </div>
    <div class="card">
      <div class="chd">{ICO['j']} {j['job_no']}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
        <span class="tag t-info">{j['job_no']}</span>
        <span class="tag t-{j['status']}">{j['status'].upper()}</span>
        <span style="font-size:11.5px;color:var(--mut)">Batch: {j['batch_no'] or '-'}</span>
        <span style="font-size:11.5px;color:var(--mut)">Created: {j['created_at'][:16]}</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div>
          <div class="stitle">Employee and Customer</div>
          <table class="dtbl">
            <tr><td>Employee</td><td><strong>{j['emp']}</strong></td></tr>
            <tr><td>Designation</td><td>{j['empd'] or '-'}</td></tr>
            <tr><td>Customer</td><td><strong>{j['cust'] or '-'}</strong></td></tr>
            <tr><td>Code</td><td>{j['ccode'] or '-'}{' (' + j['cnick'] + ')' if j['cnick'] else ''}</td></tr>
          </table>
          <div class="stitle">Timing</div>
          <table class="dtbl">
            <tr><td>Start</td><td>{j['start_date'] or '-'} {j['start_time'] or ''}</td></tr>
            <tr><td>End</td><td>{j['end_date'] or '-'} {j['end_time'] or ''}</td></tr>
          </table>
        </div>
        <div>
          <div class="stitle">Location</div>
          <table class="dtbl">
            <tr><td>Address</td><td>{j['location_address'] or '-'}</td></tr>
            <tr><td>District</td><td>{j['location_district'] or '-'}</td></tr>
            <tr><td>State</td><td>{j['location_state'] or '-'}</td></tr>
          </table>
          {gps}
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:12px">
        <div>
          <div class="stitle">Driver Details</div>
          <table class="dtbl">
            <tr><td>Name</td><td><strong>{j['dname'] or '-'}</strong></td></tr>
            <tr><td>Phone</td><td>{j['dph'] or '-'}</td></tr>
            <tr><td>License</td><td>{j['dlic'] or '-'}</td></tr>
            <tr><td>Blood Group</td><td>{j['dblood'] or '-'}</td></tr>
            <tr><td>Emergency</td><td>{j['demg'] or '-'}</td></tr>
            <tr><td>Vehicle</td><td>{(j['vreg'] + ' ' + j['vmod']) if j['vreg'] else '-'}</td></tr>
          </table>
        </div>
        <div>
          <div class="stitle">Machine Details</div>
          <table class="dtbl">
            <tr><td>Machine</td><td><strong>{j['mname'] or '-'}</strong></td></tr>
            <tr><td>Model</td><td>{j['mmod'] or '-'}</td></tr>
            <tr><td>Serial No</td><td>{j['mser'] or '-'}</td></tr>
            <tr><td>Calibration Due</td><td>{j['mcal'] or '-'}</td></tr>
            <tr><td>Next Service</td><td>{j['mnxt'] or '-'}</td></tr>
            <tr><td>V-Probe</td><td>{'Yes - Used' if j['v_probe_used'] else 'Not Used'}</td></tr>
            <tr><td>Laptop</td><td>{j['laptop'] or '-'}</td></tr>
            <tr><td>Fuel</td><td>{'Rs.' + str(j['fuel_amount']) if j['fuel_amount'] else '-'}</td></tr>
          </table>
        </div>
      </div>
      {'<div class="stitle">Other / Repairs</div><p style="font-size:13px">' + j['other_repairs'] + '</p>' if j['other_repairs'] else ''}
    </div>
    {shift_section}
    <div class="card mt14">
      <div class="chd">Documents</div>
      {doc_rows or '<p style="color:var(--mut);font-size:13px">No documents uploaded.</p>'}
    </div>"""
    return page(f'Job: {j["job_no"]}', body, '/job-cards')


@app.route('/job-cards/<int:jid>/add-shift', methods=['POST'])
@login_req
@admin_req
def add_shift(jid):
    j = db_fetch("SELECT batch_no FROM job_cards WHERE id=?", (jid,), one=True)
    bno = (j['batch_no'] or 'B') + f"-{now_str()}"
    db_run(
        "INSERT INTO job_shifts(job_card_id,batch_no,shift_date,shift_hrs,stock) VALUES(?,?,?,?,?)",
        (jid, bno, request.form['shift_date'], request.form['shift_hrs'], request.form.get('stock', 0)))
    flash('Shift added.', 'al-ok')
    return redirect(url_for('view_job', jid=jid))


@app.route('/job-cards/<int:jid>/close')
@login_req
@admin_req
def close_job(jid):
    db_run("UPDATE job_cards SET status='closed' WHERE id=?", (jid,))
    flash('Job card closed.', 'al-ok')
    return redirect(url_for('view_job', jid=jid))


# ── Finance ───────────────────────────────────────────────────────────────────
@app.route('/finance')
@login_req
@admin_req
def finance_list():
    recs = db_fetch("""SELECT f.*,j.job_no,c.name cust FROM finance f
        JOIN job_cards j ON f.job_card_id=j.id
        JOIN customers c ON j.customer_id=c.id ORDER BY f.id DESC""")
    rows = ''.join(f"""<tr>
        <td class="tc">{r['job_no']}</td>
        <td>{r['cust']}</td>
        <td>{r['po_number'] or '-'}</td>
        <td>Rs.{r['bill_amount'] or 0}</td>
        <td>{r['gst_percent'] or 18}%</td>
        <td><strong>Rs.{r['total_amount'] or 0}</strong></td>
        <td class="tg">Rs.{r['received_amount'] or 0}</td>
        <td class="{'tr' if (r['balance'] or 0) > 0 else 'tg'}">Rs.{r['balance'] or 0}</td>
        <td>{r['invoice_date'] or '-'}</td>
        <td><span class="tag t-{r['status']}">{r['status'].upper()}</span></td>
        <td><a href="/job-cards/{r['job_card_id']}/finance" class="btn bs bsm">Edit</a></td>
        </tr>""" for r in recs)
    body = f"""
    <div class="card">
      <div class="chd">{ICO['f']} Finance Records</div>
      <div class="tw"><table>
        <thead><tr><th>Job No</th><th>Customer</th><th>PO</th><th>Bill</th><th>GST</th>
          <th>Total</th><th>Received</th><th>Balance</th><th>Invoice Date</th><th>Status</th><th></th></tr></thead>
        <tbody>{rows or '<tr><td colspan="11" style="text-align:center;padding:24px;color:var(--mut)">No finance records.</td></tr>'}</tbody>
      </table></div>
    </div>"""
    return page('Finance', body, '/finance')


@app.route('/job-cards/<int:jid>/finance', methods=['GET', 'POST'])
@login_req
@admin_req
def job_finance(jid):
    job  = db_fetch("""SELECT j.*,c.name cust,c.tds_percent tds FROM job_cards j
                       JOIN customers c ON j.customer_id=c.id WHERE j.id=?""", (jid,), one=True)
    fin  = db_fetch("SELECT * FROM finance WHERE job_card_id=?", (jid,), one=True)
    fdocs = db_fetch("SELECT * FROM finance_docs WHERE finance_id=?", (fin['id'] if fin else -1,))

    if request.method == 'POST':
        f = request.form
        bill = float(f.get('bill_amount') or 0)
        gp   = float(f.get('gst_percent') or 18)
        ga   = round(bill * gp / 100, 2)
        total = round(bill + ga, 2)
        tds  = float(f.get('tds_amount') or 0)
        recv = float(f.get('received_amount') or 0)
        bal  = round(total - tds - recv, 2)
        conn = get_db()
        if fin:
            conn.execute("""UPDATE finance SET po_number=?,quotation_no=?,bill_amount=?,gst_percent=?,
                gst_amount=?,total_amount=?,tds_amount=?,received_amount=?,balance=?,
                invoice_date=?,due_date=?,status=? WHERE id=?""",
                (f.get('po_number'), f.get('quotation_no'), bill, gp, ga, total, tds, recv, bal,
                 f.get('invoice_date'), f.get('due_date'), f.get('status'), fin['id']))
            fid = fin['id']
        else:
            conn.execute("""INSERT INTO finance(job_card_id,po_number,quotation_no,bill_amount,gst_percent,
                gst_amount,total_amount,tds_amount,received_amount,balance,invoice_date,due_date,status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (jid, f.get('po_number'), f.get('quotation_no'), bill, gp, ga, total, tds, recv, bal,
                 f.get('invoice_date'), f.get('due_date'), f.get('status', 'pending')))
            fid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for dt in ['quotation', 'po', 'tax_invoice', 'other1', 'other2']:
            fn = save_file(request.files.get(dt))
            if fn:
                ex = conn.execute(
                    "SELECT MAX(version) FROM finance_docs WHERE finance_id=? AND doc_type=?",
                    (fid, dt)).fetchone()[0]
                conn.execute(
                    "INSERT INTO finance_docs(finance_id,doc_type,description,filename,version) VALUES(?,?,?,?,?)",
                    (fid, dt, f.get(f'{dt}_desc', dt), fn, (ex or 0) + 1))
        conn.commit()
        conn.close()
        flash('Finance saved.', 'al-ok')
        return redirect(url_for('job_finance', jid=jid))

    def fv(k, d=''):
        return fin[k] if fin and fin[k] is not None else d

    st_opts = ''.join(
        f'<option value="{s}" {"selected" if fv("status", "pending") == s else ""}>{s.upper()}</option>'
        for s in ['pending', 'invoiced', 'completed', 'overdue'])
    doc_html = ''.join(f"""
        <div class="fg">
          <label>{lb} (Revisable)</label>
          <input type="text" name="{n}_desc" placeholder="Description">
          <label class="flbl" for="{n}f">Upload / Revise</label>
          <input type="file" id="{n}f" name="{n}">
        </div>"""
        for n, lb in [
            ('quotation', 'Quotation'), ('po', 'PO'),
            ('tax_invoice', 'Tax Invoice'), ('other1', 'Other 1'), ('other2', 'Other 2')
        ])
    doc_hist = ''.join(f"""
        <div class="docrow">
          <span style="font-size:18px">&#128196;</span>
          <div style="flex:1">
            <div style="font-size:13px">{d['description'] or d['doc_type']}
              <span style="font-size:10.5px;color:var(--mut)"> v{d['version']}</span></div>
            <div style="font-size:10.5px;color:var(--mut)">{d['uploaded_at'][:16]}</div>
          </div>
          <a href="/uploads/{d['filename']}" target="_blank" class="btn bs bsm">Open</a>
        </div>""" for d in fdocs)

    body = f"""
    <div class="brow" style="margin-bottom:13px">
      <a href="/job-cards/{jid}" class="btn bs bsm">Back to Job Card</a>
      <a href="/finance" class="btn bs bsm">Finance List</a>
    </div>
    <div class="card">
      <div class="chd">{ICO['f']} Finance - {job['cust']} / {job['job_no']}</div>
      <form method="POST" enctype="multipart/form-data">
        <div class="fgrid">
          <div class="fg"><label>PO Number</label>
            <input type="text" name="po_number" value="{fv('po_number')}"></div>
          <div class="fg"><label>Quotation No</label>
            <input type="text" name="quotation_no" value="{fv('quotation_no')}"></div>
          <div class="fg"><label>Bill Amount (Rs.)</label>
            <input type="number" name="bill_amount" id="ba" step="0.01"
                   value="{fv('bill_amount')}" oninput="calc()"></div>
          <div class="fg"><label>GST %</label>
            <input type="number" name="gst_percent" id="gp" step="0.01"
                   value="{fv('gst_percent', 18)}" oninput="calc()"></div>
          <div class="fg"><label>GST Amount</label>
            <input type="number" name="gst_amount" id="ga" step="0.01"
                   value="{fv('gst_amount')}" readonly></div>
          <div class="fg"><label>Total (Rs.)</label>
            <input type="number" name="total_amount" id="ta" step="0.01"
                   value="{fv('total_amount')}" readonly></div>
          <div class="fg"><label>TDS (Rs.) <small class="tm">{job['tds']}%</small></label>
            <input type="number" name="tds_amount" id="tds" step="0.01"
                   value="{fv('tds_amount')}" oninput="calc()"></div>
          <div class="fg"><label>Received (Rs.)</label>
            <input type="number" name="received_amount" id="recv" step="0.01"
                   value="{fv('received_amount', 0)}" oninput="calc()"></div>
          <div class="fg"><label>Balance (Rs.)</label>
            <input type="number" name="balance" id="bal" step="0.01"
                   value="{fv('balance')}" readonly></div>
          <div class="fg"><label>Invoice Date</label>
            <input type="date" name="invoice_date" value="{fv('invoice_date')}"></div>
          <div class="fg"><label>Due Date</label>
            <input type="date" name="due_date" value="{fv('due_date')}"></div>
          <div class="fg"><label>Status</label>
            <select name="status">{st_opts}</select></div>
        </div>
        <div class="stitle">Documents</div>
        <div class="fgrid">{doc_html}</div>
        <div class="brow">
          <button type="submit" class="btn bp">Save Finance</button>
        </div>
      </form>
    </div>
    {('<div class="card mt14"><div class="chd">Document History</div>' + doc_hist + '</div>') if fdocs else ''}
    <script>
    function calc() {{
      var b = parseFloat(document.getElementById('ba').value) || 0;
      var g = parseFloat(document.getElementById('gp').value) || 18;
      var t = parseFloat(document.getElementById('tds').value) || 0;
      var r = parseFloat(document.getElementById('recv').value) || 0;
      var ga = Math.round(b * g / 100 * 100) / 100;
      var tot = Math.round((b + ga) * 100) / 100;
      document.getElementById('ga').value = ga;
      document.getElementById('ta').value = tot;
      document.getElementById('bal').value = Math.round((tot - t - r) * 100) / 100;
    }}
    </script>"""
    return page('Finance', body, '/finance')


# ── Drivers ───────────────────────────────────────────────────────────────────
@app.route('/drivers', methods=['GET', 'POST'])
@login_req
@admin_req
def drivers():
    if request.method == 'POST':
        f = request.form
        fn = save_file(request.files.get('photo'))
        conn = get_db()
        conn.execute("""INSERT INTO drivers(name,phone,license_no,license_expiry,
            blood_group,emergency_contact,emergency_phone,photo) VALUES(?,?,?,?,?,?,?,?)""",
            (f['name'], f.get('phone'), f.get('license_no'), f.get('license_expiry') or None,
             f.get('blood_group'), f.get('emergency_contact'), f.get('emergency_phone'), fn))
        conn.commit()
        conn.close()
        flash('Driver added.', 'al-ok')
        return redirect(url_for('drivers'))

    drvs = db_fetch("""SELECT d.*,v.reg_no vreg,v.model vmod FROM drivers d
        LEFT JOIN vehicles v ON v.driver_id=d.id WHERE d.active=1 ORDER BY d.name""")

    def ph(d):
        if d['photo']:
            return f'<img src="/uploads/{d["photo"]}" class="ph-circ">'
        return '<div style="width:42px;height:42px;border-radius:50%;background:var(--acc-l);display:flex;align-items:center;justify-content:center;font-size:18px;color:var(--acc)">D</div>'

    rows = ''.join(f"""<tr>
        <td>{ph(d)}</td>
        <td><strong>{d['name']}</strong></td>
        <td>{d['phone'] or '-'}</td>
        <td>{d['license_no'] or '-'}</td>
        <td>{d['license_expiry'] or '-'}</td>
        <td><span class="tag t-info">{d['blood_group'] or '-'}</span></td>
        <td>{d['emergency_contact'] or '-'}{'<br><small class="tm">' + d['emergency_phone'] + '</small>' if d['emergency_phone'] else ''}</td>
        <td>{(d['vreg'] + ' ' + d['vmod']) if d['vreg'] else '<span class="tm">Unassigned</span>'}</td>
        <td style="white-space:nowrap">
          <a href="/drivers/{d['id']}" class="btn bs bsm">Edit</a>
          <a href="/drivers/{d['id']}/delete" class="btn br bsm"
             onclick="return confirm('Delete this driver?')">Delete</a>
        </td>
        </tr>""" for d in drvs)

    bgs = ''.join(f'<option>{bg}</option>' for bg in ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'])
    body = f"""
    <div class="card">
      <div class="chd">{ICO['dr']} Add Driver</div>
      <form method="POST" enctype="multipart/form-data">
        <div class="fgrid">
          <div class="fg"><label>Full Name *</label><input name="name" required></div>
          <div class="fg"><label>Phone</label><input name="phone"></div>
          <div class="fg"><label>License No</label><input name="license_no"></div>
          <div class="fg"><label>License Expiry</label><input type="date" name="license_expiry"></div>
          <div class="fg"><label>Blood Group</label>
            <select name="blood_group">
              <option value="">Select</option>{bgs}
            </select></div>
          <div class="fg"><label>Emergency Contact Name</label><input name="emergency_contact"></div>
          <div class="fg"><label>Emergency Phone</label><input name="emergency_phone"></div>
          <div class="fg"><label>Photo</label>
            <label class="flbl" for="dph">Upload Photo</label>
            <input type="file" id="dph" name="photo" accept="image/*">
          </div>
        </div>
        <div class="brow"><button type="submit" class="btn bp">Add Driver</button></div>
      </form>
    </div>
    <div class="card">
      <div class="chd">{ICO['dr']} All Drivers</div>
      <div class="tw"><table>
        <thead><tr><th>Photo</th><th>Name</th><th>Phone</th><th>License</th>
          <th>Expiry</th><th>Blood Group</th><th>Emergency Contact</th><th>Vehicle</th><th></th></tr></thead>
        <tbody>{rows or '<tr><td colspan="9" style="text-align:center;padding:24px;color:var(--mut)">No drivers added yet.</td></tr>'}</tbody>
      </table></div>
    </div>"""
    return page('Drivers', body, '/drivers')


@app.route('/drivers/<int:did>', methods=['GET', 'POST'])
@login_req
@admin_req
def edit_driver(did):
    d = db_fetch("SELECT * FROM drivers WHERE id=?", (did,), one=True)
    if not d:
        flash('Not found.', 'al-err')
        return redirect(url_for('drivers'))
    if request.method == 'POST':
        f = request.form
        fn = save_file(request.files.get('photo')) or d['photo']
        db_run("""UPDATE drivers SET name=?,phone=?,license_no=?,license_expiry=?,
            blood_group=?,emergency_contact=?,emergency_phone=?,photo=? WHERE id=?""",
            (f['name'], f.get('phone'), f.get('license_no'), f.get('license_expiry') or None,
             f.get('blood_group'), f.get('emergency_contact'), f.get('emergency_phone'), fn, did))
        flash('Driver updated.', 'al-ok')
        return redirect(url_for('drivers'))

    v = lambda k: d[k] or ''
    bgs = ''.join(
        f'<option {"selected" if v("blood_group") == bg else ""}>{bg}</option>'
        for bg in ['', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'])
    body = f"""
    <div class="brow" style="margin-bottom:13px">
      <a href="/drivers" class="btn bs bsm">Back to Drivers</a>
    </div>
    <div class="card">
      <div class="chd">Edit Driver - {d['name']}</div>
      {'<img src="/uploads/' + d["photo"] + '" style="width:88px;height:88px;border-radius:50%;object-fit:cover;margin-bottom:14px;border:3px solid var(--border)">' if d['photo'] else ''}
      <form method="POST" enctype="multipart/form-data">
        <div class="fgrid">
          <div class="fg"><label>Full Name *</label><input name="name" value="{v('name')}" required></div>
          <div class="fg"><label>Phone</label><input name="phone" value="{v('phone')}"></div>
          <div class="fg"><label>License No</label><input name="license_no" value="{v('license_no')}"></div>
          <div class="fg"><label>License Expiry</label>
            <input type="date" name="license_expiry" value="{v('license_expiry')}"></div>
          <div class="fg"><label>Blood Group</label>
            <select name="blood_group"><option value="">Select</option>{bgs}</select></div>
          <div class="fg"><label>Emergency Contact</label>
            <input name="emergency_contact" value="{v('emergency_contact')}"></div>
          <div class="fg"><label>Emergency Phone</label>
            <input name="emergency_phone" value="{v('emergency_phone')}"></div>
          <div class="fg"><label>New Photo</label>
            <label class="flbl" for="dph">Change Photo</label>
            <input type="file" id="dph" name="photo" accept="image/*">
          </div>
        </div>
        <div class="brow">
          <button type="submit" class="btn bp">Save Changes</button>
          <a href="/drivers/{did}/delete" class="btn br"
             onclick="return confirm('Delete this driver permanently?')">Delete Driver</a>
        </div>
      </form>
    </div>"""
    return page('Edit Driver', body, '/drivers')


@app.route('/drivers/<int:did>/delete')
@login_req
@admin_req
def delete_driver(did):
    db_run("UPDATE drivers SET active=0 WHERE id=?", (did,))
    flash('Driver deleted.', 'al-ok')
    return redirect(url_for('drivers'))


# ── Machines ──────────────────────────────────────────────────────────────────
@app.route('/machines', methods=['GET', 'POST'])
@login_req
@admin_req
def machines():
    if request.method == 'POST':
        f = request.form
        fn = save_file(request.files.get('photo'))
        conn = get_db()
        conn.execute("""INSERT INTO machines(name,model,serial_no,manufacturer,
            purchase_date,last_service,next_service,calibration_due,specs,photo)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (f['name'], f.get('model'), f.get('serial_no'), f.get('manufacturer'),
             f.get('purchase_date') or None, f.get('last_service') or None,
             f.get('next_service') or None, f.get('calibration_due') or None,
             f.get('specs'), fn))
        conn.commit()
        conn.close()
        flash('Machine added.', 'al-ok')
        return redirect(url_for('machines'))

    machs = db_fetch("SELECT * FROM machines WHERE active=1 ORDER BY name")

    def ph(m):
        if m['photo']:
            return f'<img src="/uploads/{m["photo"]}" class="ph-sq">'
        return '<div style="width:60px;height:45px;border-radius:7px;background:var(--acc-l);display:flex;align-items:center;justify-content:center;font-size:13px;color:var(--acc);font-weight:600">M</div>'

    rows = ''.join(f"""<tr>
        <td>{ph(m)}</td>
        <td><strong>{m['name']}</strong><br><small class="tm">{m['manufacturer'] or ''}</small></td>
        <td>{m['model'] or '-'}</td>
        <td>{m['serial_no'] or '-'}</td>
        <td>{m['last_service'] or '-'}</td>
        <td>{m['next_service'] or '-'}</td>
        <td>{m['calibration_due'] or '-'}</td>
        <td style="white-space:nowrap">
          <a href="/machines/{m['id']}" class="btn bs bsm">Edit</a>
          <a href="/machines/{m['id']}/delete" class="btn br bsm"
             onclick="return confirm('Delete this machine?')">Delete</a>
        </td>
        </tr>""" for m in machs)

    body = f"""
    <div class="card">
      <div class="chd">{ICO['m']} Add Machine</div>
      <form method="POST" enctype="multipart/form-data">
        <div class="fgrid">
          <div class="fg"><label>Machine Name *</label><input name="name" required></div>
          <div class="fg"><label>Model</label><input name="model"></div>
          <div class="fg"><label>Serial No</label><input name="serial_no"></div>
          <div class="fg"><label>Manufacturer</label><input name="manufacturer"></div>
          <div class="fg"><label>Purchase Date</label><input type="date" name="purchase_date"></div>
          <div class="fg"><label>Last Service Date</label><input type="date" name="last_service"></div>
          <div class="fg"><label>Next Service Date</label><input type="date" name="next_service"></div>
          <div class="fg"><label>Calibration Due</label><input type="date" name="calibration_due"></div>
          <div class="fg full"><label>Specifications / Notes</label>
            <textarea name="specs" placeholder="Technical specs, notes..."></textarea></div>
          <div class="fg"><label>Machine Photo</label>
            <label class="flbl" for="mph">Upload Photo</label>
            <input type="file" id="mph" name="photo" accept="image/*">
          </div>
        </div>
        <div class="brow"><button type="submit" class="btn bp">Add Machine</button></div>
      </form>
    </div>
    <div class="card">
      <div class="chd">{ICO['m']} All Machines</div>
      <div class="tw"><table>
        <thead><tr><th>Photo</th><th>Name</th><th>Model</th><th>Serial No</th>
          <th>Last Service</th><th>Next Service</th><th>Calibration Due</th><th></th></tr></thead>
        <tbody>{rows or '<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--mut)">No machines added yet.</td></tr>'}</tbody>
      </table></div>
    </div>"""
    return page('Machines', body, '/machines')


@app.route('/machines/<int:mid>', methods=['GET', 'POST'])
@login_req
@admin_req
def edit_machine(mid):
    m = db_fetch("SELECT * FROM machines WHERE id=?", (mid,), one=True)
    if not m:
        flash('Not found.', 'al-err')
        return redirect(url_for('machines'))
    if request.method == 'POST':
        f = request.form
        fn = save_file(request.files.get('photo')) or m['photo']
        db_run("""UPDATE machines SET name=?,model=?,serial_no=?,manufacturer=?,
            purchase_date=?,last_service=?,next_service=?,calibration_due=?,specs=?,photo=? WHERE id=?""",
            (f['name'], f.get('model'), f.get('serial_no'), f.get('manufacturer'),
             f.get('purchase_date') or None, f.get('last_service') or None,
             f.get('next_service') or None, f.get('calibration_due') or None,
             f.get('specs'), fn, mid))
        flash('Machine updated.', 'al-ok')
        return redirect(url_for('machines'))

    v = lambda k: m[k] or ''
    body = f"""
    <div class="brow" style="margin-bottom:13px">
      <a href="/machines" class="btn bs bsm">Back to Machines</a>
    </div>
    <div class="card">
      <div class="chd">Edit Machine - {m['name']}</div>
      {'<img src="/uploads/' + m["photo"] + '" style="max-width:180px;border-radius:9px;margin-bottom:14px;border:2px solid var(--border)">' if m['photo'] else ''}
      <form method="POST" enctype="multipart/form-data">
        <div class="fgrid">
          <div class="fg"><label>Name *</label><input name="name" value="{v('name')}" required></div>
          <div class="fg"><label>Model</label><input name="model" value="{v('model')}"></div>
          <div class="fg"><label>Serial No</label><input name="serial_no" value="{v('serial_no')}"></div>
          <div class="fg"><label>Manufacturer</label><input name="manufacturer" value="{v('manufacturer')}"></div>
          <div class="fg"><label>Purchase Date</label>
            <input type="date" name="purchase_date" value="{v('purchase_date')}"></div>
          <div class="fg"><label>Last Service</label>
            <input type="date" name="last_service" value="{v('last_service')}"></div>
          <div class="fg"><label>Next Service</label>
            <input type="date" name="next_service" value="{v('next_service')}"></div>
          <div class="fg"><label>Calibration Due</label>
            <input type="date" name="calibration_due" value="{v('calibration_due')}"></div>
          <div class="fg full"><label>Specifications</label>
            <textarea name="specs">{v('specs')}</textarea></div>
          <div class="fg"><label>New Photo</label>
            <label class="flbl" for="mph">Change Photo</label>
            <input type="file" id="mph" name="photo" accept="image/*">
          </div>
        </div>
        <div class="brow">
          <button type="submit" class="btn bp">Save Changes</button>
          <a href="/machines/{mid}/delete" class="btn br"
             onclick="return confirm('Delete this machine permanently?')">Delete Machine</a>
        </div>
      </form>
    </div>"""
    return page('Edit Machine', body, '/machines')


@app.route('/machines/<int:mid>/delete')
@login_req
@admin_req
def delete_machine(mid):
    db_run("UPDATE machines SET active=0 WHERE id=?", (mid,))
    flash('Machine deleted.', 'al-ok')
    return redirect(url_for('machines'))


# ── Master List (Vehicles only — customers added via Job Card) ────────────────
@app.route('/master')
@login_req
@admin_req
def master_list():
    vehs = db_fetch("SELECT * FROM vehicles ORDER BY reg_no")

    def vrow():
        return ''.join(f"""<tr>
            <td><strong>{v['reg_no']}</strong></td>
            <td>{v['model'] or '-'}</td>
            <td>{v['type'] or '-'}</td>
            <td>{v['insurance_expiry'] or '-'}</td>
            <td>{v['fitness_expiry'] or '-'}</td>
            <td style="white-space:nowrap">
              <a href="/master/vehicle/{v['id']}/edit" class="btn bs bsm">Edit</a>
              <a href="/master/vehicle/{v['id']}/delete" class="btn br bsm"
                 onclick="return confirm('Delete this vehicle?')">Delete</a>
            </td>
            </tr>""" for v in vehs)

    body = f"""
    <div class="card">
      <div class="chd">{ICO['ml']} Vehicles</div>
      <form method="POST" action="/master/vehicle/add">
        <div class="fgrid">
          <div class="fg"><label>Reg No *</label><input name="reg_no" required placeholder="TN-01-AB-1234"></div>
          <div class="fg"><label>Model</label><input name="model" placeholder="Swift Dzire"></div>
          <div class="fg"><label>Type</label><input name="type" placeholder="Car / Van / Truck"></div>
          <div class="fg"><label>Insurance Expiry</label><input type="date" name="insurance_expiry"></div>
          <div class="fg"><label>Fitness Expiry</label><input type="date" name="fitness_expiry"></div>
        </div>
        <div class="brow"><button type="submit" class="btn bp">Add Vehicle</button></div>
      </form>
      <div class="tw" style="margin-top:14px"><table>
        <thead><tr><th>Reg No</th><th>Model</th><th>Type</th><th>Insurance Expiry</th><th>Fitness Expiry</th><th>Actions</th></tr></thead>
        <tbody>{vrow() or '<tr><td colspan="6" style="text-align:center;color:var(--mut);padding:18px">No vehicles added yet.</td></tr>'}</tbody>
      </table></div>
    </div>
    <div class="card" style="margin-top:0">
      <div class="chd" style="color:var(--mut);font-size:12px;border:none;padding-bottom:0">
        Customers are added by employees at the time of job card creation.
        To edit or delete a customer, use the Job Cards section.
      </div>
    </div>"""
    return page('Master List', body, '/master')


@app.route('/master/customer/add', methods=['POST'])
@login_req
@admin_req
def add_customer():
    f = request.form
    try:
        db_run("INSERT INTO customers(name,nickname,code,tds_percent) VALUES(?,?,?,?)",
               (f['name'], f.get('nickname'), f['code'], f.get('tds_percent', 10)))
        flash('Customer added.', 'al-ok')
    except Exception as e:
        flash(f'Error: {e}', 'al-err')
    return redirect(url_for('master_list'))


@app.route('/master/customer/<int:cid>/edit', methods=['GET', 'POST'])
@login_req
@admin_req
def edit_customer(cid):
    c = db_fetch("SELECT * FROM customers WHERE id=?", (cid,), one=True)
    if not c:
        flash('Customer not found.', 'al-err')
        return redirect(url_for('master_list'))
    if request.method == 'POST':
        f = request.form
        try:
            db_run("UPDATE customers SET name=?,nickname=?,code=?,tds_percent=? WHERE id=?",
                   (f['name'], f.get('nickname'), f['code'], f.get('tds_percent', 0), cid))
            flash('Customer updated.', 'al-ok')
        except Exception as e:
            flash(f'Error: {e}', 'al-err')
        return redirect(url_for('master_list'))
    v = lambda k: c[k] or ''
    body = f"""
    <div class="brow" style="margin-bottom:13px">
      <a href="/master" class="btn bs bsm">Back to Master List</a>
    </div>
    <div class="card">
      <div class="chd">Edit Customer — {c['name']}</div>
      <form method="POST">
        <div class="fgrid">
          <div class="fg"><label>Company Name *</label>
            <input name="name" value="{v('name')}" required></div>
          <div class="fg"><label>Nickname</label>
            <input name="nickname" value="{v('nickname')}"></div>
          <div class="fg"><label>Code *</label>
            <input name="code" value="{v('code')}" required></div>
          <div class="fg"><label>TDS %</label>
            <input name="tds_percent" type="number" step="0.1" value="{v('tds_percent')}"></div>
          <div class="fg"><label>Address</label>
            <input name="address" value="{v('address')}"></div>
          <div class="fg"><label>GST No</label>
            <input name="gst" value="{v('gst')}"></div>
        </div>
        <div class="brow">
          <button type="submit" class="btn bp">Save Changes</button>
          <a href="/master/customer/{cid}/delete" class="btn br"
             onclick="return confirm('Delete this customer permanently?')">Delete Customer</a>
        </div>
      </form>
    </div>"""
    return page('Edit Customer', body, '/master')


@app.route('/master/customer/<int:cid>/delete')
@login_req
@admin_req
def delete_customer(cid):
    db_run("DELETE FROM customers WHERE id=?", (cid,))
    flash('Customer deleted.', 'al-ok')
    return redirect(url_for('master_list'))


@app.route('/master/vehicle/add', methods=['POST'])
@login_req
@admin_req
def add_vehicle():
    f = request.form
    db_run("""INSERT INTO vehicles(reg_no,type,model,insurance_expiry,fitness_expiry)
              VALUES(?,?,?,?,?)""",
           (f['reg_no'], f.get('type'), f.get('model'),
            f.get('insurance_expiry') or None, f.get('fitness_expiry') or None))
    flash('Vehicle added.', 'al-ok')
    return redirect(url_for('master_list'))


@app.route('/master/vehicle/<int:vid>/edit', methods=['GET', 'POST'])
@login_req
@admin_req
def edit_vehicle(vid):
    v = db_fetch("SELECT * FROM vehicles WHERE id=?", (vid,), one=True)
    if not v:
        flash('Vehicle not found.', 'al-err')
        return redirect(url_for('master_list'))
    if request.method == 'POST':
        f = request.form
        db_run("""UPDATE vehicles SET reg_no=?,type=?,model=?,
                  insurance_expiry=?,fitness_expiry=? WHERE id=?""",
               (f['reg_no'], f.get('type'), f.get('model'),
                f.get('insurance_expiry') or None, f.get('fitness_expiry') or None, vid))
        flash('Vehicle updated.', 'al-ok')
        return redirect(url_for('master_list'))
    vv = lambda k: v[k] or ''
    body = f"""
    <div class="brow" style="margin-bottom:13px">
      <a href="/master" class="btn bs bsm">Back to Master List</a>
    </div>
    <div class="card">
      <div class="chd">Edit Vehicle — {v['reg_no']}</div>
      <form method="POST">
        <div class="fgrid">
          <div class="fg"><label>Reg No *</label>
            <input name="reg_no" value="{vv('reg_no')}" required></div>
          <div class="fg"><label>Model</label>
            <input name="model" value="{vv('model')}"></div>
          <div class="fg"><label>Type</label>
            <input name="type" value="{vv('type')}" placeholder="Car / Van / Truck"></div>
          <div class="fg"><label>Insurance Expiry</label>
            <input type="date" name="insurance_expiry" value="{vv('insurance_expiry')}"></div>
          <div class="fg"><label>Fitness Expiry</label>
            <input type="date" name="fitness_expiry" value="{vv('fitness_expiry')}"></div>
        </div>
        <div class="brow">
          <button type="submit" class="btn bp">Save Changes</button>
          <a href="/master/vehicle/{vid}/delete" class="btn br"
             onclick="return confirm('Delete this vehicle permanently?')">Delete Vehicle</a>
        </div>
      </form>
    </div>"""
    return page('Edit Vehicle', body, '/master')


@app.route('/master/vehicle/<int:vid>/delete')
@login_req
@admin_req
def delete_vehicle(vid):
    db_run("DELETE FROM vehicles WHERE id=?", (vid,))
    flash('Vehicle deleted.', 'al-ok')
    return redirect(url_for('master_list'))


# ── Employees ─────────────────────────────────────────────────────────────────
@app.route('/employees', methods=['GET', 'POST'])
@login_req
@admin_req
def employees():
    if request.method == 'POST':
        f = request.form
        try:
            db_run("""INSERT INTO users(username,password,name,role,designation,department,phone)
                      VALUES(?,?,?,?,?,?,?)""",
                   (f['username'], hash_pw(f['password']), f['name'],
                    f.get('role', 'employee'), f.get('designation'),
                    f.get('department'), f.get('phone')))
            flash('Employee added.', 'al-ok')
        except Exception as e:
            flash(f'Error: {e}', 'al-err')

    users = db_fetch("SELECT * FROM users ORDER BY role,name")
    rows = ''.join(f"""<tr>
        <td><strong>{u['name']}</strong></td>
        <td class="tm">{u['username']}</td>
        <td><span class="tag {'t-admin' if u['role']=='admin' else 't-employee'}">{u['role'].upper()}</span></td>
        <td>{u['designation'] or '-'}</td>
        <td>{u['department'] or '-'}</td>
        <td>{u['phone'] or '-'}</td>
        <td><small class="tm">{u['created_at'][:10]}</small></td>
        <td>
          <a href="/employees/{u['id']}/edit" class="btn bs bsm">Edit</a>
          <a href="/employees/{u['id']}/delete"
             class="btn br bsm"
             onclick="return confirm('Delete this employee? This cannot be undone.')">Delete</a>
        </td>
        </tr>""" for u in users)

    body = f"""
    <div class="card">
      <div class="chd">{ICO['e']} Add Employee</div>
      <form method="POST">
        <div class="fgrid">
          <div class="fg"><label>Full Name *</label><input name="name" required></div>
          <div class="fg"><label>Username *</label><input name="username" required></div>
          <div class="fg"><label>Password *</label><input type="password" name="password" required></div>
          <div class="fg"><label>Phone</label><input name="phone"></div>
          <div class="fg"><label>Role</label>
            <select name="role">
              <option value="employee">Employee</option>
              <option value="admin">Admin</option>
            </select></div>
          <div class="fg"><label>Designation</label><input name="designation"></div>
          <div class="fg"><label>Department</label><input name="department"></div>
        </div>
        <div class="brow"><button type="submit" class="btn bp">Add Employee</button></div>
      </form>
    </div>
    <div class="card">
      <div class="chd">{ICO['e']} All Staff</div>
      <div class="tw"><table>
        <thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Designation</th>
          <th>Department</th><th>Phone</th><th>Since</th><th>Actions</th></tr></thead>
        <tbody>{rows}</tbody>
      </table></div>
    </div>"""
    return page('Employees', body, '/employees')


@app.route('/employees/<int:eid>/edit', methods=['GET', 'POST'])
@login_req
@admin_req
def edit_employee(eid):
    u = db_fetch("SELECT * FROM users WHERE id=?", (eid,), one=True)
    if not u:
        flash('Employee not found.', 'al-err')
        return redirect(url_for('employees'))
    if request.method == 'POST':
        f = request.form
        pw_sql = ", password=?" if f.get('password') else ""
        params = [f['name'], f.get('role', 'employee'), f.get('designation'),
                  f.get('department'), f.get('phone')]
        if f.get('password'):
            params.append(hash_pw(f['password']))
        params.append(eid)
        db_run(f"""UPDATE users SET name=?,role=?,designation=?,department=?,phone=?{pw_sql}
                   WHERE id=?""", params)
        flash('Employee updated.', 'al-ok')
        return redirect(url_for('employees'))
    v = lambda k: u[k] or ''
    role_opts = ''.join(
        f'<option value="{r}" {"selected" if v("role")==r else ""}>{r.capitalize()}</option>'
        for r in ['employee', 'admin'])
    body = f"""
    <div class="brow" style="margin-bottom:13px">
      <a href="/employees" class="btn bs bsm">Back to Employees</a>
    </div>
    <div class="card">
      <div class="chd">{ICO['e']} Edit Employee — {u['name']}</div>
      <form method="POST">
        <div class="fgrid">
          <div class="fg"><label>Full Name *</label>
            <input name="name" value="{v('name')}" required></div>
          <div class="fg"><label>Username (cannot change)</label>
            <input value="{v('username')}" readonly></div>
          <div class="fg"><label>New Password <small class="tm">(leave blank to keep)</small></label>
            <input type="password" name="password" placeholder="Enter new password to change"></div>
          <div class="fg"><label>Phone</label>
            <input name="phone" value="{v('phone')}"></div>
          <div class="fg"><label>Role</label>
            <select name="role">{role_opts}</select></div>
          <div class="fg"><label>Designation</label>
            <input name="designation" value="{v('designation')}"></div>
          <div class="fg"><label>Department</label>
            <input name="department" value="{v('department')}"></div>
        </div>
        <div class="brow">
          <button type="submit" class="btn bp">Save Changes</button>
          <a href="/employees/{eid}/delete" class="btn br"
             onclick="return confirm('Delete this employee permanently?')">Delete Employee</a>
        </div>
      </form>
    </div>"""
    return page('Edit Employee', body, '/employees')


@app.route('/employees/<int:eid>/delete')
@login_req
@admin_req
def delete_employee(eid):
    if eid == session['uid']:
        flash('You cannot delete your own account.', 'al-err')
        return redirect(url_for('employees'))
    db_run("DELETE FROM users WHERE id=?", (eid,))
    flash('Employee deleted.', 'al-ok')
    return redirect(url_for('employees'))


# ── File serve ────────────────────────────────────────────────────────────────
@app.route('/uploads/<filename>')
@login_req
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("\n" + "=" * 50)
    print("  GMS - Employee Tracking System")
    print("  URL:   http://localhost:5000")
    print("  Admin: admin / admin123")
    print("  Emp:   emp1  / emp123")
    print("=" * 50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
