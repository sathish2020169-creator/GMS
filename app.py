from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from datetime import datetime
import json, os, uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gms-tracker-secret-2025')
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

# ─── Data Layer ───────────────────────────────────────────────────────────────

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {
        "users": [
            {"id": "ADM001", "name": "Admin",        "password": "admin123",  "role": "admin",    "designation": "Administrator"},
            {"id": "EMP001", "name": "Rajesh Kumar", "password": "emp123",    "role": "employee", "designation": "CMM Engineer"},
            {"id": "EMP002", "name": "Priya Sharma", "password": "emp123",    "role": "employee", "designation": "Finance"},
            {"id": "EMP003", "name": "Selvam M",     "password": "emp123",    "role": "employee", "designation": "Laser Technician"},
        ],
        "customers": [
            {"code": "WI001", "name": "Wheels India",  "nick": "WI"},
            {"code": "TM002", "name": "TVS Motors",    "nick": "TVS"},
            {"code": "AL003", "name": "Ashok Leyland", "nick": "AL"},
            {"code": "BH004", "name": "Bharat Forge",  "nick": "BF"},
        ],
        "machines": ["Portable CMM Arm", "Laser Tracker API", "3D Laser Scanner", "CMM Machine"],
        "laptops":  ["Laptop-001", "Laptop-002", "Laptop-003"],
        "cars":     ["TN-01-AB-1234", "TN-01-CD-5678", "TN-58-EF-9012"],
        "drivers":  ["Murugan", "Selvam", "Rajan", "Vijay"],
        "tds_rate": 10,
        "job_cards": [],
        "finance":   []
    }

def save(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def auth(uid, pwd):
    for u in load()['users']:
        if u['id'] == uid and u['password'] == pwd:
            return u
    return None

# ─── Base CSS & Layout ────────────────────────────────────────────────────────

BASE_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#f1f5fb;color:#1e293b;min-height:100vh}
a{text-decoration:none;color:inherit}
.sb{width:230px;background:#1e3a5f;position:fixed;top:0;left:0;height:100vh;display:flex;flex-direction:column;z-index:100}
.sb-logo{padding:20px 16px;font-size:18px;font-weight:700;color:#fff;border-bottom:1px solid rgba(255,255,255,.1)}
.sb-logo span{color:#3b82f6}
.sb-nav{flex:1;padding:12px 0}
.sb-nav a{display:flex;align-items:center;gap:10px;padding:11px 18px;color:rgba(255,255,255,.75);font-size:14px;font-weight:500;transition:.2s}
.sb-nav a:hover,.sb-nav a.active{background:rgba(59,130,246,.18);color:#fff}
.sb-nav a .ic{font-size:17px;width:22px;text-align:center}
.sb-foot{padding:14px 16px;border-top:1px solid rgba(255,255,255,.1)}
.sb-foot .user{color:#fff;font-size:13px;font-weight:600}
.sb-foot .role{color:rgba(255,255,255,.5);font-size:11px;margin-top:2px}
.sb-foot a{display:inline-block;margin-top:8px;font-size:12px;color:#ef4444;font-weight:500}
.main{margin-left:230px;padding:24px}
.topbar{background:#fff;border-radius:10px;padding:14px 20px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.topbar h1{font-size:18px;font-weight:700;color:#1e3a5f}
.card{background:#fff;border-radius:10px;padding:20px;margin-bottom:18px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.card-title{font-size:15px;font-weight:700;color:#1e3a5f;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #e2e8f5}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:18px}
.stat{background:#fff;border-radius:10px;padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.stat .val{font-size:26px;font-weight:700;color:#2563eb}
.stat .lbl{font-size:12px;color:#64748b;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 12px;background:#f8fafc;color:#64748b;font-size:12px;font-weight:600;text-transform:uppercase}
td{padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#334155}
tr:hover td{background:#f8fafc}
.badge{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600}
.badge-pending{background:#fef9c3;color:#854d0e}
.badge-completed{background:#dcfce7;color:#166534}
.badge-active{background:#dbeafe;color:#1e40af}
.btn{display:inline-block;padding:8px 16px;border-radius:7px;font-size:13px;font-weight:600;cursor:pointer;border:none;transition:.2s}
.btn-primary{background:#2563eb;color:#fff}.btn-primary:hover{background:#1d4ed8}
.btn-success{background:#059669;color:#fff}.btn-success:hover{background:#047857}
.btn-danger{background:#dc2626;color:#fff}.btn-danger:hover{background:#b91c1c}
.btn-secondary{background:#e2e8f5;color:#334155}.btn-secondary:hover{background:#cbd5e1}
.btn-sm{padding:5px 11px;font-size:12px}
.form-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.fg{display:flex;flex-direction:column;gap:5px}
.fg label{font-size:12px;font-weight:600;color:#475569}
.fg input,.fg select,.fg textarea{border:1px solid #e2e8f5;border-radius:7px;padding:8px 11px;font-size:13px;color:#1e293b;background:#fff;outline:none;transition:.2s;font-family:inherit}
.fg input:focus,.fg select:focus,.fg textarea:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1)}
.fg textarea{resize:vertical;min-height:70px}
.alert{padding:10px 14px;border-radius:7px;margin-bottom:14px;font-size:13px;font-weight:500}
.alert-success{background:#dcfce7;color:#166534}
.alert-error{background:#fee2e2;color:#991b1b}
.search-bar{display:flex;gap:10px;margin-bottom:14px}
.search-bar input{flex:1;border:1px solid #e2e8f5;border-radius:7px;padding:8px 12px;font-size:13px;outline:none}
.search-bar input:focus{border-color:#2563eb}
</style>
"""

LOGIN_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);min-height:100vh;display:flex;align-items:center;justify-content:center}
.login-box{background:#fff;border-radius:16px;padding:36px 32px;width:100%;max-width:400px;box-shadow:0 20px 60px rgba(0,0,0,.2)}
.login-logo{text-align:center;margin-bottom:24px}
.login-logo h1{font-size:24px;font-weight:700;color:#1e3a5f}
.login-logo p{font-size:13px;color:#64748b;margin-top:4px}
.fg{display:flex;flex-direction:column;gap:5px;margin-bottom:14px}
.fg label{font-size:12px;font-weight:600;color:#475569}
.fg input{border:1px solid #e2e8f5;border-radius:8px;padding:10px 13px;font-size:14px;outline:none;transition:.2s}
.fg input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1)}
.btn{width:100%;padding:11px;border-radius:8px;border:none;font-size:14px;font-weight:700;cursor:pointer;background:#2563eb;color:#fff;transition:.2s;margin-top:6px}
.btn:hover{background:#1d4ed8}
.alert{padding:10px 13px;border-radius:7px;margin-bottom:12px;font-size:13px;font-weight:500;background:#fee2e2;color:#991b1b}
.hint{text-align:center;margin-top:16px;font-size:12px;color:#94a3b8}
</style>
"""

def sidebar(user, active=''):
    is_admin = user['role'] == 'admin'
    links = []
    if is_admin:
        links = [
            ('/admin',          '📊', 'Dashboard'),
            ('/admin/job_cards','📋', 'Job Cards'),
            ('/admin/finance',  '💰', 'Finance'),
            ('/admin/master',   '⚙️',  'Master List'),
            ('/admin/stock',    '📦', 'Stock'),
        ]
    else:
        links = [
            ('/employee',      '🏠', 'My Dashboard'),
            ('/employee/new_job','➕','New Job Card'),
        ]
    nav = ''.join(f'<a href="{h}" class="{"active" if active==h else ""}"><span class="ic">{ic}</span>{lbl}</a>'
                  for h, ic, lbl in links)
    return f"""
    <div class="sb">
      <div class="sb-logo">GMS <span>Tracker</span></div>
      <div class="sb-nav">{nav}</div>
      <div class="sb-foot">
        <div class="user">{user['name']}</div>
        <div class="role">{user['designation']}</div>
        <a href="/logout">Logout →</a>
      </div>
    </div>"""

def page(title, content, user, active=''):
    flashes = ''
    for cat, msg in session.get('_flashes', []):
        cls = 'alert-success' if cat == 'success' else 'alert-error'
        flashes += f'<div class="alert {cls}">{msg}</div>'
    return render_template_string(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — GMS</title>{BASE_CSS}</head>
<body>
{sidebar(user, active)}
<div class="main">
  <div class="topbar"><h1>{title}</h1><span style="font-size:13px;color:#64748b">{datetime.now().strftime('%d %b %Y')}</span></div>
  {{% with messages = get_flashed_messages(with_categories=true) %}}
  {{% for cat, msg in messages %}}
  <div class="alert {{'alert-success' if cat=='success' else 'alert-error'}}">{{{{ msg }}}}</div>
  {{% endfor %}}{{% endwith %}}
  {content}
</div>
</body></html>""")

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = auth(request.form.get('uid', '').strip(), request.form.get('pwd', '').strip())
        if u:
            session['user'] = u
            return redirect(url_for('admin_dash' if u['role'] == 'admin' else 'emp_dash'))
        flash('Invalid ID or password', 'error')
    err = ''
    for cat, msg in session.get('_flashes', []):
        if cat == 'error':
            err = f'<div class="alert">{msg}</div>'
    return render_template_string(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Login — GMS</title>{LOGIN_CSS}</head>
<body>
<div class="login-box">
  <div class="login-logo">
    <h1>📐 GMS Tracker</h1>
    <p>Geometry Measurement Service</p>
  </div>
  {{% with messages = get_flashed_messages(with_categories=true) %}}
  {{% for cat, msg in messages %}}
  <div class="alert">{{{{ msg }}}}</div>
  {{% endfor %}}{{% endwith %}}
  <form method="POST">
    <div class="fg"><label>Employee ID</label><input name="uid" placeholder="e.g. ADM001" required autofocus></div>
    <div class="fg"><label>Password</label><input type="password" name="pwd" placeholder="Enter password" required></div>
    <button class="btn">Login</button>
  </form>
  <div class="hint">Admin: ADM001 / admin123 &nbsp;|&nbsp; Emp: EMP001 / emp123</div>
</div>
</body></html>""")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── Employee Routes ──────────────────────────────────────────────────────────

@app.route('/employee')
def emp_dash():
    if 'user' not in session:
        return redirect(url_for('login'))
    d   = load()
    uid = session['user']['id']
    my  = [j for j in d['job_cards'] if j['employee_id'] == uid]
    rows = ''.join(f"""<tr>
        <td><strong>{j['batch_no']}</strong></td>
        <td>{j['customer_name']}</td>
        <td>{j['location']}</td>
        <td>{j['start_date']}</td>
        <td>{j['shift_hrs']} hrs</td>
        <td><span class="badge {'badge-completed' if j['status']=='Completed' else 'badge-pending'}">{j['status']}</span></td>
    </tr>""" for j in reversed(my)) or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">No job cards yet</td></tr>'
    content = f"""
    <div class="stats">
      <div class="stat"><div class="val">{len(my)}</div><div class="lbl">Total Jobs</div></div>
      <div class="stat"><div class="val">{sum(1 for j in my if j['status']=='Pending')}</div><div class="lbl">Pending</div></div>
      <div class="stat"><div class="val">{sum(1 for j in my if j['status']=='Completed')}</div><div class="lbl">Completed</div></div>
    </div>
    <div class="card">
      <div class="card-title">My Job Cards</div>
      <div style="margin-bottom:12px"><a href="/employee/new_job" class="btn btn-primary">➕ New Job Card</a></div>
      <table><thead><tr><th>Batch No</th><th>Customer</th><th>Location</th><th>Date</th><th>Hours</th><th>Status</th></tr></thead>
      <tbody>{rows}</tbody></table>
    </div>"""
    return page('My Dashboard', content, session['user'], '/employee')

@app.route('/employee/new_job', methods=['GET', 'POST'])
def new_job():
    if 'user' not in session:
        return redirect(url_for('login'))
    d = load()
    if request.method == 'POST':
        f   = request.form
        now = datetime.now()
        bn  = f"B-{now.strftime('%Y%m%d%H%M%S')}"
        card = {
            "id":            str(uuid.uuid4())[:8].upper(),
            "batch_no":      bn,
            "employee_id":   session['user']['id'],
            "employee_name": session['user']['name'],
            "designation":   session['user']['designation'],
            "customer_code": f.get('customer_code', ''),
            "customer_name": f.get('customer_name', ''),
            "start_date":    f.get('start_date', ''),
            "end_date":      f.get('end_date', ''),
            "start_time":    f.get('start_time', ''),
            "end_time":      f.get('end_time', ''),
            "unit":          f.get('unit', ''),
            "location":      f.get('location', ''),
            "district":      f.get('district', ''),
            "state":         f.get('state', ''),
            "driver":        f.get('driver', ''),
            "vehicle":       f.get('vehicle', ''),
            "fuel_amount":   f.get('fuel_amount', ''),
            "machine":       f.get('machine', ''),
            "laptop":        f.get('laptop', ''),
            "v_probe":       f.get('v_probe', 'NOT USED'),
            "shift_hrs":     f.get('shift_hrs', ''),
            "stock":         f.get('stock', ''),
            "other_amount":  f.get('other_amount', ''),
            "other_details": f.get('other_details', ''),
            "status":        "Pending",
            "created_at":    now.strftime('%Y-%m-%d %H:%M'),
            "splits":        []
        }
        d['job_cards'].append(card)
        save(d)
        flash(f'Job Card created! Batch No: {bn}', 'success')
        return redirect(url_for('emp_dash'))

    cust_opts = ''.join(f'<option value="{c["code"]}" data-name="{c["name"]}">{c["name"]} ({c["code"]})</option>' for c in d['customers'])
    machine_opts = ''.join(f'<option>{m}</option>' for m in d['machines'])
    laptop_opts  = ''.join(f'<option>{l}</option>' for l in d['laptops'])
    car_opts     = ''.join(f'<option>{c}</option>' for c in d['cars'])
    driver_opts  = ''.join(f'<option>{dr}</option>' for dr in d['drivers'])

    content = f"""
    <div class="card">
      <div class="card-title">➕ New Job Card</div>
      <form method="POST">
        <div class="form-grid">
          <div class="fg"><label>Customer</label>
            <select name="customer_code" id="cust" onchange="setCustName()" required>
              <option value="">Select Customer</option>{cust_opts}
            </select>
          </div>
          <input type="hidden" name="customer_name" id="cust_name">
          <div class="fg"><label>Unit / Department</label><input name="unit" placeholder="e.g. Quality Dept"></div>
          <div class="fg"><label>Location / Site</label><input name="location" required placeholder="Site name"></div>
          <div class="fg"><label>District</label><input name="district"></div>
          <div class="fg"><label>State</label><input name="state"></div>
          <div class="fg"><label>Start Date</label><input type="date" name="start_date" required></div>
          <div class="fg"><label>End Date</label><input type="date" name="end_date"></div>
          <div class="fg"><label>Start Time</label><input type="time" name="start_time"></div>
          <div class="fg"><label>End Time</label><input type="time" name="end_time"></div>
          <div class="fg"><label>Machine</label><select name="machine"><option value="">Select</option>{machine_opts}</select></div>
          <div class="fg"><label>Laptop</label><select name="laptop"><option value="">Select</option>{laptop_opts}</select></div>
          <div class="fg"><label>Vehicle</label><select name="vehicle"><option value="">Select</option>{car_opts}</select></div>
          <div class="fg"><label>Driver</label><select name="driver"><option value="">Select</option>{driver_opts}</select></div>
          <div class="fg"><label>Fuel Amount (₹)</label><input type="number" name="fuel_amount" placeholder="0"></div>
          <div class="fg"><label>Shift Hours</label><input type="number" step="0.5" name="shift_hrs" required placeholder="e.g. 8"></div>
          <div class="fg"><label>Stock</label><input type="number" name="stock" placeholder="0"></div>
          <div class="fg"><label>V-Probe Used?</label>
            <select name="v_probe"><option value="NOT USED">Not Used</option><option value="USED">Used</option></select>
          </div>
          <div class="fg"><label>Other Expense (₹)</label><input type="number" name="other_amount" placeholder="0"></div>
          <div class="fg" style="grid-column:span 2"><label>Other Details</label><textarea name="other_details" placeholder="Any additional notes..."></textarea></div>
        </div>
        <div style="margin-top:16px;display:flex;gap:10px">
          <button type="submit" class="btn btn-primary">Submit Job Card</button>
          <a href="/employee" class="btn btn-secondary">Cancel</a>
        </div>
      </form>
    </div>
    <script>
    var customers = {json.dumps(d['customers'])};
    function setCustName(){{
      var sel = document.getElementById('cust');
      var code = sel.value;
      var cust = customers.find(c => c.code === code);
      document.getElementById('cust_name').value = cust ? cust.name : '';
    }}
    </script>"""
    return page('New Job Card', content, session['user'], '/employee/new_job')

# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route('/admin')
def admin_dash():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d         = load()
    total     = len(d['job_cards'])
    pending   = sum(1 for j in d['job_cards'] if j['status'] == 'Pending')
    completed = sum(1 for j in d['job_cards'] if j['status'] == 'Completed')
    fin_total = sum(r.get('total', 0) for r in d['finance'])
    received  = sum(r.get('received_amount', 0) for r in d['finance'])
    balance   = sum(r.get('balance', 0) for r in d['finance'])
    recent    = list(reversed(d['job_cards']))[:8]
    rows = ''.join(f"""<tr>
        <td><strong>{j['batch_no']}</strong></td>
        <td>{j['employee_name']}</td>
        <td>{j['customer_name']}</td>
        <td>{j['location']}</td>
        <td>{j['start_date']}</td>
        <td><span class="badge {'badge-completed' if j['status']=='Completed' else 'badge-pending'}">{j['status']}</span></td>
        <td><a href="/admin/job_card/{j['id']}" class="btn btn-secondary btn-sm">View</a></td>
    </tr>""" for j in recent) or '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:20px">No job cards yet</td></tr>'
    content = f"""
    <div class="stats">
      <div class="stat"><div class="val">{total}</div><div class="lbl">Total Jobs</div></div>
      <div class="stat"><div class="val">{pending}</div><div class="lbl">Pending</div></div>
      <div class="stat"><div class="val">{completed}</div><div class="lbl">Completed</div></div>
      <div class="stat"><div class="val">₹{fin_total:,.0f}</div><div class="lbl">Total Invoiced</div></div>
      <div class="stat"><div class="val">₹{received:,.0f}</div><div class="lbl">Received</div></div>
      <div class="stat"><div class="val">₹{balance:,.0f}</div><div class="lbl">Balance</div></div>
    </div>
    <div class="card">
      <div class="card-title">Recent Job Cards</div>
      <table><thead><tr><th>Batch No</th><th>Employee</th><th>Customer</th><th>Location</th><th>Date</th><th>Status</th><th>Action</th></tr></thead>
      <tbody>{rows}</tbody></table>
    </div>"""
    return page('Admin Dashboard', content, session['user'], '/admin')

@app.route('/admin/job_cards')
def admin_jobs():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d      = load()
    search = request.args.get('q', '').lower()
    cards  = d['job_cards']
    if search:
        cards = [c for c in cards if search in c.get('customer_name', '').lower()
                 or search in c.get('batch_no', '').lower()
                 or search in c.get('employee_name', '').lower()]
    rows = ''.join(f"""<tr>
        <td><strong>{j['batch_no']}</strong></td>
        <td>{j['employee_name']}</td>
        <td>{j['customer_name']}</td>
        <td>{j['location']}</td>
        <td>{j['start_date']}</td>
        <td>{j['shift_hrs']} hrs</td>
        <td><span class="badge {'badge-completed' if j['status']=='Completed' else 'badge-pending'}">{j['status']}</span></td>
        <td><a href="/admin/job_card/{j['id']}" class="btn btn-secondary btn-sm">View</a></td>
    </tr>""" for j in reversed(cards)) or '<tr><td colspan="8" style="text-align:center;color:#94a3b8;padding:20px">No job cards found</td></tr>'
    content = f"""
    <div class="card">
      <div class="card-title">All Job Cards ({len(cards)} records)</div>
      <form method="GET" class="search-bar">
        <input name="q" value="{search}" placeholder="Search by customer, batch no, employee...">
        <button type="submit" class="btn btn-primary">Search</button>
        <a href="/admin/job_cards" class="btn btn-secondary">Clear</a>
      </form>
      <table><thead><tr><th>Batch No</th><th>Employee</th><th>Customer</th><th>Location</th><th>Date</th><th>Hours</th><th>Status</th><th>Action</th></tr></thead>
      <tbody>{rows}</tbody></table>
    </div>"""
    return page('Job Cards', content, session['user'], '/admin/job_cards')

@app.route('/admin/job_card/<cid>', methods=['GET', 'POST'])
def admin_view_job(cid):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d    = load()
    card = next((j for j in d['job_cards'] if j['id'] == cid), None)
    if not card:
        flash('Job card not found', 'error')
        return redirect(url_for('admin_jobs'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'status':
            card['status'] = request.form.get('status')
            save(d)
            flash('Status updated', 'success')
        elif action == 'split':
            try:
                split_h = float(request.form.get('split_hrs', 0))
                orig_h  = float(card.get('shift_hrs', 0))
                if 0 < split_h < orig_h:
                    new = dict(card)
                    suffix       = f"-{len(card['splits'])+1:02d}"
                    new['id']    = str(uuid.uuid4())[:8].upper()
                    new['batch_no']  = card['batch_no'] + suffix
                    new['shift_hrs'] = str(split_h)
                    new['splits']    = []
                    card['shift_hrs']= str(orig_h - split_h)
                    card['splits'].append(new['batch_no'])
                    d['job_cards'].append(new)
                    save(d)
                    flash(f"Split done → New batch: {new['batch_no']}", 'success')
                else:
                    flash('Invalid split hours', 'error')
            except:
                flash('Error during split', 'error')
        return redirect(url_for('admin_view_job', cid=cid))

    def row(label, val):
        return f'<tr><td style="font-weight:600;color:#475569;width:160px">{label}</td><td>{val or "-"}</td></tr>'

    splits_html = ''
    if card.get('splits'):
        splits_html = '<div style="margin-top:6px"><strong>Split Batches:</strong> ' + ', '.join(card['splits']) + '</div>'

    content = f"""
    <div style="margin-bottom:14px;display:flex;gap:10px">
      <a href="/admin/job_cards" class="btn btn-secondary">← Back</a>
    </div>
    <div class="card">
      <div class="card-title">Job Card — {card['batch_no']}</div>
      <table style="font-size:13px">
        {row('Batch No', card['batch_no'])}
        {row('Employee', card['employee_name'])}
        {row('Designation', card['designation'])}
        {row('Customer', card['customer_name'] + ' (' + card['customer_code'] + ')')}
        {row('Unit', card['unit'])}
        {row('Location', card['location'])}
        {row('District', card['district'])}
        {row('State', card['state'])}
        {row('Start Date', card['start_date'] + ' ' + card.get('start_time',''))}
        {row('End Date', card['end_date'] + ' ' + card.get('end_time',''))}
        {row('Machine', card['machine'])}
        {row('Laptop', card['laptop'])}
        {row('Vehicle', card['vehicle'])}
        {row('Driver', card['driver'])}
        {row('Fuel Amount', '₹' + str(card['fuel_amount']))}
        {row('Shift Hours', str(card['shift_hrs']) + ' hrs')}
        {row('Stock', card['stock'])}
        {row('V-Probe', card['v_probe'])}
        {row('Other Expense', '₹' + str(card['other_amount']))}
        {row('Other Details', card['other_details'])}
        {row('Status', f'<span class="badge {"badge-completed" if card["status"]=="Completed" else "badge-pending"}">{card["status"]}</span>')}
        {row('Created', card['created_at'])}
      </table>
      {splits_html}
    </div>
    <div class="card">
      <div class="card-title">Update Status</div>
      <form method="POST" style="display:flex;gap:10px;align-items:center">
        <input type="hidden" name="action" value="status">
        <select name="status" style="border:1px solid #e2e8f5;border-radius:7px;padding:8px 11px;font-size:13px">
          <option {'selected' if card['status']=='Pending' else ''}>Pending</option>
          <option {'selected' if card['status']=='Completed' else ''}>Completed</option>
          <option {'selected' if card['status']=='Cancelled' else ''}>Cancelled</option>
        </select>
        <button type="submit" class="btn btn-success">Update</button>
      </form>
    </div>
    <div class="card">
      <div class="card-title">Split Job Card</div>
      <form method="POST" style="display:flex;gap:10px;align-items:center">
        <input type="hidden" name="action" value="split">
        <input type="number" name="split_hrs" step="0.5" placeholder="Hours to split off" style="border:1px solid #e2e8f5;border-radius:7px;padding:8px 11px;font-size:13px;width:200px">
        <button type="submit" class="btn btn-primary" onclick="return confirm('Split this job card?')">Split</button>
      </form>
      <p style="font-size:12px;color:#94a3b8;margin-top:8px">Current shift hours: {card['shift_hrs']}</p>
    </div>"""
    return page(f'Job Card Detail', content, session['user'], '/admin/job_cards')

@app.route('/admin/finance', methods=['GET', 'POST'])
def admin_finance():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d = load()
    if request.method == 'POST':
        f       = request.form
        amount  = float(f.get('amount', 0) or 0)
        gst_pct = float(f.get('gst_pct', 18) or 18)
        gst_amt = round(amount * gst_pct / 100, 2)
        total   = round(amount + gst_amt, 2)
        tds     = round(amount * d.get('tds_rate', 10) / 100, 2)
        recv    = float(f.get('received_amount', 0) or 0)
        balance = round(total - tds - recv, 2)
        rec = {
            "id":              len(d['finance']) + 1,
            "po_number":       f.get('po_number', ''),
            "quotation_no":    f.get('quotation_no', ''),
            "invoice_no":      f.get('invoice_no', ''),
            "invoice_date":    f.get('invoice_date', ''),
            "due_date":        f.get('due_date', ''),
            "customer":        f.get('customer', ''),
            "amount":          amount,
            "gst_pct":         gst_pct,
            "gst_amount":      gst_amt,
            "total":           total,
            "tds":             tds,
            "received_amount": recv,
            "balance":         balance,
            "status":          "COMPLETED" if balance <= 0 else "PENDING",
            "created_at":      datetime.now().strftime('%Y-%m-%d')
        }
        d['finance'].append(rec)
        save(d)
        flash('Finance record added!', 'success')
        return redirect(url_for('admin_finance'))

    cust_opts = ''.join(f'<option>{c["name"]}</option>' for c in d['customers'])
    rows = ''.join(f"""<tr>
        <td>{r['invoice_no'] or '-'}</td>
        <td>{r['customer']}</td>
        <td>{r['po_number'] or '-'}</td>
        <td>₹{r['amount']:,.2f}</td>
        <td>₹{r['gst_amount']:,.2f}</td>
        <td>₹{r['total']:,.2f}</td>
        <td>₹{r['tds']:,.2f}</td>
        <td>₹{r['received_amount']:,.2f}</td>
        <td>₹{r['balance']:,.2f}</td>
        <td><span class="badge {'badge-completed' if r['status']=='COMPLETED' else 'badge-pending'}">{r['status']}</span></td>
        <td>{r['invoice_date']}</td>
    </tr>""" for r in reversed(d['finance'])) or '<tr><td colspan="11" style="text-align:center;color:#94a3b8;padding:20px">No finance records yet</td></tr>'

    content = f"""
    <div class="card">
      <div class="card-title">Add Finance Record</div>
      <form method="POST">
        <div class="form-grid">
          <div class="fg"><label>Customer</label><select name="customer" required><option value="">Select</option>{cust_opts}</select></div>
          <div class="fg"><label>PO Number</label><input name="po_number" placeholder="PO-XXXX"></div>
          <div class="fg"><label>Quotation No</label><input name="quotation_no"></div>
          <div class="fg"><label>Invoice No</label><input name="invoice_no"></div>
          <div class="fg"><label>Invoice Date</label><input type="date" name="invoice_date"></div>
          <div class="fg"><label>Due Date</label><input type="date" name="due_date"></div>
          <div class="fg"><label>Bill Amount (₹)</label><input type="number" step="0.01" name="amount" required placeholder="0.00"></div>
          <div class="fg"><label>GST %</label><input type="number" step="0.01" name="gst_pct" value="18"></div>
          <div class="fg"><label>Received Amount (₹)</label><input type="number" step="0.01" name="received_amount" value="0"></div>
        </div>
        <div style="margin-top:14px"><button type="submit" class="btn btn-primary">Add Record</button></div>
      </form>
    </div>
    <div class="card">
      <div class="card-title">Finance Records</div>
      <div style="overflow-x:auto">
      <table><thead><tr><th>Invoice</th><th>Customer</th><th>PO No</th><th>Amount</th><th>GST</th><th>Total</th><th>TDS</th><th>Received</th><th>Balance</th><th>Status</th><th>Date</th></tr></thead>
      <tbody>{rows}</tbody></table>
      </div>
    </div>"""
    return page('Finance', content, session['user'], '/admin/finance')

@app.route('/admin/master', methods=['GET', 'POST'])
def admin_master():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d = load()
    if request.method == 'POST':
        cat = request.form.get('category')
        if cat == 'customer':
            d['customers'].append({"code": request.form.get('code', ''), "name": request.form.get('name', ''), "nick": request.form.get('nick', '')})
        elif cat == 'employee':
            d['users'].append({"id": request.form.get('emp_id', ''), "name": request.form.get('emp_name', ''), "password": request.form.get('emp_pwd', 'emp123'), "role": "employee", "designation": request.form.get('designation', '')})
        elif cat == 'car':
            d['cars'].append(request.form.get('car', ''))
        elif cat == 'driver':
            d['drivers'].append(request.form.get('driver', ''))
        elif cat == 'machine':
            d['machines'].append(request.form.get('machine', ''))
        save(d)
        flash('Master list updated!', 'success')
        return redirect(url_for('admin_master'))

    def list_items(items, label):
        if isinstance(items[0] if items else None, dict):
            lis = ''.join(f'<li style="padding:5px 0;border-bottom:1px solid #f1f5f9;font-size:13px">{i.get("name","")} <span style="color:#94a3b8">({i.get("code","")})</span></li>' for i in items)
        else:
            lis = ''.join(f'<li style="padding:5px 0;border-bottom:1px solid #f1f5f9;font-size:13px">{i}</li>' for i in items)
        return f'<div class="card"><div class="card-title">{label} ({len(items)})</div><ul style="list-style:none">{lis}</ul></div>'

    content = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div>
        <div class="card">
          <div class="card-title">Add Customer</div>
          <form method="POST"><input type="hidden" name="category" value="customer">
            <div class="fg" style="margin-bottom:10px"><label>Code</label><input name="code" placeholder="CU001" required></div>
            <div class="fg" style="margin-bottom:10px"><label>Name</label><input name="name" required></div>
            <div class="fg" style="margin-bottom:10px"><label>Nickname</label><input name="nick"></div>
            <button type="submit" class="btn btn-primary btn-sm">Add</button>
          </form>
        </div>
        <div class="card">
          <div class="card-title">Add Employee</div>
          <form method="POST"><input type="hidden" name="category" value="employee">
            <div class="fg" style="margin-bottom:10px"><label>Employee ID</label><input name="emp_id" placeholder="EMP004" required></div>
            <div class="fg" style="margin-bottom:10px"><label>Name</label><input name="emp_name" required></div>
            <div class="fg" style="margin-bottom:10px"><label>Designation</label><input name="designation"></div>
            <div class="fg" style="margin-bottom:10px"><label>Password</label><input name="emp_pwd" value="emp123"></div>
            <button type="submit" class="btn btn-primary btn-sm">Add</button>
          </form>
        </div>
        <div class="card">
          <div class="card-title">Add Vehicle</div>
          <form method="POST" style="display:flex;gap:8px"><input type="hidden" name="category" value="car">
            <input name="car" placeholder="TN-XX-XX-0000" style="flex:1;border:1px solid #e2e8f5;border-radius:7px;padding:8px 11px;font-size:13px" required>
            <button type="submit" class="btn btn-primary btn-sm">Add</button>
          </form>
        </div>
        <div class="card">
          <div class="card-title">Add Driver</div>
          <form method="POST" style="display:flex;gap:8px"><input type="hidden" name="category" value="driver">
            <input name="driver" placeholder="Driver name" style="flex:1;border:1px solid #e2e8f5;border-radius:7px;padding:8px 11px;font-size:13px" required>
            <button type="submit" class="btn btn-primary btn-sm">Add</button>
          </form>
        </div>
        <div class="card">
          <div class="card-title">Add Machine</div>
          <form method="POST" style="display:flex;gap:8px"><input type="hidden" name="category" value="machine">
            <input name="machine" placeholder="Machine name" style="flex:1;border:1px solid #e2e8f5;border-radius:7px;padding:8px 11px;font-size:13px" required>
            <button type="submit" class="btn btn-primary btn-sm">Add</button>
          </form>
        </div>
      </div>
      <div>
        {list_items(d['customers'], '👥 Customers')}
        {list_items([u for u in d['users'] if u['role']=='employee'], '👤 Employees')}
        {list_items(d['cars'], '🚗 Vehicles')}
        {list_items(d['drivers'], '🧑‍✈️ Drivers')}
        {list_items(d['machines'], '⚙️ Machines')}
      </div>
    </div>"""
    return page('Master List', content, session['user'], '/admin/master')

@app.route('/admin/stock')
def admin_stock():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d = load()
    stock_cards = [j for j in d['job_cards'] if str(j.get('stock', '0')) not in ('', '0')]
    total_stock = sum(int(j.get('stock', 0) or 0) for j in d['job_cards'])
    rows = ''.join(f"""<tr>
        <td><strong>{j['batch_no']}</strong></td>
        <td>{j['employee_name']}</td>
        <td>{j['customer_name']}</td>
        <td>{j['location']}</td>
        <td>{j['start_date']}</td>
        <td style="font-weight:700;color:#2563eb">{j.get('stock', 0)}</td>
    </tr>""" for j in reversed(stock_cards)) or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">No stock entries yet</td></tr>'
    content = f"""
    <div class="stats">
      <div class="stat"><div class="val">{total_stock}</div><div class="lbl">Total Stock Used</div></div>
      <div class="stat"><div class="val">{len(stock_cards)}</div><div class="lbl">Jobs with Stock</div></div>
    </div>
    <div class="card">
      <div class="card-title">Stock Report</div>
      <table><thead><tr><th>Batch No</th><th>Employee</th><th>Customer</th><th>Location</th><th>Date</th><th>Stock</th></tr></thead>
      <tbody>{rows}</tbody></table>
    </div>"""
    return page('Stock', content, session['user'], '/admin/stock')

# ─── Run ──────────────────────────────────────────────────────────────────────

import json as _json_module
json = _json_module

if __name__ == '__main__':
    app.run(debug=True, port=5050)
