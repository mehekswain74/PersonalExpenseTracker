from flask import Flask,Response,jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import UserMixin,LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime,timedelta
from flask_mail import Mail, Message
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import logging
import pandas as pd
import plotly.express as px
from sqlalchemy.orm import relationship
from collections import defaultdict
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from sqlalchemy.sql import extract
import io


app=Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql://root:12345@localhost/personaltracker'
app.secret_key = 'the random string'
db = SQLAlchemy(app)

migrate = Migrate(app, db)
app.static_folder = 'static'
#-------------Flask-Login----------
login_manager = LoginManager(app)
login_manager.login_view = 'login'
#For secure verification of passwords---------------------->
bcrypt = Bcrypt(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = '587'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '21cse316.mehekswain@giet.edu'
app.config['MAIL_PASSWORD'] = '##mehek21'
app.config['MAIL_DEFAULT_SENDER'] = '21cse316.mehekswain@giet.edu'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_DEBUG'] = True

mail = Mail(app)




#Model for Users---------------------------------------------------->
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password



@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Model for categories
class Categories(db.Model):
    category_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    cat_img=db.Column(db.String(1255), nullable=True)
    spending_limit= db.Column(db.Integer, nullable=True)
    

    def __init__(self, user_id, name, cat_img,spending_limit):
        self.user_id = user_id
        self.name = name
        self.cat_img=cat_img
        self.spending_limit=spending_limit
        
# Model for income............................................
class Income(db.Model):
    income_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    user = db.relationship('Users', backref='income')
    def __init__(self, user_id, amount, source, date):
        self.user_id = user_id
        self.amount = amount
        self.source = source
        self.date = date

#Model for expense----------------------------------------->
class Expenses(db.Model):
    expense_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    date = db.Column(db.Date, nullable=False)
    vendor=db.Column(db.String(100))
    pay_method=db.Column(db.String(255))
    category = relationship("Categories")

    def __init__(self, user_id, category_id, amount, description, date, vendor, pay_method):
        self.user_id = user_id
        self.category_id = category_id
        self.amount = amount
        self.description = description
        self.date = date
        self.vendor = vendor
        self.pay_method=pay_method


class Notification(db.Model):
    notify_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.message}>'

def get_monthly_expenses_data(year, month):
    expenses = Expenses.query.filter(
        extract('year', Expenses.date) == year,
        extract('month', Expenses.date) == month
    ).all()

    # Calculate total expenses for each category
    expenses_data = {}
    for expense in expenses:
        category_name = expense.category.name  # Assuming Expenses has a relationship with Categories
        if category_name not in expenses_data:
            expenses_data[category_name] = 0
        expenses_data[category_name] += expense.amount

    return expenses_data


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Users.query.filter_by(username=username).first()
        
        if user and user.password == password:
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Please check your username and password.', 'error')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
   
    if request.method=='POST':
        username=request.form['uname']
        password = request.form['pass']
        password_confirm = request.form['repass']
        email=request.form['email']
        #check for existing users
        existing_user = Users.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different username.', 'error')
        elif password != password_confirm:
            flash('Passwords do not match. Please re-enter your password.', 'error')
        else:
            # Create a new user and set their password
            new_user = Users(username=username,email=email,password=password)
            
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful. You can now log in.', 'success')
            return redirect(url_for('login'))

    return render_template('signup.html')

@login_required
@app.route('/dashboard')
def dashboard():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    if 5 <= now.hour < 12:
        greeting = "Good morning"
    elif 12 <= now.hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    
    today=datetime.today()
    today_str = today.strftime('%Y-%m-%d')
    user_id = current_user.id 
    expenses=Expenses.query.filter_by(user_id=user_id, date=today_str).all()
    income_amount=Income.query.filter_by(user_id=user_id).first()
    user_income = income_amount.amount if income_amount else 0
    
    
    user_balance=get_user_balance(user_id)
    today_expenses = Expenses.query.filter_by(user_id=user_id, date=today_str).all()
    #For displaying notification 
    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.timestamp.desc()).limit(20).all()
    category_expenses = {}
    for expense in today_expenses:
        category = expense.category.name
        amount = expense.amount
    
        if category in category_expenses:
            category_expenses[category] += amount
        else:
            category_expenses[category] = amount
    category_expenses_list = [{'category': key, 'amount': value} for key, value in category_expenses.items()]
    plot_html = ''
    if not category_expenses_list:
        fig=px.pie(
            names=['No Expenses'],
            values=[1],
            title='Today\'s Expenses by Category (No Data)',
            hole=0.4
        )
        fig.update_traces(hoverinfo='none')
    else:
        fig = px.pie(category_expenses_list, names='category', values='amount', title='Today\'s Expenses by Category')
        fig.update_traces(hovertemplate='%{label}: ₹%{value:.2f}')
        fig.update_traces(hole=0.4)
    fig.update_layout(width=400, height=300)
    fig.update_layout(margin=dict(l=50, r=50, b=50, t=50),template='plotly_dark')
    plot_html = fig.to_html(full_html=False)



    
    return render_template('dashboard.html', today_expenses=today_expenses,greeting=greeting,current_time=current_time,user_income=user_income,user_balance=user_balance,username=current_user.username,expenses=expenses, category_expenses=category_expenses, plot_html=plot_html,notifications=notifications)

@app.route('/category/add', methods=['GET','POST'])
@login_required
def add_category():
    all_categories=Categories.query.all()
    if request.method == 'POST':
        
        category_name = request.form['categoryName']
        category_icon = request.form['categoryIcon']
        category_limit = request.form['categoryLimit']
        
        if not category_name:
            flash('Category name is required', 'error')
        else:
            new_category = Categories(name=category_name,cat_img=category_icon,spending_limit=category_limit, user_id=current_user.id)
            db.session.add(new_category)
            db.session.commit()
            return render_template('add_categories.html', message='Category added successfully',categories=all_categories)
    return render_template('add_categories.html', message='Invalid request',categories=all_categories)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

def get_user_balance(user_id):
    total_expenses = Expenses.query.filter_by(user_id=user_id).with_entities(db.func.sum(Expenses.amount)).scalar() or 0.0
    total_income = Income.query.filter_by(user_id=user_id).with_entities(db.func.sum(Income.amount)).scalar() or 0.0
    
    balance = total_income - total_expenses
    
    return balance
# Route to add a new expense
@app.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    user_id = current_user.id 
    if request.method == 'POST':
        user_categories = Categories.query.filter_by(user_id=current_user.id).all()
        category_id=Categories.category_id
        user_balance=get_user_balance(user_id)

        
        category_id = request.form['category_id']
        amount = float(request.form['amount'])
        description = request.form['description']
        date = request.form['date']
        vendor=request.form['vendor']
        pay_method=request.form['paymentmethod']
        
        category=Categories.query.get(category_id)
        if user_balance>=amount:
            # Create a new expense record in the database
            if category:
                if amount > category.spending_limit:
                    send_limit_exceeded_email(category, amount)
                    flash(f'Expense amount exceeded the limit for {category.name}. Email notification sent.', 'warning')
                    notification=Notification(user_id=user_id,message=f"Expense amount exceeded the limit for {category.name}.")
                    db.session.add(notification)
                    db.session.commit()
            new_expense = Expenses(user_id, category_id, amount, description, date, vendor, pay_method)
            db.session.add(new_expense)
            db.session.commit()

            flash('Expense added successfully!', 'success')
            return redirect(url_for('add_expense'))
        else:
            flash('Insufficient balance to cover the expense.', 'error')

    # Fetch categories to display in the form
    categories = Categories.query.filter_by(user_id=user_id).all()
    return render_template('add_expenses.html', categories=categories)

def send_limit_exceeded_email(category, amount):
    msg = Message('Expense Limit Exceeded',
                  sender='21cse316.mehekswain@giet.edu',
                  recipients=['navyamehek10@gmail.com'])
    msg.body = f'The expense amount of {amount} for {category.name} has exceeded the set limit.'
    with app.app_context():
        mail.send(msg)

@login_required
@app.route('/edit/<int:expense_id>', methods=["GET","POST"])
def edit(expense_id):
    today=datetime.today()
    today_str = today.strftime('%Y-%m-%d')
    user_id = current_user.id 
    expenses = Expenses.query.get_or_404(expense_id)
    if request.method=='POST':
        category_id = request.form['category_id']
        amount = float(request.form['amount'])
        description = request.form['description']
        date = request.form['date']
        vendor=request.form['vendor']
        pay_method=request.form['paymentmethod']

        
        expenses.amount=amount
        expenses.description=description
        expenses.date=date
        expenses.category_id=category_id
        expenses.vendor=vendor
        expenses.pay_method=pay_method
        db.session.commit()
        return redirect('/dashboard')
    categories = Categories.query.filter_by(user_id=current_user.id).all()
    
    return render_template('edit.html',expenses=expenses,expense_id=expense_id,categories=categories)

@app.route('/delete_expense/<int:expense_id>', methods=['GET','POST'])
@login_required 
def delete_expense(expense_id):

    expense = Expenses.query.filter_by(expense_id=expense_id, user_id=current_user.id).first()
    if not expense:
        flash('Expense not found or does not belong to you.', 'error')
    else:
      
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully.', 'success')

   
    return redirect(url_for('dashboard'))

@app.route('/view_expenses', methods=['GET','POST'])
@login_required
def view_expenses():
    # if request.method == 'POST':
    # #     selected_month = request.form.get('month')
    # #     selected_year = request.form.get('year')
    # #     if not selected_month or not selected_year:
    # #         flash('Please select a valid month and year.', 'error')
    # #         return redirect(url_for('view_expenses'))

   
    # #     year, month = map(int, selected_month.split('-'))

    # #     expenses = Expenses.query.filter(
    # #     func.extract('year', Expenses.date) == year,
    # #     func.extract('month', Expenses.date) == month
    # #     ).all()

    
    # #     return render_template('select_month_year_form.html', expenses=expenses,selected_month=selected_month, selected_year=selected_year)
    # # else:
    # #     # Display the form for selecting month and year
    # #     return render_template('select_month_year_form.html') 
    category_totals=None   
    if request.method == 'POST':
        # Handle form submission here if needed
        selected_option = request.form.get('selected_option')
        user_id = current_user.id
        
        if selected_option == 'today':
            today_str = datetime.today().strftime('%Y-%m-%d')
            expenses = Expenses.query.filter_by(user_id=user_id, date=today_str).all()
            category_totals=calculate_category_totals(expenses)
            #
           
       ##for month year 
        selected_month = request.form.get('month')
        selected_year = request.form.get('year')
        if not selected_month or not selected_year:
            flash('Please select a valid month and year.', 'error')
            return redirect(url_for('view_expenses'))

   
        month = int(selected_month)
        year = int(selected_year)

        expenses = Expenses.query.filter(
        func.extract('year', Expenses.date) == year,
        func.extract('month', Expenses.date) == month
        ).all()
        if not expenses:
            plot_html=None
        else:
            category_totals=calculate_category_totals(expenses)

        #for ploting graph for above inputs
        # Create a list of dictionaries for Plotly Express
            data = [{'date': expense.date, 'amount': expense.amount} for expense in expenses]

        # Create a DataFrame from the list of dictionaries
            df = pd.DataFrame(data)

        # Plot line graph for monthly expenses
            fig = px.line(
            df,
            x='date',
            y='amount',
            labels={'x': 'Date', 'y': 'Expense Amount'},
            title=f'Monthly Expenses - {datetime(year, month, 1).strftime("%B, %Y")}'
            )

        # Update layout
            fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Expense Amount',
            )

        # Convert the plot to HTML
            plot_html = fig.to_html(full_html=False)
           
        return render_template('view_expenses.html', expenses=expenses,selected_option=selected_option,category_totals=category_totals,plot_html=plot_html)

    return render_template('view_expenses.html',category_totals=category_totals)    

def calculate_category_totals(expenses):
    category_totals = {}
    for expense in expenses:
        category = expense.category
        amount = expense.amount
        if category not in category_totals:
            category_totals[category] = 0
        category_totals[category] += amount
    return category_totals

@app.route('/expenses', methods=['GET'])

def expenses():
   
    # Fetch expenses for the logged-in user
    user_id = current_user.id
    expenses = Expenses.query.filter_by(user_id=user_id).all()
    return render_template('expenses.html', expenses=expenses)

# Add routes for editing and deleting expenses

@app.route('/categories', methods=['GET'])
@login_required
def categories():
    
    user_id = current_user.id
    categories = Categories.query.filter_by(user_id=user_id).all()
    return render_template('categories.html', categories=categories)

# Add routes for adding, editing, and deleting categories

@app.route('/incomes', methods=['GET'])
@login_required
def incomes():
    
    user_id = current_user.id
    incomes = Income.query.filter_by(user_id=user_id).all()
    return render_template('incomes.html', incomes=incomes)
@app.route('/income/add',methods=['GET','POST'])
@login_required
def add_income():
    
    if request.method =='POST':
        amount = float(request.form['amount'])
        source = request.form['source']
        date = request.form['date']
        # Stores the notification 
        notification=Notification(user_id=current_user.id,message=f"Expense amount exceeded the limit for {amount}.")
        db.session.add(notification)
        db.session.commit()
        # Create a new income record in the database
        new_income = Income(user_id=current_user.id, amount=amount, source=source, date=date)
        db.session.add(new_income)
        db.session.commit()

        flash('Income added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template("add_income.html")

def get_category_expenses(user_id):
    # Query the database to get the total expenses for each category
    category_expenses = db.session.query(Categories.name, func.sum(Expenses.amount)) \
        .filter(Categories.user_id == user_id) \
        .join(Expenses, Categories.category_id == Expenses.category_id) \
        .group_by(Categories.name) \
        .all()
    
    return category_expenses

@app.route('/index')
@login_required
def index():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    today=datetime.today()
    today_str = today.strftime('%Y-%m-%d')
    user_id = current_user.id 
    today_expenses = Expenses.query.filter_by(user_id=user_id, date=today_str).all()
    category_expenses = {}  # Dictionary to store category-wise expenses

#     labels = [expense.category.name for expense in today_expenses]
#     amounts = [expense.amount for expense in today_expenses]

# # Create a Matplotlib figure and axis
#     fig, ax = plt.subplots()

# # Create a pie chart
#     ax.pie(amounts, labels=labels, autopct='%1.1f%%', startangle=90)

# # Set title
#     ax.set_title("Today's Expenses by Category")

# # Save the plot to a BytesIO buffer
#     png_output = io.BytesIO()
#     plt.savefig(png_output, format='png')
#     plt.close()

# # Convert the plot to base64 for embedding in HTML
#     png_output.seek(0)
#     plot_base64 = base64.b64encode(png_output.read()).decode('utf-8')
    for expense in today_expenses:
        category = expense.category.name
        amount = expense.amount
    
        if category in category_expenses:
            category_expenses[category] += amount
        else:
            category_expenses[category] = amount
    category_expenses_list = [{'category': key, 'amount': value} for key, value in category_expenses.items()]
    fig = px.pie(category_expenses_list, names='category', values='amount', title='Today\'s Expenses by Category')
    fig.update_traces(hovertemplate='%{label}: ₹%{value:.2f}')
    fig.update_traces(hole=0.4)
    plot_html = fig.to_html(full_html=False)


    return render_template('index2.html', category_expenses=category_expenses, plot_html=plot_html)

###For email
@app.route('/notify_savings', methods=['GET'])
def notify_savings():
    # Get the current date
    today = datetime.now()

    # Calculate the start and end dates for the previous month
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month_end = today.replace(day=1) - timedelta(days=1)

    # Query the database for expenses and income in the previous month
    expenses = Expenses.query.filter(
        Expenses.date >= last_month_start,
        Expenses.date <= last_month_end
    ).all()

    # Calculate total expenses for the previous month
    total_expenses = sum(expense.amount for expense in expenses)

    # Calculate savings for each category
    category_savings = {}
    for category in Categories.query.all():
        category_expenses = [expense for expense in expenses if expense.category_id == category.id]
        category_total = sum(expense.amount for expense in category_expenses)
        category_savings[category.name] = category.income - category_total

    # Calculate total savings
    total_income = Income.query.filter(
        Income.date >= last_month_start,
        Income.date <= last_month_end
    ).sum('amount')
    total_savings = total_income - total_expenses

    # Send an email to the user with savings information
    subject = 'Your Savings Report for Last Month'
    recipients = ['user@example.com']  # Replace with the user's email address
    message_body = f"Total Savings: ${total_savings}\n\n"
    for category, savings in category_savings.items():
        message_body += f"{category} Savings: ${savings}\n"
    msg = Message(subject, recipients=recipients, body=message_body)
    mail.send(msg)

    return "Savings report sent successfully!"

# @app.route('/stats')
# @login_required
# def previous_month_expenses():
#     now = datetime.now()
#     previous_month = (now.month - 2) % 12 + 1
#     previous_year = now.year if previous_month != 12 else now.year - 1

#     # Fetch previous month's expenses data
#     previous_month_expenses_data = get_monthly_expenses_data(previous_year, previous_month)

#     # Create a bar chart using Plotly Express
#     fig = px.bar(
#         x=list(previous_month_expenses_data.keys()),
#         y=list(previous_month_expenses_data.values()),
#         labels={'x': 'Category', 'y': 'Total Expense'},
#         title=f'Previous Month Expenses - {datetime(previous_year, previous_month, 1).strftime("%B, %Y")}'
#     )

#     # Update layout
#     fig.update_layout(
#         xaxis_title='Category',
#         yaxis_title='Total Expense',
#         barmode='group',
#     )

#     # Convert the plot to HTML and pass it to your template
#     plot_html = fig.to_html(full_html=False)

#     #####################################################################
#     #graph amount vs date of current year
#     expenses = db.session.query(Expenses).all()
#     df_expenses = pd.DataFrame([expense.__dict__ for expense in expenses])
#     df_expenses['date'] = pd.to_datetime(df_expenses['date'])
#     current_year_expenses = df_expenses[df_expenses['date'].dt.year == datetime.today().year]

#     if current_year_expenses.empty:
#         pass
#     else:
        
#         monthly_totals = current_year_expenses.groupby(pd.Grouper(key='date', freq='M')).sum().reset_index()

#     # Create a line chart for total expense amount vs. date
#         fig = px.line(monthly_totals, x='date', y='amount', title=f'Total Expenses for {datetime.today().year}')
#         fig.update_layout(xaxis_title='Date', yaxis_title='Total Expense Amount')
#         plot_html1 = fig.to_html(full_html=False)
#     ############################################################

#     current_month = datetime.today().month
#     expenses = Expenses.query.filter(
#     func.extract('month', Expenses.date) == current_month
# ).all()
#     if expenses is not None:
#         expenses_df = pd.DataFrame([(expense.date, expense.amount) for expense in expenses], columns=['date', 'amount'])
#         expenses_df['date'] = pd.to_datetime(expenses_df['date'])

#         current_month_expenses = expenses_df[expenses_df['date'].dt.month == datetime.today().month]
#         if not current_month_expenses.empty:
#             fig = px.line(current_month_expenses, x='date', y='amount', title='Amount vs Date - Current Month')
#             fig.update_layout(
#             xaxis_title='Date',
#             yaxis_title='Amount',
#             showlegend=True,
#             )
#             plot_html2 = fig.to_html(full_html=False)

    

#     return render_template('stats.html', plot_html=plot_html,plot_html1=plot_html1,plot_html2=plot_html2)

@app.route('/stats')
@login_required
def previous_month_expenses():
    now = datetime.now()
    previous_month = (now.month - 2) % 12 + 1
    previous_year = now.year if previous_month != 12 else now.year - 1

    # Fetch previous month's expenses data
    previous_month_expenses_data = get_monthly_expenses_data(previous_year, previous_month)

    # Create a bar chart using Plotly Express
    previous_month_df = pd.DataFrame(previous_month_expenses_data.items(), columns=['Category', 'Total Expense'])
    fig = px.bar(
        previous_month_df,
        x='Category',
        y='Total Expense',
        title=f'Previous Month Expenses - {datetime(previous_year, previous_month, 1).strftime("%B, %Y")}'
    )

    # Update layout
    fig.update_layout(
        xaxis_title='Category',
        yaxis_title='Total Expense',
        barmode='group',
    )

    # Convert the plot to HTML and pass it to your template
    plot_html = fig.to_html(full_html=False)

    # Graph amount vs date of current year
    expenses = db.session.query(Expenses).all()
    df_expenses = pd.DataFrame([expense.__dict__ for expense in expenses])
    df_expenses['date'] = pd.to_datetime(df_expenses['date'])
    current_year_expenses = df_expenses[df_expenses['date'].dt.year == datetime.today().year]

    plot_html1 = None
    if not current_year_expenses.empty:
        monthly_totals = current_year_expenses.groupby(pd.Grouper(key='date', freq='M')).sum().reset_index()
        fig1 = px.line(monthly_totals, x='date', y='amount', title=f'Total Expenses for {datetime.today().year}')
        fig1.update_layout(xaxis_title='Date', yaxis_title='Total Expense Amount')
        plot_html1 = fig1.to_html(full_html=False)

    # Graph amount vs date of current month
    current_month = datetime.today().month
    expenses = Expenses.query.filter(
        func.extract('month', Expenses.date) == current_month
    ).all()
    plot_html2 = None
    if expenses:
        expenses_df = pd.DataFrame([(expense.date, expense.amount) for expense in expenses], columns=['date', 'amount'])
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        current_month_expenses = expenses_df[expenses_df['date'].dt.month == current_month]
        if not current_month_expenses.empty:
            fig2 = px.line(current_month_expenses, x='date', y='amount', title='Amount vs Date - Current Month')
            fig2.update_layout(
                xaxis_title='Date',
                yaxis_title='Amount',
                showlegend=True,
            )
            plot_html2 = fig2.to_html(full_html=False)

    return render_template('stats.html', plot_html=plot_html, plot_html1=plot_html1, plot_html2=plot_html2)

@app.route('/notification',methods=['GET','POST'])
@login_required
def notification():
    user_id = current_user.id
    category=Categories.query.filter_by(user_id=current_user.id).all()
    
    if request.method=='POST':
        category_id = request.form['category_id']
        limit = float(request.form['limit'])
        categories=Categories.query.get(category_id)
        if categories:
            categories.spending_limit=limit
            db.session.commit()
            flash('Category limit updated successfully', 'success')
        else:
            flash('Category not found', 'error')

    return render_template('notification.html', category=category)

def send_email(subject, recipient, body):
    message = Message(subject, recipients=[recipient])
    message.html = body

    try:
        mail.send(message)
        return True  # Email sent successfully
    except Exception as e:
        print(f"Error sending email: {e}")
        return False  # Failed to send email
    
def get_user_email(user_id):
    user = Users.query.get(user_id)
    return user.email if user else None

def create_expense(user_id, category_id, amount):
    category = Categories.query.get(category_id)
    if category and category.spending_limit is not None:
        if amount > category.spending_limit:
            user_email = get_user_email(user_id)
            subject = "Expense Limit Exceeded"
            body = render_template("email/expense_limit_exceeded.html", category=category.name, amount=amount)
            send_email(subject, user_email, body)

@app.route('/submit_feedback', methods=['POST','GET'])
@login_required
def submit_feedback():
    user_feedback = request.form.get('feedback')
  
    user_phone = request.form.get('phone')
    # Send an email to the admin
    msg = Message('Feedback from User   ', recipients=['navyamehek10@gmail.com'])
    
    # Include user information in the email body
    user_info = f"User Name: {current_user.username}\nUser Email: {current_user.email}\nUser"
    
    msg.body = f"{user_info}\n\nFeedback from user: {user_feedback} \n\nContact: {user_phone}"
    mail.send(msg)
    

    flash('Thank you for your feedback!')
    return render_template('feedback.html')
    

@app.route('/feedback_thank_you')
@login_required
def feedback_thank_you():
    return 'Thank you for your feedback!'

if __name__ == '__main__':
    app.run(debug=True)
