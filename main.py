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
    username = "test", 
    password = "test", 
    use_keys = False)

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


@app.route("/looking_glass/", methods=["GET", "POST"])
def looking_glass():
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


@app.route("/looking_glass/<router>/get_bgp_peer_routes/", methods=["GET", "POST"])
def get_bgp_peer_routes(router):
    
    peer = (request.args.get("peer"))

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    result = rtrname.get_bgp_peer_routes(peer)

    return render_template("get_bgp_peer_routes.html", router=router, result=result, peer=peer)


@app.route("/looking_glass/<router>/get_bgp_peer_advertised_routes/", methods=["GET", "POST"])
def get_bgp_peer_advertised_routes(router):
    
    peer = (request.args.get("peer"))

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    result = rtrname.get_bgp_peer_advertised_routes(peer)

    return render_template("get_bgp_peer_advertised_routes.html", router=router, result=result, peer=peer)


@app.route("/looking_glass/<router>/get_bgp_peer/<peer>/", methods=["GET", "POST"])
def get_bgp_peer(router, peer):

    desc = (request.args.get("desc"))

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

    result = rtrname.get_bgp_peer(peer)

    return render_template("get_bgp_peer.html", router=router, result=result, peer=peer, desc=desc)

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


@app.route("/looking_glass/<router>/summary/", methods=["GET", "POST"])
def summary(router):

    rtrname = eval(router) # gets object name, instead of string
    
    if not hasattr(rtrname, "SSHConnection"):  # if object doesn't 
                                               # have SSHConnection attribute (not connected via SSH)
        rtrname.init_ssh()                     # initialize SSHConnection     (establish tunnel)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
    db.create_all()

