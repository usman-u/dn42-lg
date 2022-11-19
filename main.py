from flask import Flask, redirect, url_for, render_template, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, Email, InputRequired
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from net_automation import net_automation

app = Flask(__name__)                                         # create an instance of the Flask class
app.config["SECRET_KEY"] = "fhdujghrfdjkhgdfjk"               # secret key
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sql"    # location of DB
db = SQLAlchemy(app)                                          # inits the db, instance of SQLAlchemy

usmanerx = net_automation.EdgeOS(
    device_type = "ubiquiti_edgerouter",
    host = "erx.usman.lan",
    username = "usman", 
    use_keys = True, 
    key_file = r"C:\Users\Usman\.ssh\id_rsa",)


fr_lil1 = net_automation.Vyos(
    device_type = "vyos",
    host = "10.100.100.4",
    username = "usman", 
    use_keys = True, 
    key_file = r"C:\Users\Usman\.ssh\id_rsa",)

# DBs
class Devices(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(200), nullable = False)
    nickname = db.Column(db.String(200), nullable = False)
    device_type = db.Column(db.String(200), nullable = False)
    username = db.Column(db.String(200), nullable = False)
    password = db.Column(db.String(200), nullable = False)
    usekeys = db.Column(db.Boolean(200), nullable=False)
    keyfile = db.Column(db.String(200), nullable = False)
    secret = db.Column(db.String(200), nullable = False)
    dateadded = db.Column(db.DateTime, default=datetime.utcnow)
    dateupdated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Devices %r>' % self.id

def devices_query():
    return Devices.query

# FORMS
class NamerForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[InputRequired("This Requires an Email!!"), Email("This Requires an Email!!")])
    submit = SubmitField("Submit")

class DeviceForm(FlaskForm):
    hostname = StringField("Hostname", validators=[DataRequired()], render_kw={"placeholder": "10.0.10.1"})
    device_type = SelectField(u"Device Type", choices=["VyOS", "EdgeOS", "Cisco_IOS"])
    nickname = StringField("Nickname", render_kw={"placeholder": "nickname"})
    username = StringField("Username", validators=[DataRequired()], render_kw={"placeholder": "username"})
    password = StringField("Password", render_kw={"placeholder": "password"})
    use_keys = BooleanField("Use SSH Keys?")
    key_file = StringField("SSH Key Location", render_kw={"placeholder": "key_file"})
    secret = StringField("Secret", render_kw={"placeholder": "secret"})
    submit = SubmitField("Submit")

class LookingGlassForm(FlaskForm):

    # device = QuerySelectField(query_factory=Devices.query.all())
    # all_devices = Devices.query.all()
    # device = SelectField(u"Device Name", choices=[all_devices, "test", "test2"])
    # print (all_devices)

    device = SelectField(u"Device Name", choices=["usmanerx"])

    operation = SelectField(u"Operation", choices=["Show IP Route", "Show IP Route to"])
    target = StringField("Target", render_kw={"placeholder": "1.1.1.1"})
    submit = SubmitField("Submit")

# ROUTES
@app.route('/')                               # route for the home page
def home():
    return render_template('index.html')

@app.route('/inventory/')                               # route for the home page
def inventory():
    all_devices = Devices.query.order_by(Devices.dateadded.desc()).all()
    return render_template("inventory.html", all_devices=all_devices)

@app.route("/name/", methods=["GET", "POST"])
def name():
    name = None
    email = None
    form = NamerForm()

    if form.validate_on_submit():
        name = form.name.data    # if valid, submit the name
        email = form.email.data    # if valid, submit the name
        form.name.data = ""      # clear the form
        form.email.data = ""      # clear the form
        flash("Form submitted successfully!")

    return render_template("name.html",     # parsing parmsto html
                                 form=form, 
                                 name=name,
                                 email=email)

@app.route("/inventory/add_device/", methods=["GET", "POST"])          # add device route
def device():                                                # add device fuction
    hostname = None                                          # set to none
    nickname = None                                          # set to none
    device_type = None
    username = None
    password = None
    use_keys = None
    key_file = None
    secret = None
    form = DeviceForm()                                       # create a form instance

    if form.validate_on_submit():                             # if form totally is valid
        # adding form data to DB
        device = Devices(hostname=form.hostname.data,
                            device_type=form.device_type.data,
                            nickname=form.nickname.data,
                            username=form.username.data,
                            password=form.password.data,
                            usekeys=form.use_keys.data,
                            keyfile=form.key_file.data,
                            secret=form.secret.data)
        db.session.add(device)                               # add to DB
        db.session.commit()                                  # commit to DB

        hostname = form.hostname.data
        device_type = form.device_type.data
        nickname=form.nickname.data,
        username = form.username.data
        password = form.password.data
        use_keys = form.use_keys.data
        key_file = form.key_file.data
        secret = form.secret.data

        form.hostname.data = ""                                 # clear the form for next use
        form.device_type.data = ""
        form.nickname.data = ""
        form.username.data = ""
        form.password.data = ""
        form.use_keys.data = ""
        form.key_file.data = ""
        form.secret.data = ""
        flash("Form submitted successfully!")

    all_devices = Devices.query.order_by(Devices.dateadded.desc()).all()

    return render_template("add_device.html",
                                 form=form, 
                                 hostname=hostname,
                                 nickname=nickname,
                                 device_type=device_type,
                                 username=username,
                                 password=password,
                                 use_keys=use_keys,
                                 key_file=key_file,
                                 secret=secret,
                                 all_devices=all_devices)

@app.route("/inventory/update/<int:id>/", methods=["GET", "POST"])          # route updating device records
def update(id):
    form = DeviceForm()
    device_to_update = Devices.query.get_or_404(id)

    if request.method == "POST":
        print (device_to_update)
        device_to_update.hostname = request.form["hostname"]
        device_to_update.device_type = request.form["device_type"]
        device_to_update.username = request.form["username"]
        device_to_update.password = request.form["password"]
        device_to_update.usekeys = form.use_keys.data
        device_to_update.keyfile = request.form["key_file"]
        device_to_update.secret = request.form["secret"]
        try:
            flash("Updated Successfully!")
            db.session.commit()
            return render_template("update.html",
                            form=form, 
                            device_to_update=device_to_update)
        except:
            flash("Error Updating Device!")
            return render_template("update.html", form=form, device_to_update=device_to_update)

    else:
        return render_template("update.html", form=form, device_to_update=device_to_update)

@app.route("/inventory/delete_device/<int:id>") 
def delete(id):
    form = DeviceForm()                                       # create a form instance
    device_to_delete = Devices.query.get_or_404(id)  # queries for device id

    try:
        db.session.delete(device_to_delete)
        db.session.commit()
        flash("User Deleted Successfully")

        all_devices = Devices.query.order_by(Devices.dateadded.desc()).all()

        return render_template("add_device.html",
                                    form=form, 
                                    all_devices=all_devices)

    except:
        flash("Error Deleting Device!")
        return render_template("add_device.html",
                                    form=form, 
                                    all_devices=all_devices)

@app.route("/looking_glass/", methods=["GET", "POST"])
def looking_glass():
    # all_devices = Devices.query.order_by(Devices.dateadded.desc()).all()
    device = ""
    operation = ""
    target = ""
    form = LookingGlassForm()
    


    if form.validate_on_submit():
        # device = form.device.data
        device = form.device.data
        operation = form.operation.data
        target = form.target.data

        # form.device.data = ""
        # form.operation.data = ""
        # form.target.data = ""

        flash("Form submitted successfully!")
        print (form.operation.data)
        # if form.operation.data == "Show IP Route To":
        
        return redirect(url_for("routes", router=form.device.data, target=form.target.data))
        
    
    return render_template("looking_glass.html",
                                 form=form, 
                                 device=device,
                                 operation=operation,
                                 target=target)


@app.route("/looking_glass/<router>/whois/<query>", methods=["GET", "POST"])
def whois(router, query):


    target = (request.args.get("target"))

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    result = fr_lil1.whois_dn42(query)

    return render_template("whois.html", result=result)

@app.route("/looking_glass/<router>/routes/", methods=["GET", "POST"])
def routes(router):
    target = (request.args.get("target"))

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    if target == None:
        result = rtrname.get_route_table("")
    else:
        result = rtrname.get_route(target)

    return render_template("routes.html", target=target, result=result, router=router, time=datetime.now())


@app.route("/looking_glass/<router>/bgp/", methods=["GET", "POST"])
def bgp(router):

    neighbor = (request.args.get("neighbor"))

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    if neighbor == None:
        result = rtrname.get_bgp_summary()
    
    return render_template("bgp.html", result=result, router=router, time=datetime.now())


@app.route("/looking_glass/<router>/peerbgproutes/<peer>", methods=["GET", "POST"])
def get_bgp_peer(router, peer):

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    result = rtrname.get_bgp_peer(peer)

    return render_template("get_bgp_peer.html", router=router, result=result, peer=peer)


@app.route("/looking_glass/<router>/peerbgproutes/<peer>", methods=["GET", "POST"])
def peer_bgp_routes(router, peer):

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    result = rtrname.get_peer_bgp_routes(peer)

    return render_template("bgppeerroutes.html", router=router, result=result, peer=peer)

@app.route("/looking_glass/<router>/bgp/<prefix>/", methods=["GET", "POST"])
def bgp_route(router, prefix):

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    result = rtrname.get_bgp_route(prefix)

    return render_template("bgproute.html", result=result, router=router, prefix=prefix)

@app.route("/looking_glass/<router>/ospf/", methods=["GET", "POST"])
def ospf(router):

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    # if neighbor == None:
    #     result = rtrname.get_bgp_neighbors()
    
    result = rtrname.get_ospf_neighbors()
    
    return render_template("ospf.html", result=result, router=router)

@app.route("/looking_glass/<router>/interfaces/", methods=["GET", "POST"])
def interfaces(router):
    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    result = rtrname.get_interfaces()

    return render_template("interfaces.html", result=result, router=router)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
    db.create_all()

