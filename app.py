import sqlite3
from datetime import datetime, date
from flask import Flask, render_template_string, request, redirect, url_for, flash

app = Flask(__name__)
# Required for flash messages
app.secret_key = 'corporate_secret_key_change_in_production'
DB_NAME = "billing_system.db"

# ==========================================
# DATABASE LAYER (Robust & Migratable)
# ==========================================


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_and_migrate_db():
    """
    Initializes the DB and handles schema migrations automatically 
    to prevent errors when adding new features to existing data.
    """
    conn = get_db_connection()
    c = conn.cursor()

    # 1. Create Tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    sku TEXT,
                    category TEXT,
                    price REAL NOT NULL
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    customer_email TEXT,
                    date TEXT NOT NULL,
                    due_date TEXT,
                    status TEXT DEFAULT 'Pending',
                    subtotal REAL DEFAULT 0.0,
                    tax_rate REAL DEFAULT 0.0,
                    tax_amount REAL DEFAULT 0.0,
                    total_amount REAL NOT NULL
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER,
                    product_name TEXT,
                    quantity INTEGER,
                    price REAL,
                    subtotal REAL,
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
                )''')

    # 2. Smart Migrations (Add columns if they are missing from older versions)
    def add_column_if_not_exists(table, column, definition):
        try:
            c.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
            print(f"Migrated: Added {column} to {table}")
        except sqlite3.OperationalError:
            pass  # Column likely exists

    add_column_if_not_exists('products', 'sku', 'TEXT')
    add_column_if_not_exists('products', 'category', 'TEXT')
    add_column_if_not_exists('invoices', 'due_date', 'TEXT')
    add_column_if_not_exists('invoices', 'status', "TEXT DEFAULT 'Pending'")
    add_column_if_not_exists('invoices', 'subtotal', 'REAL DEFAULT 0.0')
    add_column_if_not_exists('invoices', 'tax_rate', 'REAL DEFAULT 0.0')
    add_column_if_not_exists('invoices', 'tax_amount', 'REAL DEFAULT 0.0')
    add_column_if_not_exists('invoices', 'customer_email', 'TEXT')

    # 3. Seed Data
    c.execute('SELECT count(*) FROM products')
    if c.fetchone()[0] == 0:
        products = [
            ('Enterprise Laptop X1', 'HW-001', 'Hardware', 1299.99),
            ('Wireless Ergonomic Mouse', 'ACC-055', 'Accessories', 45.50),
            ('Mechanical Keyboard', 'ACC-089', 'Accessories', 85.00),
            ('IT Consultation (Hourly)', 'SVC-101', 'Services', 150.00),
            ('Software License (Annual)', 'SW-500', 'Software', 599.00)
        ]
        c.executemany(
            'INSERT INTO products (name, sku, category, price) VALUES (?, ?, ?, ?)', products)
        print("Database seeded with enterprise catalog.")

    conn.commit()
    conn.close()


# Initialize on start
init_and_migrate_db()

# ==========================================
# CONFIG & UTILS
# ==========================================

COMPANY_INFO = {
    "name": "NexusBilling Corp",
    "address": "123 Innovation Drive, Tech Valley, CA 94043",
    "email": "finance@nexuscorp.com",
    "phone": "+1 (555) 019-2834"
}

# ==========================================
# FRONTEND TEMPLATES (NO 3RD PARTY DEPENDENCIES)
# ==========================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NexusBilling | Enterprise Suite</title>
    
    <style>
        /* Custom lightweight CSS Reset & Framework */
        :root {
            --primary: #2563eb;
            --primary-dark: #1e40af;
            --secondary: #64748b;
            --success: #16a34a;
            --danger: #dc2626;
            --warning: #ca8a04;
            --light: #f8fafc;
            --dark: #0f172a;
            --border: #e2e8f0;
            --sidebar-bg: #1e293b;
            --text-main: #334155;
        }

        body { 
            margin: 0; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background: var(--light); 
            color: var(--text-main);
            display: flex;
            min-height: 100vh;
        }
        
        * { box-sizing: border-box; }

        /* Sidebar */
        .sidebar {
            width: 260px;
            background-color: var(--sidebar-bg);
            color: #94a3b8;
            position: fixed;
            top: 0; left: 0; bottom: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            z-index: 100;
        }

        .sidebar-brand {
            color: white;
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 30px;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .nav-link {
            color: inherit;
            padding: 12px 15px;
            text-decoration: none;
            border-radius: 6px;
            margin-bottom: 5px;
            display: block;
            transition: background 0.2s;
        }

        .nav-link:hover, .nav-link.active {
            background-color: rgba(255,255,255,0.1);
            color: white;
        }
        
        /* Layout */
        .main-content {
            margin-left: 260px;
            padding: 30px;
            width: 100%;
            max-width: 1400px;
        }

        /* Typography & Utils */
        h1, h2, h3, h4, h5 { margin-top: 0; color: var(--dark); }
        .text-secondary { color: var(--secondary); font-size: 0.9em; }
        .text-primary { color: var(--primary); }
        .text-danger { color: var(--danger); }
        .text-success { color: var(--success); }
        .text-end { text-align: right; }
        .text-center { text-align: center; }
        .fw-bold { font-weight: bold; }
        .small { font-size: 0.85em; }
        .d-flex { display: flex; }
        .justify-content-between { justify-content: space-between; }
        .align-items-center { align-items: center; }
        .gap-2 { gap: 10px; }
        .mb-3 { margin-bottom: 1rem; }
        .mb-4 { margin-bottom: 1.5rem; }
        
        /* Components */
        .card {
            background: white;
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 20px;
            overflow: hidden;
        }
        
        .card-header {
            background: #f8fafc;
            padding: 15px 20px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .card-body { padding: 20px; }
        .card-footer { padding: 15px 20px; background: #fff; border-top: 1px solid var(--border); }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            border-radius: 6px;
            border: 1px solid transparent;
            font-size: 0.9rem;
            cursor: pointer;
            text-decoration: none;
            font-weight: 500;
            gap: 6px;
        }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: var(--primary-dark); }
        .btn-success { background: var(--success); color: white; }
        .btn-outline { background: white; border-color: var(--border); color: var(--text-main); }
        .btn-outline:hover { background: #f1f5f9; }
        .btn-danger { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
        .btn-sm { padding: 4px 10px; font-size: 0.8rem; }
        .btn-link { background: none; border: none; padding: 0; color: var(--danger); text-decoration: underline; cursor: pointer; }

        /* Forms */
        .form-control, .form-select {
            display: block;
            width: 100%;
            padding: 9px 12px;
            font-size: 0.95rem;
            color: var(--text-main);
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-top: 5px;
        }
        .input-group { display: flex; align-items: stretch; }
        .input-group-text { background: #f1f5f9; padding: 0 12px; border: 1px solid var(--border); border-right: none; display: flex; align-items: center; border-radius: 6px 0 0 6px; }
        .input-group .form-control { border-top-left-radius: 0; border-bottom-left-radius: 0; margin-top: 0; }

        /* Tables */
        .table-responsive { overflow-x: auto; }
        .table { width: 100%; border-collapse: collapse; text-align: left; }
        .table th { background: #f8fafc; padding: 12px 15px; border-bottom: 2px solid var(--border); font-size: 0.75rem; text-transform: uppercase; color: var(--secondary); }
        .table td { padding: 12px 15px; border-bottom: 1px solid var(--border); vertical-align: middle; }
        .table tr:hover { background-color: #f8fafc; }

        /* Alerts */
        .alert { padding: 15px; margin-bottom: 20px; border-radius: 6px; border: 1px solid transparent; display: flex; justify-content: space-between; align-items: center; }
        .alert-success { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
        .alert-danger { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
        .alert-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: inherit; opacity: 0.7; }

        /* Badges */
        .status-badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
        .status-paid { background: #dcfce7; color: #166534; }
        .status-pending { background: #fef9c3; color: #854d0e; }
        .status-overdue { background: #fee2e2; color: #991b1b; }

        /* Dropdown Simple */
        .dropdown { position: relative; display: inline-block; }
        .dropdown-menu { display: none; position: absolute; right: 0; background: white; border: 1px solid var(--border); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-radius: 6px; min-width: 150px; z-index: 50; }
        .dropdown-menu.show { display: block; }
        .dropdown-item { display: block; width: 100%; text-align: left; padding: 8px 16px; background: none; border: none; cursor: pointer; color: var(--text-main); }
        .dropdown-item:hover { background: #f1f5f9; }

        /* Grid System (Simple) */
        .row { display: flex; flex-wrap: wrap; margin: -10px; }
        .col { flex: 1; padding: 10px; }
        .col-3 { width: 25%; padding: 10px; }
        .col-4 { width: 33.333%; padding: 10px; }
        .col-6 { width: 50%; padding: 10px; }
        .col-8 { width: 66.666%; padding: 10px; }
        
        /* Dashboard Specific Grid */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 30px; }

        @media (max-width: 768px) {
            .sidebar { display: none; }
            .main-content { margin-left: 0; width: 100%; }
            .col-3, .col-4, .col-6, .col-8 { width: 100%; }
        }
        
        @media print {
            .no-print, .sidebar { display: none !important; }
            .main-content { margin: 0; padding: 0; }
            .card { border: none; box-shadow: none; }
        }
    </style>
</head>
<body>

<nav class="sidebar">
    <a href="/" class="sidebar-brand">
        <span>📦 NexusBilling</span>
    </a>
    <div style="flex: 1;">
        <a class="nav-link {% if request.path == '/' %}active{% endif %}" href="/">
            📊 Dashboard
        </a>
        <a class="nav-link {% if request.path == '/create_invoice' %}active{% endif %}" href="/create_invoice">
            📄 New Invoice
        </a>
        <a class="nav-link {% if request.path == '/products' %}active{% endif %}" href="/products">
            🏷️ Inventory
        </a>
    </div>
    <div style="border-top: 1px solid #334155; padding-top: 20px;">
         <a class="nav-link" href="#" onclick="alert('Settings module is a placeholder.')">
            ⚙️ Settings
        </a>
    </div>
</nav>

<main class="main-content">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">
            <span>{{ message }}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">×</button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}
</main>

<!-- Minimal Vanilla JS -->
<script>
    // Simple Dropdown Toggle
    document.addEventListener('click', function(e) {
        const isDropdownButton = e.target.matches('[data-toggle="dropdown"]');
        if (!isDropdownButton && e.target.closest('.dropdown') != null) return;
        
        let currentDropdown;
        if (isDropdownButton) {
            currentDropdown = e.target.closest('.dropdown').querySelector('.dropdown-menu');
            currentDropdown.classList.toggle('show');
        }
        
        document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
            if (menu !== currentDropdown) {
                menu.classList.remove('show');
            }
        });
    });
</script>
{% block scripts %}{% endblock %}
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h2 class="fw-bold" style="margin-bottom: 5px;">Executive Dashboard</h2>
        <div class="text-secondary">{{ today }}</div>
    </div>
    <div class="d-flex gap-2">
        <form class="d-flex" action="/" method="GET">
            <input class="form-control" style="margin-top:0; margin-right: 10px;" type="search" name="q" placeholder="Search invoices..." value="{{ request.args.get('q', '') }}">
            <button class="btn btn-primary" type="submit">🔍</button>
        </form>
        <a href="/create_invoice" class="btn btn-primary"><span>+</span> New Invoice</a>
    </div>
</div>

<div class="stats-grid">
    <!-- Revenue Card -->
    <div class="card" style="margin:0;">
        <div class="card-body">
            <div class="text-secondary fw-bold small" style="text-transform: uppercase;">Total Revenue</div>
            <h2 class="text-primary" style="margin: 10px 0;">${{ "%.2f"|format(total_revenue) }}</h2>
            <div class="text-success small">Lifetime earnings</div>
        </div>
    </div>
    <!-- Pending Card -->
    <div class="card" style="margin:0;">
        <div class="card-body">
            <div class="text-secondary fw-bold small" style="text-transform: uppercase;">Pending Payments</div>
            <h2 class="text-warning" style="margin: 10px 0;">${{ "%.2f"|format(pending_amount) }}</h2>
            <div class="text-secondary small">{{ pending_count }} invoices awaiting</div>
        </div>
    </div>
    <!-- Count Card -->
    <div class="card" style="margin:0;">
        <div class="card-body">
            <div class="text-secondary fw-bold small" style="text-transform: uppercase;">Total Invoices</div>
            <h2 style="margin: 10px 0;">{{ invoice_count }}</h2>
            <div class="text-secondary small">Processed</div>
        </div>
    </div>
    <!-- Product Card -->
    <div class="card" style="margin:0;">
        <div class="card-body">
            <div class="text-secondary fw-bold small" style="text-transform: uppercase;">Inventory Items</div>
            <h2 style="margin: 10px 0; color: #0891b2;">{{ product_count }}</h2>
            <div class="text-secondary small">Active SKUs</div>
        </div>
    </div>
</div>

<div class="card">
    <div class="card-header">
        <span>Recent Invoices</span>
        <div class="dropdown">
            <button class="btn btn-outline btn-sm" data-toggle="dropdown">
                Filter Status ▼
            </button>
            <div class="dropdown-menu">
                <a class="dropdown-item" href="/">All</a>
                <a class="dropdown-item" href="/?status=Paid">Paid</a>
                <a class="dropdown-item" href="/?status=Pending">Pending</a>
                <a class="dropdown-item" href="/?status=Overdue">Overdue</a>
            </div>
        </div>
    </div>
    <div class="table-responsive">
        <table class="table">
            <thead>
                <tr>
                    <th>Invoice</th>
                    <th>Date Issued</th>
                    <th>Due Date</th>
                    <th>Client</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th class="text-end">Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for invoice in invoices %}
                <tr>
                    <td class="fw-bold text-primary">#{{ "%05d"|format(invoice.id) }}</td>
                    <td>{{ invoice.date }}</td>
                    <td class="text-secondary">{{ invoice.due_date or '-' }}</td>
                    <td>
                        {{ invoice.customer_name }}
                    </td>
                    <td class="fw-bold">${{ "%.2f"|format(invoice.total_amount) }}</td>
                    <td>
                        <span class="status-badge status-{{ invoice.status.lower() }}">
                            {{ invoice.status }}
                        </span>
                    </td>
                    <td class="text-end">
                        <a href="/invoice/{{ invoice.id }}" class="btn btn-outline btn-sm">View</a>
                        <!-- Delete Form -->
                        <form action="/delete_invoice/{{ invoice.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Permanently delete this invoice?');">
                            <button type="submit" class="btn btn-danger btn-sm" title="Delete">🗑</button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="7" class="text-center" style="padding: 40px;">
                        <div style="font-size: 2rem; opacity: 0.3; margin-bottom: 10px;">🔍</div>
                        No invoices found matching your criteria.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% if pages > 1 %}
    <div class="card-footer text-center">
        <div style="display: inline-flex; gap: 5px;">
            <button class="btn btn-outline btn-sm" disabled>Previous</button>
            <button class="btn btn-primary btn-sm">1</button>
            <button class="btn btn-outline btn-sm">Next</button>
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}
"""

PRODUCTS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="row">
    <!-- Add/Edit Form Area -->
    <div class="col-4">
        <div class="card" style="position: sticky; top: 20px;">
            <div class="card-header">
                <span>🏷️ Manage Product</span>
            </div>
            <div class="card-body">
                <form action="{{ url_for('save_product') }}" method="POST">
                    <input type="hidden" name="id" id="productId" value="">
                    
                    <div class="mb-3">
                        <label class="small fw-bold text-secondary">SKU (OPTIONAL)</label>
                        <input type="text" name="sku" id="productSku" class="form-control" placeholder="e.g. SRV-001">
                    </div>
                    
                    <div class="mb-3">
                        <label class="small fw-bold text-secondary">PRODUCT NAME</label>
                        <input type="text" name="name" id="productName" class="form-control" placeholder="e.g. Annual Maintenance" required>
                    </div>

                    <div class="mb-3">
                        <label class="small fw-bold text-secondary">CATEGORY</label>
                        <select name="category" id="productCategory" class="form-select">
                            <option value="Services">Services</option>
                            <option value="Hardware">Hardware</option>
                            <option value="Software">Software</option>
                            <option value="Consulting">Consulting</option>
                        </select>
                    </div>
                    
                    <div class="mb-4">
                        <label class="small fw-bold text-secondary">UNIT PRICE</label>
                        <div class="input-group">
                            <span class="input-group-text">$</span>
                            <input type="number" step="0.01" name="price" id="productPrice" class="form-control" placeholder="0.00" required>
                        </div>
                    </div>
                    
                    <div style="display: grid; gap: 10px;">
                        <button type="submit" class="btn btn-primary" style="justify-content: center;">Save Product</button>
                        <button type="button" class="btn btn-outline" style="justify-content: center;" onclick="resetForm()">Clear Form</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Product List -->
    <div class="col-8">
        <div class="card">
            <div class="card-header">
                <span>Product Catalog</span>
                <form style="display:flex;">
                    <input class="form-control btn-sm" style="margin:0;" type="search" placeholder="Search products...">
                </form>
            </div>
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>SKU</th>
                            <th>Item Details</th>
                            <th>Category</th>
                            <th>Price</th>
                            <th class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for product in products %}
                        <tr>
                            <td class="text-secondary small" style="font-family: monospace;">{{ product.sku or '--' }}</td>
                            <td>
                                <div class="fw-bold">{{ product.name }}</div>
                            </td>
                            <td><span class="badge" style="background:#f1f5f9; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">{{ product.category or 'General' }}</span></td>
                            <td class="fw-bold">${{ "%.2f"|format(product.price) }}</td>
                            <td class="text-end">
                                <button class="btn btn-outline btn-sm" 
                                        onclick='editProduct({{ product.id }}, {{ product|tojson }})' title="Edit">
                                    ✎
                                </button>
                                <form action="/delete_product/{{ product.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete this product?');">
                                    <button type="submit" class="btn btn-danger btn-sm" title="Delete">
                                        🗑
                                    </button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
    function editProduct(id, data) {
        document.getElementById('productId').value = id;
        document.getElementById('productName').value = data.name;
        document.getElementById('productPrice').value = data.price;
        document.getElementById('productSku').value = data.sku || '';
        document.getElementById('productCategory').value = data.category || 'Services';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function resetForm() {
        document.getElementById('productId').value = '';
        document.getElementById('productName').value = '';
        document.getElementById('productPrice').value = '';
        document.getElementById('productSku').value = '';
    }
</script>
{% endblock %}
"""

CREATE_INVOICE_TEMPLATE = """
{% extends "base" %}
{% block content %}
<form id="invoiceForm" action="/save_invoice" method="POST">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h2 class="fw-bold" style="margin-bottom: 5px;">Create Invoice</h2>
            <p class="text-secondary" style="margin:0;">Fill in the details below to generate a new bill.</p>
        </div>
        <div>
            <a href="/" class="btn btn-outline me-2">Cancel</a>
            <button type="submit" class="btn btn-success">Create & Send ➤</button>
        </div>
    </div>

    <div class="row">
        <!-- Client Info -->
        <div class="col-4">
            <div class="card mb-4">
                <div class="card-header">Client Details</div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="small fw-bold text-secondary">CLIENT NAME *</label>
                        <input type="text" name="customer_name" class="form-control" required placeholder="Company or Name">
                    </div>
                    <div class="mb-3">
                        <label class="small fw-bold text-secondary">CLIENT EMAIL</label>
                        <input type="email" name="customer_email" class="form-control" placeholder="billing@client.com">
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <div style="flex: 1;">
                            <label class="small fw-bold text-secondary">INVOICE DATE</label>
                            <input type="date" name="date" class="form-control" value="{{ today_date }}" required>
                        </div>
                        <div style="flex: 1;">
                            <label class="small fw-bold text-secondary">DUE DATE</label>
                            <input type="date" name="due_date" class="form-control">
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-body">
                    <h5 style="margin-bottom: 10px;">Tax Settings</h5>
                    <div class="input-group">
                        <span class="input-group-text">Tax Rate %</span>
                        <input type="number" id="taxRateInput" name="tax_rate" class="form-control" value="0" min="0" step="0.1" onchange="calculateTotals()">
                    </div>
                </div>
            </div>
        </div>

        <!-- Line Items -->
        <div class="col-8">
            <div class="card" style="min-height: 500px; display: flex; flex-direction: column;">
                <div class="card-header">
                    <span>Items & Services</span>
                    <button type="button" class="btn btn-primary btn-sm" onclick="addItemRow()">
                        + Add Line
                    </button>
                </div>
                <div style="flex: 1;">
                    <table class="table" id="itemsTable">
                        <thead style="background: #f8fafc;">
                            <tr>
                                <th style="width: 40%">Description</th>
                                <th style="width: 15%">Price</th>
                                <th style="width: 15%">Qty</th>
                                <th style="width: 20%">Total</th>
                                <th style="width: 10%"></th>
                            </tr>
                        </thead>
                        <tbody id="itemsBody"></tbody>
                    </table>
                    
                    <div id="emptyState" class="text-center" style="padding: 40px;">
                        <p class="text-secondary">No items added.</p>
                    </div>
                </div>
                
                <!-- Totals Section -->
                <div class="card-footer">
                    <div style="display: flex; justify-content: flex-end;">
                        <div style="width: 300px; text-align: right;">
                            <div class="d-flex justify-content-between mb-3">
                                <span class="text-secondary">Subtotal:</span>
                                <span class="fw-bold" id="displaySubtotal">$0.00</span>
                            </div>
                            <div class="d-flex justify-content-between mb-3">
                                <span class="text-secondary">Tax Amount:</span>
                                <span class="fw-bold" id="displayTax">$0.00</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center" style="border-top: 2px solid #e2e8f0; padding-top: 10px;">
                                <span class="fw-bold text-primary" style="font-size: 1.1rem;">Grand Total:</span>
                                <span class="fw-bold text-primary" style="font-size: 1.3rem;" id="displayGrand">$0.00</span>
                            </div>
                            
                            <!-- Hidden Inputs for Submission -->
                            <input type="hidden" name="subtotal" id="inputSubtotal" value="0">
                            <input type="hidden" name="tax_amount" id="inputTaxAmount" value="0">
                            <input type="hidden" name="total_amount" id="inputTotalAmount" value="0">
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</form>

<script>
    const products = {{ products_json | safe }};
    const tbody = document.getElementById('itemsBody');
    const emptyState = document.getElementById('emptyState');

    function checkEmpty() {
        emptyState.style.display = tbody.children.length === 0 ? 'block' : 'none';
    }

    function addItemRow() {
        const rowId = 'row-' + Date.now();
        let productOptions = '<option value="">Custom Item / Select...</option>';
        products.forEach(p => {
            productOptions += `<option value="${p.id}" data-price="${p.price}" data-name="${p.name}">${p.name} ($${p.price})</option>`;
        });

        const row = document.createElement('tr');
        row.id = rowId;
        row.innerHTML = `
            <td>
                <select class="form-select" style="margin-bottom: 5px;" onchange="autoFillRow('${rowId}', this)">
                    ${productOptions}
                </select>
                <input type="text" name="product_names[]" class="form-control" placeholder="Item Name / Description" required>
            </td>
            <td>
                <div class="input-group">
                    <span class="input-group-text">$</span>
                    <input type="number" step="0.01" name="prices[]" class="form-control price-input" onchange="updateRow('${rowId}')" required value="0">
                </div>
            </td>
            <td>
                <input type="number" name="quantities[]" class="form-control qty-input text-center" value="1" min="1" onchange="updateRow('${rowId}')" required>
            </td>
            <td class="text-end fw-bold row-total" style="vertical-align: middle;">$0.00</td>
            <td class="text-end" style="vertical-align: middle;">
                <button type="button" class="btn-link" onclick="removeRow('${rowId}')">✕</button>
            </td>
        `;
        tbody.appendChild(row);
        checkEmpty();
    }

    function autoFillRow(rowId, selectElem) {
        const row = document.getElementById(rowId);
        const selectedOption = selectElem.options[selectElem.selectedIndex];
        
        if(selectedOption.value) {
            const price = parseFloat(selectedOption.getAttribute('data-price') || 0);
            const name = selectedOption.getAttribute('data-name');
            
            row.querySelector('.price-input').value = price;
            row.querySelector('input[name="product_names[]"]').value = name;
            updateRow(rowId);
        }
    }

    function updateRow(rowId) {
        const row = document.getElementById(rowId);
        const qty = parseFloat(row.querySelector('.qty-input').value || 0);
        const price = parseFloat(row.querySelector('.price-input').value || 0);
        
        const total = qty * price;
        row.querySelector('.row-total').innerText = '$' + total.toFixed(2);
        calculateTotals();
    }

    function removeRow(rowId) {
        document.getElementById(rowId).remove();
        calculateTotals();
        checkEmpty();
    }

    function calculateTotals() {
        let subtotal = 0;
        document.querySelectorAll('#itemsBody tr').forEach(row => {
            const qty = parseFloat(row.querySelector('.qty-input').value || 0);
            const price = parseFloat(row.querySelector('.price-input').value || 0);
            subtotal += (qty * price);
        });

        const taxRate = parseFloat(document.getElementById('taxRateInput').value || 0);
        const taxAmount = subtotal * (taxRate / 100);
        const grandTotal = subtotal + taxAmount;

        // UI Updates
        document.getElementById('displaySubtotal').innerText = '$' + subtotal.toFixed(2);
        document.getElementById('displayTax').innerText = '$' + taxAmount.toFixed(2);
        document.getElementById('displayGrand').innerText = '$' + grandTotal.toFixed(2);

        // Input Updates
        document.getElementById('inputSubtotal').value = subtotal;
        document.getElementById('inputTaxAmount').value = taxAmount;
        document.getElementById('inputTotalAmount').value = grandTotal;
    }
    
    checkEmpty();
    if (products.length > 0) addItemRow(); // Add one default row
</script>
{% endblock %}
"""

VIEW_INVOICE_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div style="max-width: 900px; margin: 0 auto;">
    <!-- Action Toolbar -->
    <div class="d-flex justify-content-between align-items-center mb-4 no-print">
        <a href="/" class="btn btn-outline">← Dashboard</a>
        <div class="d-flex gap-2">
            <!-- Status Toggle Dropdown -->
            <div class="dropdown">
                <button class="btn btn-outline" data-toggle="dropdown">
                    Mark Status: {{ invoice.status }} ▼
                </button>
                <div class="dropdown-menu">
                    <form action="/update_status/{{ invoice.id }}/Paid" method="POST"><button class="dropdown-item">Paid</button></form>
                    <form action="/update_status/{{ invoice.id }}/Pending" method="POST"><button class="dropdown-item">Pending</button></form>
                    <form action="/update_status/{{ invoice.id }}/Overdue" method="POST"><button class="dropdown-item">Overdue</button></form>
                </div>
            </div>
            <button onclick="window.print()" class="btn btn-primary">🖨 Print / PDF</button>
        </div>
    </div>

    <!-- Invoice Paper -->
    <div class="card" style="padding: 40px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);">
        <!-- Header -->
        <div class="d-flex justify-content-between" style="border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 30px;">
            <div>
                <div class="d-flex align-items-center gap-2">
                    <h1 class="fw-bold" style="margin:0; font-size: 2.5rem;">INVOICE</h1>
                    <span class="status-badge status-{{ invoice.status.lower() }}" style="font-size: 0.9rem; border: 1px solid currentColor;">{{ invoice.status }}</span>
                </div>
                <p class="text-secondary" style="margin-top: 5px;">#INV-{{ "%05d"|format(invoice.id) }}</p>
            </div>
            <div class="text-end">
                <h4 class="fw-bold text-primary" style="margin: 0 0 5px 0;">{{ company.name }}</h4>
                <div class="text-secondary small">
                    {{ company.address }}<br>
                    {{ company.phone }}<br>
                    {{ company.email }}
                </div>
            </div>
        </div>

        <!-- Client & Dates -->
        <div class="row mb-4">
            <div class="col-6">
                <p class="small fw-bold text-secondary" style="text-transform: uppercase; margin-bottom: 5px;">Billed To</p>
                <h4 class="fw-bold" style="margin: 0 0 5px 0;">{{ invoice.customer_name }}</h4>
                {% if invoice.customer_email %}<p class="text-secondary">{{ invoice.customer_email }}</p>{% endif %}
            </div>
            <div class="col-6 text-end">
                <div style="margin-bottom: 10px;">
                    <span class="text-secondary small" style="margin-right: 15px;">Date Issued:</span>
                    <span class="fw-bold">{{ invoice.date }}</span>
                </div>
                <div>
                    <span class="text-secondary small" style="margin-right: 15px;">Due Date:</span>
                    <span class="fw-bold text-danger">{{ invoice.due_date or 'Upon Receipt' }}</span>
                </div>
            </div>
        </div>

        <!-- Items -->
        <div style="margin-bottom: 30px;">
            <table class="table">
                <thead style="background: #1e293b; color: white;">
                    <tr>
                        <th style="background: #1e293b; color: white;">Description</th>
                        <th style="background: #1e293b; color: white; text-align: center;">Quantity</th>
                        <th style="background: #1e293b; color: white; text-align: right;">Unit Price</th>
                        <th style="background: #1e293b; color: white; text-align: right;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in items %}
                    <tr>
                        <td class="fw-bold">{{ item.product_name }}</td>
                        <td class="text-center">{{ item.quantity }}</td>
                        <td class="text-end">${{ "%.2f"|format(item.price) }}</td>
                        <td class="text-end fw-bold">${{ "%.2f"|format(item.subtotal) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Summary -->
        <div class="row" style="justify-content: flex-end;">
            <div class="col-4">
                <div class="d-flex justify-content-between mb-2">
                    <span class="text-secondary">Subtotal</span>
                    <span style="font-weight: 500;">${{ "%.2f"|format(invoice.subtotal) }}</span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span class="text-secondary">Tax ({{ invoice.tax_rate }}%)</span>
                    <span class="text-danger" style="font-weight: 500;">+ ${{ "%.2f"|format(invoice.tax_amount) }}</span>
                </div>
                <hr style="border-top: 1px solid #e2e8f0;">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="fw-bold" style="font-size: 1.1rem;">Total Due</span>
                    <span class="fw-bold text-primary" style="font-size: 1.5rem;">${{ "%.2f"|format(invoice.total_amount) }}</span>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center" style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 0.9rem;">
            <p style="margin-bottom: 5px; font-weight: 600;">Thank you for your business!</p>
            <p>Payment is due within 30 days. Please include invoice number on your check.</p>
        </div>
    </div>
</div>
{% endblock %}
"""

# ==========================================
# ROUTES & LOGIC
# ==========================================

# --- Helper for Template Rendering ---


def render_with_base(content_template, **kwargs):
    # Pass common variables to every template
    kwargs['company'] = COMPANY_INFO
    final_html = HTML_TEMPLATE.replace(
        '{% block content %}{% endblock %}', content_template)
    final_html = final_html.replace('{% extends "base" %}', '')
    return render_template_string(final_html, **kwargs)


@app.route('/')
def index():
    query = request.args.get('q', '')
    status_filter = request.args.get('status', '')

    conn = get_db_connection()

    # Base Query
    sql = 'SELECT * FROM invoices'
    params = []
    conditions = []

    if query:
        conditions.append("(customer_name LIKE ? OR id LIKE ?)")
        params.extend([f'%{query}%', f'%{query}%'])

    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += ' ORDER BY id DESC LIMIT 20'

    invoices = conn.execute(sql, params).fetchall()

    # KPI Stats
    total_revenue = conn.execute(
        "SELECT SUM(total_amount) FROM invoices WHERE status != 'Draft'").fetchone()[0] or 0.0
    pending_amount = conn.execute(
        "SELECT SUM(total_amount) FROM invoices WHERE status = 'Pending'").fetchone()[0] or 0.0
    pending_count = conn.execute(
        "SELECT count(*) FROM invoices WHERE status = 'Pending'").fetchone()[0]
    invoice_count = conn.execute("SELECT count(*) FROM invoices").fetchone()[0]
    product_count = conn.execute("SELECT count(*) FROM products").fetchone()[0]

    conn.close()

    return render_with_base(DASHBOARD_TEMPLATE,
                            invoices=invoices,
                            total_revenue=total_revenue,
                            pending_amount=pending_amount,
                            pending_count=pending_count,
                            invoice_count=invoice_count,
                            product_count=product_count,
                            pages=1,
                            today=date.today().strftime("%B %d, %Y"))

# --- PRODUCT MANAGEMENT ---


@app.route('/products')
def products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
    conn.close()
    return render_with_base(PRODUCTS_TEMPLATE, products=products)


@app.route('/save_product', methods=['POST'])
def save_product():
    p_id = request.form.get('id')
    name = request.form['name']
    price = float(request.form['price'])
    sku = request.form.get('sku', '')
    category = request.form.get('category', 'General')

    conn = get_db_connection()
    if p_id:  # Update
        conn.execute('UPDATE products SET name=?, price=?, sku=?, category=? WHERE id=?',
                     (name, price, sku, category, p_id))
        flash('Product updated successfully.', 'success')
    else:  # Create
        conn.execute('INSERT INTO products (name, price, sku, category) VALUES (?, ?, ?, ?)',
                     (name, price, sku, category))
        flash('New product added to catalog.', 'success')

    conn.commit()
    conn.close()
    return redirect(url_for('products'))


@app.route('/delete_product/<int:id>', methods=['POST'])
def delete_product(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Product removed.', 'warning')
    return redirect(url_for('products'))

# --- INVOICE MANAGEMENT ---


@app.route('/create_invoice')
def create_invoice():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    products_list = [{'id': p['id'], 'name': p['name'],
                      'price': p['price'], 'sku': p['sku']} for p in products]
    return render_with_base(CREATE_INVOICE_TEMPLATE, products_json=products_list, today_date=date.today().isoformat())


@app.route('/save_invoice', methods=['POST'])
def save_invoice():
    customer_name = request.form['customer_name']
    customer_email = request.form.get('customer_email')
    inv_date = request.form['date']
    due_date = request.form.get('due_date')

    # Financials
    subtotal = float(request.form['subtotal'])
    tax_rate = float(request.form['tax_rate'])
    tax_amount = float(request.form['tax_amount'])
    total_amount = float(request.form['total_amount'])

    # Line Items
    product_names = request.form.getlist('product_names[]')
    quantities = request.form.getlist('quantities[]')
    prices = request.form.getlist('prices[]')

    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Create Invoice
    cur.execute('''INSERT INTO invoices 
                   (customer_name, customer_email, date, due_date, subtotal, tax_rate, tax_amount, total_amount, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')''',
                (customer_name, customer_email, inv_date, due_date, subtotal, tax_rate, tax_amount, total_amount))
    invoice_id = cur.lastrowid

    # 2. Add Items
    for i in range(len(product_names)):
        p_name = product_names[i]
        qty = int(quantities[i])
        price = float(prices[i])
        item_subtotal = qty * price

        cur.execute('''INSERT INTO invoice_items 
                       (invoice_id, product_name, quantity, price, subtotal) 
                       VALUES (?, ?, ?, ?, ?)''',
                    (invoice_id, p_name, qty, price, item_subtotal))

    conn.commit()
    conn.close()
    flash('Invoice generated successfully.', 'success')
    return redirect(url_for('view_invoice', id=invoice_id))


@app.route('/invoice/<int:id>')
def view_invoice(id):
    conn = get_db_connection()
    invoice = conn.execute(
        'SELECT * FROM invoices WHERE id = ?', (id,)).fetchone()
    items = conn.execute(
        'SELECT * FROM invoice_items WHERE invoice_id = ?', (id,)).fetchall()
    conn.close()

    if not invoice:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('index'))

    return render_with_base(VIEW_INVOICE_TEMPLATE, invoice=invoice, items=items)


@app.route('/update_status/<int:id>/<status>', methods=['POST'])
def update_status(id, status):
    conn = get_db_connection()
    conn.execute('UPDATE invoices SET status = ? WHERE id = ?', (status, id))
    conn.commit()
    conn.close()
    flash(f'Invoice #{id} marked as {status}.', 'success')
    return redirect(url_for('view_invoice', id=id))


@app.route('/delete_invoice/<int:id>', methods=['POST'])
def delete_invoice(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM invoices WHERE id = ?', (id,))
    # Cascade delete handles items usually, but let's be safe for sqlite (PRAGMA foreign_keys=ON needed)
    conn.execute('DELETE FROM invoice_items WHERE invoice_id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Invoice deleted permanently.', 'warning')
    return redirect(url_for('index'))


if __name__ == '__main__':
    print("Starting NexusBilling Enterprise Server...")
    print("Dashboard available at: http://127.0.0.1:5000")
    app.run(debug=True)
