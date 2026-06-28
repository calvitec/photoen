from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from datetime import datetime
import os
import uuid
import base64
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'dev-secret-key-12345'

# ===== SUPABASE CONFIGURATION =====
SUPABASE_URL = "https://hzqrdwerkgfmfaufabjr.supabase.co"
SUPABASE_KEY = "sb_publishable_tnBOmCO7EFfIoXfNjEH_Tg_D7WX-zld"

# Try to import supabase
try:
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    DB_CONNECTED = True
    DB_TYPE = 'supabase'
    print("✅ Supabase connected!")
except Exception as e:
    supabase = None
    DB_CONNECTED = False
    DB_TYPE = 'json'
    print(f"⚠️ Supabase error: {e}")
    print("📁 Using JSON storage")

# ===== FILE CONFIGURATION =====
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

# ===== DATABASE FUNCTIONS =====
def get_orders_from_supabase():
    """Get orders from Supabase"""
    try:
        response = supabase.table('orders').select('*').order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Supabase error: {e}")
        return None

def save_order_to_supabase(order_data):
    """Save order to Supabase"""
    try:
        response = supabase.table('orders').insert(order_data).execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"Supabase save error: {e}")
        return None

def load_orders():
    """Load orders from Supabase or JSON"""
    if DB_CONNECTED:
        try:
            orders = get_orders_from_supabase()
            if orders is not None:
                return orders
        except:
            pass
    return load_orders_json()

def load_orders_json():
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r') as f:
                return json.load(f)
        return []
    except:
        return []

def save_orders_json(orders):
    try:
        with open(ORDERS_FILE, 'w') as f:
            json.dump(orders, f, indent=2)
        return True
    except:
        return False

def get_order_by_id(order_id):
    if DB_CONNECTED:
        try:
            response = supabase.table('orders').select('*').eq('id', order_id).execute()
            return response.data[0] if response.data else None
        except:
            pass
    orders = load_orders_json()
    for order in orders:
        if order.get('id') == order_id:
            return order
    return None

def add_order(order_data):
    if DB_CONNECTED:
        try:
            order_id = save_order_to_supabase(order_data)
            if order_id:
                print(f"✅ Order saved to Supabase: {order_data['order_id']}")
                return order_id
        except:
            pass
    
    # Fallback to JSON
    orders = load_orders_json()
    order_data['id'] = len(orders) + 1
    orders.append(order_data)
    save_orders_json(orders)
    print(f"📁 Order saved to JSON: {order_data['order_id']}")
    return order_data['id']

def update_order(order_id, updates):
    if DB_CONNECTED:
        try:
            response = supabase.table('orders').update(updates).eq('id', order_id).execute()
            if response.data:
                return True
        except:
            pass
    
    # Fallback to JSON
    orders = load_orders_json()
    for order in orders:
        if order.get('id') == order_id:
            order.update(updates)
            save_orders_json(orders)
            return True
    return False

def delete_order(order_id):
    if DB_CONNECTED:
        try:
            response = supabase.table('orders').delete().eq('id', order_id).execute()
            if response.data:
                return True
        except:
            pass
    
    # Fallback to JSON
    orders = load_orders_json()
    orders = [o for o in orders if o.get('id') != order_id]
    save_orders_json(orders)
    return True

# ===== HELPER FUNCTIONS =====
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_order_id():
    return 'ORD-' + str(uuid.uuid4().hex[:8]).upper()

def get_image_preview(filename, folder):
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
    try:
        orders = load_orders()
        for order in orders:
            if 'created_at' not in order:
                order['created_at'] = datetime.utcnow().isoformat()
            order['original_preview'] = get_image_preview(order.get('stored_filename', ''), UPLOAD_FOLDER)
            if order.get('enhanced_filename'):
                order['enhanced_preview'] = get_image_preview(order['enhanced_filename'], ENHANCED_FOLDER)
        
        stats = {
            'total': len(orders),
            'pending': len([o for o in orders if o.get('status') == 'pending']),
            'processing': len([o for o in orders if o.get('status') == 'processing']),
            'completed': len([o for o in orders if o.get('status') == 'completed']),
            'paid': len([o for o in orders if o.get('payment_status') == 'paid']),
            'unpaid': len([o for o in orders if o.get('payment_status') == 'pending']),
            'revenue': sum([float(o.get('amount', 50)) for o in orders if o.get('payment_status') == 'paid'])
        }
        return render_template('admin.html', orders=orders, stats=stats, db_connected=DB_CONNECTED, db_type=DB_TYPE)
    except Exception as e:
        return f"<h1>Error loading admin</h1><p>{str(e)}</p>", 500

@app.route('/api/status')
def api_status():
    return jsonify({
        'database_connected': DB_CONNECTED,
        'database_type': DB_TYPE,
        'orders': len(load_orders()),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/test-db')
def test_db():
    result = {
        'connected': DB_CONNECTED,
        'type': DB_TYPE,
        'orders_count': len(load_orders()),
        'message': '✅ Connected to Supabase!' if DB_CONNECTED else '📁 Using JSON storage'
    }
    return jsonify(result)

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
        
        order_data = {
            'order_id': order_id,
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_phone': customer_phone or '',
            'original_filename': original_filename,
            'stored_filename': unique_filename,
            'enhanced_filename': None,
            'status': 'pending',
            'payment_status': 'pending',
            'amount': 50.00,
            'created_at': datetime.utcnow().isoformat()
        }
        
        add_order(order_data)

        return jsonify({'success': True, 'message': 'Photo uploaded successfully', 'order_id': order_id}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    orders = load_orders()
    return jsonify({'orders': orders}), 200

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'processing', 'completed']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        order = get_order_by_id(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        updates = {'status': new_status}
        if new_status == 'processing' and order.get('payment_status') == 'pending':
            updates['payment_status'] = 'paid'
        
        update_order(order_id, updates)

        return jsonify({'success': True, 'message': f'Status updated to {new_status}'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/payment', methods=['PUT'])
def update_payment_status(order_id):
    try:
        data = request.get_json()
        payment_status = data.get('payment_status')
        
        if payment_status not in ['pending', 'paid']:
            return jsonify({'success': False, 'error': 'Invalid payment status'}), 400

        order = get_order_by_id(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        updates = {'payment_status': payment_status}
        if payment_status == 'paid' and order.get('status') == 'pending':
            updates['status'] = 'processing'
        
        update_order(order_id, updates)

        return jsonify({'success': True, 'message': f'Payment status updated to {payment_status}'}), 200

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

        order = get_order_by_id(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        original_filename = secure_filename(file.filename)
        unique_filename = f"enhanced_{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(ENHANCED_FOLDER, unique_filename)
        file.save(file_path)

        update_order(order_id, {
            'enhanced_filename': unique_filename,
            'status': 'completed'
        })

        return jsonify({'success': True, 'message': 'Enhanced photo uploaded successfully'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order_route(order_id):
    try:
        order = get_order_by_id(order_id)
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

        delete_order(order_id)

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
    print("\n" + "="*60)
    print("🚀 APEXBUILT PHOTO ENHANCEMENT")
    print("="*60)
    print(f"📁 Database: {DB_TYPE}")
    print(f"🔗 Connected: {'✅ YES' if DB_CONNECTED else '❌ NO'}")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
