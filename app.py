from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
import io

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------------ MODELS ------------------------
bom_stock = db.Table('bom_stock',
    db.Column('bom_id', db.Integer, db.ForeignKey('bill_of_material.id')),
    db.Column('stock_id', db.Integer, db.ForeignKey('stock.id'))
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class ManufacturingOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    availability = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="In Progress")
    quantity = db.Column(db.Integer, nullable=False)
    placed_date = db.Column(db.Date, nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    bom_id = db.Column(db.Integer, db.ForeignKey('bill_of_material.id'))
    work_orders = db.relationship('WorkOrder', backref='order', lazy=True)


class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('manufacturing_order.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(50), default="Planned")
    comments = db.Column(db.Text)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)

class WorkCenter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cost_per_hour = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    downtime = db.Column(db.Float, default=0)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(50))  

class BillOfMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    components = db.relationship('Stock', secondary=bom_stock, backref='boms')

# ------------------------ LOGIN ------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please login.")
            return redirect(url_for('login'))

        new_user = User(username=username, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("User registered successfully!")
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ------------------------ DASHBOARD ------------------------
@app.route('/')
@login_required
def dashboard():
    orders = ManufacturingOrder.query.all()
    total_orders = len(orders)
    in_progress = len([o for o in orders if o.status=="In Progress"])
    completed = len([o for o in orders if o.status=="Done"])
    delayed = len([o for o in orders if o.status=="Planned" and o.deadline < datetime.now().date()])
    return render_template('dashboard.html', orders=orders,
                           total_orders=total_orders, in_progress=in_progress,
                           completed=completed, delayed=delayed)

# ------------------------ MANUFACTURING ORDERS ------------------------
@app.route('/orders', methods=['GET','POST'])
@login_required
def orders():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        product_name = request.form['product_name']
        availability = request.form['availability']
        status = request.form['status']
        quantity = int(request.form['quantity'])
        placed_date = datetime.strptime(request.form['placed_date'], "%Y-%m-%d")
        delivery_date = datetime.strptime(request.form['delivery_date'], "%Y-%m-%d")
        
        new_order = ManufacturingOrder(
            customer_name=customer_name,
            product_name=product_name,
            availability=availability,
            status=status,
            quantity=quantity,
            placed_date=placed_date,
            delivery_date=delivery_date
        )
        db.session.add(new_order)
        db.session.commit()
        flash("Order placed successfully!")
    
    all_orders = ManufacturingOrder.query.all()
    return render_template('orders.html', orders=all_orders)
# ------------------------ EDIT ORDER ------------------------
@app.route('/orders/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_order(id):
    order = ManufacturingOrder.query.get_or_404(id)

    if request.method == 'POST':
        order.customer_name = request.form['customer_name']
        order.product_name = request.form['product_name']
        order.availability = request.form['availability']
        order.status = request.form['status']
        order.quantity = int(request.form['quantity'])
        order.placed_date = datetime.strptime(request.form['placed_date'], "%Y-%m-%d")
        order.delivery_date = datetime.strptime(request.form['delivery_date'], "%Y-%m-%d")

        db.session.commit()
        flash("Order updated successfully!")
        return redirect(url_for('orders'))

    return render_template('edit_order.html', order=order)

@app.route('/orders/delete/<int:id>')
@login_required
def delete_order(id):
    order = ManufacturingOrder.query.get(id)
    db.session.delete(order)
    db.session.commit()
    flash("Order deleted!")
    return redirect(url_for('orders'))

@app.route('/export_orders')
@login_required
def export_orders():
    orders = ManufacturingOrder.query.all()
    data = [{'ID': o.id, 'Name': o.name, 'Status': o.status, 'Deadline': o.deadline} for o in orders]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="orders.xlsx", as_attachment=True)

# ------------------------ WORK ORDERS ------------------------
@app.route('/work_orders', methods=['GET','POST'])
@login_required
def work_orders():
    if request.method == 'POST':
        order_id = int(request.form['order_id'])
        assigned_to = int(request.form['assigned_to'])
        status = request.form['status']
        comments = request.form['comments']
        new_wo = WorkOrder(order_id=order_id, assigned_to=assigned_to, status=status, comments=comments)
        db.session.add(new_wo)
        db.session.commit()
        flash("Work order added!")
    all_wos = WorkOrder.query.all()
    return render_template('work_orders.html', work_orders=all_wos)

@app.route('/work_orders/delete/<int:id>')
@login_required
def delete_work_order(id):
    wo = WorkOrder.query.get(id)
    db.session.delete(wo)
    db.session.commit()
    flash("Work order deleted!")
    return redirect(url_for('work_orders'))

# ------------------------ WORK CENTERS ------------------------
@app.route('/work_centers', methods=['GET','POST'])
@login_required
def work_centers():
    if request.method == 'POST':
        name = request.form['name']
        cost_per_hour = float(request.form['cost_per_hour'])
        capacity = int(request.form['capacity'])
        new_wc = WorkCenter(name=name, cost_per_hour=cost_per_hour, capacity=capacity)
        db.session.add(new_wc)
        db.session.commit()
        flash("Work Center added!")
    all_wcs = WorkCenter.query.all()
    return render_template('work_centers.html', work_centers=all_wcs)

@app.route('/work_centers/delete/<int:id>')
@login_required
def delete_work_center(id):
    wc = WorkCenter.query.get(id)
    db.session.delete(wc)
    db.session.commit()
    flash("Work Center deleted!")
    return redirect(url_for('work_centers'))

# ------------------------ STOCK ------------------------
@app.route('/stock', methods=['GET','POST'])
@login_required
def stock():
    if request.method == 'POST':
        name = request.form['name']
        quantity = int(request.form['quantity'])
        type_ = request.form['type']
        new_stock = Stock(name=name, quantity=quantity, type=type_)
        db.session.add(new_stock)
        db.session.commit()
        flash("Stock item added!")
    all_stocks = Stock.query.all()
    return render_template('stock.html', stocks=all_stocks)

@app.route('/stock/delete/<int:id>')
@login_required
def delete_stock(id):
    st = Stock.query.get(id)
    db.session.delete(st)
    db.session.commit()
    flash("Stock item deleted!")
    return redirect(url_for('stock'))

# ------------------------ BILL OF MATERIAL ------------------------
@app.route('/bom', methods=['GET','POST'])
@login_required
def bom():
    if request.method == 'POST':
        name = request.form['name']
        component_ids = [int(i.strip()) for i in request.form['components'].split(',')]
        components = Stock.query.filter(Stock.id.in_(component_ids)).all()
        new_bom = BillOfMaterial(name=name)
        new_bom.components = components
        db.session.add(new_bom)
        db.session.commit()
        flash("BOM added!")
    all_boms = BillOfMaterial.query.all()
    return render_template('bom.html', boms=all_boms)

@app.route('/bom/delete/<int:id>')
@login_required
def delete_bom(id):
    b = BillOfMaterial.query.get(id)
    db.session.delete(b)
    db.session.commit()
    flash("BOM deleted!")
    return redirect(url_for('bom'))

# ------------------------ PROFILE ------------------------
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# ------------------------ RUN ------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # <-- This creates all tables
    app.run(debug=True)
