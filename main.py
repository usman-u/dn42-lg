from flask import Flask, redirect, url_for, render_template, flash, request, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, RadioField, PasswordField
from wtforms.validators import DataRequired, Email, InputRequired, ValidationError
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from datetime import datetime
from net_automation import Vyos
import os
import sys
import concurrent.futures
import dn42_whois
from inventory import routers
from validations import is_valid_address, is_valid_network
import dn42_api


app = Flask(__name__)  # create an instance of the Flask class
app.config["SECRET_KEY"] = os.getenv("flask_secret_key")  # secret key
Bootstrap(app)

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


class User(UserMixin):
    def __init__(self, id, asn):
        self.id = id
        self.asn=asn

@login_manager.unauthorized_handler
def unauthorized_hanlder():
    return redirect(url_for('enter_asn'))

@login_manager.user_loader
def load_user(user_id):
    # Fetch the user from your data source based on the user_id
    # Return an instance of the User model
    asn = session['asn']
    return User(user_id, asn)


def validate_asn(form, field):
    asn = field.data

    asn = asn.upper()

    if not asn.startswith("AS"):
        raise ValidationError("ASN must start with 'AS'")
    
    asn_number = asn[2:]


    try:
        asn_int = int(asn_number)

    except ValueError:
        raise ValidationError("Invalid ASN range. Must be a valid DN42 BGP ASN. BGP person object(s) must have email(s).")

    if asn_int < 1 or asn_int > 4294967295:
        raise ValidationError("Invalid ASN range. Must be a valid DN42 ASN.")

    if not dn42_api.aut_num_exists(asn):
        raise ValidationError("ASN not in DN42 database. Try Again.")
    
    if not dn42_api.get_persons_emails(dn42_api.get_aut_num_bgp_persons(asn)):
        raise ValidationError("No emails found related to the entered ASN. Ensure your person objects in the DN42 database have emails.")
    



class ASNForm(FlaskForm):
    asn = StringField('Enter your DN42 ASN. e.g. AS4242421869', validators=[DataRequired(), validate_asn])
    submit = SubmitField('Next')
class EmailForm(FlaskForm):
    email = SelectField('Email Address', coerce=int)
    submit = SubmitField('Next')

class VerificationForm(FlaskForm):
    verification_code = StringField('Verification Code', validators=[DataRequired()])
    submit = SubmitField('Verify')

@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():

    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if 'selected_email' not in session or 'verification_code' not in session:
        return redirect(url_for('enter_asn'))
    

    form = VerificationForm()

    if form.validate_on_submit():
        entered_code = form.verification_code.data

        # Successful verification. 
        # Where emailed code = Entered Code 
        if entered_code == session['verification_code']:
            session['verified_email'] = session['selected_email']
            
            # Creates an intance of User with the verified email
            # And logs them in, using flask_login
            user = User(session['verified_email'], session['asn'])
            login_user(user)

            return redirect(url_for('profile'))
        else:
            form.verification_code.errors.append('Invalid verification code. Recheck your code or contact dn42peering@usman.network')

    return render_template('login/verify_email.html', form=form)



@app.route('/select_email', methods=['GET', 'POST'])
def select_email():

    if current_user.is_authenticated:
        return redirect(url_for('profile'))


    # gets email addrs from current user session
    # checks whether the user has entered their dn42 email address
    email_addresses = session.get('email_addresses')
    if not email_addresses:
        return redirect(url_for('enter_asn'))

    form = EmailForm()

    # loop through the email addresses and add them (as a record) to the form's email choices
    form.email.choices = [(index, email) for index, email in enumerate(email_addresses)]

    if form.validate_on_submit():
        selected_email = email_addresses[form.email.data]

        # TODO: Generate a verification code and send it to the selected email address
        # send_verification_email(selected_email, verification_code)
        verification_code = "TEST"

        # Store the selected email and verification code in the session for later verification

        session['selected_email'] = selected_email
        session['verification_code'] = verification_code
        return redirect(url_for('verify_email'))

    return render_template('login/select_email.html', form=form)


@app.route('/enter_asn', methods=['GET', 'POST'])
def enter_asn():
    
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    form = ASNForm()
    if form.validate_on_submit():

        session['asn'] = form.asn.data.strip()

        # session['email_addresses'] = dn42_api.get_admins_emails(dn42_api.get_aut_num_admins(session["asn"]))
        session['email_addresses'] = dn42_api.get_persons_emails(dn42_api.get_aut_num_bgp_persons(form.asn.data.strip()))

        return redirect(url_for('select_email'))

    return render_template('login/enter_asn.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('enter_asn'))

@app.route('/profile')
@login_required
def profile():
    return render_template('login/profile.html', username=current_user.id, asn=current_user.asn)




if __name__ == "__main__":
    app.run(debug=True, threaded=False, host="0.0.0.0")
