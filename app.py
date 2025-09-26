# -*- coding: utf-8 -*-
# --- Import necessary libraries ---
import sqlite3
import os
import json
from datetime import datetime, timedelta
from flask import (Flask, render_template, request, redirect, url_for, 
                   session, flash, g, jsonify, send_from_directory)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- App Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_for_production_final_v9'
app.config['DATABASE'] = 'dems.db'
app.config['UPLOAD_FOLDER'] = 'uploads/pending'
app.config['AVATAR_FOLDER'] = 'uploads/avatars'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


# --- Database Connection & Global Context ---

@app.before_request
def before_request():
    """
    Before every request, this function runs.
    It checks if a user is logged in (by checking the session) and, if so,
    fetches their data from the database. This 'g.user' object is then
    available throughout the request, including in all HTML templates.
    """
    g.user = None
    if 'user_id' in session:
        g.user = query_db('SELECT * FROM users WHERE id = ?', [session['user_id']], one=True)

def get_db():
    """
    Opens a new database connection if there is none yet for the
    current application context.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """A helper function to make database queries easier."""
    cur = get_db().execute(query, args); rv = cur.fetchall(); cur.close()
    return (rv[0] if rv else None) if one else rv


# --- Helper Functions ---

def allowed_file(filename):
    """Checks if an uploaded file has an allowed image extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_next_project_name():
    """Generates the next sequential project name (e.g., HL_B_001 -> HL_B_002)."""
    last_project = query_db("SELECT project_name FROM projects ORDER BY id DESC LIMIT 1", one=True)
    if not last_project: return "HL_B_001"
    last_num = int(last_project['project_name'].split('_')[-1])
    return f"HL_B_{str(last_num + 1).zfill(3)}"

def get_next_employee_id():
    """Generates the next sequential employee ID (e.g., DT-UAO-000001 -> DT-UAO-000002)."""
    last_user = query_db('SELECT employee_id FROM users ORDER BY id DESC LIMIT 1', one=True)
    if not last_user: return "DT-UAO-000001"
    last_id_num = int(last_user['employee_id'].split('-')[-1])
    return f"DT-UAO-{str(last_id_num + 1).zfill(6)}"

def sync_images_with_db():
    """
    Scans the 'uploads/pending' folder and adds any new image filenames
    to the database so they can be assigned to projects.
    """
    db = get_db(); cursor = db.cursor()
    upload_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_path): os.makedirs(upload_path)
    cursor.execute('SELECT filename FROM images'); db_filenames = {row['filename'] for row in cursor.fetchall()}
    folder_filenames = {f for f in os.listdir(upload_path) if os.path.isfile(os.path.join(upload_path, f))}
    new_files = folder_filenames - db_filenames
    if new_files:
        cursor.executemany('INSERT INTO images (filename, status) VALUES (?, ?)', [(fname, 'unassigned') for fname in new_files])
        db.commit()
    return len(new_files)


# --- File Serving Routes ---

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serves files from the UPLOAD_FOLDER (for data entry tasks)."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/avatars/<path:filename>')
def avatar_file(filename):
    """Serves files from the AVATAR_FOLDER (for user profile pictures)."""
    avatar_path = os.path.join(app.root_path, app.config['AVATAR_FOLDER'])
    if not os.path.exists(avatar_path): os.makedirs(avatar_path)
    return send_from_directory(app.config['AVATAR_FOLDER'], filename)


# --- Authentication & Core Routes ---

@app.route('/contact', methods=['POST'])
def handle_contact():
    """Handles submission from the WhatsApp contact modal."""
    if not g.user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
    name = request.form.get('name'); email = request.form.get('email'); message = request.form.get('message')
    mobile = request.form.get('mobile_number')
    if not name or not email or not message:
        return jsonify({'status': 'error', 'message': 'All fields are required'}), 400
    db = get_db(); db.execute('INSERT INTO inquiries (name, email, mobile_number, message) VALUES (?, ?, ?, ?)', (name, email, mobile, message)); db.commit()
    return jsonify({'status': 'success', 'message': 'Your query has been received!'})

@app.route('/', methods=['GET', 'POST'])
def login():
    """Handles the user login process."""
    if g.user: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # FIX: Email is converted to lowercase for case-insensitive login
        user = query_db('SELECT * FROM users WHERE email = ?', [request.form['email'].lower()], one=True)
        if user and check_password_hash(user['password_hash'], request.form['password']):
            # FIX: Checks if the user's account is active before logging in
            if user['status'] == 'active':
                session['user_id'] = user['id']; session['user_role'] = user['role']; session['user_name'] = user['name']
                # Update last_login timestamp
                db = get_db(); db.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", [user['id']]); db.commit()
                return redirect(url_for('dashboard'))
            else:
                flash("Your account has been deactivated. Please contact an administrator.", "error")
        else:
            flash("Invalid email or password.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.clear(); flash("You have been successfully logged out.", "success"); return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Redirects logged-in users to their appropriate dashboard."""
    if not g.user: return redirect(url_for('login'))
    return redirect(url_for('admin_dashboard')) if g.user['role'] == 'admin' else redirect(url_for('employee_dashboard'))


# --- Admin Routes ---

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    """
    Displays the main admin dashboard. Also handles the project history search.
    """
    if g.user is None or g.user['role'] != 'admin': return redirect(url_for('login'))
    
    sync_images_with_db()
    available_images = query_db("SELECT COUNT(id) as count FROM images WHERE status = 'unassigned'", one=True)['count']
    review_projects = query_db("SELECT p.*, u.name as employee_name FROM projects p JOIN users u ON p.employee_id = u.id WHERE p.status = 'In Review' ORDER BY p.assigned_date DESC")
    active_employees = query_db("SELECT id, name, employee_id FROM users WHERE role = 'employee' AND status = 'active' ORDER BY name")
    
    search_results = []
    if request.method == 'POST' and 'search_term' in request.form:
        search_term = request.form.get('search_term')
        if search_term:
            search_query = f"%{search_term}%"
            search_results = query_db("""
                SELECT p.*, u.name as employee_name, u.employee_id as emp_id FROM projects p 
                JOIN users u ON p.employee_id = u.id 
                WHERE (p.project_name LIKE ? OR u.employee_id LIKE ?) AND p.status IN ('Approved', 'Rejected')
                ORDER BY p.assigned_date DESC
            """, [search_query, search_query])
    
    return render_template('admin_dashboard.html', active_employees=active_employees, available_images=available_images, review_projects=review_projects, search_results=search_results)

@app.route('/admin/inquiries')
def view_inquiries():
    """Displays the new page for viewing contact inquiries."""
    if g.user is None or g.user['role'] != 'admin': return redirect(url_for('login'))
    inquiries = query_db("SELECT * FROM inquiries ORDER BY submitted_at DESC")
    return render_template('inquiries.html', inquiries=inquiries)

@app.route('/admin/create_employee', methods=['POST'])
def create_employee():
    """Handles the creation of new employee accounts."""
    if g.user is None or g.user['role'] != 'admin': return redirect(url_for('login'))
    
    name = request.form['name']
    email = request.form['email'].lower()
    password = request.form['password']
    
    # FIX: Check if email already exists before inserting
    existing_user = query_db('SELECT * FROM users WHERE email = ?', [email], one=True)
    if existing_user:
        flash(f"Error: An account with the email '{email}' already exists.", "error")
        return redirect(url_for('admin_dashboard'))
    
    # If email is unique, proceed to create the user
    try:
        db = get_db()
        db.execute(
            'INSERT INTO users (employee_id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)',
            (get_next_employee_id(), name, email, generate_password_hash(password), 'employee')
        )
        db.commit()
        flash(f"Employee account for {name} created successfully.", "success")
    except sqlite3.IntegrityError:
        # This is a fallback check, mainly for the unique employee_id
        flash("Error: Could not create employee. The Employee ID or Email might already be in use.", "error")
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/assign_tasks', methods=['POST'])
def assign_tasks():
    """Handles the creation and assignment of a new project."""
    if g.user is None or g.user['role'] != 'admin': return redirect(url_for('login'))
    employee_id = int(request.form['employee_select']); task_count = int(request.form['task_count'])
    cost = float(request.form['project_cost']); security = float(request.form['security_money'])
    expiry_days = int(request.form['expiry_days']); 
    expiry_date = datetime.utcnow() + timedelta(days=expiry_days)
    
    unassigned_images = query_db("SELECT * FROM images WHERE status = 'unassigned' LIMIT ?", [task_count])
    if len(unassigned_images) < task_count:
        flash(f"Error: Only {len(unassigned_images)} images available.", "error"); return redirect(url_for('admin_dashboard'))
        
    db = get_db(); project_name = get_next_project_name()
    cursor = db.execute("INSERT INTO projects (project_name, employee_id, cost, security_deposit, expiry_date) VALUES (?, ?, ?, ?, ?)", (project_name, employee_id, cost, security, expiry_date))
    project_id = cursor.lastrowid
    
    for image in unassigned_images:
        db.execute("INSERT INTO tasks (project_id, image_id) VALUES (?, ?)", (project_id, image['id'])); db.execute("UPDATE images SET status = 'assigned' WHERE id = ?", [image['id']])
    db.commit(); flash(f"Project {project_name} with {task_count} tasks assigned.", "success"); return redirect(url_for('admin_dashboard'))

@app.route('/admin/employee_details/<int:user_id>')
def get_employee_details(user_id):
    """API endpoint for the admin's employee details modal."""
    if g.user is None or g.user['role'] != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    employee = query_db("SELECT * FROM users WHERE id = ?", [user_id], one=True)
    if not employee: return jsonify({'error': 'User not found'}), 404
    projects_assigned = query_db("SELECT COUNT(id) as count FROM projects WHERE employee_id = ?", [user_id], one=True)['count']
    projects_completed = query_db("SELECT COUNT(id) as count FROM projects WHERE employee_id = ? AND status IN ('In Review', 'Approved', 'Rejected')", [user_id], one=True)['count']
    details = {"id": employee['id'], "name": employee['name'], "employeeId": employee['employee_id'], "email": employee['email'], "joiningDate": employee['joining_date'].strftime('%Y-%m-%d'), "status": employee['status'], "projectsAssigned": projects_assigned, "projectsCompleted": projects_completed, "walletBalance": f"{employee['wallet_balance']:.2f}", "profilePicture": employee['profile_picture']}
    return jsonify(details)

@app.route('/admin/toggle_status/<int:user_id>', methods=['POST'])
def toggle_employee_status(user_id):
    """Activates or deactivates an employee account."""
    if g.user is None or g.user['role'] != 'admin': return redirect(url_for('login'))
    user = query_db("SELECT * FROM users WHERE id = ?", [user_id], one=True)
    if user:
        new_status = 'inactive' if user['status'] == 'active' else 'active'
        db = get_db(); db.execute("UPDATE users SET status = ? WHERE id = ?", [new_status, user_id]); db.commit()
        flash(f"User {user['name']} has been set to {new_status}.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/review/<int:project_id>')
def review_project(project_id):
    """Displays the admin's project review page."""
    if g.user is None or g.user['role'] != 'admin': return redirect(url_for('login'))
    project = query_db("SELECT p.*, u.name as employee_name, u.employee_id as emp_id FROM projects p JOIN users u ON p.employee_id = u.id WHERE p.id = ?", [project_id], one=True)
    tasks = query_db("SELECT t.id, t.data_json, i.filename FROM tasks t JOIN images i ON t.image_id = i.id WHERE t.project_id = ? ORDER BY t.id", [project_id])
    project_tasks = [dict(task, data=json.loads(task['data_json']) if task['data_json'] else {}) for task in tasks]
    return render_template('admin_review.html', project=project, tasks=project_tasks)

@app.route('/admin/update_task/<int:task_id>', methods=['POST'])
def update_task_data(task_id):
    """Handles edits made by an admin on the review page."""
    if g.user is None or g.user['role'] != 'admin': return redirect(url_for('login'))
    task = query_db("SELECT project_id FROM tasks WHERE id = ?", [task_id], one=True)
    if not task: return redirect(url_for('admin_dashboard'))
    updated_data = {
        'name': request.form.get('name'),'age': request.form.get('age'),
        'mobileNumber': request.form.get('mobileNumber'),'sex': request.form.get('sex'),
        'address': request.form.get('address'),'receiptNumber': request.form.get('receiptNumber'),
    }
    db = get_db(); db.execute("UPDATE tasks SET data_json = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?", [json.dumps(updated_data), task_id]); db.commit()
    flash(f"Task data for TASK-{str(task_id).zfill(7)} updated.", "success")
    return redirect(url_for('review_project', project_id=task['project_id']))

@app.route('/admin/finalize_project/<int:project_id>', methods=['POST'])
def finalize_project(project_id):
    """Handles approving or rejecting a completed project."""
    if g.user is None or g.user['role'] != 'admin': return redirect(url_for('login'))
    action = request.form.get('action'); project = query_db("SELECT * FROM projects WHERE id = ?", [project_id], one=True)
    if not project or project['status'] != 'In Review':
        flash("Project cannot be finalized.", "error"); return redirect(url_for('admin_dashboard'))
    db = get_db()
    if action == 'approve':
        new_status = 'Approved'
        db.execute("UPDATE users SET wallet_balance = wallet_balance + ? WHERE id = ?", [project['cost'], project['employee_id']])
        flash(f"Project {project['project_name']} approved. ₹{project['cost']:.2f} added to wallet.", "success")
    elif action == 'reject': new_status = 'Rejected'; flash(f"Project {project['project_name']} has been rejected.", "info")
    else: return redirect(url_for('admin_dashboard'))
    db.execute("UPDATE projects SET status = ? WHERE id = ?", [new_status, project_id]); db.commit()
    return redirect(url_for('admin_dashboard'))


# --- Employee Routes ---

@app.route('/employee')
def employee_dashboard():
    """Displays the main employee dashboard."""
    if g.user is None or g.user['role'] != 'employee': return redirect(url_for('login'))
    active_projects_raw = query_db("SELECT * FROM projects WHERE employee_id = ? AND status = 'In Progress' ORDER BY assigned_date DESC", [g.user['id']])
    active_projects = []
    for project in active_projects_raw:
        proj_dict = dict(project)
        total_tasks = query_db("SELECT COUNT(id) as count FROM tasks WHERE project_id = ?", [project['id']], one=True)['count']
        saved_tasks = query_db("SELECT COUNT(id) as count FROM tasks WHERE project_id = ? AND status = 'Saved'", [project['id']], one=True)['count']
        proj_dict['progress'] = int((saved_tasks / total_tasks) * 100) if total_tasks > 0 else 0
        proj_dict['is_submittable'] = total_tasks > 0 and saved_tasks == total_tasks
        proj_dict['expiry_iso'] = project['expiry_date'].strftime('%Y-%m-%dT%H:%M:%SZ') if project['expiry_date'] else None
        active_projects.append(proj_dict)
    completed_projects = query_db("SELECT * FROM projects WHERE employee_id = ? AND status IN ('In Review', 'Approved', 'Rejected') ORDER BY assigned_date DESC", [g.user['id']])
    return render_template('employee_dashboard.html', active_projects=active_projects, completed_projects=completed_projects)

@app.route('/employee/submit_project/<int:project_id>', methods=['POST'])
def submit_project(project_id):
    """Handles the employee submitting a fully saved project."""
    if g.user is None or g.user['role'] != 'employee': return redirect(url_for('login'))
    project = query_db("SELECT * FROM projects WHERE id = ? AND employee_id = ?", [project_id, g.user['id']], one=True)
    if not project or project['status'] != 'In Progress': flash("Project cannot be submitted.", "error"); return redirect(url_for('employee_dashboard'))
    db = get_db(); db.execute("UPDATE projects SET status = 'In Review' WHERE id = ?", [project_id]); db.execute("UPDATE tasks SET status = 'Submitted' WHERE project_id = ?", [project_id]); db.commit()
    flash(f"Project {project['project_name']} has been submitted for review.", "success"); return redirect(url_for('employee_dashboard'))

@app.route('/employee/profile', methods=['GET', 'POST'])
def employee_profile():
    """Displays and handles updates to the employee's profile."""
    if g.user is None or g.user['role'] != 'employee': return redirect(url_for('login'))
    if request.method == 'POST':
        db = get_db()
        db.execute("UPDATE users SET phone_number = ?, gender = ?, date_of_birth = ?, designation = ? WHERE id = ?", (request.form.get('phone_number'), request.form.get('gender'), request.form.get('date_of_birth'), request.form.get('designation'), g.user['id']))
        bank_details_dict = {"holder_name": request.form.get('holder_name'), "bank_name": request.form.get('bank_name'), "account_number": request.form.get('account_number'), "ifsc_code": request.form.get('ifsc_code')}
        db.execute("UPDATE users SET bank_details = ? WHERE id = ?", (json.dumps(bank_details_dict), g.user['id']))
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"user_{g.user['id']}_{file.filename}")
                avatar_path = os.path.join(app.root_path, app.config['AVATAR_FOLDER'])
                if not os.path.exists(avatar_path): os.makedirs(avatar_path)
                file.save(os.path.join(avatar_path, filename))
                db.execute("UPDATE users SET profile_picture = ? WHERE id = ?", (filename, g.user['id']))
        db.commit(); flash("Profile updated successfully!", "success"); return redirect(url_for('employee_profile'))
    bank_data = json.loads(g.user['bank_details']) if g.user['bank_details'] else {}
    return render_template('profile.html', bank_data=bank_data)

@app.route('/employee/project/<int:project_id>')
def view_project(project_id):
    """Displays the list of tasks for a specific project."""
    if g.user is None or g.user['role'] != 'employee': return redirect(url_for('login'))
    project = query_db("SELECT * FROM projects WHERE id = ? AND employee_id = ?", [project_id, g.user['id']], one=True)
    if not project or project['status'] != 'In Progress': flash("Project cannot be accessed.", "error"); return redirect(url_for('employee_dashboard'))
    tasks = query_db("SELECT t.id, t.status, t.data_json FROM tasks t WHERE t.project_id = ? ORDER BY t.id", [project_id])
    expiry_iso = project['expiry_date'].strftime('%Y-%m-%dT%H:%M:%SZ') if project['expiry_date'] else None
    return render_template('project_view.html', project=project, tasks=tasks, expiry_iso=expiry_iso)

@app.route('/employee/task/<int:task_id>', methods=['GET', 'POST'])
def data_entry(task_id):
    """Displays the data entry screen for a single task."""
    if g.user is None or g.user['role'] != 'employee': return redirect(url_for('login'))
    task = query_db("SELECT t.*, i.filename, p.employee_id, p.expiry_date, p.status as project_status FROM tasks t JOIN images i ON t.image_id = i.id JOIN projects p ON t.project_id = p.id WHERE t.id = ? AND p.employee_id = ?", [task_id, g.user['id']], one=True)
    if not task or task['project_status'] != 'In Progress': flash("Task cannot be accessed.", "error"); return redirect(url_for('employee_dashboard'))
    if datetime.utcnow() > task['expiry_date']: flash("This project has expired.", "error"); return redirect(url_for('view_project', project_id=task['project_id']))
    if request.method == 'POST':
        entry_data = {'name': request.form.get('name'),'age': request.form.get('age'),'mobileNumber': request.form.get('mobileNumber'),'sex': request.form.get('sex'),'address': request.form.get('address'),'receiptNumber': request.form.get('receiptNumber')}
        db = get_db(); db.execute("UPDATE tasks SET data_json = ?, status = 'Saved', last_updated = CURRENT_TIMESTAMP WHERE id = ?", [json.dumps(entry_data), task_id]); db.commit()
        flash(f"Task TASK-{str(task_id).zfill(7)} progress saved.", "success"); return redirect(url_for('view_project', project_id=task['project_id']))
    saved_data = json.loads(task['data_json']) if task['data_json'] else {}
    expiry_iso = task['expiry_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
    return render_template('data_entry.html', task=task, saved_data=saved_data, expiry_iso=expiry_iso)


if __name__ == '__main__':
    # Runs the app in debug mode for development
    app.run(debug=True, port=5001)

