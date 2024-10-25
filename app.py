from io import BytesIO
import io
from flask import Flask, render_template, request, redirect, send_file, url_for, session, flash, make_response, jsonify
from fpdf import FPDF
from Function import get_db_connection_users, get_db_connection_product, login_required, generate_pdf  # import ฟังก์ชันที่จำเป็น
from datetime import datetime
from flask import make_response
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # คีย์สำหรับ session

# หน้า Home (ต้องล็อกอินก่อนจึงจะเข้าถึงได้)
@app.route('/')
@login_required
def home():
    conn = get_db_connection_product()

    # ดึงข้อมูลยอดรวมการรับเข้าและส่งออกเป็นรายเดือน
    monthly_checkin = conn.execute('''
        SELECT strftime('%Y-%m', checkin_date) AS month, SUM(quantity) AS total
        FROM product_checkin
        GROUP BY month
        ORDER BY month
    ''').fetchall()

    monthly_export = conn.execute('''
        SELECT strftime('%Y-%m', checkin_date) AS month, SUM(quantity) AS total
        FROM product_export
        GROUP BY month
        ORDER BY month
    ''').fetchall()

    # ดึงข้อมูลสำหรับ Dashboard Summary
    checkin_total = conn.execute('SELECT SUM(quantity) AS total FROM product_checkin').fetchone()['total'] or 0
    export_total = conn.execute('SELECT SUM(quantity) AS total FROM product_export').fetchone()['total'] or 0
    stock_total = checkin_total - export_total

    # ดึงรายการล่าสุดจากการรับเข้าและส่งออก
    checkin_data = conn.execute('SELECT * FROM product_checkin ORDER BY checkin_date DESC LIMIT 10').fetchall()
    export_data = conn.execute('SELECT * FROM product_export ORDER BY checkin_date DESC LIMIT 10').fetchall()

    conn.close()

    # สร้าง response สำหรับหน้า Home และตั้งค่าไม่ให้แคช
    response = make_response(render_template(
        'home.html', 
        username=session['username'], 
        checkin_data=checkin_data, 
        export_data=export_data,
        checkin_total=checkin_total,
        export_total=export_total,
        stock_total=stock_total,
        monthly_checkin=monthly_checkin,
        monthly_export=monthly_export
    ))
    
    # ป้องกันไม่ให้หน้า Home ถูกแคชในเบราว์เซอร์
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

# หน้า Add data Product (ต้องล็อกอินก่อน)
@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        # ดึงข้อมูลจากฟอร์ม
        product_name = request.form.get('product_name')
        outer_size = request.form.get('outer_size')
        storage_area = request.form.get('storage_area')
        shelf_space = request.form.get('shelf_space')
        customer_name = request.form.get('customer_name')

        # เชื่อมต่อกับฐานข้อมูลและบันทึกข้อมูลลงในตาราง data_dropdown
        conn = get_db_connection_product()
        conn.execute('''
            INSERT INTO data_dropdown (product_name, outer_size, storage_area, shelf_space, customer_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (product_name, outer_size, storage_area, shelf_space, customer_name))
        conn.commit()
        conn.close()

        flash('Product information added successfully!')
        return redirect(url_for('add_product'))

    response = make_response(render_template('add_product.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
    
# หน้า Checkin สินค้า (ต้องล็อกอินก่อน)
# หน้า Checkin สินค้า (ต้องล็อกอินก่อน)
@app.route('/checkin', methods=['GET', 'POST'])
@login_required
def checkin():
    conn = get_db_connection_product()

    # ดึงข้อมูลสำหรับดรอปดาว
    customers = conn.execute('SELECT DISTINCT customer_name FROM data_dropdown').fetchall()
    products = conn.execute('SELECT DISTINCT product_name FROM data_dropdown').fetchall()
    outer_sizes = conn.execute('SELECT DISTINCT outer_size FROM data_dropdown').fetchall()
    storage_areas = conn.execute('SELECT DISTINCT storage_area FROM data_dropdown').fetchall()
    shelf_spaces = conn.execute('SELECT DISTINCT shelf_space FROM data_dropdown').fetchall()

    if request.method == 'POST':
        # ดึงข้อมูลจากฟอร์ม
        product_id = request.form['product_id']
        customer_name = request.form['customer_name']
        product_name = request.form['product_name']
        outer_size = request.form['outer_size']
        quantity = request.form['quantity']
        checkin_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # ใช้วันและเวลาปัจจุบัน
        storage_area = request.form['storage_area']
        shelf_space = request.form['shelf_space']
        detailed_notes = request.form['detailed_notes']
        user_name = session['username']  # ดึง username จาก session
        product_status = 'รับเข้า'  # กำหนดสถานะอัตโนมัติ

        # บันทึกข้อมูลลงในฐานข้อมูล product_checkin
        conn.execute('''
            INSERT INTO product_checkin (
                product_id, customer_name, product_name, outer_size, quantity, 
                checkin_date, storage_area, shelf_space, user_name, detailed_notes, product_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product_id, customer_name, product_name, outer_size, quantity, checkin_date, storage_area, shelf_space, user_name, detailed_notes, product_status))
        conn.commit()
        conn.close()

        flash('Product check-in successfully!')
        return redirect(url_for('checkin'))

    # ปิดการเชื่อมต่อฐานข้อมูล
    conn.close()

    # สร้าง response สำหรับหน้า Checkin และตั้งค่าไม่ให้แคช
    response = make_response(render_template('checkin.html', customers=customers, products=products, outer_sizes=outer_sizes, storage_areas=storage_areas, shelf_spaces=shelf_spaces))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# หน้า Export สินค้า (ต้องล็อกอินก่อน)
@app.route('/export', methods=['GET', 'POST'])
@login_required
def export():
    conn = get_db_connection_product()

    # ค้นหาข้อมูลจาก product_checkin โดยแสดงเฉพาะรายการที่มี quantity > 0
    search_query = request.args.get('search', '')
    if search_query:
        products = conn.execute('''
            SELECT * FROM product_checkin 
            WHERE (product_id LIKE ? OR product_name LIKE ?)
            AND quantity > 0
            ORDER BY checkin_date DESC LIMIT 10
        ''', (f'%{search_query}%', f'%{search_query}%')).fetchall()
    else:
        products = conn.execute('''
            SELECT * FROM product_checkin 
            WHERE quantity > 0 
            ORDER BY checkin_date DESC LIMIT 10
        ''').fetchall()

    # ค้นหาข้อมูลจาก product_export โดยแสดงรายการล่าสุด 10 รายการ
    export_search_query = request.args.get('export_search', '')
    if export_search_query:
        exported_products = conn.execute('''
            SELECT * FROM product_export 
            WHERE product_id LIKE ? OR product_name LIKE ?
            ORDER BY checkin_date DESC LIMIT 10
        ''', (f'%{export_search_query}%', f'%{export_search_query}%')).fetchall()
    else:
        exported_products = conn.execute('''
            SELECT * FROM product_export 
            ORDER BY checkin_date DESC LIMIT 10
        ''').fetchall()

    # กรณีที่กดปุ่ม Export ข้อมูล
    if request.method == 'POST':
        selected_products = request.form.getlist('selected_products')  # ดึงรายการสินค้าที่ถูกเลือก

        for product_id in selected_products:
            product = conn.execute('SELECT * FROM product_checkin WHERE product_id = ?', (product_id,)).fetchone()

            if product:
                export_quantity = int(request.form.get(f'export_quantity_{product_id}'))  # จำนวนที่ต้องการส่งออก
                remaining_quantity = product['quantity'] - export_quantity  # หักลบจำนวนที่ส่งออก

                if remaining_quantity < 0:
                    flash(f'Quantity to export exceeds available quantity for product {product["product_name"]}')
                    return redirect(url_for('export'))

                # บันทึกลงตาราง product_export
                conn.execute('''
                    INSERT INTO product_export (
                        product_id, customer_name, product_name, outer_size, quantity, 
                        checkin_date, storage_area, shelf_space, user_name, detailed_notes, product_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (product['product_id'], product['customer_name'], product['product_name'], product['outer_size'],
                      export_quantity, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), product['storage_area'],
                      product['shelf_space'], session['username'], product['detailed_notes'], 'ส่งออก'))

                # อัปเดตจำนวนที่เหลือใน product_checkin
                conn.execute('UPDATE product_checkin SET quantity = ? WHERE product_id = ?', (remaining_quantity, product_id))

        conn.commit()
        flash('Products exported successfully!')
        return redirect(url_for('export'))

    # ป้องกันไม่ให้หน้า Export ถูกแคชในเบราว์เซอร์
    response = make_response(render_template('export.html', products=products, exported_products=exported_products))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    conn.close()
    return response

# อัพเดตรายการสินค้า Auto
@app.route('/update_products', methods=['GET'])
def update_products():
    conn = get_db_connection_product()
    products = conn.execute('''
        SELECT * FROM product_checkin 
        WHERE product_status = 'รับเข้า'
        AND product_id NOT IN (SELECT product_id FROM product_export WHERE product_status = 'ส่งออก')
    ''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in products])



# หน้า Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection_users()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()

        if user:
            session['username'] = username
            flash('Logged in successfully!')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password!')
    
    if 'username' in session:
        return redirect(url_for('home'))

    response = make_response(render_template('login.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# หน้า Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out!')
    response = make_response(redirect(url_for('login')))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/print_export/<string:product_id>')
@login_required
def print_export(product_id):
    conn = get_db_connection_product()

    # ดึงข้อมูลสินค้าที่ถูก Export แล้วตาม product_id
    product = conn.execute('SELECT * FROM product_export WHERE product_id = ?', (product_id,)).fetchone()
    conn.close()

    if not product:
        flash('Product not found.')
        return redirect(url_for('export'))

    # สร้าง PDF ในหน่วยความจำ
    pdf = FPDF()
    pdf.add_page()

    # เพิ่มฟอนต์ THSarabun และ THSarabun-Bold
    pdf.add_font('THSarabun', '', 'fonts/THSarabun.ttf', uni=True)
    pdf.add_font('THSarabun', 'B', 'fonts/THSarabun-Bold.ttf', uni=True)  # ฟอนต์ตัวหนา

    # ตั้งฟอนต์เป็นตัวหนาสำหรับหัวเรื่อง
    pdf.set_font('THSarabun', 'B', 18)
    pdf.cell(200, 15, txt="ใบสั่งส่งออกสินค้า", ln=True, align="C")

    # ตั้งฟอนต์เป็นตัวธรรมดาสำหรับเนื้อหา
    pdf.set_font('THSarabun', '', 16)
    pdf.cell(200, 10, txt="Export Work Order", ln=True, align="C")
    pdf.ln(10)

    # ข้อมูลในตาราง
    pdf.set_font('THSarabun', '', 14)
    pdf.cell(50, 10, txt="รหัสสินค้า (Product ID):", border=1)
    pdf.cell(140, 10, txt=f"{product['product_id']}", border=1, ln=True)

    # เพิ่มกรอบเส้นและข้อมูลในลักษณะของตาราง
    pdf.set_font('THSarabun', '', 14)
    pdf.cell(50, 10, txt="รหัสสินค้า (Product ID):", border=1)
    pdf.cell(140, 10, txt=f"{product['product_id']}", border=1, ln=True)
    
    pdf.cell(50, 10, txt="ชื่อลูกค้า (Customer Name):", border=1)
    pdf.cell(140, 10, txt=f"{product['customer_name']}", border=1, ln=True)
    
    pdf.cell(50, 10, txt="ชื่อสินค้า (Product Name):", border=1)
    pdf.cell(140, 10, txt=f"{product['product_name']}", border=1, ln=True)
    
    pdf.cell(50, 10, txt="ขนาดภายนอก (Outer Size):", border=1)
    pdf.cell(140, 10, txt=f"{product['outer_size']}", border=1, ln=True)
    
    pdf.cell(50, 10, txt="จำนวนที่ส่งออก (Quantity):", border=1)
    pdf.cell(140, 10, txt=f"{product['quantity']}", border=1, ln=True)
    
    pdf.cell(50, 10, txt="วันที่ส่งออก (Export Date):", border=1)
    pdf.cell(140, 10, txt=f"{product['checkin_date']}", border=1, ln=True)

    pdf.cell(50, 10, txt="พื้นที่จัดเก็บ (Storage Area):", border=1)
    pdf.cell(140, 10, txt=f"{product['storage_area']}", border=1, ln=True)

    pdf.cell(50, 10, txt="พื้นที่บนชั้น (Shelf Space):", border=1)
    pdf.cell(140, 10, txt=f"{product['shelf_space']}", border=1, ln=True)

    pdf.cell(50, 10, txt="ผู้ใช้ (User):", border=1)
    pdf.cell(140, 10, txt=f"{product['user_name']}", border=1, ln=True)

    pdf.cell(50, 10, txt="สถานะสินค้า (Status):", border=1)
    pdf.cell(140, 10, txt=f"{product['product_status']}", border=1, ln=True)

    pdf.ln(10)  # เว้นบรรทัดก่อนส่วนลายเซ็น

    # เพิ่มลายเซ็นผู้ส่งและผู้รับ
    pdf.cell(95, 10, txt="ลายเซ็นผู้ส่ง (Sender Signature):", ln=False)
    pdf.cell(95, 10, txt="ลายเซ็นผู้รับ (Receiver Signature):", ln=True)

    # ช่องลายเซ็น
    pdf.cell(95, 10, txt=".....................................", ln=False)
    pdf.cell(95, 10, txt=".....................................", ln=True)

    # ใช้ BytesIO เพื่อเก็บ PDF ในหน่วยความจำ
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)

    # ส่งไฟล์ PDF ไปยังเบราว์เซอร์โดยใช้หน่วยความจำ (ไม่บันทึกลงในระบบไฟล์)
    return send_file(pdf_buffer, as_attachment=False, download_name=f"export_work_order_{product['product_id']}.pdf", mimetype='application/pdf')

    # ลบไฟล์หลังจากการส่งเสร็จสิ้น (อาจเพิ่มขั้นตอนนี้ถ้าต้องการลบไฟล์ชั่วคราว)
    # os.remove(pdf_output_path)


if __name__ == '__main__':
    app.run(debug=True)
