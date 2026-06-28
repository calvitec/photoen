from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ===== CONFIGURATION =====
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ENHANCED_FOLDER'] = 'enhanced'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

# Email configuration (update with your SMTP settings)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Change this
app.config['MAIL_PASSWORD'] = 'your-app-password'  # Change this
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'  # Change this

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)

# Create upload folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ENHANCED_FOLDER'], exist_ok=True)

# ===== DATABASE MODEL =====
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    original_filename = db.Column(db.String(200), nullable=False)
    stored_filename = db.Column(db.String(200), nullable=False)
    enhanced_filename = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'original_filename': self.original_filename,
            'stored_filename': self.stored_filename,
            'enhanced_filename': self.enhanced_filename,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'enhanced_url': f'/enhanced/{self.enhanced_filename}' if self.enhanced_filename else None
        }

# ===== HELPER FUNCTIONS =====
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_order_id():
    return 'ORD-' + str(uuid.uuid4().hex[:8]).upper()

def send_enhanced_photo(order):
    """Send the enhanced photo to the customer via email"""
    try:
        enhanced_path = os.path.join(app.config['ENHANCED_FOLDER'], order.enhanced_filename)
        if not os.path.exists(enhanced_path):
            return False, "Enhanced file not found"

        msg = Message(
            'Your Enhanced Photo is Ready! 🎉',
            recipients=[order.customer_email]
        )
        msg.body = f"""
        Dear {order.customer_name},

        Your photo has been professionally enhanced and is now ready!

        Order ID: {order.order_id}
        Original: {order.original_filename}
        Enhanced: {order.enhanced_filename}

        Thank you for choosing ApexBuilt Photo Enhancement!

        Best regards,
        The ApexBuilt Team
        """

        with app.open_resource(enhanced_path) as fp:
            msg.attach(
                order.enhanced_filename,
                'image/jpeg',
                fp.read()
            )

        mail.send(msg)
        return True, "Email sent successfully"
    except Exception as e:
        return False, f"Error sending email: {str(e)}"

# ===== ROUTES =====

@app.route('/')
def home():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_photo():
    """Handle photo upload from the form"""
    try:
        # Check if file is present
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed. Use JPG, JPEG, PNG, or WEBP'}), 400

        # Get form data
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

        # Create order in database
        order_id = generate_order_id()
        order = Order(
            order_id=order_id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            original_filename=original_filename,
            stored_filename=unique_filename
        )
        db.session.add(order)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Photo uploaded successfully',
            'order_id': order_id,
            'order': order.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all orders for the admin dashboard"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify({'orders': [o.to_dict() for o in orders]}), 200

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'processing', 'completed']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        order.status = new_status
        db.session.commit()

        # If status is 'completed', send email with enhanced photo
        if new_status == 'completed' and order.enhanced_filename:
            success, message = send_enhanced_photo(order)
            return jsonify({
                'success': True,
                'message': 'Order completed and email sent' if success else f'Order completed but {message}',
                'email_sent': success
            }), 200

        return jsonify({'success': True, 'message': f'Status updated to {new_status}'}), 200

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

        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        # Save enhanced file
        original_filename = secure_filename(file.filename)
        unique_filename = f"enhanced_{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(app.config['ENHANCED_FOLDER'], unique_filename)
        file.save(file_path)

        # Update order
        order.enhanced_filename = unique_filename
        order.status = 'completed'  # Auto-complete when enhanced photo is uploaded
        db.session.commit()

        # Send email with enhanced photo
        success, message = send_enhanced_photo(order)

        return jsonify({
            'success': True,
            'message': 'Enhanced photo uploaded and email sent' if success else f'Enhanced photo uploaded but {message}',
            'enhanced_filename': unique_filename,
            'email_sent': success
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/enhanced/<filename>')
def serve_enhanced(filename):
    """Serve enhanced photos"""
    return send_file(os.path.join(app.config['ENHANCED_FOLDER'], filename))

@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve original uploads"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# ===== CREATE TABLES =====
with app.app_context():
    db.create_all()

# ===== RUN APP =====
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
