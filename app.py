import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import random
import json

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="CPPA | Campus Placement Portal",
    page_icon="🎓",
    layout="wide"
)

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect("placement.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student','admin')),
            roll_number TEXT,
            branch TEXT,
            cgpa REAL,
            backlogs INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role_offered TEXT,
            package_lpa REAL,
            cgpa_cutoff REAL DEFAULT 0,
            max_backlogs INTEGER DEFAULT 0,
            drive_date TEXT,
            status TEXT DEFAULT 'Active' CHECK(status IN ('Active','Completed','Cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            app_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            current_stage TEXT DEFAULT 'Applied',
            status TEXT DEFAULT 'In Progress',
            admin_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(user_id),
            FOREIGN KEY (company_id) REFERENCES companies(company_id),
            UNIQUE(student_id, company_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS stage_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id INTEGER NOT NULL,
            stage_name TEXT NOT NULL,
            action TEXT NOT NULL,
            actor_email TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (app_id) REFERENCES applications(app_id)
        )
    """)

    # Seed admin account
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE email = 'admin@iiitm.ac.in'")
    if not c.fetchone():
        c.execute("""
            INSERT INTO users (full_name, email, password_hash, role)
            VALUES ('Placement Cell', 'admin@iiitm.ac.in', ?, 'admin')
        """, (admin_hash,))

    # Seed sample data if empty
    c.execute("SELECT COUNT(*) as cnt FROM companies")
    if c.fetchone()["cnt"] == 0:
        seed_sample_data(conn)

    conn.commit()
    return conn

def seed_sample_data(conn):
    c = conn.cursor()

    # Sample companies
    companies = [
        ("TCS", "Software Developer", 7.0, 7.0, 0, "2026-11-15", "Active"),
        ("Infosys", "Systems Engineer", 6.5, 6.5, 0, "2026-11-20", "Active"),
        ("Wipro", "Project Engineer", 6.0, 6.0, 1, "2026-11-25", "Active"),
        ("Microsoft", "SDE Intern", 18.0, 8.0, 0, "2026-12-05", "Active"),
        ("Amazon", "SDE-1", 28.0, 8.5, 0, "2026-12-10", "Active"),
        ("Deloitte", "Analyst", 8.5, 7.5, 0, "2026-11-18", "Completed"),
        ("Cognizant", "Programmer Analyst", 5.5, 6.0, 1, "2026-11-12", "Completed"),
    ]
    for comp in companies:
        c.execute("""
            INSERT INTO companies (name, role_offered, package_lpa, cgpa_cutoff, max_backlogs, drive_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, comp)

    # Sample students
    students = [
        ("Aarav Sharma", "aarav@iiitm.ac.in", "student", "2025MBA001", "MBA", 8.5, 0),
        ("Priya Patel", "priya@iiitm.ac.in", "student", "2025MBA002", "MBA", 7.8, 0),
        ("Rohit Kumar", "rohit@iiitm.ac.in", "student", "2025MBA003", "MBA", 7.2, 0),
        ("Sneha Gupta", "sneha@iiitm.ac.in", "student", "2025MBA004", "MBA", 9.1, 0),
        ("Amit Verma", "amit@iiitm.ac.in", "student", "2025MBA005", "MBA", 6.8, 1),
        ("Neha Singh", "neha@iiitm.ac.in", "student", "2025MBA006", "MBA", 8.0, 0),
        ("Vikash Yadav", "vikash@iiitm.ac.in", "student", "2025MBA007", "MBA", 6.2, 0),
        ("Pooja Mishra", "pooja@iiitm.ac.in", "student", "2025MBA008", "MBA", 7.5, 0),
    ]
    pwd_hash = hashlib.sha256("student123".encode()).hexdigest()
    for s in students:
        c.execute("""
            INSERT INTO users (full_name, email, password_hash, role, roll_number, branch, cgpa, backlogs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (s[0], s[1], pwd_hash, s[2], s[3], s[4], s[5], s[6]))

    # Sample applications with various stages
    stages = ["Applied", "Shortlisted", "Round 1", "Round 2", "HR Round", "Offered", "Accepted"]
    statuses = ["In Progress", "In Progress", "In Progress", "In Progress", "In Progress", "In Progress", "Placed"]

    sample_apps = [
        (2, 1, "Shortlisted", "In Progress"),
        (2, 6, "Offered", "In Progress"),
        (3, 1, "Applied", "In Progress"),
        (3, 3, "Round 1", "In Progress"),
        (4, 1, "Round 2", "In Progress"),
        (4, 4, "Shortlisted", "In Progress"),
        (5, 1, "Accepted", "Placed"),
        (5, 6, "Accepted", "Placed"),
        (6, 3, "Applied", "Rejected"),
        (6, 1, "Shortlisted", "In Progress"),
        (7, 7, "Accepted", "Placed"),
        (7, 1, "Round 1", "In Progress"),
        (8, 1, "Applied", "In Progress"),
        (8, 6, "Round 2", "In Progress"),
        (9, 1, "Shortlisted", "In Progress"),
        (9, 3, "Offered", "In Progress"),
    ]

    for app in sample_apps:
        c.execute("""
            INSERT INTO applications (student_id, company_id, current_stage, status)
            VALUES (?, ?, ?, ?)
        """, app)

    # Sample stage logs
    for i, app in enumerate(sample_apps, 1):
        c.execute("""
            INSERT INTO stage_logs (app_id, stage_name, action, actor_email, note)
            VALUES (?, 'Applied', 'Student applied', ?, 'Application submitted')
        """, (i, f"student{app[0]}@iiitm.ac.in"))
        if app[2] != "Applied":
            c.execute("""
                INSERT INTO stage_logs (app_id, stage_name, action, actor_email, note)
                VALUES (?, ?, 'Status updated by Placement Cell', 'admin@iiitm.ac.in', ?)
            """, (i, app[2], f"Moved to {app[2]}"))

    conn.commit()


# ─────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def authenticate(email, password, role):
    conn = get_db()
    c = conn.cursor()
    pwd_hash = hash_password(password)
    c.execute("SELECT * FROM users WHERE email = ? AND password_hash = ? AND role = ?",
              (email, pwd_hash, role))
    return c.fetchone()

def register_student(full_name, email, password, roll_number, branch, cgpa, backlogs):
    conn = get_db()
    c = conn.cursor()
    try:
        pwd_hash = hash_password(password)
        c.execute("""
            INSERT INTO users (full_name, email, password_hash, role, roll_number, branch, cgpa, backlogs)
            VALUES (?, ?, ?, 'student', ?, ?, ?, ?)
        """, (full_name, email, pwd_hash, roll_number, branch, cgpa, backlogs))
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Email already registered."


# ─────────────────────────────────────────────
# ANIMATION - PLACEMENT PIPELINE
# ─────────────────────────────────────────────
def render_pipeline_animation():
    """Animated SVG showing students flowing through placement stages"""

    animation_html = """
    <style>
        .pipeline-container {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-radius: 16px;
            padding: 30px 20px;
            overflow: hidden;
            position: relative;
            font-family: 'Segoe UI', sans-serif;
        }
        .pipeline-title {
            color: #e2e8f0;
            text-align: center;
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .pipeline-subtitle {
            color: #94a3b8;
            text-align: center;
            font-size: 13px;
            margin-bottom: 30px;
        }
        .stage-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            position: relative;
        }
        .stage-box {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 10px;
            padding: 12px 8px;
            text-align: center;
            width: 13%;
            position: relative;
            transition: all 0.3s;
        }
        .stage-box:hover {
            background: rgba(255,255,255,0.15);
            transform: translateY(-2px);
        }
        .stage-name {
            color: #e2e8f0;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .stage-count {
            font-size: 24px;
            font-weight: 800;
            margin-bottom: 2px;
        }
        .stage-label {
            color: #94a3b8;
            font-size: 10px;
        }
        .arrow {
            color: #475569;
            font-size: 20px;
            animation: pulse-arrow 1.5s ease-in-out infinite;
        }
        @keyframes pulse-arrow {
            0%, 100% { opacity: 0.4; transform: translateX(0); }
            50% { opacity: 1; transform: translateX(4px); }
        }

        /* Moving dots animation */
        .dot-track {
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 2px;
            z-index: 0;
        }
        .moving-dot {
            position: absolute;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            top: -3px;
            animation: move-dot linear infinite;
        }
        @keyframes move-dot {
            0% { left: 0%; opacity: 0; }
            5% { opacity: 1; }
            95% { opacity: 1; }
            100% { left: 100%; opacity: 0; }
        }

        /* Student icons floating */
        .student-flow {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .student-icon {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            animation: float-student 3s ease-in-out infinite;
            position: relative;
        }
        .student-icon .tooltip {
            display: none;
            position: absolute;
            bottom: 42px;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            color: #e2e8f0;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            white-space: nowrap;
            border: 1px solid #334155;
        }
        .student-icon:hover .tooltip { display: block; }

        @keyframes float-student {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-6px); }
        }

        /* Funnel visualization */
        .funnel-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 25px;
            gap: 3px;
        }
        .funnel-bar {
            height: 28px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 11px;
            font-weight: 600;
            transition: all 0.3s;
            animation: funnel-grow 1.5s ease-out forwards;
            opacity: 0;
        }
        .funnel-bar:hover {
            filter: brightness(1.2);
            transform: scaleX(1.03);
        }
        @keyframes funnel-grow {
            0% { width: 0%; opacity: 0; }
            100% { opacity: 1; }
        }

        .stats-row {
            display: flex;
            justify-content: space-around;
            margin-top: 25px;
            gap: 10px;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 14px 20px;
            text-align: center;
            flex: 1;
        }
        .stat-value {
            font-size: 28px;
            font-weight: 800;
            margin-bottom: 4px;
        }
        .stat-desc {
            color: #94a3b8;
            font-size: 11px;
        }

        /* Rejected path */
        .rejected-section {
            margin-top: 15px;
            padding: 12px;
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 10px;
            text-align: center;
        }
        .rejected-title {
            color: #f87171;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .rejected-count {
            color: #fca5a5;
            font-size: 11px;
        }
    </style>

    <div class="pipeline-container">
        <div class="pipeline-title">Placement Pipeline - Live Process Flow</div>
        <div class="pipeline-subtitle">Watch students move through each stage of the placement process</div>

        <!-- Stage Pipeline -->
        <div class="stage-row">
            <div class="dot-track">
                <div class="moving-dot" style="background:#3b82f6; animation-duration:4s; animation-delay:0s;"></div>
                <div class="moving-dot" style="background:#22c55e; animation-duration:5s; animation-delay:1s;"></div>
                <div class="moving-dot" style="background:#a855f7; animation-duration:4.5s; animation-delay:2s;"></div>
                <div class="moving-dot" style="background:#f59e0b; animation-duration:3.5s; animation-delay:0.5s;"></div>
                <div class="moving-dot" style="background:#06b6d4; animation-duration:5.5s; animation-delay:1.5s;"></div>
            </div>

            <div class="stage-box">
                <div class="stage-name">APPLIED</div>
                <div class="stage-count" style="color:#3b82f6;">200</div>
                <div class="stage-label">students</div>
            </div>
            <div class="arrow">&#10132;</div>
            <div class="stage-box">
                <div class="stage-name">ELIGIBLE</div>
                <div class="stage-count" style="color:#8b5cf6;">152</div>
                <div class="stage-label">passed cutoff</div>
            </div>
            <div class="arrow">&#10132;</div>
            <div class="stage-box">
                <div class="stage-name">SHORTLISTED</div>
                <div class="stage-count" style="color:#06b6d4;">68</div>
                <div class="stage-label">by company</div>
            </div>
            <div class="arrow">&#10132;</div>
            <div class="stage-box">
                <div class="stage-name">ROUND 1</div>
                <div class="stage-count" style="color:#f59e0b;">45</div>
                <div class="stage-label">interviewed</div>
            </div>
            <div class="arrow">&#10132;</div>
            <div class="stage-box">
                <div class="stage-name">ROUND 2</div>
                <div class="stage-count" style="color:#f97316;">22</div>
                <div class="stage-label">advanced</div>
            </div>
            <div class="arrow">&#10132;</div>
            <div class="stage-box">
                <div class="stage-name">HR ROUND</div>
                <div class="stage-count" style="color:#ec4899;">14</div>
                <div class="stage-label">final round</div>
            </div>
            <div class="arrow">&#10132;</div>
            <div class="stage-box">
                <div class="stage-name">OFFERED</div>
                <div class="stage-count" style="color:#22c55e;">10</div>
                <div class="stage-label">selected</div>
            </div>
        </div>

        <!-- Funnel Visualization -->
        <div class="funnel-container">
            <div class="funnel-bar" style="width:100%; background:linear-gradient(90deg,#3b82f6,#2563eb); animation-delay:0.1s;">Applied: 200</div>
            <div class="funnel-bar" style="width:76%; background:linear-gradient(90deg,#8b5cf6,#7c3aed); animation-delay:0.3s;">Eligible: 152</div>
            <div class="funnel-bar" style="width:34%; background:linear-gradient(90deg,#06b6d4,#0891b2); animation-delay:0.5s;">Shortlisted: 68</div>
            <div class="funnel-bar" style="width:22.5%; background:linear-gradient(90deg,#f59e0b,#d97706); animation-delay:0.7s;">Round 1: 45</div>
            <div class="funnel-bar" style="width:11%; background:linear-gradient(90deg,#f97316,#ea580c); animation-delay:0.9s;">Round 2: 22</div>
            <div class="funnel-bar" style="width:7%; background:linear-gradient(90deg,#ec4899,#db2777); animation-delay:1.1s;">HR: 14</div>
            <div class="funnel-bar" style="width:5%; background:linear-gradient(90deg,#22c55e,#16a34a); animation-delay:1.3s;">Offered: 10</div>
        </div>

        <!-- Stats -->
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-value" style="color:#22c55e;">5%</div>
                <div class="stat-desc">Conversion Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color:#3b82f6;">7</div>
                <div class="stat-desc">Active Drives</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color:#f59e0b;">12.4 LPA</div>
                <div class="stat-desc">Avg. Package</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color:#a855f7;">3</div>
                <div class="stat-desc">Students Placed</div>
            </div>
        </div>

        <!-- Rejected students indicator -->
        <div class="rejected-section">
            <div class="rejected-title">Dropoff at Each Stage</div>
            <div class="rejected-count">48 not eligible | 84 not shortlisted | 23 dropped Round 1 | 23 dropped Round 2 | 8 dropped HR | 4 declined offer</div>
        </div>
    </div>
    """
    components.html(animation_html, height=680)


# ─────────────────────────────────────────────
# STUDENT PORTAL
# ─────────────────────────────────────────────
def student_portal(user):
    st.markdown(f"### Welcome, {user['full_name']} 👋")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 My Profile", "🏢 Active Drives", "📊 My Applications", "🔄 Process Flow"])

    conn = get_db()
    c = conn.cursor()

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Full Name:**")
            st.info(user['full_name'])
            st.markdown("**Email:**")
            st.info(user['email'])
            st.markdown("**Roll Number:**")
            st.info(user['roll_number'] or "Not set")
        with col2:
            st.markdown("**Branch:**")
            st.info(user['branch'] or "Not set")
            st.markdown("**CGPA:**")
            st.info(user['cgpa'] or "Not set")
            st.markdown("**Active Backlogs:**")
            st.info(user['backlogs'])

    with tab2:
        c.execute("SELECT * FROM companies WHERE status = 'Active' ORDER BY drive_date")
        drives = c.fetchall()

        if not drives:
            st.info("No active placement drives right now.")
        else:
            for drive in drives:
                eligible = (user['cgpa'] or 0) >= drive['cgpa_cutoff'] and (user['backlogs'] or 0) <= drive['max_backlogs']

                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**{drive['name']}** - {drive['role_offered']}")
                        st.caption(f"Package: {drive['package_lpa']} LPA | CGPA Cutoff: {drive['cgpa_cutoff']} | Max Backlogs: {drive['max_backlogs']}")
                    with col2:
                        st.caption(f"Drive Date: {drive['drive_date']}")
                        if eligible:
                            st.success("Eligible", icon="✅")
                        else:
                            st.error("Not Eligible", icon="❌")
                    with col3:
                        if eligible:
                            # Check if already applied
                            c.execute("SELECT * FROM applications WHERE student_id = ? AND company_id = ?",
                                      (user['user_id'], drive['company_id']))
                            existing = c.fetchone()
                            if existing:
                                st.info("Applied ✓")
                            else:
                                if st.button("Apply", key=f"apply_{drive['company_id']}"):
                                    c.execute("""
                                        INSERT INTO applications (student_id, company_id, current_stage, status)
                                        VALUES (?, ?, 'Applied', 'In Progress')
                                    """, (user['user_id'], drive['company_id']))
                                    c.execute("""
                                        INSERT INTO stage_logs (app_id, stage_name, action, actor_email, note)
                                        VALUES (last_insert_rowid(), 'Applied', 'Student applied', ?, 'Application submitted')
                                    """, (user['email'],))
                                    conn.commit()
                                    st.success("Applied!")
                                    st.rerun()
                    st.divider()

    with tab3:
        c.execute("""
            SELECT a.*, c.name as company_name, c.role_offered, c.package_lpa
            FROM applications a
            JOIN companies c ON a.company_id = c.company_id
            WHERE a.student_id = ?
            ORDER BY a.updated_at DESC
        """, (user['user_id'],))
        apps = c.fetchall()

        if not apps:
            st.info("You haven't applied to any drives yet. Check the Active Drives tab!")
        else:
            for app in apps:
                stage_colors = {
                    "Applied": "🔵", "Shortlisted": "🟣", "Round 1": "🟡",
                    "Round 2": "🟠", "HR Round": "🩷", "Offered": "🟢",
                    "Accepted": "✅", "Rejected": "🔴"
                }
                icon = stage_colors.get(app['current_stage'], "⚪")

                with st.container():
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.markdown(f"**{app['company_name']}** - {app['role_offered']} ({app['package_lpa']} LPA)")
                        st.caption(f"Applied on: {app['created_at'][:10] if app['created_at'] else 'N/A'}")

                        # Stage progress bar
                        all_stages = ["Applied", "Shortlisted", "Round 1", "Round 2", "HR Round", "Offered", "Accepted"]
                        current_idx = all_stages.index(app['current_stage']) if app['current_stage'] in all_stages else 0
                        progress = (current_idx + 1) / len(all_stages)
                        st.progress(progress, text=f"Stage: {icon} {app['current_stage']}")

                    with col2:
                        if app['status'] == 'Placed':
                            st.success("PLACED", icon="🎉")
                        elif app['status'] == 'Rejected':
                            st.error("REJECTED", icon="❌")
                        else:
                            st.info(f"Status: {app['status']}")

                        if app['admin_note']:
                            st.caption(f"Admin Note: {app['admin_note']}")

                    # Show stage history
                    with st.expander("View Stage History"):
                        c.execute("""
                            SELECT * FROM stage_logs WHERE app_id = ? ORDER BY created_at
                        """, (app['app_id'],))
                        logs = c.fetchall()
                        for log in logs:
                            st.caption(f"➤ **{log['stage_name']}** - {log['action']} ({log['created_at'][:16] if log['created_at'] else ''})")
                            if log['note']:
                                st.caption(f"   Note: {log['note']}")

                    st.divider()

    with tab4:
        st.markdown("### Placement Process Flow")
        st.caption("Watch how students move through the placement pipeline")
        render_pipeline_animation()


# ─────────────────────────────────────────────
# ADMIN PORTAL
# ─────────────────────────────────────────────
def admin_portal(user):
    st.markdown("### Placement Cell Dashboard 🏛️")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Analytics", "🏢 Manage Drives", "📋 Applications", "🔄 Process Flow", "📈 Performance KPIs"
    ])

    conn = get_db()
    c = conn.cursor()

    with tab1:
        # Key metrics
        c.execute("SELECT COUNT(*) as cnt FROM users WHERE role='student'")
        total_students = c.fetchone()['cnt']

        c.execute("SELECT COUNT(*) as cnt FROM companies WHERE status='Active'")
        active_drives = c.fetchone()['cnt']

        c.execute("SELECT COUNT(*) as cnt FROM applications")
        total_apps = c.fetchone()['cnt']

        c.execute("SELECT COUNT(*) as cnt FROM applications WHERE status='Placed'")
        placed = c.fetchone()['cnt']

        c.execute("SELECT COUNT(DISTINCT student_id) as cnt FROM applications WHERE status='Placed'")
        unique_placed = c.fetchone()['cnt']

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Students", total_students)
        col2.metric("Active Drives", active_drives)
        col3.metric("Total Applications", total_apps)
        col4.metric("Students Placed", unique_placed)

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            # Applications by stage
            c.execute("""
                SELECT current_stage, COUNT(*) as cnt
                FROM applications
                GROUP BY current_stage
            """)
            stage_data = c.fetchall()
            if stage_data:
                df_stage = pd.DataFrame([dict(row) for row in stage_data])
                stage_order = ["Applied", "Shortlisted", "Round 1", "Round 2", "HR Round", "Offered", "Accepted", "Rejected"]
                df_stage['current_stage'] = pd.Categorical(df_stage['current_stage'], categories=stage_order, ordered=True)
                df_stage = df_stage.sort_values('current_stage')
                fig = px.bar(df_stage, x='current_stage', y='cnt',
                             title="Applications by Stage",
                             color='current_stage',
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(showlegend=False, xaxis_title="Stage", yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Applications by company
            c.execute("""
                SELECT c.name, COUNT(*) as cnt
                FROM applications a
                JOIN companies c ON a.company_id = c.company_id
                GROUP BY c.name
                ORDER BY cnt DESC
            """)
            comp_data = c.fetchall()
            if comp_data:
                df_comp = pd.DataFrame([dict(row) for row in comp_data])
                fig = px.pie(df_comp, names='name', values='cnt',
                             title="Applications by Company",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)

        # Status distribution
        c.execute("""
            SELECT status, COUNT(*) as cnt
            FROM applications
            GROUP BY status
        """)
        status_data = c.fetchall()
        if status_data:
            df_status = pd.DataFrame([dict(row) for row in status_data])
            fig = px.bar(df_status, x='status', y='cnt',
                         title="Application Status Overview",
                         color='status',
                         color_discrete_map={
                             'In Progress': '#3b82f6',
                             'Placed': '#22c55e',
                             'Rejected': '#ef4444'
                         })
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("#### Create New Drive")

        with st.form("new_drive"):
            col1, col2 = st.columns(2)
            with col1:
                comp_name = st.text_input("Company Name")
                role = st.text_input("Role Offered")
                package = st.number_input("Package (LPA)", min_value=0.0, step=0.5)
            with col2:
                cgpa_cut = st.number_input("CGPA Cutoff", min_value=0.0, max_value=10.0, step=0.1, value=6.0)
                max_back = st.number_input("Max Backlogs Allowed", min_value=0, step=1, value=0)
                drive_date = st.date_input("Drive Date")

            submitted = st.form_submit_button("Create Drive")
            if submitted and comp_name:
                c.execute("""
                    INSERT INTO companies (name, role_offered, package_lpa, cgpa_cutoff, max_backlogs, drive_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'Active')
                """, (comp_name, role, package, cgpa_cut, max_back, str(drive_date)))
                conn.commit()
                st.success(f"Drive for {comp_name} created!")
                st.rerun()

        st.divider()
        st.markdown("#### All Drives")
        c.execute("SELECT * FROM companies ORDER BY drive_date DESC")
        drives = c.fetchall()
        if drives:
            df_drives = pd.DataFrame([dict(row) for row in drives])
            st.dataframe(df_drives[['name', 'role_offered', 'package_lpa', 'cgpa_cutoff', 'max_backlogs', 'drive_date', 'status']],
                         hide_index=True, use_container_width=True)

    with tab3:
        st.markdown("#### Manage Applications")

        # Filter by company
        c.execute("SELECT company_id, name FROM companies ORDER BY name")
        companies = c.fetchall()
        company_options = {comp['name']: comp['company_id'] for comp in companies}
        selected_company = st.selectbox("Filter by Company", ["All"] + list(company_options.keys()))

        if selected_company == "All":
            c.execute("""
                SELECT a.*, u.full_name, u.roll_number, u.cgpa, u.branch, c.name as company_name
                FROM applications a
                JOIN users u ON a.student_id = u.user_id
                JOIN companies c ON a.company_id = c.company_id
                ORDER BY a.updated_at DESC
            """)
        else:
            c.execute("""
                SELECT a.*, u.full_name, u.roll_number, u.cgpa, u.branch, c.name as company_name
                FROM applications a
                JOIN users u ON a.student_id = u.user_id
                JOIN companies c ON a.company_id = c.company_id
                WHERE a.company_id = ?
                ORDER BY a.updated_at DESC
            """, (company_options[selected_company],))

        apps = c.fetchall()

        if not apps:
            st.info("No applications found.")
        else:
            for app in apps:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{app['full_name']}** ({app['roll_number']})")
                        st.caption(f"CGPA: {app['cgpa']} | Branch: {app['branch']} | Company: {app['company_name']}")
                    with col2:
                        st.caption(f"Current Stage: **{app['current_stage']}**")
                        st.caption(f"Status: {app['status']}")

                    with col3:
                        stages = ["Applied", "Shortlisted", "Round 1", "Round 2", "HR Round", "Offered", "Accepted"]
                        new_stage = st.selectbox(
                            "Update Stage",
                            stages + ["Rejected"],
                            index=stages.index(app['current_stage']) if app['current_stage'] in stages else 0,
                            key=f"stage_{app['app_id']}"
                        )

                        note_text = st.text_input("Add note", key=f"note_{app['app_id']}", placeholder="Optional note")

                        if st.button("Update", key=f"update_{app['app_id']}"):
                            new_status = "In Progress"
                            if new_stage == "Accepted":
                                new_status = "Placed"
                            elif new_stage == "Rejected":
                                new_status = "Rejected"

                            c.execute("""
                                UPDATE applications
                                SET current_stage = ?, status = ?, admin_note = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE app_id = ?
                            """, (new_stage, new_status, note_text or app['admin_note'], app['app_id']))

                            c.execute("""
                                INSERT INTO stage_logs (app_id, stage_name, action, actor_email, note)
                                VALUES (?, ?, ?, ?, ?)
                            """, (app['app_id'], new_stage, f"Updated to {new_stage}", user['email'], note_text or f"Moved to {new_stage}"))

                            conn.commit()
                            st.success(f"Updated {app['full_name']} to {new_stage}")
                            st.rerun()

                    st.divider()

    with tab4:
        st.markdown("### Placement Pipeline Animation")
        st.caption("Visual representation of student flow through placement stages")
        render_pipeline_animation()

    with tab5:
        st.markdown("### Process Performance KPIs")

        # KPI Cards
        c.execute("SELECT COUNT(*) as cnt FROM applications WHERE status='In Progress'")
        pending = c.fetchone()['cnt']

        c.execute("SELECT COUNT(*) as cnt FROM applications WHERE status='Rejected'")
        rejected = c.fetchone()['cnt']

        c.execute("SELECT AVG(package_lpa) as avg_pkg FROM companies c JOIN applications a ON c.company_id = a.company_id WHERE a.status='Placed'")
        avg_pkg_row = c.fetchone()
        avg_pkg = avg_pkg_row['avg_pkg'] if avg_pkg_row['avg_pkg'] else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pending Applications", pending)
        col2.metric("Rejected", rejected)
        col3.metric("Avg. Package (Placed)", f"{avg_pkg:.1f} LPA")
        col4.metric("Placement Rate", f"{(unique_placed/total_students*100):.0f}%" if total_students > 0 else "0%")

        st.divider()

        # Conversion funnel data
        st.markdown("#### Stage-wise Conversion Analysis")
        c.execute("""
            SELECT current_stage, COUNT(*) as cnt
            FROM applications
            GROUP BY current_stage
        """)
        funnel_data = c.fetchall()
        if funnel_data:
            df_funnel = pd.DataFrame([dict(row) for row in funnel_data])
            stage_order = ["Applied", "Shortlisted", "Round 1", "Round 2", "HR Round", "Offered", "Accepted"]
            df_funnel['current_stage'] = pd.Categorical(df_funnel['current_stage'], categories=stage_order + ["Rejected"], ordered=True)
            df_funnel = df_funnel.sort_values('current_stage')

            fig = go.Figure(go.Funnel(
                y=df_funnel['current_stage'],
                x=df_funnel['cnt'],
                textinfo="value+percent initial",
                marker=dict(color=['#3b82f6', '#8b5cf6', '#f59e0b', '#f97316', '#ec4899', '#22c55e', '#16a34a', '#ef4444'])
            ))
            fig.update_layout(title="Placement Funnel", height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Company-wise placement stats
        st.markdown("#### Company-wise Results")
        c.execute("""
            SELECT c.name, c.package_lpa,
                   COUNT(a.app_id) as total_apps,
                   SUM(CASE WHEN a.status = 'Placed' THEN 1 ELSE 0 END) as placed,
                   SUM(CASE WHEN a.status = 'Rejected' THEN 1 ELSE 0 END) as rejected
            FROM companies c
            LEFT JOIN applications a ON c.company_id = a.company_id
            GROUP BY c.company_id
            ORDER BY c.package_lpa DESC
        """)
        comp_stats = c.fetchall()
        if comp_stats:
            df_comp = pd.DataFrame([dict(row) for row in comp_stats])
            df_comp['conversion_rate'] = (df_comp['placed'] / df_comp['total_apps'] * 100).fillna(0).round(1)
            st.dataframe(df_comp.rename(columns={
                'name': 'Company', 'package_lpa': 'Package (LPA)',
                'total_apps': 'Applications', 'placed': 'Placed',
                'rejected': 'Rejected', 'conversion_rate': 'Conversion %'
            }), hide_index=True, use_container_width=True)


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────
def main():
    conn = init_db()

    # Custom CSS
    st.markdown("""
    <style>
        .stApp { }
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #f0f4ff, #e8f0fe);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #dbeafe;
        }
    </style>
    """, unsafe_allow_html=True)

    # Session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.role = None

    if not st.session_state.logged_in:
        # Login / Register page
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0f172a, #1e3a5f); padding: 30px; border-radius: 16px; margin-bottom: 20px;">
            <h1 style="color: white; margin: 0;">🎓 Campus Placement Portal</h1>
            <p style="color: #94a3b8; margin-top: 8px;">Apply for placements, track your applications, and get placed.</p>
        </div>
        """, unsafe_allow_html=True)

        login_tab, register_tab = st.tabs(["🔐 Login", "📝 Register as Student"])

        with login_tab:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Student Login")
                s_email = st.text_input("Email", placeholder="student@iiitm.ac.in", key="s_email")
                s_pwd = st.text_input("Password", type="password", key="s_pwd")
                if st.button("Login as Student", use_container_width=True):
                    user = authenticate(s_email, s_pwd, 'student')
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = dict(user)
                        st.session_state.role = 'student'
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")

                st.caption("Demo: use any seeded email (e.g. aarav@iiitm.ac.in) with password: student123")

            with col2:
                st.markdown("#### Placement Cell Login")
                a_email = st.text_input("Email", placeholder="admin@iiitm.ac.in", key="a_email")
                a_pwd = st.text_input("Password", type="password", key="a_pwd")
                if st.button("Login as Admin", use_container_width=True):
                    user = authenticate(a_email, a_pwd, 'admin')
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = dict(user)
                        st.session_state.role = 'admin'
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")

                st.caption("Demo: admin@iiitm.ac.in / admin123")

        with register_tab:
            st.markdown("#### Create Student Account")
            with st.form("register_form"):
                col1, col2 = st.columns(2)
                with col1:
                    r_name = st.text_input("Full Name")
                    r_email = st.text_input("College Email")
                    r_pwd = st.text_input("Password", type="password")
                    r_pwd2 = st.text_input("Confirm Password", type="password")
                with col2:
                    r_roll = st.text_input("Roll Number")
                    r_branch = st.selectbox("Programme", ["MBA", "M.Tech", "IPG", "PhD"])
                    r_cgpa = st.number_input("CGPA", min_value=0.0, max_value=10.0, step=0.01)
                    r_back = st.number_input("Active Backlogs", min_value=0, step=1)

                if st.form_submit_button("Register"):
                    if r_pwd != r_pwd2:
                        st.error("Passwords don't match!")
                    elif not r_name or not r_email:
                        st.error("Name and email are required.")
                    else:
                        success, msg = register_student(r_name, r_email, r_pwd, r_roll, r_branch, r_cgpa, r_back)
                        if success:
                            st.success(msg + " You can now login.")
                        else:
                            st.error(msg)
    else:
        # Sidebar
        with st.sidebar:
            st.markdown(f"**{st.session_state.user['full_name']}**")
            st.caption(f"Role: {st.session_state.role.title()}")
            st.caption(f"Email: {st.session_state.user['email']}")
            st.divider()
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()

        if st.session_state.role == 'student':
            student_portal(st.session_state.user)
        else:
            admin_portal(st.session_state.user)


if __name__ == "__main__":
    main()
