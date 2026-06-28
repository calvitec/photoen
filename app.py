from flask import Flask, request, jsonify, render_template, send_file
from flask_mail import Mail, Message
from datetime import datetime
import os
import uuid
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ===== HARDCODED CONFIGURATION (No .env needed) =====
app.config['SECRET_KEY'] = 'dev-secret-key-12345'

# File Upload
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ENHANCED_FOLDER'] = 'enhanced'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

# ===== EMAIL CONFIGURATION (OPTIONAL - Comment out if not needed) =====
# If you don't want email, just comment these lines out
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Change this
app.config['MAIL_PASSWORD'] = 'your-app-password'     # Change this
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'

# Initialize mail (comment this out if not using email)
mail = Mail(app)

# Create folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ENHANCED_FOLDER'], exist_ok=True)

# JSON file for orders (acts as database)
ORDERS_FILE = 'orders.json'

# ===== HELPER FUNCTIONS =====
def load_orders():
    """Load orders from JSON file"""
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r') as f:
                return json.load(f)
        return []
    except:
        return []

def save_orders(orders):
    """Save orders to JSON file"""
    try:
        with open(ORDERS_FILE, 'w') as f:
            json.dump(orders, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving orders: {e}")
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_order_id():
    return 'ORD-' + str(uuid.uuid4().hex[:8]).upper()

def send_enhanced_photo(order):
    """Send the enhanced photo to the customer via email"""
    # If email not configured, skip
    if not app.config.get('MAIL_USERNAME'):
        return False, "Email not configured - skipping"
    
    try:
        enhanced_path = os.path.join(app.config['ENHANCED_FOLDER'], order['enhanced_filename'])
        if not os.path.exists(enhanced_path):
            return False, "Enhanced file not found"

        msg = Message(
            'Your Enhanced Photo is Ready! 🎉',
            recipients=[order['customer_email']]
        )
        msg.body = f"""
Dear {order['customer_name']},

Your photo has been professionally enhanced and is now ready!

Order ID: {order['order_id']}
Original: {order['original_filename']}
Enhanced: {order['enhanced_filename']}

Thank you for choosing ApexBuilt Photo Enhancement!

Best regards,
The ApexBuilt Team
        """

        with app.open_resource(enhanced_path) as fp:
            msg.attach(
                order['enhanced_filename'],
                'image/jpeg',
                fp.read()
            )

        mail.send(msg)
        return True, "Email sent successfully"
    except Exception as e:
        return False, f"Error sending email: {str(e)}"

# ===== ROUTES =====

@app.route('/')
def index():
    """Public homepage"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """Admin dashboard"""
    orders = load_orders()
    return render_template('admin.html', orders=orders)

@app.route('/api/upload', methods=['POST'])
def upload_photo():
    """API endpoint for photo upload"""
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'}), 400

        customer_name = request.form.get('name', '').strip()
        customer_email = request.form.get('email', '').strip()
        customer_phone = request.form.get('phone', '').strip()

        if not customer_name or not customer_email:
            return jsonify({'success': False, 'error': 'Name and email are required'}), 400

        # Save file
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        # Create order
        order_id = generate_order_id()
        orders = load_orders()
        
        new_order = {
            'id': len(orders) + 1,
            'order_id': order_id,
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_phone': customer_phone,
            'original_filename': original_filename,
            'stored_filename': unique_filename,
            'enhanced_filename': None,
            'status': 'pending',
            'payment_status': 'pending',
            'amount': 100.00,
            'created_at': datetime.utcnow().isoformat()
        }
        
        orders.append(new_order)
        save_orders(orders)

        return jsonify({
            'success': True,
            'message': 'Photo uploaded successfully',
            'order_id': order_id
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all orders"""
    orders = load_orders()
    return jsonify({'orders': orders}), 200

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'processing', 'completed']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        orders = load_orders()
        order = next((o for o in orders if o['id'] == order_id), None)
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        order['status'] = new_status
        save_orders(orders)

        if new_status == 'completed' and order.get('enhanced_filename'):
            success, message = send_enhanced_photo(order)

        return jsonify({'success': True, 'message': f'Status updated to {new_status}'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/payment', methods=['PUT'])
def update_payment_status(order_id):
    """Update payment status"""
    try:
        data = request.get_json()
        payment_status = data.get('payment_status')
        
        if payment_status not in ['pending', 'paid']:
            return jsonify({'success': False, 'error': 'Invalid payment status'}), 400

        orders = load_orders()
        order = next((o for o in orders if o['id'] == order_id), None)
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        order['payment_status'] = payment_status
        save_orders(orders)

        return jsonify({'success': True, 'message': f'Payment status updated to {payment_status}'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/enhance', methods=['POST'])
def upload_enhanced_photo(order_id):
    """Upload enhanced version of a photo"""
    try:
        if 'enhanced_photo' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['enhanced_photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'}), 400

        orders = load_orders()
        order = next((o for o in orders if o['id'] == order_id), None)
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        # Save enhanced file
        original_filename = secure_filename(file.filename)
        unique_filename = f"enhanced_{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(app.config['ENHANCED_FOLDER'], unique_filename)
        file.save(file_path)

        # Update order
        order['enhanced_filename'] = unique_filename
        order['status'] = 'completed'
        save_orders(orders)

        # Try to send email (if configured)
        success, message = send_enhanced_photo(order)

        return jsonify({
            'success': True,
            'message': 'Enhanced photo uploaded successfully',
            'enhanced_filename': unique_filename,
            'email_sent': success
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve original uploads"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/enhanced/<filename>')
def serve_enhanced(filename):
    """Serve enhanced photos"""
    return send_file(os.path.join(app.config['ENHANCED_FOLDER'], filename))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
