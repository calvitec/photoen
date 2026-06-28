from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from datetime import datetime
import os
import uuid
import base64
from werkzeug.utils import secure_filename
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'dev-secret-key-12345'

# ===== CONFIGURATION =====
UPLOAD_FOLDER = 'uploads'
ENHANCED_FOLDER = 'enhanced'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENHANCED_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

# ===== SUPABASE CONFIGURATION =====
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ Warning: Supabase credentials not found. Using local storage.")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected successfully!")

# ===== HELPER FUNCTIONS =====
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

# ===== SUPABASE DATABASE FUNCTIONS =====
def load_orders():
    """Load orders from Supabase"""
    if not supabase:
        # Fallback to JSON file
        try:
            with open('orders.json', 'r') as f:
                return json.load(f)
        except:
            return []
    
    try:
        response = supabase.table('orders').select('*').order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error loading orders from Supabase: {e}")
        return []

def add_order(order_data):
    """Add a new order to Supabase"""
    if not supabase:
        # Fallback to JSON file
        try:
            import json
            orders = []
            try:
                with open('orders.json', 'r') as f:
                    orders = json.load(f)
            except:
                pass
            orders.append(order_data)
            with open('orders.json', 'w') as f:
                json.dump(orders, f, indent=2)
            return len(orders)
        except:
            return None
    
    try:
        response = supabase.table('orders').insert(order_data).execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"Error adding order to Supabase: {e}")
        return None

def update_order(order_id, updates):
    """Update an order in Supabase"""
    if not supabase:
        return False
    
    try:
        response = supabase.table('orders').update(updates).eq('id', order_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error updating order in Supabase: {e}")
        return False

def delete_order_from_db(order_id):
    """Delete an order from Supabase"""
    if not supabase:
        return False
    
    try:
        response = supabase.table('orders').delete().eq('id', order_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error deleting order from Supabase: {e}")
        return False

def get_order_by_id(order_id):
    """Get a single order by ID"""
    if not supabase:
        return None
    
    try:
        response = supabase.table('orders').select('*').eq('id', order_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error getting order: {e}")
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
        'revenue': sum([float(o.get('amount', 50)) for o in orders if o['payment_status'] == 'paid'])
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
            'amount': 50.00
        }
        
        # Add to Supabase
        if supabase:
            try:
                response = supabase.table('orders').insert(order_data).execute()
                if not response.data:
                    raise Exception("Failed to insert order")
                order_id_db = response.data[0]['id']
            except Exception as e:
                return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
        else:
            # Fallback to JSON
            import json
            orders = []
            try:
                with open('orders.json', 'r') as f:
                    orders = json.load(f)
            except:
                pass
            order_data['id'] = len(orders) + 1
            orders.append(order_data)
            with open('orders.json', 'w') as f:
                json.dump(orders, f, indent=2)

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

        order = get_order_by_id(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        updates = {'status': new_status}
        if new_status == 'processing' and order.get('payment_status') == 'pending':
            updates['payment_status'] = 'paid'
        
        success = update_order(order_id, updates)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to update order'}), 500

        return jsonify({
            'success': True, 
            'message': f'Status updated to {new_status}'
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

        order = get_order_by_id(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        updates = {'payment_status': payment_status}
        if payment_status == 'paid' and order.get('status') == 'pending':
            updates['status'] = 'processing'
        
        success = update_order(order_id, updates)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to update order'}), 500

        return jsonify({
            'success': True, 
            'message': f'Payment status updated to {payment_status}'
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

        order = get_order_by_id(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        original_filename = secure_filename(file.filename)
        unique_filename = f"enhanced_{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(ENHANCED_FOLDER, unique_filename)
        file.save(file_path)

        success = update_order(order_id, {
            'enhanced_filename': unique_filename,
            'status': 'completed'
        })
        
        if not success:
            return jsonify({'success': False, 'error': 'Failed to update order'}), 500

        return jsonify({
            'success': True,
            'message': 'Enhanced photo uploaded successfully',
            'enhanced_filename': unique_filename
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order_route(order_id):
    try:
        order = get_order_by_id(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        # Delete files if they exist
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

        success = delete_order_from_db(order_id)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to delete order'}), 500

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
