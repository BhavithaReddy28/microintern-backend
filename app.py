from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import razorpay
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import secrets
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    
    filename = secure_filename(file.filename)
    filename = f"{int(time.time())}_{filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    file_url = f"{request.host_url}uploads/{filename}"
    return jsonify({"url": file_url})

# Razorpay Configuration
RAZORPAY_KEY_ID = "rzp_test_SmKrPvIIVOi39k"
RAZORPAY_KEY_SECRET = "5yxv0i7tCOLqRRRaYKcQSDZW"
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

import os
# We use an environment variable for the live database URL, defaulting to local if it doesn't exist
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:2810@localhost:5433/microinternDB')

# EMAIL CONFIGURATION (Fill these to enable notifications)
SMTP_SERVER = "smtp.office365.com"  # For Outlook/Edu accounts
SMTP_PORT = 587
SMTP_USER = "bl.en.u4cse23255@bl.students.amrita.edu"     # USER: Replace with your actual email
SMTP_PASS = "Bhavitha@28"         # USER: Replace with your app password

@app.route("/admin/init", methods=["GET"])
def init_admin():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        pw_hash = generate_password_hash("admin123", method="pbkdf2:sha256")
        cur.execute("INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'admin') ON CONFLICT (email) DO NOTHING", 
                   ("admin@marketplace.com", pw_hash))
        conn.commit()
        return "Admin initialized"
    finally:
        cur.close()
        conn.close()

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", SMTP_USER)

def send_email(to_email, subject, body_text):
    # Try sending via Brevo API if key is available
    if BREVO_API_KEY:
        try:
            import requests
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json"
            }
            payload = {
                "sender": {"email": SENDER_EMAIL, "name": "MicroIntern Team"},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": body_text.replace("\n", "<br>")
            }
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            if response.status_code in [200, 201, 202]:
                print(f"Email sent via Brevo API to {to_email}!")
                return True
            else:
                print(f"Brevo API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Brevo API failed: {e}")
            
    # Fallback to local SMTP
    try:
        msg = MIMEText(body_text)
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=5) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"Email sent via SMTP fallback to {to_email}!")
        return True
    except Exception as e:
        print(f"SMTP fallback failed: {e}")
        return False

def send_notification_emails(task_title, company_name):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT email FROM users WHERE role = 'student'")
        student_emails = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()

        if not student_emails:
            return

        subject = f"New Internship Alert: {task_title}"
        body = f"Hi there!\n\n{company_name} has just posted a new task: {task_title}.\n\nLog in to the Micro Internship Marketplace to apply now!\n\nBest Regards,\nMicroIntern Team"

        for email in student_emails:
            send_email(email, subject, body)
        print("Alert emails processed.")
    except Exception as e:
        print(f"Failed to process alerts: {e}")

def send_application_email(recruiter_email, student_name, task_title):
    subject = f"New Applicant for {task_title}"
    body = f"Hi!\n\n{student_name} has just applied for your task: {task_title}.\n\nLog in to your dashboard to review their application!\n\nBest,\nMicroIntern Team"
    send_email(recruiter_email, subject, body)

def send_acceptance_email(student_email, student_name, task_title):
    subject = f"Application Accepted: {task_title}"
    body = f"Congratulations {student_name}!\n\nYour application for the task '{task_title}' has been accepted.\n\nYou can now start working on the task. Check your dashboard for more details.\n\nBest regards,\nMicroIntern Team"
    send_email(student_email, subject, body)

def send_completion_email(student_email, student_name, task_title, amount):
    subject = f"Payment Received: {task_title}"
    body = f"Hi {student_name}!\n\nGreat job! Your work for '{task_title}' has been approved.\n\n₹{amount} has been credited to your wallet.\n\nYou can withdraw this amount or use it on the platform.\n\nKeep up the great work!\n\nBest regards,\nMicroIntern Team"
    send_email(student_email, subject, body)

def send_reset_password_email(user_email, token):
    subject = "Password Reset Request"
    # Try to detect request origin, fallback to vercel production link
    origin = "https://microintern-frontend-flame.vercel.app"
    try:
        if request.headers.get("Origin"):
            origin = request.headers.get("Origin")
    except Exception:
        pass
    reset_link = f"{origin}/reset-password?token={token}"
    body = f"Hi!\n\nYou requested a password reset for your Micro Internship Marketplace account.\n\nPlease click the link below to reset your password. This link will expire in 1 hour:\n\n{reset_link}\n\nIf you didn't request this, you can safely ignore this email.\n\nBest,\nMicroIntern Team"
    send_email(user_email, subject, body)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.route("/")
def home():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM task_applications")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return f"Backend is running! Total applications in DB: {count}"

@app.route("/debug/brevo-status")
def debug_brevo_status():
    email = request.args.get("email", "bl.en.u4cse23255@bl.students.amrita.edu")
    key_status = "Loaded successfully!" if BREVO_API_KEY else "Not found/Empty"
    
    api_response = None
    if BREVO_API_KEY:
        try:
            import requests
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json"
            }
            payload = {
                "sender": {"email": SENDER_EMAIL, "name": "MicroIntern Team"},
                "to": [{"email": email}],
                "subject": "Diagnostic Brevo Test",
                "htmlContent": "If you are reading this, your Brevo integration is working perfectly!"
            }
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            api_response = {
                "status_code": response.status_code,
                "response_text": response.json() if response.status_code in [200, 201, 202] else response.text
            }
        except Exception as e:
            api_response = {"error": str(e)}
            
    return jsonify({
        "BREVO_API_KEY_status": key_status,
        "SMTP_USER_configured": SMTP_USER,
        "SENDER_EMAIL_configured": SENDER_EMAIL,
        "api_response": api_response
    })

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not email or not password or not role:
        return jsonify({"message": "Email, password and role are required"}), 400

    if role == "student":
        allowed_domains = ['.edu', '.in', '.ac.in']
        if not any(email.lower().endswith(domain) for domain in allowed_domains):
            return jsonify({"message": "Invalid email domain. Students must use a valid university email (.edu, .in, .ac.in)."}), 400
    
    elif role == "company":
        generic_domains = ['@gmail.com', '@yahoo.com', '@hotmail.com', '@outlook.com', '@aol.com']
        if any(email.lower().endswith(domain) for domain in generic_domains):
            return jsonify({"message": "Invalid email domain. Companies must use an official corporate email."}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s) RETURNING user_id",
            (email, hashed_password, role)
        )
        user_id = cur.fetchone()[0]

        if role == "student":
            cur.execute(
                """INSERT INTO students (user_id, first_name, last_name, phone, university, major, id_card_url, graduation_year, verification_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending') RETURNING student_id""",
                (user_id, data.get("first_name"), data.get("last_name"), data.get("phone"), 
                 data.get("university"), data.get("major"), data.get("id_card_url"), data.get("graduation_year"))
            )
        elif role == "company":
            cur.execute(
                """INSERT INTO companies (user_id, company_name, industry, company_size, contact_first_name, contact_last_name, phone, website) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING company_id""",
                (user_id, data.get("company_name"), data.get("industry"), data.get("company_size"), data.get("contact_first_name"), data.get("contact_last_name"), data.get("phone"), data.get("website"))
            )
        
        conn.commit()
        return jsonify({"message": "User registered successfully", "user_id": user_id, "role": role})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Registration failed", "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    email = data.get("email")
    
    if not email:
        return jsonify({"message": "Email is required"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if user:
            # Generate a secure token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=1)
            
            # Store token in database
            cur.execute("""
                INSERT INTO password_reset_tokens (user_id, token, expires_at) 
                VALUES (%s, %s, %s)
            """, (user['user_id'], token, expires_at))
            conn.commit()
            
            send_reset_password_email(email, token)
            return jsonify({"message": "Password reset email sent"}), 200
        else:
            return jsonify({"message": "Email is not registered on the platform"}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Failed to process request", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.json
    token = data.get("token")
    new_password = data.get("new_password")
    
    if not token or not new_password:
        return jsonify({"message": "Token and new password are required"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Check if token is valid and not expired
        cur.execute("""
            SELECT user_id FROM password_reset_tokens 
            WHERE token = %s AND expires_at > %s
        """, (token, datetime.now()))
        reset_req = cur.fetchone()
        
        if not reset_req:
            return jsonify({"message": "Invalid or expired token"}), 400
        
        # Update user's password
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
        cur.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (hashed_password, reset_req['user_id']))
        
        # Delete the token so it can't be used again
        cur.execute("DELETE FROM password_reset_tokens WHERE token = %s", (token,))
        
        conn.commit()
        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Failed to reset password", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if user and check_password_hash(user["password_hash"], password):
            profile_id = None
            verification_status = None
            
            if user["role"] == "student":
                cur.execute("SELECT student_id, verification_status FROM students WHERE user_id = %s", (user["user_id"],))
                res = cur.fetchone()
                if res:
                    profile_id = res["student_id"]
                    verification_status = res["verification_status"]
            elif user["role"] == "company":
                cur.execute("SELECT company_id FROM companies WHERE user_id = %s", (user["user_id"],))
                res = cur.fetchone()
                profile_id = res["company_id"] if res else None

            return jsonify({
                "message": "Login successful",
                "user_id": user["user_id"],
                "role": user["role"],
                "email": user["email"],
                "profile_id": profile_id,
                "verification_status": verification_status
            })
        return jsonify({"message": "Invalid email or password"}), 401
    finally:
        cur.close()
        conn.close()

@app.route("/tasks", methods=["GET"])
def get_tasks():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT t.*, t.task_name as title, c.company_name, u.email as company_email,
            (SELECT COUNT(*) FROM task_applications WHERE task_id = t.task_id) as applicants_count
            FROM tasks t 
            JOIN companies c ON t.company_id = c.company_id
            JOIN users u ON c.user_id = u.user_id
        """)
        tasks = cur.fetchall()
        return jsonify(tasks)
    finally:
        cur.close()
        conn.close()

@app.route("/wallet/balance/<int:user_id>", methods=["GET"])
def get_balance(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        if not user: return jsonify({"message": "User not found"}), 404
        
        if user["role"] == "student":
            cur.execute("SELECT balance FROM students WHERE user_id = %s", (user_id,))
        else:
            cur.execute("SELECT balance FROM companies WHERE user_id = %s", (user_id,))
        
        balance = cur.fetchone()["balance"]
        return jsonify({"balance": float(balance)})
    finally:
        cur.close()
        conn.close()

@app.route("/wallet/transactions/<int:user_id>", methods=["GET"])
def get_transactions(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM transactions WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        transactions = cur.fetchall()
        # Convert Decimals to float for JSON
        for t in transactions:
            t["amount"] = float(t["amount"])
        return jsonify(transactions)
    finally:
        cur.close()
        conn.close()

@app.route("/wallet/topup", methods=["POST"])
def topup_wallet():
    # This was the old simulated topup, now we use Razorpay
    pass

@app.route("/payment/create-order", methods=["POST"])
def create_order():
    data = request.json
    amount = int(float(data.get("amount")) * 100) # Razorpay expects amount in paise
    
    try:
        order_data = {
            "amount": amount,
            "currency": "INR",
            "receipt": f"receipt_{int(time.time())}",
            "payment_capture": 1 # Auto capture
        }
        order = client.order.create(data=order_data)
        return jsonify(order)
    except Exception as e:
        return jsonify({"message": "Failed to create order", "error": str(e)}), 400

@app.route("/payment/verify", methods=["POST"])
def verify_payment():
    data = request.json
    try:
        # Verify signature
        client.utility.verify_payment_signature({
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        })
        
        # If verification successful, update balance
        user_id = data.get("user_id")
        amount = float(data.get("amount"))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        
        if user[0] == "student":
            cur.execute("UPDATE students SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
        else:
            cur.execute("UPDATE companies SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
            
        cur.execute("INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, 'credit', 'Razorpay Wallet Top-up')", 
                   (user_id, amount))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Payment verified and wallet updated"})
    except Exception as e:
        return jsonify({"message": "Payment verification failed", "error": str(e)}), 400

@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.json
    company_id = data.get("company_id")
    if not company_id:
        return jsonify({"message": "company_id is required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Check and deduct balance (Payment + 5% Platform Fee + 18% GST = 23% extra)
        base_payment = float(data.get("payment") or 0)
        platform_fee = base_payment * 0.05
        gst = base_payment * 0.18
        total_amount = base_payment + platform_fee + gst
        
        cur.execute("SELECT balance, user_id FROM companies WHERE company_id = %s", (company_id,))
        company_info = cur.fetchone()
        
        if not company_info:
            return jsonify({"message": "Company not found"}), 404
            
        if float(company_info[0]) < total_amount:
            return jsonify({"message": f"Insufficient balance. You need ₹{total_amount:.2f} but have ₹{float(company_info[0]):.2f}"}), 400
            
        cur.execute("UPDATE companies SET balance = balance - %s WHERE company_id = %s", (total_amount, company_id))
        cur.execute("INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, 'debit', %s)", 
                   (company_info[1], total_amount, f"Payment locked for task: {data.get('title')} (Incl. Fees & GST)"))
        
        # Update Platform Escrow
        cur.execute("UPDATE platform_stats SET total_escrow = total_escrow + %s WHERE id = 1", (total_amount,))

        cur.execute("""
            INSERT INTO tasks (company_id, task_name, task_date, category, description, payment, duration, max_applicants, skills, deadline, task_link, level)
            VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING task_id
        """, (company_id, data.get("title") or data.get("task_name"), data.get("category"), data.get("description"), 
             data.get("payment"), data.get("duration"), data.get("max_applicants"), data.get("skills"), data.get("deadline"), 
             data.get("task_link"), data.get("level", "Medium"))
        )
        task_id = cur.fetchone()[0]
        
        # Fetch company name for the email
        cur.execute("SELECT company_name FROM companies WHERE company_id = %s", (company_id,))
        company_name = cur.fetchone()[0]
        
        conn.commit()
        
        # Send notifications in the background (simplified)
        send_notification_emails(data.get("title") or data.get("task_name"), company_name)
        
        return jsonify({"message": "Task created and notifications sent", "task_id": task_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Failed to create task", "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route("/students", methods=["GET"])
def get_all_students():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT s.*, u.email 
            FROM students s
            JOIN users u ON s.user_id = u.user_id
            ORDER BY s.hireable DESC, s.rating DESC
        """)
        students = cur.fetchall()
        return jsonify(students)
    except Exception as e:
        return jsonify({"message": "Failed to fetch students", "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route("/student/<int:student_id>/invite", methods=["POST"])
def invite_student(student_id):
    data = request.json
    company_name = data.get("company_name")
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT u.email FROM students s JOIN users u ON s.user_id = u.user_id WHERE s.student_id = %s", (student_id,))
        student = cur.fetchone()
        
        if student:
            subject = f"Interview Invitation from {company_name}"
            body = f"Hi!\n\n{company_name} is impressed with your profile and would like to invite you for an interview.\n\nPlease reply to this email to coordinate a time.\n\nBest,\nMicroIntern Team"
            
            send_email(student["email"], subject, body)
            return jsonify({"message": "Invitation sent successfully"})
        return jsonify({"message": "Student not found"}), 404
    except Exception as e:
        return jsonify({"message": "Failed to send invitation", "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route("/student/<int:student_id>/rate", methods=["PUT"])
def rate_student(student_id):
    data = request.json
    rating = data.get("rating")
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE students SET rating = %s WHERE student_id = %s", (rating, student_id))
        conn.commit()
        return jsonify({"message": "Rating updated"})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Failed to update rating", "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route("/student/<int:student_id>", methods=["PUT"])
def update_student_profile(student_id):
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE students 
            SET bio = %s, resume_url = %s, github_url = %s, linkedin_url = %s,
                first_name = %s, last_name = %s, university = %s, major = %s, phone = %s
            WHERE student_id = %s
        """, (data.get("bio"), data.get("resume_url"), data.get("github_url"), data.get("linkedin_url"),
              data.get("first_name"), data.get("last_name"), data.get("university"), data.get("major"), data.get("phone"),
              student_id))
        conn.commit()
        return jsonify({"message": "Profile updated successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Update failed", "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    student_id = request.args.get("student_id")
    if student_id:
        try:
            student_id = int(student_id)
        except:
            student_id = None
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT t.*, t.task_name as title, c.company_name,
            (SELECT COUNT(*) FROM task_applications WHERE task_id = t.task_id) as applicants_count
            FROM tasks t
            JOIN companies c ON t.company_id = c.company_id
            WHERE t.task_id = %s
        """, (task_id,))
        task = cur.fetchone()
        
        if task:
            # Security check for task_link
            if student_id:
                cur.execute("SELECT application_id, status FROM task_applications WHERE task_id = %s AND student_id = %s", (task_id, student_id))
                app = cur.fetchone()
                if app:
                    task["application_id"] = app["application_id"]
                    task["application_status"] = app["status"]
                    if app["status"] != "accepted":
                        task["task_link"] = None
                else:
                    task["task_link"] = None
            else:
                task["task_link"] = None
                
        return jsonify(task) if task else (jsonify({"message": "Task not found"}), 404)
    finally:
        cur.close()
        conn.close()

@app.route("/company/<int:company_id>/tasks", methods=["GET"])
def get_company_tasks(company_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT *, task_name as title,
            (SELECT COUNT(*) FROM task_applications WHERE task_id = tasks.task_id) as applicants_count
            FROM tasks WHERE company_id = %s
        """, (company_id,))
        tasks = cur.fetchall()
        return jsonify(tasks)
    finally:
        cur.close()
        conn.close()

@app.route("/student/<int:student_id>/applications", methods=["GET"])
def get_student_applications(student_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT a.*, t.task_name as task_title, c.company_name, t.payment, t.level as task_level,
                   CASE WHEN a.status = 'accepted' THEN t.task_link ELSE NULL END as task_link
            FROM task_applications a
            JOIN tasks t ON a.task_id = t.task_id
            JOIN companies c ON t.company_id = c.company_id
            WHERE a.student_id = %s
        """, (student_id,))
        apps = cur.fetchall()
        return jsonify(apps)
    finally:
        cur.close()
        conn.close()

@app.route("/student/<int:student_id>", methods=["GET"])
def get_student_profile(student_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cur.fetchone()
        return jsonify(student)
    finally:
        cur.close()
        conn.close()

@app.route("/tasks/<int:task_id>/applicants", methods=["GET"])
def get_task_applicants(task_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT a.*, s.first_name, s.last_name, u.email, s.university, s.major, s.resume_url
            FROM task_applications a
            JOIN students s ON a.student_id = s.student_id
            JOIN users u ON s.user_id = u.user_id
            WHERE a.task_id = %s
        """, (task_id,))
        applicants = cur.fetchall()
        return jsonify(applicants)
    finally:
        cur.close()
        conn.close()

@app.route("/applications/<int:app_id>/submit", methods=["PUT"])
def submit_task(app_id):
    print(f"DEBUG: Received submission for application_id: {app_id}")
    data = request.json
    submission_link = data.get("submission_link")
    print(f"DEBUG: Submission link: {submission_link}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE task_applications SET status = 'submitted', submission_link = %s WHERE application_id = %s",
            (submission_link, app_id)
        )
        conn.commit()
        print(f"DEBUG: Successfully updated application_id: {app_id}")
        return jsonify({"message": "Task submitted for review"})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Submission failed", "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route("/applications/<int:app_id>/status", methods=["PUT"])
def update_application_status(app_id):
    data = request.json
    status = data.get("status")
    
    if status not in ["pending", "accepted", "rejected", "completed"]:
        return jsonify({"message": "Invalid status"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE task_applications SET status = %s WHERE application_id = %s",
            (status, app_id)
        )
        
        # If accepted, send mail to student
        if status == "accepted":
            cur.execute("""
                SELECT u.email, s.first_name, s.last_name, t.task_name
                FROM task_applications a
                JOIN students s ON a.student_id = s.student_id
                JOIN users u ON s.user_id = u.user_id
                JOIN tasks t ON a.task_id = t.task_id
                WHERE a.application_id = %s
            """, (app_id,))
            info = cur.fetchone()
            if info:
                send_acceptance_email(info[0], f"{info[1]} {info[2]}", info[3])

        # If completed, transfer money to student
        if status == "completed":
            # Transfer funds: Recruiter has already paid total_amount (Locked in Escrow)
            # Student gets base_payment - 5% fee
            # Admin gets 5% fee + GST + 5% (from student)
            cur.execute("""
                SELECT t.payment, s.user_id, t.task_name, t.task_id, t.level, s.level, s.student_id, s.first_name, s.last_name
                FROM task_applications a 
                JOIN tasks t ON a.task_id = t.task_id 
                JOIN students s ON a.student_id = s.student_id 
                WHERE a.application_id = %s
            """, (app_id,))
            pay_info = cur.fetchone()
            if pay_info:
                base_pay = float(pay_info[0])
                task_lvl = pay_info[4]
                student_curr_lvl = pay_info[5]
                student_id = pay_info[6]

                # Real-time Point and Level Progression System
                difficulty_points = {"Easy": 2, "Medium": 5, "Hard": 10}
                points_to_add = difficulty_points.get(task_lvl, 2)
                
                # Update points and calculate new level
                cur.execute("""
                    UPDATE students 
                    SET points = points + %s 
                    WHERE student_id = %s 
                    RETURNING points
                """, (points_to_add, student_id))
                new_total_points = cur.fetchone()[0]
                
                # Define rank thresholds
                new_rank = "Beginner"
                if new_total_points >= 50:
                    new_rank = "Master"
                elif new_total_points >= 25:
                    new_rank = "Expert"
                elif new_total_points >= 10:
                    new_rank = "Intermediate"
                
                # Update rank if it has changed
                cur.execute("UPDATE students SET level = %s WHERE student_id = %s", (new_rank, student_id))

                base_pay = pay_info[0]

                from decimal import Decimal
                base_pay_dec = Decimal(str(base_pay))
                platform_fee_recruiter = base_pay_dec * Decimal('0.05')
                gst = base_pay_dec * Decimal('0.18')
                total_from_recruiter = base_pay_dec + platform_fee_recruiter + gst
                
                # Student receives base_pay - 5% student fee
                student_fee = base_pay_dec * Decimal('0.05')
                net_to_student = base_pay_dec - student_fee
                
                cur.execute("UPDATE students SET balance = balance + %s WHERE user_id = %s", (float(net_to_student), pay_info[1]))
                cur.execute("INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, 'credit', %s)", 
                           (pay_info[1], float(net_to_student), f"Earning for task: {pay_info[2]} (Net of 5% fee)"))
                
                # Update Admin Stats: Fees from both sides + GST
                admin_gain_fees = platform_fee_recruiter + student_fee
                admin_gain_gst = gst
                
                cur.execute("""
                    UPDATE platform_stats 
                    SET total_fees = total_fees + %s, 
                        total_gst = total_gst + %s, 
                        total_escrow = total_escrow - %s 
                    WHERE id = 1
                """, (float(admin_gain_fees), float(admin_gain_gst), float(total_from_recruiter)))

                # Send completion email
                cur.execute("SELECT email FROM users WHERE user_id = %s", (pay_info[1],))
                student_email = cur.fetchone()[0]
                send_completion_email(student_email, f"{pay_info[7]} {pay_info[8]}", pay_info[2], net_to_student)

        
        conn.commit()
        return jsonify({"message": f"Status updated to {status}"})
    except Exception as e:
        conn.rollback()
@app.route('/admin/pending-verifications', methods=['GET'])
def get_pending_verifications():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT s.*, u.email 
            FROM students s 
            JOIN users u ON s.user_id = u.user_id 
            WHERE s.verification_status = 'pending'
        """)
        return jsonify(cur.fetchall())
    finally:
        cur.close()
        conn.close()

@app.route('/admin/verify-student', methods=['POST'])
def verify_student():
    data = request.json
    student_id = data.get('student_id')
    status = data.get('status') # 'approved' or 'rejected'
    reason = data.get('reason', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE students 
            SET verification_status = %s, rejection_reason = %s 
            WHERE student_id = %s
        """, (status, reason, student_id))
        conn.commit()
        return jsonify({"message": f"Student {status}"})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/withdraw', methods=['POST'])
def admin_withdraw():
    data = request.json
    amount = float(data.get('amount', 0))
    withdraw_type = data.get('type') # 'revenue' or 'gst'
    
    if amount <= 0:
        return jsonify({"message": "Invalid amount"}), 400
        
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # In a real app, you'd check if stats.total_fees >= amount
        # For this version, we just log the withdrawal
        print(f"ADMIN WITHDRAWAL: ₹{amount} from {withdraw_type}")
        
        # Optionally update platform_stats to subtract (but maybe better to keep totals and track 'withdrawn')
        # For now, we just return success
        conn.commit()
        return jsonify({"message": "Withdrawal processed successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"message": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/admin/stats", methods=["GET"])
def get_admin_stats():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM platform_stats WHERE id = 1")
        stats = cur.fetchone()
        if not stats:
            cur.execute("INSERT INTO platform_stats (id, total_fees, total_gst, total_escrow) VALUES (1, 0, 0, 0) ON CONFLICT (id) DO NOTHING")
            conn.commit()
            cur.execute("SELECT * FROM platform_stats WHERE id = 1")
            stats = cur.fetchone()
        
        cur.execute("SELECT COUNT(*) FROM students")
        stats["student_count"] = cur.fetchone()["count"]
        
        cur.execute("SELECT COUNT(*) FROM companies")
        stats["company_count"] = cur.fetchone()["count"]
        
        cur.execute("SELECT COUNT(*) FROM tasks")
        stats["total_tasks"] = cur.fetchone()["count"]
        
        # Convert Decimals
        stats["total_fees"] = float(stats["total_fees"])
        stats["total_gst"] = float(stats["total_gst"])
        stats["total_escrow"] = float(stats["total_escrow"])
        
        return jsonify(stats)
    finally:
        cur.close()
        conn.close()

@app.route("/wallet/withdraw", methods=["POST"])
def withdraw_funds():
    data = request.json
    user_id = data.get("user_id")
    amount = float(data.get("amount"))
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user_role = cur.fetchone()[0]
        
        if user_role == "student":
            cur.execute("SELECT balance FROM students WHERE user_id = %s", (user_id,))
        else:
            cur.execute("SELECT balance FROM companies WHERE user_id = %s", (user_id,))
            
        current_balance = float(cur.fetchone()[0])
        if current_balance < amount:
            return jsonify({"message": "Insufficient balance"}), 400
            
        if user_role == "student":
            cur.execute("UPDATE students SET balance = balance - %s WHERE user_id = %s", (amount, user_id))
        else:
            cur.execute("UPDATE companies SET balance = balance - %s WHERE user_id = %s", (amount, user_id))
            
        cur.execute("INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, 'debit', 'Withdrawal to Bank Account')", 
                   (user_id, amount))
        conn.commit()
        return jsonify({"message": "Withdrawal processed successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Withdrawal failed", "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route("/apply", methods=["POST"])
def apply():
    data = request.json
    task_id = data.get("task_id")
    student_id = data.get("student_id")

    if not task_id or not student_id:
        return jsonify({"message": "task_id and student_id are required"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Check verification status
        cur.execute("SELECT verification_status FROM students WHERE student_id = %s", (student_id,))
        student = cur.fetchone()
        if not student or student["verification_status"] != "approved":
            return jsonify({"message": "You must be a verified student to apply for tasks. Please wait for admin approval."}), 403

        # Check if already applied
        cur.execute(
            "SELECT * FROM task_applications WHERE task_id = %s AND student_id = %s",
            (task_id, student_id)
        )
        if cur.fetchone():
            return jsonify({"message": "You have already applied for this task"}), 400

        cur.execute(
            "INSERT INTO task_applications (task_id, student_id) VALUES (%s, %s)",
            (task_id, student_id)
        )
        
        # Fetch data for email notification
        cur.execute("""
            SELECT u.email as recruiter_email, t.task_name, s.first_name, s.last_name
            FROM tasks t
            JOIN companies c ON t.company_id = c.company_id
            JOIN users u ON c.user_id = u.user_id
            CROSS JOIN (SELECT first_name, last_name FROM students WHERE student_id = %s) s
            WHERE t.task_id = %s
        """, (student_id, task_id))
        
        info = cur.fetchone()
        
        if info:
            send_application_email(
                info['recruiter_email'],
                f"{info['first_name']} {info['last_name']}",
                info['task_name']
            )
        
        conn.commit()
        return jsonify({"message": "Applied successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Apply failed", "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("STARTING BACKEND ON PORT 5001...")
    app.run(debug=True, port=5001, host='0.0.0.0')