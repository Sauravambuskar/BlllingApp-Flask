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
                      [('Laptop', 999.99), ('Mouse', 25.50), ('Keyboard', 45.00), ('Monitor', 150.00)])
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
    <title>Flask Billing System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background-color: #f8f9fa; }
        .navbar { background-color: #2c3e50; }
        .navbar-brand { color: white !important; font-weight: bold; }
        .card { border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .btn-primary { background-color: #3498db; border-color: #3498db; }
        .btn-success { background-color: #2ecc71; border-color: #2ecc71; }
        .table thead th { background-color: #ecf0f1; border-top: none; }
        .total-section { font-size: 1.5rem; font-weight: bold; text-align: right; color: #2c3e50; }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark mb-4">
    <div class="container">
        <a class="navbar-brand" href="/"><i class="fas fa-file-invoice-dollar"></i> Flask Billing</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav ms-auto">
                <li class="nav-item"><a class="nav-link" href="/">Dashboard</a></li>
                <li class="nav-item"><a class="nav-link" href="/products">Products</a></li>
                <li class="nav-item"><a class="nav-link" href="/create_invoice">New Invoice</a></li>
            </ul>
        </div>
    </div>
</nav>

<div class="container">
    {% if message %}
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    {% endif %}

    {% block content %}{% endblock %}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
{% block scripts %}{% endblock %}
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="row">
    <div class="col-md-4">
        <div class="card text-center p-4">
            <h3><i class="fas fa-box text-primary"></i> {{ product_count }}</h3>
            <p>Products Available</p>
            <a href="/products" class="btn btn-outline-primary btn-sm">Manage</a>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-center p-4">
            <h3><i class="fas fa-file-invoice text-success"></i> {{ invoice_count }}</h3>
            <p>Invoices Generated</p>
            <a href="/create_invoice" class="btn btn-outline-success btn-sm">New Invoice</a>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-center p-4">
            <h3><i class="fas fa-dollar-sign text-warning"></i> ${{ "%.2f"|format(total_revenue) }}</h3>
            <p>Total Revenue</p>
        </div>
    </div>
</div>

<h4 class="mt-4 mb-3">Recent Invoices</h4>
<div class="card p-3">
    <table class="table table-hover">
        <thead>
            <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Customer</th>
                <th>Total</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            {% for invoice in invoices %}
            <tr>
                <td>#{{ invoice.id }}</td>
                <td>{{ invoice.date }}</td>
                <td>{{ invoice.customer_name }}</td>
                <td>${{ "%.2f"|format(invoice.total_amount) }}</td>
                <td><a href="/invoice/{{ invoice.id }}" class="btn btn-sm btn-info text-white">View</a></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""

PRODUCTS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="row">
    <div class="col-md-4">
        <div class="card p-3">
            <h5>Add New Product</h5>
            <form action="/add_product" method="POST">
                <div class="mb-3">
                    <label>Product Name</label>
                    <input type="text" name="name" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label>Price ($)</label>
                    <input type="number" step="0.01" name="price" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-primary w-100">Add Product</button>
            </form>
        </div>
    </div>
    <div class="col-md-8">
        <div class="card p-3">
            <h5>Product List</h5>
            <table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Price</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for product in products %}
                    <tr>
                        <td>{{ product.id }}</td>
                        <td>{{ product.name }}</td>
                        <td>${{ "%.2f"|format(product.price) }}</td>
                        <td>
                            <form action="/delete_product/{{ product.id }}" method="POST" style="display:inline;">
                                <button type="submit" class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
"""

CREATE_INVOICE_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="row">
    <div class="col-md-8 offset-md-2">
        <div class="card p-4">
            <h3 class="mb-4">Create New Invoice</h3>
            
            <form id="invoiceForm" action="/save_invoice" method="POST">
                <div class="mb-3">
                    <label>Customer Name</label>
                    <input type="text" name="customer_name" class="form-control" required placeholder="Enter customer name">
                </div>

                <h5>Items</h5>
                <div class="table-responsive">
                    <table class="table table-bordered" id="itemsTable">
                        <thead>
                            <tr>
                                <th width="50%">Product</th>
                                <th width="15%">Price</th>
                                <th width="15%">Qty</th>
                                <th width="15%">Total</th>
                                <th width="5%"></th>
                            </tr>
                        </thead>
                        <tbody id="itemsBody">
                            <!-- Items will be added here via JS -->
                        </tbody>
                    </table>
                </div>
                
                <button type="button" class="btn btn-secondary mb-3" onclick="addItemRow()">
                    <i class="fas fa-plus"></i> Add Item
                </button>

                <div class="total-section p-3 bg-light rounded">
                    Grand Total: $<span id="grandTotal">0.00</span>
                    <input type="hidden" name="total_amount" id="inputGrandTotal" value="0">
                </div>

                <div class="mt-4 text-end">
                    <a href="/" class="btn btn-light">Cancel</a>
                    <button type="submit" class="btn btn-success btn-lg">Generate Invoice</button>
                </div>
            </form>
        </div>
    </div>
</div>

<script>
    // Pass products from backend to JS
    const products = {{ products_json | safe }};

    function addItemRow() {
        const tbody = document.getElementById('itemsBody');
        const rowId = 'row-' + Date.now();
        
        let productOptions = '<option value="">Select Product...</option>';
        products.forEach(p => {
            productOptions += `<option value="${p.id}" data-price="${p.price}">${p.name} - $${p.price.toFixed(2)}</option>`;
        });

        const row = document.createElement('tr');
        row.id = rowId;
        row.innerHTML = `
            <td>
                <select name="product_ids[]" class="form-control" onchange="updateRow('${rowId}')" required>
                    ${productOptions}
                </select>
            </td>
            <td>
                <input type="text" class="form-control price-display" readonly value="0.00">
                <input type="hidden" name="prices[]" class="price-input">
            </td>
            <td>
                <input type="number" name="quantities[]" class="form-control" value="1" min="1" onchange="updateRow('${rowId}')" required>
            </td>
            <td>
                <span class="row-total fw-bold">$0.00</span>
            </td>
            <td>
                <button type="button" class="btn btn-sm btn-danger" onclick="removeRow('${rowId}')">&times;</button>
            </td>
        `;
        tbody.appendChild(row);
    }

    function updateRow(rowId) {
        const row = document.getElementById(rowId);
        const select = row.querySelector('select');
        const quantity = row.querySelector('input[type="number"]').value;
        const priceDisplay = row.querySelector('.price-display');
        const priceInput = row.querySelector('.price-input');
        const totalSpan = row.querySelector('.row-total');

        // Get price from selected option dataset
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
    }

    function calculateGrandTotal() {
        let total = 0;
        document.querySelectorAll('.row-total').forEach(span => {
            total += parseFloat(span.innerText.replace('$', ''));
        });
        document.getElementById('grandTotal').innerText = total.toFixed(2);
        document.getElementById('inputGrandTotal').value = total;
    }

    // Add one empty row on load
    window.onload = addItemRow;
</script>
{% endblock %}
"""

VIEW_INVOICE_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="row">
    <div class="col-md-8 offset-md-2">
        <div class="card p-5">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h2>INVOICE</h2>
                <div class="text-end">
                    <h5 class="text-muted">#{{ invoice.id }}</h5>
                    <small>{{ invoice.date }}</small>
                </div>
            </div>

            <div class="mb-4">
                <strong>Bill To:</strong><br>
                <h4>{{ invoice.customer_name }}</h4>
            </div>

            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Item</th>
                        <th class="text-center">Qty</th>
                        <th class="text-end">Price</th>
                        <th class="text-end">Subtotal</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in items %}
                    <tr>
                        <td>{{ item.product_name }}</td>
                        <td class="text-center">{{ item.quantity }}</td>
                        <td class="text-end">${{ "%.2f"|format(item.price) }}</td>
                        <td class="text-end">${{ "%.2f"|format(item.subtotal) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <div class="row mt-4">
                <div class="col-6"></div>
                <div class="col-6">
                    <div class="table-responsive">
                        <table class="table">
                            <tr class="table-dark">
                                <th>Total:</th>
                                <td class="text-end h4">${{ "%.2f"|format(invoice.total_amount) }}</td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>

            <div class="text-center mt-5 no-print">
                <button onclick="window.print()" class="btn btn-secondary me-2"><i class="fas fa-print"></i> Print</button>
                <a href="/" class="btn btn-primary">Back to Dashboard</a>
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
    full_template = HTML_TEMPLATE.replace('{% extends "base" %}', '').replace(
        '{% block content %}', '{% block content %}' + content_template + '{% endblock %}')
    # A cleaner way using Jinja's proper extension inheritance in strings requires a loader,
    # but for single-file simplicity, we register the base as a template or just nest strings.
    # To keep it extremely simple without dictionary loaders, we will just patch the strings.
    # Actually, render_template_string supports inheritance if we define the parent in a dict loader
    # OR we can just concatenation for this simple script.

    # Let's use the simplest robust method:
    # We will pass the templates as variables to a master renderer or just overwrite the blocks manually.
    # But standard Jinja inheritance is tricky with just strings unless using a FunctionLoader.

    # STRATEGY: We will just inject the child content into the HTML_TEMPLATE variable manually before rendering.
    final_html = HTML_TEMPLATE.replace(
        '{% block content %}{% endblock %}', content_template)
    # Remove the extends tag from child to avoid syntax error
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
    print("Starting Billing App...")
    print("Go to http://127.0.0.1:5000 in your browser.")
    app.run(debug=True)
