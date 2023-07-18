from flask import Flask, redirect, url_for, render_template, flash, request, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, RadioField, PasswordField, EmailField
from wtforms.validators import DataRequired, Email, InputRequired, ValidationError, EqualTo
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_bootstrap import Bootstrap
from flask_mail import Mail, Message
from flask_migrate import Migrate
from datetime import datetime
from net_automation import Vyos
import os
import sys
import concurrent.futures
import dn42_whois
from inventory import routers
from validations import is_valid_address, is_valid_network
import dn42_api
import time
import random
import string


app = Flask(__name__)  # create an instance of the Flask class
app.config["SECRET_KEY"] = os.getenv("flask_secret_key")  # secret key
Bootstrap(app)

app.config['MAIL_SERVER']=os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = os.getenv("MAIL_PORT")
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

# from auth import auth
# app.register_blueprint(auth)

class LookingGlassForm(FlaskForm):
    device = SelectField("Router", choices=["fr-lil1.usman.dn42", "us-ca1.usman.dn42"])

    device = RadioField(
        "Router",
        choices=[("fr_lil1", "fr-lil1.usman.dn42"), ("us_ca1", "us-ca1.usman.dn42")],
        validators=[InputRequired()],
    )

    query = RadioField(
        "Query",
        choices=[
            ("show ip route", "show ip route <e.g. 172.20.0.53>"),
            ("show ip bgp summary", "show ip bgp summary"),
            ("show ip bgp route", "show ip bgp route <e.g. 172.20.0.53 > "),
            ("show ip bgp peer", "show ip bgp peer <e.g. fe80::ade0>"),
            ("show ip bgp advertised-routes", "show ip bgp peer advertised-routes <e.g. fe80::ade0>"),
            ("show ip bgp received-routes", "show ip bgp peer received routes <e.g. fe80::ade0>"),
            ("show ip ospf routes", "show ip ospf routes"),
            ("show ip ospf neighbors", "show ip ospf neighbors"),
            ("show interfaces", "show interfaces"),
            ("whois", "whois ..."),
        ],
        validators=[InputRequired()],
    )

    # operation = SelectField("Operation", choices=["BGP Peer Summary"])
    target = StringField("Target", render_kw={"placeholder": "e.g. fe80::abc0"})
    submit = SubmitField("Submit")


# ROUTES
@app.route("/")  # route for the home page
def index():
    return render_template("index.html")
    # return redirect(url_for("looking_glass"))


@app.route("/looking_glass/", methods=["GET", "POST"])
def looking_glass():
    form = LookingGlassForm()
    result = None

    if request.method == "POST":
        device = form.device.data
        query = form.query.data
        target = form.target.data

        if query == "show ip route":
            result_url = url_for("get_route", router=device, prefix=target)
            return redirect(result_url)

        if query == "show ip bgp summary":
            result_url = url_for("get_bgp_peers", router=device)
            return redirect(result_url)

        if query == "show ip bgp route":
            result_url = url_for("get_bgp_route", prefix=target, router=device)
            return redirect(result_url)

        if query == "show ip bgp peer":
            result_url = url_for("get_bgp_peer", router=device, peer=target)
            return redirect(result_url)

        if query == "show ip bgp received-routes":
            result_url = url_for("get_bgp_peer_received_routes", router=device, peer=target)
            return redirect(result_url)

        if query == "show ip bgp advertised-routes":
            result_url = url_for("get_bgp_peer_advertised_routes", router=device, peer=target)
            return redirect(result_url)

        if query == "show ip ospf routes":
            result_url = url_for("get_ospf_routes", router=device)
            return redirect(result_url)

        if query == "show ip ospf neighbors":
            result_url = url_for("get_ospf_neighbors", router=device)
            return redirect(result_url)

        if query == "show interfaces":
            result_url = url_for("get_interfaces", router=device)
            return redirect(result_url)
        if query == "whois":
            result_url = url_for("whois", target=target)
            return redirect(result_url)

    return render_template("looking_glass.html", form=form, result=result)


@app.route("/looking_glass/get_ospf_routes/", methods=["GET", "POST"])
def get_ospf_routes():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
        if not rtr_instance.check_ssh():  # check if SSH session is active
            rtr_instance.init_ssh()       # if not, create a new SSH session
        result = rtr_instance.get_ospf_route_all()
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    return render_template("get_ospf_routes.html", router=router, result=result)


@app.route("/looking_glass/get_ospf_neighbors/", methods=["GET", "POST"])
def get_ospf_neighbors():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
        if not rtr_instance.check_ssh():  # check if SSH session is active
            rtr_instance.init_ssh()       # if not, create a new SSH session
        result = rtr_instance.get_ospf_neighbors()
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    return render_template("get_ospf_neighbors.html", router=router, result=result)

@app.route("/looking_glass/get_all_routes/", methods=["GET", "POST"])
def get_routes():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    inet = rtr_instance.get_all_routes("inet")
    inet6 = rtr_instance.get_all_routes("inet6")

    return render_template("get_all_routes.html", inet=inet, inet6=inet6, router=router)


@app.route("/looking_glass/route_summary/", methods=["GET", "POST"])
def get_route_summary():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    inet = rtr_instance.get_route_summary("inet")
    inet6 = rtr_instance.get_route_summary("inet6")

    return render_template(
        "get_route_summary.html", inet=inet, inet6=inet6, router=router
    )


@app.route("/looking_glass/summary/bgp/", methods=["GET", "POST"])
def get_summary_bgp():
    url_routers = request.args.getlist("router")

    results = [None] * len(url_routers)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_router = {(router, i): executor.submit(routers[router].get_bgp_peers) for i, router in enumerate(url_routers)}
        for future in concurrent.futures.as_completed(future_to_router.values()):
            for router, i in future_to_router.keys():
                if future_to_router[(router, i)] == future:
                    break
            try:
                result = future.result()
                results[i] = result
            except KeyError:
                return render_template(
                    "error.html", input=router, error="Invalid router name. Please try again."
                )

    return render_template("summary_bgp.html", results=results, routers=url_routers)

@app.route("/looking_glass/get_route/", methods=["GET", "POST"])
def get_route():
    router = request.args.get("router")
    prefix = request.args.get("prefix")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_network(prefix):
        return render_template(
            "error.html",
            input=prefix,
            error=f"Invalid IP address/prefix: {prefix}",
        )

    try:
        result = routers[router].get_route(prefix, "inet")

    except KeyError:              # accounts for when the router name is wrong
        return render_template(
            "error.html",
            input=router,
            error="Invalid router name. Please try again. If you're trying to inject something, please stop.",
        )
    except TypeError:             # accounts for when the peer IP doesn't exist
        return render_template(
            "error.html",
            input=prefix,
            error="Invalid Peer IP. Please try again. It's likely that the peer IP doesn't exist on this router - see the 'show ip bgp summary' for a list of peer IPs on this router.",
        )

    return render_template(
        "get_route.html", router=router, result=result, prefix=prefix
    )



@app.route("/looking_glass/get_bgp_peer/", methods=["GET", "POST"])
def get_bgp_peer():
    router = request.args.get("router")
    peer = request.args.get("peer")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_address(peer):
        return render_template(
            "error.html",
            input=peer,
            error="Invalid Peer IP. Please try again. It's likely that the peer IP doesn't exist on this router - see the 'show ip bgp summary' for a list of peer IP addresses.",
        )

    try:
        result = routers[router].get_bgp_peer(peer)

    except KeyError:              # accounts for when the router name is wrong
        return render_template(
            "error.html",
            input=router,
            error="Invalid router name. Please try again. If you're trying to inject something, please stop.",
        )
    except TypeError:             # accounts for when the peer IP doesn't exist
        return render_template(
            "error.html",
            input=peer,
            error="Invalid Peer IP. Please try again. It's likely that the peer IP doesn't exist on this router - see the 'show ip bgp summary' for a list of peer IPs on this router.",
        )

    return render_template(
        "get_bgp_peer.html", router=router, result=result, peer=peer, desc=desc
    )


@app.route("/looking_glass/get_bgp_route/", methods=["GET", "POST"])
def get_bgp_route():
    router = request.args.get("router")
    prefix = request.args.get("prefix")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_network(prefix):
        return render_template(
            "error.html",
            input=prefix,
            error="Invalid BGP Preifx/IP address. Please try again. If you're trying to inject something, please stop.",
        )

    try:
        rtr_instance = routers[router]
        if not rtr_instance.check_ssh():  # check if SSH session is active
            rtr_instance.init_ssh()  # if not, create a new SSH session
        result = rtr_instance.get_bgp_route(prefix)

    except KeyError:
        return render_template(
            "error.html",
            input=router,
            error="Invalid router name. Please try again. If you're trying to inject something, please stop.",
        )

    return render_template(
        "get_bgp_route.html", router=router, result=result, prefix=prefix, desc=desc
    )

@app.route("/looking_glass/bgp_peers/", methods=["GET", "POST"])
def get_bgp_peers():
    router = request.args.get("router")

    try:
        result = routers[router].get_bgp_peers()
    except KeyError:
        return render_template(
            "error.html",
            input=router,
            error="Invalid router name. Please try again. If you're trying to inject something, please stop.",
        )

    return render_template(
        "get_bgp_peers.html", result=result, router=router, time=datetime.now()
    )


@app.route("/looking_glass/get_bgp_peer_received_routes/", methods=["GET", "POST"])
def get_bgp_peer_received_routes():
    router = request.args.get("router")
    desc = request.args.get("desc")
    peer = request.args.get("peer")

    # injection attack check
    if not is_valid_address(peer):
        return render_template(
            "error.html",
            input=peer,
            error="Invalid Peer IP address. Please try again. If you're trying to inject something, please stop.",
        )

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    if not rtr_instance.check_ssh():  # check if SSH session is active
        rtr_instance.init_ssh()  # if not, create a new SSH session

    result = rtr_instance.get_bgp_peer_received_routes(peer)

    return render_template(
        "get_bgp_peer_received_routes.html",
        router=router,
        result=result,
        peer=peer,
        desc=desc,
    )


@app.route("/looking_glass/get_bgp_peer_advertised_routes/", methods=["GET", "POST"])
def get_bgp_peer_advertised_routes():
    router = request.args.get("router")
    peer = request.args.get("peer")
    desc = request.args.get("desc")

    # injection attack check
    if not is_valid_address(peer):
        return render_template(
            "error.html",
            input=peer,
            error="Invalid Peer IP address. Please try again. If you're trying to inject something, please stop.",
        )

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    if not rtr_instance.check_ssh():
        rtr_instance.init_ssh()

    result = rtr_instance.get_bgp_peer_advertised_routes(peer)

    return render_template(
        "get_bgp_peer_advertised_routes.html",
        router=router,
        result=result,
        peer=peer,
        desc=desc,
    )


@app.route("/looking_glass/whois/", methods=["GET", "POST"])
def whois():
    target = request.args.get("target")

    result = dn42_whois.dn42_whois(target)

    return render_template("whois.html", target=target, result=result)


@app.route("/looking_glass/get_interfaces/", methods=["GET", "POST"])
def get_interfaces():
    router = request.args.get("router")

    try:
        rtr_instance = routers[router]
    except KeyError:
        return render_template(
            "error.html", input=router, error="Invalid router name. Please try again."
        )

    if not rtr_instance.check_ssh():
        rtr_instance.init_ssh()

    result = rtr_instance.get_interfaces()

    return render_template("get_interfaces.html", result=result, router=router)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


login_manager = LoginManager(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    asn = db.Column(db.String(80), unique=False, nullable=True)
    password = db.Column(db.String(300), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<User %r>' % self.email

    def get_id(self):
        return str(self.id)


@login_manager.unauthorized_handler
def unauthorized_hanlder():
    flash("You aren't logged in or aren't authorised to access this page.", "warning")
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


def validate_asn(form, field):
    asn = field.data.strip()

    asn = asn.upper()

    if not asn.startswith("AS"):
        flash("ASN must start with'AS'", "danger")
        raise ValidationError
    
    asn_number = asn[2:]


    try:
        asn_int = int(asn_number)

    except ValueError:
        flash("Invalid ASN range. Must be a valid DN42 BGP ASN. BGP person object(s) must have email(s).", "danger")
        raise ValidationError

    if asn_int < 1 or asn_int > 4294967295:
        flash("Invalid ASN range. Must be a valid DN42 ASN.", "danger")
        raise ValidationError("Invalid ASN range. Must be a valid DN42 ASN.")

    if not dn42_api.aut_num_exists(asn):
        flash("ASN not in DN42 database. Try Again.", "danger")
        raise ValidationError("ASN not in DN42 database. Try Again.")

    person = dn42_api.get_aut_num_bgp_persons(asn)
    
    if not dn42_api.get_persons_emails(person):
        flash("No emails found related to the entered ASN. Ensure your person objects in the DN42 database have emails.", "danger")
        raise ValidationError("No emails found related to the entered ASN. Ensure your person objects in the DN42 database have emails.")
    
    session["person"] = person

    



class ASNForm(FlaskForm):
    asn = StringField('Enter your DN42 ASN. e.g. AS4242421869', validators=[DataRequired(), validate_asn])
    submit = SubmitField('Next')
class EmailForm(FlaskForm):
    email = SelectField('Email Address', coerce=int)
    submit = SubmitField('Next')

class VerificationForm(FlaskForm):
    verification_code = StringField('Verification Code', validators=[DataRequired()])
    password = PasswordField("Enter Your Password ", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Your Password", validators=[DataRequired()])
    submit = SubmitField('Verify')

class LoginForm(FlaskForm):
    email = EmailField('Enter your email', validators=[DataRequired()])
    password = PasswordField("Enter Your Password ", validators=[DataRequired()])
    submit = SubmitField('Log in')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired()])
    submit = SubmitField('Change Password')



# Edge case for if the admin wants to create a user with no ASN (offline user)
# Only starts validating the input if the asn field is not empty
def newuser_validate_asn(self, field):
    if field.data:
        asn = field.data.strip()

        asn = asn.upper()

        if not asn.startswith("AS"):
            flash("ASN must start with'AS'", "danger")
            raise ValidationError
        
        asn_number = asn[2:]


        try:
            asn_int = int(asn_number)

        except ValueError:
            flash("Invalid ASN range. Must be a valid DN42 BGP ASN. BGP person object(s) must have email(s).", "danger")
            raise ValidationError

        if asn_int < 1 or asn_int > 4294967295:
            flash("Invalid ASN range. Must be a valid DN42 ASN.", "danger")
            raise ValidationError("Invalid ASN range. Must be a valid DN42 ASN.")

        if not dn42_api.aut_num_exists(asn):
            flash("ASN not in DN42 database. Try Again.", "danger")
            raise ValidationError("ASN not in DN42 database. Try Again.")

        person = dn42_api.get_aut_num_bgp_persons(asn)
        
        if not dn42_api.get_persons_emails(person):
            flash("No emails found related to the entered ASN. Ensure your person objects in the DN42 database have emails.", "danger")
            raise ValidationError("No emails found related to the entered ASN. Ensure your person objects in the DN42 database have emails.")
# For if the admin makes a user
class AddUserForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    asn = StringField('ASN', validators=[newuser_validate_asn])
    admin = BooleanField('Admin', default=False)
    email_password = BooleanField('Email Randomly Generated Password', default=False)
    submit = SubmitField('Create User')


def generate_verification_code():
    code = random.randint(100000, 999999)
    timestamp = time.time()
    return str(code), timestamp

# Check if the verification code has expired (valid for 5 minutes)
def has_code_expired(timestamp):
    if timestamp == None:
        return False
    current_time = time.time()
    return (current_time - timestamp) > 300  # 300 seconds = 5 minutes

@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():

    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if 'selected_email' not in session or 'verification_code' not in session:
        return redirect(url_for('enter_asn'))
    

    form = VerificationForm()

    if form.validate_on_submit():
        entered_code = form.verification_code.data.strip()
        stored_code = session.get('verification_code')
        stored_timestamp = session.get('timestamp')

        if (entered_code is None) or (stored_code is None) or has_code_expired(stored_timestamp):
            flash('Verification code has expired. Please request a new code or contact usman@usman.network for support.', 'danger')
        
        elif entered_code == session['verification_code'] and (not has_code_expired(session['timestamp'])):
            session['verified_email'] = session['selected_email']
            

            if form.password.data != form.confirm_password.data:
                flash("Passwords must match!", "danger")
                return redirect(url_for("verify_email"))

            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

            # Creates an intance of User with the verified email
            # And logs them in, using flask_login
            new_user = User(email=session["verified_email"], password=hashed_password, asn=session["asn"])
            db.session.add(new_user)
            db.session.commit()

            # user = User(session['verified_email'], session['asn'])
            login_user(new_user)

            # return "Done"

            flash(f"Authentication Success. You're logged in as {session['verified_email']} of {session['asn']}", "success")

            session.pop('verification_code', None)
            session.pop('timestamp', None)


            return redirect(url_for('profile'))
        else:
            flash("Invalid verification code. Recheck your code or contact usman@usman.network", "danger")

    return render_template('login/verify_email.html', form=form)



@app.route('/select_email', methods=['GET', 'POST'])
def select_email():

    if current_user.is_authenticated:
        return redirect(url_for('profile'))


    # Gets email addrs from current user session
    # Checks whether the user has entered their dn42 email address
    email_addresses = session.get('email_addresses')
    if not email_addresses:
        return redirect(url_for('enter_asn'))

    # If code has been generated and emailed to the user (& code not expired)
    # Then, redirect then back to the verify_email page
    if (session.get("verification_code") != None) and (not has_code_expired(session.get("timestamp"))):
        flash("You've already generated a code that hasn't expired. Check your email or request a new code.", "warning")
        return redirect(url_for('verify_email'))

    form = EmailForm()

    # loops through the email addresses and add them (as a record) to the form's email choices
    form.email.choices = [(index, email) for index, email in enumerate(email_addresses)]

    if form.validate_on_submit():
        selected_email = email_addresses[form.email.data]

        # Checks if the email address is already registered
        existing_user = User.query.filter_by(email=selected_email).first()
        if existing_user:
            flash(f"{selected_email} already registered. Please login.", "danger")
            return redirect(url_for('login'))
        

        # TODO: error handling for email credentials
        verification_code, timestamp = generate_verification_code()
        message = Message('USMAN BGP PEERING Verification Code', sender='dn42verification@usman.network', recipients=[selected_email])
        message.body = f' Hello!. Your verification code is: {verification_code}.  It will expire in 5 minutes.'
        mail.send(message)
        flash(f"Message sent to {selected_email}. Please check your spam!", "success")

        # Stores the selected email and verification code in the session for later verification
        session['selected_email'] = selected_email
        session['verification_code'] = verification_code
        session['timestamp'] = timestamp

        return redirect(url_for('verify_email'))

    return render_template('login/select_email.html', form=form)


@app.route('/enter_asn', methods=['GET', 'POST'])
def enter_asn():
    
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    # If code has been generated and emailed to the user (& code not expired)
    # redirect then back to the verify_email page
    if (session.get("verification_code") != None) and (not has_code_expired(session.get("timestamp"))):
        flash("You've already generated a code that hasn't expired. Check your email or request a new code.", "warning")
        return redirect(url_for('verify_email'))

    form = ASNForm()
    if form.validate_on_submit():

        session['asn'] = form.asn.data.strip()

        session['email_addresses'] = dn42_api.get_persons_emails(dn42_api.get_aut_num_bgp_persons(form.asn.data.strip()))

        flash(f"{session['asn']} entered & person(s): {' '.join(x for x in session['person'])} successfully looked up.", "success")

        return redirect(url_for('select_email'))

    return render_template('login/enter_asn.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        flash(f"You're already logged in as {current_user.email}.", "warning")
        return redirect(url_for('profile'))
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)

            flashed_message = f"Authentication Success. You're logged in as {user.email}"
            if user.asn:
                flashed_message += f" of {user.asn}"

            flash(flashed_message, "success")
            return redirect(url_for('profile'))
        else:
            flash("Login Unsuccessful. Please check email and password", "danger")

    return render_template('login/login.html', form=form)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data

        # Verify the current password matches the user's stored password
        if bcrypt.check_password_hash(current_user.password, current_password):

            # Verify the new password matches the confirm password
            if new_password != form.confirm_password.data:
                flash("Passwords must match!", "danger")
                return redirect(url_for("change_password"))

            # Hash new password
            # Commit changes to db
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            current_user.password = hashed_password

            # Save the updated user information in the database
            db.session.commit()

            flash('Password successfully changed!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Incorrect current password. Please try again.', 'danger')

    return render_template('login/change_password.html', form=form)


@app.route('/admin/user_management/add_user', methods=['GET', 'POST'])
@login_required
def add_user():

    if not current_user.admin:
        flash("You aren't authorised to access this page.", "warning")
        return redirect(url_for('profile'))
    

    form = AddUserForm()
    if form.validate_on_submit():

        random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(10))

        user = User(email=form.email.data, asn=form.asn.data, admin=form.admin.data, password=bcrypt.generate_password_hash(random_password).decode('utf-8'))
        db.session.add(user)
        db.session.commit()

        if form.email_password.data:
            message = Message('usman.dn42 User Registration', sender='dn42registration@usman.network', recipients=[form.email.data.strip()])
            message.body = f' Hello! Your account has been created. Your temporary password is: {random_password}. Please login at https://usman.dn42/login. Please change your password after logging in.'
            mail.send(message)

        flashed_message = f"{form.email.data.strip()} added successfully"
        if form.asn.data:
            flashed_message += f", with ASN {form.asn.data.strip()}"
        if form.admin.data:
            flashed_message += ", as an admin"
        if form.email_password.data:
            flashed_message += f", and emailed their password to {form.email.data.strip()} "

        flash(flashed_message, "success")
        flash(f"Randomly generated password is {random_password}", "success")

        return redirect(url_for('user_management'))
    
    return render_template('user_management/add_user.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    return render_template('login/profile.html', current_user=current_user)


@app.route('/admin')
@login_required
def admin():
    if not current_user.admin:
        flash("You aren't authorised to access this page.", "warning")
        return redirect(url_for('profile'))
    return render_template('login/admin.html', current_user=current_user)


@app.route('/admin/user_management')
@login_required
def user_management():
    if not current_user.admin:
        flash("You aren't authorised to access this page.", "warning")
        return redirect(url_for('profile'))

    users = User.query.all()

    return render_template('user_management/user_management.html', current_user=current_user, users=users)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, threaded=False, host="0.0.0.0")
