from turtle import title
from unittest import result
from flask import Flask, redirect, render_template, request, flash, session, url_for
from flask_mysqldb import MySQL
from functools import wraps
from twilio.rest import Client
account_sid = "ACffa141d2a198b5fdb3dcff087b6e925e"

# Your Auth Token from twilio.com/console
auth_token = "56b7a61e1bdbfaa939714f0bb918eb81"


app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'crime_report'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)


# @app.route("/")
# def index():
#     return "<p>Hello, World!</p>"


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        result = cur.execute("select user.first_name,user.last_name,user.id,user.email,user.password,user_role.role from user \
 INNER JOIN user_role ON user.id=user_role.user_id \
 where email=%s\
 ;", [email])
        if result > 0:
            data = cur.fetchone()
            password_candidate = data['password']
            if(password == password_candidate):
                session['logged_in'] = True
                session['email'] = email
                session['name'] = data['first_name'] + " " + data['last_name']
                session['id'] = data['id']
                # print(data['role'])
                if(data['role'] == 'admin'):

                    session['is_admin_logged'] = True

                flash('You are now logged in', 'success')
                return redirect(url_for('home'))
        flash('username or password didn\'t match')
    if(session.get("logged_in") != None):
        return redirect('home')
    return render_template('login.html', title="Login")


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        phone_number = request.form['phone_number']

        cur = mysql.connection.cursor()

        result = cur.execute("INSERT INTO user(first_name,last_name,email,password,phone_number) VALUES(%s,%s,%s,%s,%s)",
                             (first_name, last_name, email, password, phone_number))
        if(result):
            data = cur.execute("SELECT id from user WHERE email = %s", [email])
            data = cur.fetchone()
            data = data['id']
            cur.execute(
                "INSERT INTO user_role(role,user_id) VALUES(%s,%s)", ("user", data))
        mysql.connection.commit()
        cur.close()
        flash('You are now registered and can login ', 'sucess')
        return redirect(url_for('signup'))
    if session.get("logged_in") != None:
        return redirect('home')
    return render_template('signup.html', title="Sign up")


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


def is_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'is_admin_logged' in session:
            return f(*args, **kwargs)
        else:
            flash('You dont have permission to visit this page', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route("/home")
@app.route('/')
@is_logged_in
def home():
    return render_template('home.html', title="Home")


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


@app.route('/admin')
def admin_panel():
    return render_template('admin_panel.html', title="Admin Pannel")


@app.route("/admin/add_complain_type", methods=['GET', 'POST'])
def add_complain_type():
    if request.method == "POST":
        name = request.form['name']
        description = request.form['description']
        user_id = session['id']
        cur = mysql.connection.cursor()
        result = cur.execute(
            "INSERT INTO complain_type(name,description,user_id) VALUES(%s,%s,%s)", (name, description, user_id))
        if(result > 0):
            mysql.connection.commit()
            cur.close()

            flash('Complain type Added', 'sucess')
        # return redirect()
    return render_template('add_complain_type.html', title="Add Complain Type")


@app.route('/admin/add_admin', methods=['POST', 'GET'])
@is_admin
def add_admin():
    if request.method == 'POST':
        email = request.form['email']
        cur = mysql.connection.cursor()
        result = cur.execute("select * from user where email=%s;", [email])
        if result > 0:
            data = cur.fetchone()
            user_id = data['id']
            cur.execute(
                " UPDATE user_role SET role = 'admin' WHERE user_id = %s;", [user_id])
            mysql.connection.commit()
            cur.close()
            flash("This Email is promoted to admin.")
            return redirect('/home')
        else:
            flash("Invalid email")
        # print(email)
    return render_template('add_admin.html', title="Add Admin")


@app.route("/make_complain", methods=['POST', 'GET'])
def make_complain():
    if request.method == 'POST':
        description = request.form['description']
        user_id = session.get("id")
        location = request.form['city'] + " " + request.form['street']
        date = request.form['date']
        contact = request.form['contact']
        complain_type_id = request.form['complain_type_id']

        cur = mysql.connection.cursor()
        result = cur.execute(
            "INSERT INTO complain(description,user_id,location,date,contact_number,complain_type_id) VALUES(%s,%s,%s,%s,%s,%s)",
            (description,
             user_id,
             location,
             date,
             contact,
             complain_type_id))
        if(result > 0):
            result = cur.execute(
                "select name from complain_type where id=%s;", [complain_type_id])
            data = cur.fetchone()
            # print(data['name'])

            mysql.connection.commit()
            cur.close()
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                to="+977",
                from_="+12",
                body="Crime: "+data['name']+" Location: "+location+" phone: "+contact)
            print(message.sid)
            flash('Complain has been sent. We will contact you soon.', 'sucess')
        else:
            flash('Error while filing this complain', 'danger')
    cur = mysql.connection.cursor()

    select = cur.execute("SELECT * FROM complain_type;")

    select = cur.fetchall()

    if select:
        return render_template('make_complain.html', selects=select, title="Make a complain")
    else:
        msg = 'Not Found'
        return render_template('make_complain.html', msg=msg)
    # Close connection
    cur.close()

    # return render_template('make_complain.html', title="File Complain", select=select)


@app.route("/show_complain")
def show_complain():
    cur = mysql.connection.cursor()

    result = cur.execute("\
    select complain.id,complain.description,complain.location,complain.contact_number,complain.date, \
complain_type.name,\
user.email,user.first_name,user.last_name, \
    complain_update.status\
 from complain \
 INNER JOIN complain_type ON complain_type.id=complain.complain_type_id \
 INNER JOIN user ON user.id = complain.user_id \
left outer join complain_update on complain_update.complain_id = complain.id\
; \
    ")

    result = cur.fetchall()
    cur.close()
    return render_template('show_complain.html', results=result, title="Show Complain")


@app.route("/update_case/<string:id>", methods=['POST', 'GET'])
def update_case(id):
    if request.method == 'POST':
        status = request.form['caseUpdate']
        user_id = session.get("id")
        remarks = request.form['remarks']
        date = request.form['date']
        cur = mysql.connection.cursor()
        result = cur.execute(
            'select * from complain_update where complain_id = %s;', [id])
        if result > 0:
            result = cur.execute('UPDATE complain_update \
                set status =%s, user_id=%s, remarks=%s, date = %s\
                    where complain_id=%s', [status, user_id, remarks, date, id])
            # result = cur.fetchone()
            mysql.connection.commit()
            cur.close()
            flash('Case updated')
        else:
            # print({user_id, id, remarks, status, date})
            print('date is :', date)
            result = cur.execute('INSERT INTO complain_update(user_id,complain_id,remarks,status,date) values(\
                %s,%s,%s,%s,%s);', [user_id, id, remarks, status, date])
            mysql.connection.commit()
            cur.close()
            flash('Case updated')
        return redirect('/home')
    cur = mysql.connection.cursor()

    result = cur.execute(" select complain.id,complain.description,complain.location,complain.contact_number,complain.date, \
complain_type.name,\
user.email,user.first_name,user.last_name \
 from complain \
 INNER JOIN complain_type ON complain_type.id=complain.complain_type_id \
 INNER JOIN user ON user.id = complain.user_id \
     where complain.id=%s\
; ", [id])

    result = cur.fetchone()
    cur.close()
    return render_template('update_case.html', title="Update case", result=result)


@app.route('/test')
def send_sms():
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        to="+977",
        from_="+12",
        body="Yo message app batta pathako ho xD!")

    print(message.sid)
    return "Message send sucess"


if __name__ == '__main__':
    # db.init_app(app)
    app.secret_key = 'secret123'
    app.run(port=5000, debug=True)
