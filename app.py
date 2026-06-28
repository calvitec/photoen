import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_ai_enhancer_key'

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
DATABASE = 'database.db'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                enhanced_filename TEXT,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Ensure database is initialized
init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Mock template loop data matching index structure
MOCK_SERVICES = [
    {"name": "Portrait Sharpening", "icon": "fa-user-astronaut", "image": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&q=80", "description": "Recover facial details, remove motion blur, and add stunning clarity.", "features": ["Face Detection", "Texture Fix", "Eye Enhancement"]},
    {"name": "Vintage Restoration", "icon": "fa-clock-rotate-left", "image": "https://images.unsplash.com/photo-1509281373149-e957c6296406?w=500&q=80", "description": "Remove scratches, balance fading contrast, and colorize historic photos.", "features": ["De-scratch", "B&W Colorization", "Grain Balance"]},
    {"name": "Low-Light Repair", "icon": "fa-moon", "image": "https://images.unsplash.com/photo-1516339901601-2e1d62dc0c45?w=500&q=80", "description": "Eliminate digital noise and naturally illuminate dark or nighttime photography.", "features": ["Denoise AI", "Shadow Recovery", "ISO Correction"]}
]

MOCK_PROJECTS = [
    {"title": "Retro Family Archive", "category": "Restoration", "image": "https://images.unsplash.com/photo-1472457897821-70d3819a0e24?w=500&q=80", "description": "Saved a 40-year-old torn family snapshot with crisp facial detailing."},
    {"title": "E-Commerce Product Shot", "category": "Sharpening", "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&q=80", "description": "Enhanced lighting, reflections, and structural lines for studio accuracy."},
    {"title": "Night Corporate Headshot", "category": "Low-Light", "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500&q=80", "description": "Removed severe grain patterns from an outdoor late-evening portrait."}
]

MOCK_TESTIMONIALS = [
    {"name": "Mwangi K.", "location": "Nairobi", "project": "Portrait Edit", "rating": 5, "text": "Turnaround time was less than 20 minutes! The clarity on my blurry photo is absolutely wild."},
    {"name": "Sarah O.", "location": "Mombasa", "project": "Vintage Scan", "rating": 5, "text": "I was skeptical about KSh 100 pricing, but the manual fine-tuning brought my grandmother's old photo to life."},
    {"name": "David L.", "location": "Kisumu", "project": "Product Design", "rating": 5, "text": "Super crisp processing. The admin panel workflow is clean and delivery was direct to my mail inbox."}
]

@app.route('/')
def index():
    return render_template('index.html', 
                           services=MOCK_SERVICES, 
                           projects=MOCK_PROJECTS, 
                           testimonials=MOCK_TESTIMONIALS,
                           success=request.args.get('success'))

@app.route('/upload', methods=['POST'])
def handle_upload():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    file = request.files.get('photo')

    if not file or file.filename == '':
        flash("No file selected.")
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Append unique prefix to avoid overrides
        import time
        unique_filename = f"{int(time.time())}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        # Persist information into sqlite database
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO orders (customer_name, email, phone, original_filename)
                VALUES (?, ?, ?, ?)
            ''', (name, email, phone, unique_filename))
            conn.commit()

        return redirect(url_for('index', success=True) + '#upload')
    
    flash("Invalid file extension.")
    return redirect(url_for('index'))


# ===== ADMINISTRATIVE ROUTING =====

@app.route('/admin')
def admin_dashboard():
    with get_db_connection() as conn:
        orders = conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    return render_template('admin.html', orders=orders)

@app.route('/admin/update_status/<int:order_id>', methods=['POST'])
def update_status(order_id):
    status = request.form.get('status')
    with get_db_connection() as conn:
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/upload_enhanced/<int:order_id>', methods=['POST'])
def upload_enhanced(order_id):
    file = request.files.get('enhanced_photo')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        enhanced_filename = f"enhanced_{int(os.time.time() if hasattr(os, 'time') else 12345)}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], enhanced_filename))
        
        with get_db_connection() as conn:
            # Fetch current order details to get customer email info
            order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
            conn.execute('''
                UPDATE orders 
                SET enhanced_filename = ?, status = 'Completed' 
                WHERE id = ?
            ''', (enhanced_filename, order_id))
            conn.commit()
            
        # Mock Email Routine logic block execution hook
        simulate_email_send(order['email'], enhanced_filename)
        
    return redirect(url_for('admin_dashboard'))

def simulate_email_send(recipient_email, filename):
    """
    Hook framework placeholder to connect SMTP, Mailgun, or SendGrid systems.
    """
    print(f"--- OUTBOUND DISPATCH ---")
    print(f"To: {recipient_email}")
    print(f"Subject: Your Enhanced Photo is Ready!")
    print(f"Attachment Reference: {filename}")
    print(f"-------------------------")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
