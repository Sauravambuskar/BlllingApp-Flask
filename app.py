import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, jsonify

app = Flask(__name__)
DB_NAME = "billing_system.db"

# ==========================================
# DATABASE CONFIGURATION & HELPERS
# ==========================================


def init_db():
    """Initialize the database with tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Products Table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL
                )''')

    # Invoices Table
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT,
                    date TEXT,
                    total_amount REAL
                )''')

    # Invoice Items Table
    c.execute('''CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER,
                    product_name TEXT,
                    quantity INTEGER,
                    price REAL,
                    subtotal REAL,
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
                )''')

    # Seed some data if empty
    c.execute('SELECT count(*) FROM products')
    if c.fetchone()[0] == 0:
        c.executemany('INSERT INTO products (name, price) VALUES (?, ?)',
                      [('Enterprise Laptop X1', 1299.99), ('Wireless Ergonomic Mouse', 45.50), ('Mechanical Keyboard', 85.00), ('4K Monitor', 350.00)])
        print("Database seeded with default products.")

    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# Initialize DB on startup
init_db()

# ==========================================
# FRONTEND TEMPLATES (HTML/CSS/JS)
# ==========================================

# We store the HTML in a variable to keep this a single-file application.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise Billing Suite</title>
    <!-- Bootstrap 5 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Google Fonts: Inter -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --sidebar-width: 260px;
            --sidebar-bg: #0f172a;
            --sidebar-text: #94a3b8;
            --sidebar-hover: #1e293b;
            --sidebar-active: #3b82f6;
            --bg-color: #f1f5f9;
            --card-bg: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
        }

        body { 
            background-color: var(--bg-color); 
            font-family: 'Inter', sans-serif; 
            color: var(--text-primary);
            overflow-x: hidden;
        }

        /* Sidebar Styles */
        .sidebar {
            width: var(--sidebar-width);
            background-color: var(--sidebar-bg);
            position: fixed;
            top: 0;
            left: 0;
            height: 100vh;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            z-index: 1000;
        }

        .sidebar-brand {
            color: white;
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
        }

        .nav-item {
            margin-bottom: 0.5rem;
        }

        .nav-link {
            color: var(--sidebar-text);
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            font-weight: 500;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .nav-link:hover {
            background-color: var(--sidebar-hover);
            color: white;
        }

        .nav-link.active {
            background-color: var(--sidebar-active);
            color: white;
        }

        .nav-link i { width: 20px; text-align: center; }

        /* Main Content */
        .main-content {
            margin-left: var(--sidebar-width);
            padding: 2rem;
        }

        /* Cards */
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
        }

        .card-header {
            background: transparent;
            border-bottom: 1px solid var(--border-color);
            padding: 1.25rem;
            font-weight: 600;
        }

        /* Tables */
        .table thead th {
            background-color: #f8fafc;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border-color);
            padding: 1rem;
        }
        
        .table td {
            padding: 1rem;
            vertical-align: middle;
            color: var(--text-primary);
            border-bottom: 1px solid var(--border-color);
        }

        /* Buttons */
        .btn-primary {
            background-color: var(--sidebar-active);
            border-color: var(--sidebar-active);
            padding: 0.6rem 1.2rem;
            font-weight: 500;
        }
        
        .btn-primary:hover {
            background-color: #2563eb;
        }

        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            background-color: #dcfce7;
            color: #166534;
        }

        /* Invoice Sheet Look */
        .invoice-sheet {
            background: white;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 40px;
            min-height: 800px;
        }

        /* Utilities */
        .text-label {
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-bottom: 0.25rem;
        }
    </style>
</head>
<body>

<!-- Sidebar -->
<nav class="sidebar">
    <a href="/" class="sidebar-brand">
        <i class="fas fa-layer-group text-primary"></i> 
        <span>NexusBilling</span>
    </a>
    <div class="nav flex-column">
        <div class="nav-item">
            <a class="nav-link {% if request.path == '/' %}active{% endif %}" href="/">
                <i class="fas fa-chart-pie"></i> Dashboard
            </a>
        </div>
        <div class="nav-item">
            <a class="nav-link {% if request.path == '/create_invoice' %}active{% endif %}" href="/create_invoice">
                <i class="fas fa-plus-circle"></i> New Invoice
            </a>
        </div>
        <div class="nav-item">
            <a class="nav-link {% if request.path == '/products' %}active{% endif %}" href="/products">
                <i class="fas fa-box"></i> Products
            </a>
        </div>
        <div class="mt-auto">
            <a class="nav-link" href="#" onclick="alert('Settings not implemented')">
                <i class="fas fa-cog"></i> Settings
            </a>
        </div>
    </div>
</nav>

<!-- Main Content -->
<main class="main-content">
    {% if message %}
        <div class="alert alert-success alert-dismissible fade show mb-4" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    {% endif %}

    {% block content %}{% endblock %}
</main>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
{% block scripts %}{% endblock %}
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h2 class="h3 fw-bold mb-1">Dashboard Overview</h2>
        <p class="text-secondary mb-0">Welcome back, Admin.</p>
    </div>
    <a href="/create_invoice" class="btn btn-primary"><i class="fas fa-plus me-2"></i>Create Invoice</a>
</div>

<!-- Stats Cards -->
<div class="row g-4 mb-5">
    <div class="col-md-4">
        <div class="card h-100 border-0 shadow-sm">
            <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div class="text-secondary fw-medium">Total Revenue</div>
                    <div class="bg-primary bg-opacity-10 p-2 rounded text-primary">
                        <i class="fas fa-dollar-sign"></i>
                    </div>
                </div>
                <h3 class="fw-bold mb-0">${{ "%.2f"|format(total_revenue) }}</h3>
                <small class="text-success"><i class="fas fa-arrow-up me-1"></i> +2.5% vs last month</small>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card h-100 border-0 shadow-sm">
            <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div class="text-secondary fw-medium">Total Invoices</div>
                    <div class="bg-success bg-opacity-10 p-2 rounded text-success">
                        <i class="fas fa-file-invoice"></i>
                    </div>
                </div>
                <h3 class="fw-bold mb-0">{{ invoice_count }}</h3>
                <small class="text-secondary">Across all time</small>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card h-100 border-0 shadow-sm">
            <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div class="text-secondary fw-medium">Active Products</div>
                    <div class="bg-warning bg-opacity-10 p-2 rounded text-warning">
                        <i class="fas fa-box"></i>
                    </div>
                </div>
                <h3 class="fw-bold mb-0">{{ product_count }}</h3>
                <small class="text-secondary">In catalog</small>
            </div>
        </div>
    </div>
</div>

<!-- Recent Invoices Table -->
<div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Recent Transactions</h5>
        <button class="btn btn-sm btn-outline-secondary">Export CSV</button>
    </div>
    <div class="table-responsive">
        <table class="table table-hover mb-0">
            <thead>
                <tr>
                    <th>Invoice ID</th>
                    <th>Date Issued</th>
                    <th>Customer</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th class="text-end">Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for invoice in invoices %}
                <tr>
                    <td><span class="fw-bold text-primary">#INV-{{ "%05d"|format(invoice.id) }}</span></td>
                    <td>{{ invoice.date }}</td>
                    <td>
                        <div class="d-flex align-items-center">
                            <div class="bg-light rounded-circle p-2 me-2 text-secondary">
                                <i class="fas fa-user-circle"></i>
                            </div>
                            {{ invoice.customer_name }}
                        </div>
                    </td>
                    <td class="fw-semibold">${{ "%.2f"|format(invoice.total_amount) }}</td>
                    <td><span class="status-badge">Paid</span></td>
                    <td class="text-end">
                        <a href="/invoice/{{ invoice.id }}" class="btn btn-sm btn-light border">View Details</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""

PRODUCTS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="row g-4">
    <!-- Add Product Form -->
    <div class="col-md-4">
        <div class="card h-100">
            <div class="card-header">
                <h5 class="mb-0">Add New Product</h5>
            </div>
            <div class="card-body p-4">
                <form action="/add_product" method="POST">
                    <div class="mb-3">
                        <label class="form-label text-secondary small">Product Name</label>
                        <input type="text" name="name" class="form-control" placeholder="e.g. Consultation Fee" required>
                    </div>
                    <div class="mb-4">
                        <label class="form-label text-secondary small">Unit Price ($)</label>
                        <div class="input-group">
                            <span class="input-group-text">$</span>
                            <input type="number" step="0.01" name="price" class="form-control" placeholder="0.00" required>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="fas fa-plus me-2"></i> Add to Catalog
                    </button>
                </form>
            </div>
        </div>
    </div>

    <!-- Product List -->
    <div class="col-md-8">
        <div class="card h-100">
            <div class="card-header">
                <h5 class="mb-0">Product Catalog</h5>
            </div>
            <div class="table-responsive">
                <table class="table table-hover mb-0 align-middle">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Product Name</th>
                            <th>Unit Price</th>
                            <th class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for product in products %}
                        <tr>
                            <td class="text-secondary">#{{ "%03d"|format(product.id) }}</td>
                            <td class="fw-medium">{{ product.name }}</td>
                            <td>${{ "%.2f"|format(product.price) }}</td>
                            <td class="text-end">
                                <form action="/delete_product/{{ product.id }}" method="POST" style="display:inline;">
                                    <button type="submit" class="btn btn-sm btn-outline-danger border-0" onclick="return confirm('Are you sure?')">
                                        <i class="fas fa-trash-alt"></i>
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
{% endblock %}
"""

CREATE_INVOICE_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="container-fluid px-0">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="h3 fw-bold">New Invoice</h2>
        <a href="/" class="btn btn-outline-secondary">Cancel</a>
    </div>

    <form id="invoiceForm" action="/save_invoice" method="POST">
        <div class="row g-4">
            <!-- Customer Details -->
            <div class="col-lg-4">
                <div class="card mb-4">
                    <div class="card-header">Client Details</div>
                    <div class="card-body">
                        <div class="mb-3">
                            <label class="form-label text-secondary small">Customer / Company Name</label>
                            <input type="text" name="customer_name" class="form-control form-control-lg" required placeholder="Enter client name...">
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-secondary small">Billing Address (Optional)</label>
                            <textarea class="form-control" rows="3" placeholder="Street, City, Zip..."></textarea>
                        </div>
                    </div>
                </div>
                
                <div class="card bg-primary text-white border-0">
                    <div class="card-body p-4">
                        <h6 class="text-white-50 text-uppercase small ls-1">Estimated Total</h6>
                        <h2 class="display-4 fw-bold mb-0">$<span id="grandTotalDisplay">0.00</span></h2>
                        <input type="hidden" name="total_amount" id="inputGrandTotal" value="0">
                    </div>
                </div>
            </div>

            <!-- Line Items -->
            <div class="col-lg-8">
                <div class="card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>Line Items</span>
                        <button type="button" class="btn btn-sm btn-primary" onclick="addItemRow()">
                            <i class="fas fa-plus me-1"></i> Add Item
                        </button>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table mb-0" id="itemsTable">
                                <thead class="bg-light">
                                    <tr>
                                        <th style="width: 40%">Item Description</th>
                                        <th style="width: 15%">Unit Price</th>
                                        <th style="width: 15%">Qty</th>
                                        <th style="width: 20%">Total</th>
                                        <th style="width: 10%"></th>
                                    </tr>
                                </thead>
                                <tbody id="itemsBody">
                                    <!-- Items via JS -->
                                </tbody>
                            </table>
                        </div>
                        
                        <!-- Empty State -->
                        <div id="emptyState" class="text-center py-5">
                            <i class="fas fa-basket-shopping text-secondary opacity-25 fa-3x mb-3"></i>
                            <p class="text-secondary">No items added yet.</p>
                            <button type="button" class="btn btn-outline-primary btn-sm" onclick="addItemRow()">Add First Item</button>
                        </div>
                    </div>
                    <div class="card-footer bg-white p-3 text-end">
                        <button type="submit" class="btn btn-success btn-lg px-5">
                            <i class="fas fa-check-circle me-2"></i> Generate Invoice
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </form>
</div>

<script>
    const products = {{ products_json | safe }};
    const tbody = document.getElementById('itemsBody');
    const emptyState = document.getElementById('emptyState');

    function checkEmpty() {
        if (tbody.children.length === 0) {
            emptyState.style.display = 'block';
        } else {
            emptyState.style.display = 'none';
        }
    }

    function addItemRow() {
        const rowId = 'row-' + Date.now();
        let productOptions = '<option value="">Select Item...</option>';
        products.forEach(p => {
            productOptions += `<option value="${p.id}" data-price="${p.price}">${p.name}</option>`;
        });

        const row = document.createElement('tr');
        row.id = rowId;
        row.innerHTML = `
            <td>
                <select name="product_ids[]" class="form-select" onchange="updateRow('${rowId}')" required>
                    ${productOptions}
                </select>
            </td>
            <td>
                <div class="input-group input-group-sm">
                    <span class="input-group-text border-0 bg-light">$</span>
                    <input type="text" class="form-control border-0 bg-light price-display text-end" readonly value="0.00">
                    <input type="hidden" name="prices[]" class="price-input">
                </div>
            </td>
            <td>
                <input type="number" name="quantities[]" class="form-control form-control-sm text-center" value="1" min="1" onchange="updateRow('${rowId}')" required>
            </td>
            <td class="text-end fw-bold align-middle row-total">$0.00</td>
            <td class="text-end">
                <button type="button" class="btn btn-link text-danger p-0" onclick="removeRow('${rowId}')">
                    <i class="fas fa-times"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
        checkEmpty();
    }

    function updateRow(rowId) {
        const row = document.getElementById(rowId);
        const select = row.querySelector('select');
        const quantity = row.querySelector('input[type="number"]').value;
        const priceDisplay = row.querySelector('.price-display');
        const priceInput = row.querySelector('.price-input');
        const totalSpan = row.querySelector('.row-total');

        const selectedOption = select.options[select.selectedIndex];
        const price = parseFloat(selectedOption.getAttribute('data-price') || 0);

        priceDisplay.value = price.toFixed(2);
        priceInput.value = price;

        const total = price * quantity;
        totalSpan.innerText = '$' + total.toFixed(2);

        calculateGrandTotal();
    }

    function removeRow(rowId) {
        document.getElementById(rowId).remove();
        calculateGrandTotal();
        checkEmpty();
    }

    function calculateGrandTotal() {
        let total = 0;
        document.querySelectorAll('.row-total').forEach(span => {
            total += parseFloat(span.innerText.replace('$', ''));
        });
        document.getElementById('grandTotalDisplay').innerText = total.toFixed(2);
        document.getElementById('inputGrandTotal').value = total;
    }
    
    // Initial Load
    checkEmpty();
    if (products.length > 0) addItemRow();
</script>
{% endblock %}
"""

VIEW_INVOICE_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-9">
        <div class="d-flex justify-content-between mb-4 no-print">
            <a href="/" class="btn btn-outline-secondary"><i class="fas fa-arrow-left me-2"></i>Back</a>
            <button onclick="window.print()" class="btn btn-primary"><i class="fas fa-print me-2"></i>Print Invoice</button>
        </div>

        <!-- Paper Sheet -->
        <div class="invoice-sheet">
            <div class="row mb-5">
                <div class="col-6">
                    <h1 class="fw-bold text-primary mb-2">INVOICE</h1>
                    <p class="text-secondary">#INV-{{ "%05d"|format(invoice.id) }}</p>
                </div>
                <div class="col-6 text-end">
                    <h4 class="fw-bold">NexusBilling Inc.</h4>
                    <p class="text-secondary small mb-0">123 Corporate Blvd</p>
                    <p class="text-secondary small mb-0">Tech City, CA 90210</p>
                    <p class="text-secondary small">billing@nexus.com</p>
                </div>
            </div>

            <div class="row mb-5">
                <div class="col-6">
                    <p class="text-uppercase text-secondary small fw-bold mb-1">Bill To</p>
                    <h5 class="fw-bold">{{ invoice.customer_name }}</h5>
                    <p class="text-secondary small">Client ID: C-{{ "%04d"|format(invoice.id) }}</p>
                </div>
                <div class="col-6 text-end">
                    <p class="text-uppercase text-secondary small fw-bold mb-1">Invoice Date</p>
                    <h5 class="fw-bold">{{ invoice.date }}</h5>
                </div>
            </div>

            <table class="table table-striped mb-5">
                <thead class="table-dark">
                    <tr>
                        <th class="ps-4">Description</th>
                        <th class="text-center">Quantity</th>
                        <th class="text-end">Unit Price</th>
                        <th class="text-end pe-4">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in items %}
                    <tr>
                        <td class="ps-4 fw-medium">{{ item.product_name }}</td>
                        <td class="text-center">{{ item.quantity }}</td>
                        <td class="text-end text-secondary">${{ "%.2f"|format(item.price) }}</td>
                        <td class="text-end fw-bold pe-4">${{ "%.2f"|format(item.subtotal) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <div class="row">
                <div class="col-7">
                    <p class="fw-bold mb-1">Payment Instructions</p>
                    <p class="text-secondary small">Please make checks payable to NexusBilling Inc.<br>Bank Transfer: BOFA US32 1230 0000 1234</p>
                </div>
                <div class="col-5">
                    <div class="d-flex justify-content-between mb-2">
                        <span class="text-secondary">Subtotal</span>
                        <span class="fw-medium">${{ "%.2f"|format(invoice.total_amount) }}</span>
                    </div>
                    <div class="d-flex justify-content-between mb-3">
                        <span class="text-secondary">Tax (0%)</span>
                        <span class="fw-medium">$0.00</span>
                    </div>
                    <hr>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="fw-bold h5 mb-0">Total Due</span>
                        <span class="fw-bold h3 text-primary mb-0">${{ "%.2f"|format(invoice.total_amount) }}</span>
                    </div>
                </div>
            </div>
            
            <div class="mt-5 pt-5 text-center text-secondary small border-top">
                <p class="mb-0">Thank you for your business!</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# ==========================================
# FLASK ROUTES
# ==========================================

# Helper to render templates with base


def render_with_base(content_template, **kwargs):
    # STRATEGY: Inject the child content into the HTML_TEMPLATE variable.
    final_html = HTML_TEMPLATE.replace(
        '{% block content %}{% endblock %}', content_template)
    final_html = final_html.replace('{% extends "base" %}', '')
    return render_template_string(final_html, **kwargs)


@app.route('/')
def index():
    conn = get_db_connection()
    invoices = conn.execute(
        'SELECT * FROM invoices ORDER BY id DESC LIMIT 10').fetchall()
    product_count = conn.execute('SELECT count(*) FROM products').fetchone()[0]
    invoice_count = conn.execute('SELECT count(*) FROM invoices').fetchone()[0]
    total_revenue = conn.execute(
        'SELECT SUM(total_amount) FROM invoices').fetchone()[0] or 0.0
    conn.close()

    return render_with_base(DASHBOARD_TEMPLATE,
                            invoices=invoices,
                            product_count=product_count,
                            invoice_count=invoice_count,
                            total_revenue=total_revenue)


@app.route('/products')
def products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_with_base(PRODUCTS_TEMPLATE, products=products)


@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    price = float(request.form['price'])

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO products (name, price) VALUES (?, ?)', (name, price))
    conn.commit()
    conn.close()
    return redirect(url_for('products'))


@app.route('/delete_product/<int:id>', methods=['POST'])
def delete_product(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('products'))


@app.route('/create_invoice')
def create_invoice():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()

    # Convert row objects to dict for JSON serialization
    products_list = [{'id': p['id'], 'name': p['name'],
                      'price': p['price']} for p in products]

    return render_with_base(CREATE_INVOICE_TEMPLATE, products_json=products_list)


@app.route('/save_invoice', methods=['POST'])
def save_invoice():
    customer_name = request.form['customer_name']
    total_amount = float(request.form['total_amount'])
    product_ids = request.form.getlist('product_ids[]')
    quantities = request.form.getlist('quantities[]')
    prices = request.form.getlist('prices[]')

    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Create Invoice
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cur.execute('INSERT INTO invoices (customer_name, date, total_amount) VALUES (?, ?, ?)',
                (customer_name, date_str, total_amount))
    invoice_id = cur.lastrowid

    # 2. Add Items
    for i in range(len(product_ids)):
        if product_ids[i]:  # Check if product selected
            p_id = int(product_ids[i])
            qty = int(quantities[i])
            price = float(prices[i])
            subtotal = qty * price

            # Get product name for historical record
            p_name = cur.execute(
                'SELECT name FROM products WHERE id = ?', (p_id,)).fetchone()[0]

            cur.execute('''INSERT INTO invoice_items 
                           (invoice_id, product_name, quantity, price, subtotal) 
                           VALUES (?, ?, ?, ?, ?)''',
                        (invoice_id, p_name, qty, price, subtotal))

    conn.commit()
    conn.close()

    return redirect(url_for('view_invoice', id=invoice_id))


@app.route('/invoice/<int:id>')
def view_invoice(id):
    conn = get_db_connection()
    invoice = conn.execute(
        'SELECT * FROM invoices WHERE id = ?', (id,)).fetchone()
    items = conn.execute(
        'SELECT * FROM invoice_items WHERE invoice_id = ?', (id,)).fetchall()
    conn.close()
    return render_with_base(VIEW_INVOICE_TEMPLATE, invoice=invoice, items=items)


if __name__ == '__main__':
    print("Starting Enterprise Billing App...")
    print("Go to http://127.0.0.1:5000 in your browser.")
    app.run(debug=True)
