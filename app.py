from flask import Flask, request, jsonify, render_template, send_file
from datetime import datetime
import os
import uuid
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'dev-secret-key-12345'

# ===== CONFIGURATION =====
# Use /tmp for Vercel, local folder for development
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = '/tmp/uploads'
    ENHANCED_FOLDER = '/tmp/enhanced'
    ORDERS_FILE = '/tmp/orders.json'
else:
    UPLOAD_FOLDER = 'uploads'
    ENHANCED_FOLDER = 'enhanced'
    ORDERS_FILE = 'orders.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENHANCED_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

# ===== HELPER FUNCTIONS =====
def load_orders():
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r') as f:
                return json.load(f)
        return []
    except:
        return []

def save_orders(orders):
    try:
        with open(ORDERS_FILE, 'w') as f:
            json.dump(orders, f, indent=2)
        return True
    except:
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_order_id():
    return 'ORD-' + str(uuid.uuid4().hex[:8]).upper()

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

        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)

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

        original_filename = secure_filename(file.filename)
        unique_filename = f"enhanced_{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(ENHANCED_FOLDER, unique_filename)
        file.save(file_path)

        order['enhanced_filename'] = unique_filename
        order['status'] = 'completed'
        save_orders(orders)

        return jsonify({
            'success': True,
            'message': 'Enhanced photo uploaded successfully',
            'enhanced_filename': unique_filename
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve original uploads"""
    return send_file(os.path.join(UPLOAD_FOLDER, filename))

@app.route('/enhanced/<filename>')
def serve_enhanced(filename):
    """Serve enhanced photos"""
    return send_file(os.path.join(ENHANCED_FOLDER, filename))

# ===== VERCEL HANDLER =====
def handler(request, context):
    return app(request, context)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
