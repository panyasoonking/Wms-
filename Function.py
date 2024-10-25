import sqlite3
from functools import wraps
from flask import session, redirect, url_for, request
from fpdf import FPDF

# ฟังก์ชันเชื่อมต่อกับฐานข้อมูล users.db สำหรับข้อมูลผู้ใช้
def get_db_connection_users():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row  # ทำให้การดึงข้อมูลเป็น dict
    return conn

# ฟังก์ชันเชื่อมต่อกับฐานข้อมูล product.db สำหรับข้อมูลสินค้า
def get_db_connection_product():
    conn = sqlite3.connect('product.db', timeout=10)  # เพิ่ม timeout 10 วินาที
    conn.row_factory = sqlite3.Row
    return conn

# ฟังก์ชัน decorator เพื่อป้องกันการเข้าถึงหน้า Home โดยไม่ได้ล็อกอิน
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ฟังก์ชันสำหรับสร้าง PDF
def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Work Order", ln=True, align="C")
    
    for key, value in data.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)

    pdf.output("work_order.pdf")
    return "work_order.pdf"

# ฟังก์ชัน decorator เพื่อป้องกันการเข้าถึงหน้า Export โดยไม่ได้ล็อกอิน
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function