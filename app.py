from flask import Flask, request, jsonify, render_template_string, send_file
import os
import uuid
import json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-for-vercel')

# Configuration
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

# Use Vercel's /tmp directory for file storage (writable)
UPLOAD_FOLDER = '/tmp/uploads'
ENHANCED_FOLDER = '/tmp/enhanced'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENHANCED_FOLDER, exist_ok=True)

# Use Vercel's /tmp for database (JSON file storage)
DATA_FILE = '/tmp/orders.json'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_orders():
    """Load orders from JSON file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        return []
    except:
        return []

def save_orders(orders):
    """Save orders to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(orders, f, indent=2)
        return True
    except:
        return False

def generate_order_id():
    return 'ORD-' + str(uuid.uuid4().hex[:8]).upper()

# HTML template as a string (since we can't use templates in serverless)
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Photo Enhancement · ApexBuilt</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
    <style>
        * { font-family: 'Inter', sans-serif; }
        .gradient-hero {
            background: linear-gradient(135deg, #0b2b44 0%, #1a5276 50%, #0b2b44 100%);
            position: relative;
            overflow: hidden;
        }
        .glass-card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255,255,255,0.08);
        }
        .btn-primary {
            background: linear-gradient(135deg, #1a5276, #2e86c1);
            transition: all 0.3s ease;
        }
        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 20px 50px rgba(26, 82, 118, 0.4);
        }
        .pricing-card {
            background: white;
            border-radius: 24px;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            border: 1px solid rgba(0,0,0,0.04);
        }
        .pricing-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 30px 70px rgba(26, 82, 118, 0.1);
        }
        .drop-zone {
            border: 2px dashed #1a5276;
            border-radius: 20px;
            transition: all 0.3s ease;
            background: rgba(26, 82, 118, 0.03);
        }
        .drop-zone.drag-over {
            border-color: #2e86c1;
            background: rgba(26, 82, 118, 0.08);
            transform: scale(1.01);
        }
        .contact-input {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 14px 18px;
            transition: all 0.3s ease;
            width: 100%;
        }
        .contact-input:focus {
            outline: none;
            border-color: #1a5276;
            box-shadow: 0 0 0 4px rgba(26, 82, 118, 0.1);
        }
        .admin-card {
            background: white;
            border-radius: 16px;
            transition: all 0.3s ease;
            border: 1px solid #e2e8f0;
        }
        .admin-card:hover {
            box-shadow: 0 8px 25px rgba(0,0,0,0.06);
        }
        .status-badge {
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .status-pending { background: #fef3c7; color: #92400e; }
        .status-processing { background: #dbeafe; color: #1e40af; }
        .status-completed { background: #d1fae5; color: #065f46; }
        .nav-link {
            position: relative;
            color: rgba(255,255,255,0.7);
            transition: color 0.3s;
        }
        .nav-link::after {
            content: '';
            position: absolute;
            bottom: -6px;
            left: 50%;
            width: 0;
            height: 2.5px;
            background: #2e86c1;
            transition: all 0.3s ease;
            transform: translateX(-50%);
            border-radius: 2px;
        }
        .nav-link:hover { color: white; }
        .nav-link:hover::after { width: 80%; }
        .section-title { font-weight: 800; letter-spacing: -0.02em; }
        .animate-float { animation: float 6s ease-in-out infinite; }
        @keyframes float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
        .fade-slide { opacity: 0; transform: translateY(20px); animation: fadeSlide 0.6s ease-out forwards; }
        @keyframes fadeSlide { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }
        .thumbnail-preview {
            width: 100px;
            height: 100px;
            object-fit: cover;
            border-radius: 12px;
            border: 2px solid #e2e8f0;
        }
        .success-message {
            background: #d1fae5;
            border-left: 4px solid #065f46;
            border-radius: 12px;
            padding: 16px 20px;
        }
        .admin-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #1e293b;
            padding: 12px 16px;
            text-align: left;
            border-bottom: 2px solid #e2e8f0;
        }
        .admin-table td {
            padding: 12px 16px;
            border-bottom: 1px solid #f1f5f9;
            vertical-align: middle;
        }
        .admin-table tr:hover {
            background: #f8fafc;
        }
    </style>
</head>
<body>
    <!-- TOP BAR -->
    <div class="bg-[#0b2b44] text-white/60 text-xs py-1.5 text-center border-b border-white/5">
        <div class="container mx-auto px-4 flex flex-wrap justify-center items-center gap-6">
            <span><i class="fas fa-phone text-[#2e86c1] mr-1"></i> +254 700 123 456</span>
            <span><i class="fas fa-envelope text-[#2e86c1] mr-1"></i> hello@apexbuilt.com</span>
            <span><i class="fas fa-clock text-[#2e86c1] mr-1"></i> 24/7 Support</span>
        </div>
    </div>

    <!-- NAV -->
    <nav class="fixed top-6 left-0 right-0 z-50 px-4">
        <div class="max-w-7xl mx-auto glass-card rounded-2xl shadow-2xl border border-white/5">
            <div class="flex items-center justify-between h-16 px-6">
                <a href="/" class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#1a5276] to-[#2e86c1] flex items-center justify-center text-white font-bold text-lg shadow-lg">
                        <i class="fas fa-crown"></i>
                    </div>
                    <span class="text-xl font-bold text-white">Apex<span class="text-[#2e86c1]">Built</span></span>
                </a>
                <div class="hidden md:flex items-center gap-6 text-sm">
                    <a href="#home" class="nav-link">Home</a>
                    <a href="#pricing" class="nav-link">Pricing</a>
                    <a href="#upload" class="nav-link">Upload</a>
                    <a href="#admin" class="nav-link">Dashboard</a>
                </div>
                <div class="flex items-center gap-3">
                    <button onclick="document.getElementById('upload').scrollIntoView({behavior:'smooth'})" class="px-5 py-2 rounded-full btn-primary text-white font-semibold text-sm shadow-lg">
                        <i class="fas fa-upload mr-1.5"></i> Upload
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <!-- HERO -->
    <section id="home" class="gradient-hero min-h-[70vh] flex items-center pt-20 relative">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
            <div class="text-center max-w-4xl mx-auto">
                <div class="fade-slide">
                    <div class="inline-flex items-center gap-2 bg-[#2e86c1]/10 backdrop-blur-sm px-4 py-2 rounded-full text-sm text-[#2e86c1] font-semibold mb-6 border border-[#2e86c1]/20">
                        <span class="w-2.5 h-2.5 bg-[#2e86c1] rounded-full animate-pulse"></span> AI-Powered Enhancement
                    </div>
                    <h1 class="text-4xl md:text-7xl font-extrabold text-white leading-[1.05]">
                        <span class="text-[#2e86c1]">AI</span> Photo Enhancement
                    </h1>
                    <p class="text-gray-300 text-lg md:text-xl mt-4 max-w-2xl mx-auto leading-relaxed">
                        Upload your photo and we'll professionally enhance it using advanced AI technology.
                    </p>
                    <div class="flex flex-wrap justify-center gap-4 mt-8">
                        <button onclick="document.getElementById('upload').scrollIntoView({behavior:'smooth'})" class="px-8 py-4 rounded-full btn-primary text-white font-bold shadow-lg flex items-center gap-2 text-base">
                            <i class="fas fa-cloud-upload-alt"></i> Upload Now
                        </button>
                        <a href="#pricing" class="px-8 py-4 rounded-full border-2 border-[#2e86c1] text-[#2e86c1] font-bold flex items-center gap-2 text-base hover:bg-[#2e86c1] hover:text-white transition">
                            <i class="fas fa-tag"></i> Pricing
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- PRICING -->
    <section id="pricing" class="py-20 px-4 bg-[#f0f7ff]">
        <div class="max-w-7xl mx-auto">
            <div class="text-center mb-14">
                <span class="text-[#1a5276] text-sm font-semibold tracking-[0.2em] uppercase">Pricing</span>
                <h2 class="section-title text-4xl md:text-5xl text-[#0b2b44] mt-2">Simple, Transparent Pricing</h2>
                <p class="text-gray-500 mt-3 max-w-md mx-auto">Professional AI photo enhancement at an affordable rate</p>
            </div>
            <div class="max-w-md mx-auto">
                <div class="pricing-card p-8 shadow-lg">
                    <div class="text-center">
                        <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#1a5276] to-[#2e86c1] flex items-center justify-center text-white text-3xl mx-auto shadow-lg mb-4">
                            <i class="fas fa-image"></i>
                        </div>
                        <h3 class="text-2xl font-bold text-[#0b2b44]">Photo Enhancement</h3>
                        <div class="text-5xl font-extrabold text-[#1a5276] mt-4">KSh 100</div>
                        <p class="text-gray-500 text-sm mt-1">per photo</p>
                        <div class="flex items-center justify-center gap-2 mt-4 text-[#1a5276]">
                            <i class="fas fa-clock"></i>
                            <span class="font-semibold">Delivery within 30 minutes</span>
                        </div>
                        <div class="mt-6 space-y-2 text-sm text-gray-600">
                            <p><i class="fas fa-check-circle text-[#2e86c1] mr-2"></i> AI-powered enhancement</p>
                            <p><i class="fas fa-check-circle text-[#2e86c1] mr-2"></i> Color correction & sharpening</p>
                            <p><i class="fas fa-check-circle text-[#2e86c1] mr-2"></i> Manual quality check</p>
                            <p><i class="fas fa-check-circle text-[#2e86c1] mr-2"></i> Delivered to your email</p>
                        </div>
                        <button onclick="document.getElementById('upload').scrollIntoView({behavior:'smooth'})" class="mt-8 w-full py-4 rounded-full btn-primary text-white font-bold text-lg shadow-lg transition">
                            <i class="fas fa-upload mr-2"></i> Start Now
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- UPLOAD -->
    <section id="upload" class="py-20 px-4 bg-white">
        <div class="max-w-4xl mx-auto">
            <div class="text-center mb-14">
                <span class="text-[#1a5276] text-sm font-semibold tracking-[0.2em] uppercase">Upload</span>
                <h2 class="section-title text-4xl md:text-5xl text-[#0b2b44] mt-2">Upload Your Photo</h2>
                <p class="text-gray-500 mt-3">Drag & drop or click to select your image</p>
            </div>

            <div class="glass-card bg-white rounded-3xl p-8 shadow-xl border border-gray-100">
                <div id="successMessage" class="success-message hidden mb-6">
                    <div class="flex items-start gap-3">
                        <i class="fas fa-check-circle text-[#065f46] text-xl mt-0.5"></i>
                        <div>
                            <p class="font-semibold text-[#065f46]">Your photo has been received!</p>
                            <p class="text-sm text-[#065f46]/80">Please complete payment. Once payment is confirmed, your photo will be manually enhanced and sent to your email.</p>
                        </div>
                    </div>
                </div>

                <form id="uploadForm" class="space-y-6" enctype="multipart/form-data">
                    <div id="dropZone" class="drop-zone p-12 text-center cursor-pointer transition">
                        <div class="flex flex-col items-center gap-4">
                            <div class="w-20 h-20 rounded-full bg-[#1a5276]/10 flex items-center justify-center text-[#1a5276] text-3xl">
                                <i class="fas fa-cloud-upload-alt"></i>
                            </div>
                            <div>
                                <p class="text-lg font-semibold text-[#0b2b44]">Drag & drop your image here</p>
                                <p class="text-sm text-gray-400">or click to browse</p>
                                <p class="text-xs text-gray-400 mt-2">Supports JPG, JPEG, PNG, WEBP (max 20MB)</p>
                            </div>
                            <input type="file" id="fileInput" name="photo" accept=".jpg,.jpeg,.png,.webp" class="hidden" required />
                        </div>
                    </div>

                    <div id="thumbnailContainer" class="hidden mt-4 flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                        <img id="thumbnailPreview" class="thumbnail-preview" src="#" alt="Preview" />
                        <div>
                            <p id="fileName" class="font-semibold text-[#0b2b44]"></p>
                            <p id="fileSize" class="text-sm text-gray-400"></p>
                        </div>
                        <button type="button" id="removeFile" class="ml-auto text-red-500 hover:text-red-700 transition">
                            <i class="fas fa-times-circle text-xl"></i>
                        </button>
                    </div>

                    <div class="grid md:grid-cols-2 gap-4">
                        <div>
                            <label class="text-sm font-semibold text-[#0b2b44] block mb-1">Full Name *</label>
                            <input type="text" name="name" placeholder="John Doe" class="contact-input" required />
                        </div>
                        <div>
                            <label class="text-sm font-semibold text-[#0b2b44] block mb-1">Email Address *</label>
                            <input type="email" name="email" placeholder="john@example.com" class="contact-input" required />
                        </div>
                    </div>
                    <div>
                        <label class="text-sm font-semibold text-[#0b2b44] block mb-1">Phone Number</label>
                        <input type="tel" name="phone" placeholder="+254 700 123 456" class="contact-input" />
                    </div>

                    <button type="submit" class="w-full py-4 rounded-xl btn-primary text-white font-bold text-lg transition shadow-lg">
                        <i class="fas fa-upload mr-2"></i> Upload Photo
                    </button>
                </form>
            </div>
        </div>
    </section>

    <!-- ADMIN DASHBOARD -->
    <section id="admin" class="py-20 px-4 bg-[#f8fafc]">
        <div class="max-w-7xl mx-auto">
            <div class="text-center mb-14">
                <span class="text-[#1a5276] text-sm font-semibold tracking-[0.2em] uppercase">Dashboard</span>
                <h2 class="section-title text-4xl md:text-5xl text-[#0b2b44] mt-2">Admin Dashboard</h2>
                <p class="text-gray-500 mt-3">Manage orders, track status, and deliver enhanced photos</p>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div class="admin-card p-6 text-center">
                    <div class="text-3xl font-bold text-[#1a5276]" id="totalOrders">0</div>
                    <p class="text-sm text-gray-500">Total Orders</p>
                </div>
                <div class="admin-card p-6 text-center">
                    <div class="text-3xl font-bold text-[#f59e0b]" id="pendingOrders">0</div>
                    <p class="text-sm text-gray-500">Pending</p>
                </div>
                <div class="admin-card p-6 text-center">
                    <div class="text-3xl font-bold text-[#3b82f6]" id="processingOrders">0</div>
                    <p class="text-sm text-gray-500">Processing</p>
                </div>
                <div class="admin-card p-6 text-center">
                    <div class="text-3xl font-bold text-[#10b981]" id="completedOrders">0</div>
                    <p class="text-sm text-gray-500">Completed</p>
                </div>
            </div>

            <div class="admin-card p-6 shadow-sm overflow-x-auto">
                <h3 class="text-lg font-bold text-[#0b2b44] mb-4">All Orders</h3>
                <table class="admin-table w-full text-sm">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Customer</th>
                            <th>Email</th>
                            <th>Phone</th>
                            <th>Photo</th>
                            <th>Status</th>
                            <th>Enhanced</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="ordersBody">
                        <tr>
                            <td colspan="8" class="text-center py-8 text-gray-400">
                                <i class="fas fa-inbox text-2xl block mb-2"></i>
                                No orders yet
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </section>

    <!-- FOOTER -->
    <footer class="bg-[#0b2b44] text-white/50 pt-12 pb-6 px-4 border-t border-white/5">
        <div class="max-w-7xl mx-auto">
            <div class="grid md:grid-cols-3 gap-8">
                <div>
                    <div class="flex items-center gap-3 mb-3">
                        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#1a5276] to-[#2e86c1] flex items-center justify-center text-white text-lg"><i class="fas fa-crown"></i></div>
                        <span class="text-xl font-bold text-white">Apex<span class="text-[#2e86c1]">Built</span></span>
                    </div>
                    <p class="text-sm leading-relaxed text-gray-400 max-w-xs">Professional AI photo enhancement and construction services.</p>
                </div>
                <div>
                    <h4 class="text-white font-semibold text-base mb-3">Quick Links</h4>
                    <ul class="space-y-1.5 text-sm">
                        <li><a href="#home" class="hover:text-[#2e86c1] transition">Home</a></li>
                        <li><a href="#pricing" class="hover:text-[#2e86c1] transition">Pricing</a></li>
                        <li><a href="#upload" class="hover:text-[#2e86c1] transition">Upload</a></li>
                        <li><a href="#admin" class="hover:text-[#2e86c1] transition">Dashboard</a></li>
                    </ul>
                </div>
                <div>
                    <h4 class="text-white font-semibold text-base mb-3">Contact</h4>
                    <ul class="space-y-2 text-sm">
                        <li class="flex items-start gap-3"><i class="fas fa-phone text-[#2e86c1] mt-1"></i><span>+254 700 123 456</span></li>
                        <li class="flex items-start gap-3"><i class="fas fa-envelope text-[#2e86c1] mt-1"></i><span>hello@apexbuilt.com</span></li>
                        <li class="flex items-start gap-3"><i class="fas fa-map-pin text-[#2e86c1] mt-1"></i><span>Nairobi, Kenya</span></li>
                    </ul>
                </div>
            </div>
            <div class="border-t border-white/5 mt-8 pt-6 text-center text-xs text-gray-500">
                © 2026 ApexBuilt. All rights reserved.
            </div>
        </div>
    </footer>

    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const thumbnailContainer = document.getElementById('thumbnailContainer');
        const thumbnailPreview = document.getElementById('thumbnailPreview');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const removeFileBtn = document.getElementById('removeFile');

        let selectedFile = null;

        dropZone.addEventListener('click', () => fileInput.click());

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0) {
                handleFile(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });

        function handleFile(file) {
            const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
            if (!validTypes.includes(file.type)) {
                alert('Please upload a JPG, JPEG, PNG, or WEBP image.');
                return;
            }
            if (file.size > 20 * 1024 * 1024) {
                alert('File size must be less than 20MB.');
                return;
            }
            selectedFile = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                thumbnailPreview.src = e.target.result;
                fileName.textContent = file.name;
                fileSize.textContent = (file.size / 1024 / 1024).toFixed(2) + ' MB';
                thumbnailContainer.classList.remove('hidden');
                dropZone.classList.add('hidden');
            };
            reader.readAsDataURL(file);
        }

        removeFileBtn.addEventListener('click', () => {
            selectedFile = null;
            thumbnailContainer.classList.add('hidden');
            dropZone.classList.remove('hidden');
            fileInput.value = '';
        });

        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!selectedFile) {
                alert('Please select a photo to upload.');
                return;
            }

            const formData = new FormData();
            formData.append('photo', selectedFile);
            formData.append('name', document.querySelector('input[name="name"]').value);
            formData.append('email', document.querySelector('input[name="email"]').value);
            formData.append('phone', document.querySelector('input[name="phone"]').value);

            const submitBtn = e.target.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Uploading...';

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    document.getElementById('successMessage').classList.remove('hidden');
                    document.getElementById('successMessage').scrollIntoView({ behavior: 'smooth', block: 'center' });
                    
                    selectedFile = null;
                    thumbnailContainer.classList.add('hidden');
                    dropZone.classList.remove('hidden');
                    fileInput.value = '';
                    document.querySelector('input[name="name"]').value = '';
                    document.querySelector('input[name="email"]').value = '';
                    document.querySelector('input[name="phone"]').value = '';
                    
                    loadOrders();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Upload failed: ' + error.message);
            }

            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-upload mr-2"></i> Upload Photo';
        });

        async function loadOrders() {
            try {
                const response = await fetch('/api/orders');
                const data = await response.json();
                
                const orders = data.orders || [];
                const tbody = document.getElementById('ordersBody');
                
                if (orders.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="8" class="text-center py-8 text-gray-400">
                                <i class="fas fa-inbox text-2xl block mb-2"></i>
                                No orders yet
                            </td>
                        </tr>
                    `;
                } else {
                    tbody.innerHTML = orders.map((order, index) => `
                        <tr>
                            <td class="font-medium text-[#0b2b44]">${index + 1}</td>
                            <td class="font-medium">${order.customer_name}</td>
                            <td class="text-gray-600">${order.customer_email}</td>
                            <td class="text-gray-600">${order.customer_phone || '—'}</td>
                            <td>
                                <span class="text-xs bg-gray-100 px-2 py-1 rounded">${order.original_filename}</span>
                            </td>
                            <td>
                                <span class="status-badge status-${order.status}">${order.status.charAt(0).toUpperCase() + order.status.slice(1)}</span>
                            </td>
                            <td>
                                ${order.enhanced_filename 
                                    ? `<span class="text-xs text-[#10b981]"><i class="fas fa-check-circle mr-1"></i> Delivered</span>`
                                    : `<span class="text-xs text-gray-400">—</span>`
                                }
                            </td>
                            <td>
                                <div class="flex gap-2 flex-wrap">
                                    ${order.status === 'pending' ? `
                                        <button onclick="updateStatus(${order.id}, 'processing')" class="text-xs bg-blue-100 text-blue-700 px-3 py-1 rounded-full hover:bg-blue-200 transition">
                                            Process
                                        </button>
                                    ` : ''}
                                    ${order.status === 'processing' ? `
                                        <button onclick="completeOrder(${order.id})" class="text-xs bg-green-100 text-green-700 px-3 py-1 rounded-full hover:bg-green-200 transition">
                                            Complete
                                        </button>
                                    ` : ''}
                                    ${order.status === 'completed' ? `
                                        <span class="text-xs text-green-600 font-medium"><i class="fas fa-check-circle"></i> Done</span>
                                    ` : ''}
                                </div>
                            </td>
                        </tr>
                    `).join('');
                }

                // Update stats
                const total = orders.length;
                const pending = orders.filter(o => o.status === 'pending').length;
                const processing = orders.filter(o => o.status === 'processing').length;
                const completed = orders.filter(o => o.status === 'completed').length;
                
                document.getElementById('totalOrders').textContent = total;
                document.getElementById('pendingOrders').textContent = pending;
                document.getElementById('processingOrders').textContent = processing;
                document.getElementById('completedOrders').textContent = completed;
                
            } catch (error) {
                console.error('Error loading orders:', error);
            }
        }

        async function updateStatus(orderId, status) {
            try {
                const response = await fetch(`/api/orders/${orderId}/status`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: status })
                });
                const data = await response.json();
                if (data.success) {
                    loadOrders();
                    alert(`Order updated to ${status.charAt(0).toUpperCase() + status.slice(1)}`);
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        async function completeOrder(orderId) {
            try {
                // Simulate enhanced photo upload
                const response = await fetch(`/api/orders/${orderId}/enhance`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        enhanced_filename: 'enhanced_' + Date.now() + '.jpg'
                    })
                });
                const data = await response.json();
                if (data.success) {
                    loadOrders();
                    alert('✅ Order completed! Enhanced photo would be sent to customer via email.');
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        // Load orders on page load
        document.addEventListener('DOMContentLoaded', loadOrders);

        // Smooth scroll
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        });

        window.addEventListener('scroll', () => {
            const nav = document.querySelector('nav .glass-card');
            if (window.scrollY > 40) {
                nav.style.background = 'rgba(11, 43, 68, 0.92)';
                nav.style.borderColor = 'rgba(46, 134, 193, 0.2)';
            } else {
                nav.style.background = 'rgba(255,255,255,0.05)';
                nav.style.borderColor = 'rgba(255,255,255,0.05)';
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    """Serve the main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/upload', methods=['POST'])
def upload_photo():
    """Handle photo upload"""
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'}), 400

        # Get form data
        customer_name = request.form.get('name', '').strip()
        customer_email = request.form.get('email', '').strip()
        customer_phone = request.form.get('phone', '').strip()

        if not customer_name or not customer_email:
            return jsonify({'success': False, 'error': 'Name and email are required'}), 400

        # Save file
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
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

@app.route('/api/orders/<int:order_id>/enhance', methods=['POST'])
def upload_enhanced_photo(order_id):
    """Simulate enhanced photo upload"""
    try:
        data = request.get_json()
        enhanced_filename = data.get('enhanced_filename')

        orders = load_orders()
        order = next((o for o in orders if o['id'] == order_id), None)
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        order['enhanced_filename'] = enhanced_filename
        order['status'] = 'completed'
        save_orders(orders)

        return jsonify({
            'success': True,
            'message': 'Enhanced photo uploaded successfully',
            'enhanced_filename': enhanced_filename
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Vercel handler
def handler(request, context):
    """Vercel serverless function handler"""
    return app(request, context)

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
