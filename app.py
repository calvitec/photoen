from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from datetime import datetime
import os
import uuid
import json
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'dev-secret-key-12345'

# ===== CONFIGURATION =====
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

def get_image_preview(filename, folder):
    """Get base64 encoded image preview"""
    try:
        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
                ext = filename.rsplit('.', 1)[1].lower()
                mime_type = 'image/jpeg' if ext in ['jpg', 'jpeg'] else 'image/png' if ext == 'png' else 'image/webp'
                return f'data:{mime_type};base64,{img_data}'
    except:
        pass
    return None

# ===== ROUTES =====

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    orders = load_orders()
    # Add preview URLs
    for order in orders:
        order['original_preview'] = get_image_preview(order['stored_filename'], UPLOAD_FOLDER)
        if order.get('enhanced_filename'):
            order['enhanced_preview'] = get_image_preview(order['enhanced_filename'], ENHANCED_FOLDER)
    
    stats = {
        'total': len(orders),
        'pending': len([o for o in orders if o['status'] == 'pending']),
        'processing': len([o for o in orders if o['status'] == 'processing']),
        'completed': len([o for o in orders if o['status'] == 'completed']),
        'paid': len([o for o in orders if o['payment_status'] == 'paid']),
        'unpaid': len([o for o in orders if o['payment_status'] == 'pending']),
        'revenue': sum([o.get('amount', 100) for o in orders if o['payment_status'] == 'paid'])
    }
    return render_template('admin.html', orders=orders, stats=stats)

@app.route('/api/upload', methods=['POST'])
def upload_photo():
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
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
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
    orders = load_orders()
    for order in orders:
        order['original_preview'] = get_image_preview(order['stored_filename'], UPLOAD_FOLDER)
        if order.get('enhanced_filename'):
            order['enhanced_preview'] = get_image_preview(order['enhanced_filename'], ENHANCED_FOLDER)
    return jsonify({'orders': orders}), 200

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
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
        order['updated_at'] = datetime.utcnow().isoformat()
        
        if new_status == 'processing' and order['payment_status'] == 'pending':
            order['payment_status'] = 'paid'
        
        save_orders(orders)

        return jsonify({
            'success': True, 
            'message': f'Status updated to {new_status}',
            'order': order
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/payment', methods=['PUT'])
def update_payment_status(order_id):
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
        order['updated_at'] = datetime.utcnow().isoformat()
        
        if payment_status == 'paid' and order['status'] == 'pending':
            order['status'] = 'processing'
        
        save_orders(orders)

        return jsonify({
            'success': True, 
            'message': f'Payment status updated to {payment_status}',
            'order': order
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/enhance', methods=['POST'])
def upload_enhanced_photo(order_id):
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
        order['updated_at'] = datetime.utcnow().isoformat()
        save_orders(orders)

        return jsonify({
            'success': True,
            'message': 'Enhanced photo uploaded successfully',
            'enhanced_filename': unique_filename,
            'download_url': f'/enhanced/{unique_filename}'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    try:
        orders = load_orders()
        order = next((o for o in orders if o['id'] == order_id), None)
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        try:
            original_path = os.path.join(UPLOAD_FOLDER, order['stored_filename'])
            if os.path.exists(original_path):
                os.remove(original_path)
            
            if order.get('enhanced_filename'):
                enhanced_path = os.path.join(ENHANCED_FOLDER, order['enhanced_filename'])
                if os.path.exists(enhanced_path):
                    os.remove(enhanced_path)
        except:
            pass

        orders = [o for o in orders if o['id'] != order_id]
        save_orders(orders)

        return jsonify({'success': True, 'message': 'Order deleted successfully'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/enhanced/<filename>')
def serve_enhanced(filename):
    return send_from_directory(ENHANCED_FOLDER, filename, as_attachment=True)

# ===== VERCEL HANDLER =====
def handler(request, context):
    return app(request, context)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
