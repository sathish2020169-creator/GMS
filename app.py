from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import json, os, uuid

app = Flask(__name__)
app.secret_key = 'gms-tracker-secret-2025'
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

# ─── Data Layer ───────────────────────────────────────────────────────────────

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {
        "users": [
            {"id": "ADM001", "name": "Admin",          "password": "admin123",  "role": "admin",    "designation": "Administrator"},
            {"id": "EMP001", "name": "Rajesh Kumar",   "password": "emp123",    "role": "employee", "designation": "CMM Engineer"},
            {"id": "EMP002", "name": "Priya Sharma",   "password": "emp123",    "role": "employee", "designation": "Finance"},
            {"id": "EMP003", "name": "Selvam M",       "password": "emp123",    "role": "employee", "designation": "Laser Technician"},
        ],
        "customers": [
            {"code": "WI001", "name": "Wheels India",    "nick": "WI"},
            {"code": "TM002", "name": "TVS Motors",      "nick": "TVS"},
            {"code": "AL003", "name": "Ashok Leyland",   "nick": "AL"},
            {"code": "BH004", "name": "Bharat Forge",    "nick": "BF"},
        ],
        "machines":  ["Portable CMM Arm", "Laser Tracker API", "3D Laser Scanner", "CMM Machine"],
        "laptops":   ["Laptop-001", "Laptop-002", "Laptop-003"],
        "cars":      ["TN-01-AB-1234", "TN-01-CD-5678", "TN-58-EF-9012"],
        "drivers":   ["Murugan", "Selvam", "Rajan", "Vijay"],
        "tds_rate":  10,
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

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = auth(request.form.get('uid','').strip(), request.form.get('pwd','').strip())
        if u:
            session['user'] = u
            return redirect(url_for('admin_dash' if u['role']=='admin' else 'emp_dash'))
        flash('Invalid ID or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── Employee Routes ──────────────────────────────────────────────────────────

@app.route('/employee')
def emp_dash():
    if 'user' not in session: return redirect(url_for('login'))
    d = load()
    uid = session['user']['id']
    my = [j for j in d['job_cards'] if j['employee_id'] == uid]
    return render_template('emp_dash.html', user=session['user'], cards=my)

@app.route('/employee/new_job', methods=['GET','POST'])
def new_job():
    if 'user' not in session: return redirect(url_for('login'))
    d = load()
    if request.method == 'POST':
        f  = request.form
        now = datetime.now()
        bn  = f"B-{now.strftime('%Y%m%d%H%M%S')}"
        card = {
            "id":            str(uuid.uuid4())[:8].upper(),
            "batch_no":      bn,
            "employee_id":   session['user']['id'],
            "employee_name": session['user']['name'],
            "designation":   session['user']['designation'],
            "customer_code": f.get('customer_code',''),
            "customer_name": f.get('customer_name',''),
            "start_date":    f.get('start_date',''),
            "end_date":      f.get('end_date',''),
            "start_time":    f.get('start_time',''),
            "end_time":      f.get('end_time',''),
            "unit":          f.get('unit',''),
            "location":      f.get('location',''),
            "district":      f.get('district',''),
            "state":         f.get('state',''),
            "driver":        f.get('driver',''),
            "vehicle":       f.get('vehicle',''),
            "fuel_amount":   f.get('fuel_amount',''),
            "machine":       f.get('machine',''),
            "laptop":        f.get('laptop',''),
            "v_probe":       f.get('v_probe','NOT USED'),
            "shift_hrs":     f.get('shift_hrs',''),
            "stock":         f.get('stock',''),
            "other_amount":  f.get('other_amount',''),
            "other_details": f.get('other_details',''),
            "status":        "Pending",
            "created_at":    now.strftime('%Y-%m-%d %H:%M'),
            "splits":        []
        }
        d['job_cards'].append(card)
        save(d)
        flash(f'Job Card created! Batch No: {bn}', 'success')
        return redirect(url_for('emp_dash'))
    return render_template('new_job.html', user=session['user'], d=d)

# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route('/admin')
def admin_dash():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d = load()
    total     = len(d['job_cards'])
    pending   = sum(1 for j in d['job_cards'] if j['status']=='Pending')
    completed = sum(1 for j in d['job_cards'] if j['status']=='Completed')
    fin_total = sum(r.get('total',0) for r in d['finance'])
    received  = sum(r.get('received_amount',0) for r in d['finance'])
    balance   = sum(r.get('balance',0) for r in d['finance'])
    employees = [u for u in d['users'] if u['role']=='employee']
    return render_template('admin_dash.html', user=session['user'], d=d,
        total=total, pending=pending, completed=completed,
        fin_total=fin_total, received=received, balance=balance,
        employees=employees)

@app.route('/admin/job_cards')
def admin_jobs():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d = load()
    search = request.args.get('q','').lower()
    cards  = d['job_cards']
    if search:
        cards = [c for c in cards if search in c.get('customer_name','').lower()
                 or search in c.get('batch_no','').lower()
                 or search in c.get('employee_name','').lower()]
    return render_template('admin_jobs.html', user=session['user'], cards=cards, q=search)

@app.route('/admin/job_card/<cid>', methods=['GET','POST'])
def admin_view_job(cid):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d    = load()
    card = next((j for j in d['job_cards'] if j['id']==cid), None)
    if not card:
        flash('Job card not found','error')
        return redirect(url_for('admin_jobs'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'status':
            card['status'] = request.form.get('status')
            save(d)
            flash('Status updated','success')
        elif action == 'split':
            split_h = float(request.form.get('split_hrs', 0))
            orig_h  = float(card.get('shift_hrs', 0))
            if 0 < split_h < orig_h:
                new = dict(card)
                suffix = f"-{len(card['splits'])+1:02d}"
                new['id']       = str(uuid.uuid4())[:8].upper()
                new['batch_no'] = card['batch_no'] + suffix
                new['shift_hrs']= str(split_h)
                new['splits']   = []
                card['shift_hrs'] = str(orig_h - split_h)
                card['splits'].append(new['batch_no'])
                d['job_cards'].append(new)
                save(d)
                flash(f"Split done → New batch: {new['batch_no']}", 'success')
            else:
                flash('Invalid split hours','error')
        return redirect(url_for('admin_view_job', cid=cid))
    return render_template('view_job.html', user=session['user'], card=card)

@app.route('/admin/finance', methods=['GET','POST'])
def admin_finance():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d = load()
    if request.method == 'POST':
        f       = request.form
        amount  = float(f.get('amount',0) or 0)
        gst_pct = float(f.get('gst_pct',18) or 18)
        gst_amt = round(amount * gst_pct / 100, 2)
        total   = round(amount + gst_amt, 2)
        tds     = round(amount * d.get('tds_rate',10) / 100, 2)
        recv    = float(f.get('received_amount',0) or 0)
        balance = round(total - tds - recv, 2)
        rec = {
            "id":               len(d['finance'])+1,
            "po_number":        f.get('po_number',''),
            "quotation_no":     f.get('quotation_no',''),
            "invoice_no":       f.get('invoice_no',''),
            "invoice_date":     f.get('invoice_date',''),
            "due_date":         f.get('due_date',''),
            "customer":         f.get('customer',''),
            "amount":           amount,
            "gst_pct":          gst_pct,
            "gst_amount":       gst_amt,
            "total":            total,
            "tds":              tds,
            "received_amount":  recv,
            "balance":          balance,
            "status":           "COMPLETED" if balance <= 0 else "PENDING",
            "created_at":       datetime.now().strftime('%Y-%m-%d')
        }
        d['finance'].append(rec)
        save(d)
        flash('Finance record added!','success')
        return redirect(url_for('admin_finance'))
    return render_template('finance.html', user=session['user'], d=d)

@app.route('/admin/master', methods=['GET','POST'])
def admin_master():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d = load()
    if request.method == 'POST':
        cat = request.form.get('category')
        if cat == 'customer':
            d['customers'].append({
                "code": request.form.get('code',''),
                "name": request.form.get('name',''),
                "nick": request.form.get('nick','')
            })
        elif cat == 'employee':
            d['users'].append({
                "id":          request.form.get('emp_id',''),
                "name":        request.form.get('emp_name',''),
                "password":    request.form.get('emp_pwd','emp123'),
                "role":        "employee",
                "designation": request.form.get('designation','')
            })
        elif cat == 'car':
            d['cars'].append(request.form.get('car',''))
        elif cat == 'driver':
            d['drivers'].append(request.form.get('driver',''))
        elif cat == 'machine':
            d['machines'].append(request.form.get('machine',''))
        save(d)
        flash('Master list updated!','success')
        return redirect(url_for('admin_master'))
    return render_template('master.html', user=session['user'], d=d)

@app.route('/admin/stock')
def admin_stock():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    d = load()
    return render_template('stock.html', user=session['user'], d=d)

if __name__ == '__main__':
    app.run(debug=True, port=5050)
