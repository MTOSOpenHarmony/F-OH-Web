from datetime import datetime
import json
from zipfile import ZipFile
from flask import (
    Flask,
    flash,
    request,
    jsonify,
    abort,
    redirect,
    send_file,
    session,
    url_for,
    render_template,
    redirect,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from hashing import Hashing
from flask_login import AnonymousUserMixin
import flask_login
import uuid
from dotenv import load_dotenv

app = Flask(__name__)
hasher = Hashing()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../apps.db"
app.config["UPLOAD_FOLDER"] = "data"
db = SQLAlchemy(app)
app.secret_key = "ABCDEFGOH-F"
homepageDataCfg = {"showAnnouncement": True,"sections":[],"slideshow":[],"announcement": "Welcome To AppMarket!","appName":"AppMarket"}
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
download_urls = {}
home_adpost = []
with open("data/home_adpost.json", "r") as f:
    home_adpost=json.loads(f.read())
# dynamicURL = {uuid:/data/....}

class ReleaseInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    version = db.Column(db.String(20), nullable=False)
    hapUrl = db.Column(db.String(200), nullable=False)
    releaseTime = db.Column(db.String(20), nullable=False)
    minimumAPI = db.Column(db.Integer, nullable=False)
    minimumOldVersion = db.Column(db.Integer, nullable=False)
    downloadLatestIfNew = db.Column(db.Integer, nullable=False)
    deviceType = db.Column(db.String, nullable=True)  # P=Phone, T=Tablet,
    archType = db.Column(db.Integer, nullable=False)  # arm64 arm x86 x86_64
    changeLog = db.Column(db.String, nullable=True)
    requiredPerm = db.Column(db.String, nullable=False)
    verCode = db.Column(db.Integer, nullable=False)


class App(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    desc = db.Column(db.String(200), nullable=False)
    maindesc = db.Column(db.String, nullable=False)
    icon = db.Column(db.String(200), nullable=False)
    vender = db.Column(db.String(80), nullable=False)
    packageName = db.Column(db.String(80), nullable=False)
    # version = db.Column(db.String(20), nullable=False)
    # hapUrl = db.Column(db.String(200), nullable=False)
    # type = db.Column(db.String(20), nullable=False)
    tags = db.Column(db.String(200), nullable=False)
    website = db.Column(db.String(200), nullable=False)
    appReleases = db.Column(db.String, nullable=False)
    # releaseTime = db.Column(db.String(20), nullable=False)
    # editUrl = db.Column(db.String(200), unique=True, nullable=False)
    # permitted = db.Column(db.Integer)
    stars = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.String, nullable=False)
    downloadCount = db.Column(db.Integer)
    screenShots = db.Column(db.String, nullable=True)
def loadsections():
    global app
    with app.app_context():
        global homepageDataCfg
        homepageDataCfg["sections"]=[]
        for i in home_adpost:
            apps2 = []
            for app2 in i["apps"]:
                # load app_data
                app_data = App.query.filter_by(id=app2).first()
                # covert to json
                dicts = app_data.__dict__
                dicts["screenShots"] = json.loads(dicts["screenShots"])
                dicts.pop("appReleases")
                dicts.pop("_sa_instance_state")
                apps2.append(dicts)
            dat = {"name":i["name"],"apps":apps2}
            homepageDataCfg["sections"].append(dat)
loadsections()

class User(db.Model):
    username = db.Column(db.String, unique=True, nullable=False, primary_key=True)
    password = db.Column(db.String, nullable=False)
    myApps = db.Column(db.String, nullable=False)

    def correct_password(self, password):
        if hasher.hash(password) == self.password:
            return True
        else:
            return False

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def get_id(self):
        return self.username

    def __repr__(self):
        return "<User %r>" % self.username


class Admin(db.Model):
    username = db.Column(db.String, unique=True, nullable=False, primary_key=True)
    password = db.Column(db.String, nullable=False)

    def __init__(self):
        self.auth = False

    def correct_password(self, password):
        if hasher.hash(password) == self.password:
            return True
        else:
            return False

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def get_id(self):
        return self.username

    def __repr__(self):
        return "<Admin %r>" % self.username


@app.route("/favicon.ico")
def favicon():
    return send_file("static/favicon.ico")


@app.route("/console/newapp")
@flask_login.login_required
def newappui():
    return render_template("newapp.html")


def checkReleaseCollision(id, version):
    app_data = App.query.filter_by(id=id).first()
    appReleases = json.loads(app_data.appReleases)[::-1]
    for i in appReleases:
        release = ReleaseInfo.query.filter_by(id=i).first()
        if release.verCode >= int(version):
            return True


def decomposePack(packdir):
    with ZipFile(packdir, "r") as inzipfile:
        for infile in (name for name in inzipfile.namelist() if name[-1] != "/"):
            if "module.json" in os.path.split(infile):
                packinfo = json.loads(inzipfile.open(infile, "r").read())
    # Check Permissions
    permissions = []
    bundleName = packinfo["app"]["bundleName"]
    minimumAPI = packinfo["app"]["minAPIVersion"]
    versionCode = packinfo["app"]["versionCode"]
    versionName = packinfo["app"]["versionName"]
    try:
        for perm in packinfo["module"]["requestPermissions"]:
            permissions.append(perm["name"])
    except:
        pass
    return (bundleName, permissions,versionCode,versionName,minimumAPI)


@app.route("/console/releases/<edit_url>")
@flask_login.login_required
def ar(edit_url):
    right = False
    if int(edit_url) in json.loads(flask_login.current_user.myApps):
        for i in getApps2():
            if i["id"] == int(edit_url):
                right = True
                break
    if not right:
        abort(503, "No permission")
    # get the app object from the database by the edit url
    app_data = App.query.filter_by(id=edit_url).first()
    appReleases = json.loads(app_data.appReleases)[::-1]
    # get Releases based on the list got
    releases = []
    for i in appReleases:
        release = ReleaseInfo.query.filter_by(id=i).first()
        releases.append(
            {
                "id": release.id,
                "version": release.version,
                "hapUrl": release.hapUrl,
                "releaseTime": release.releaseTime,
                "minimumAPI": release.minimumAPI,
                "minimumOldVersion": release.minimumOldVersion,
                "downloadLatestIfNew": release.downloadLatestIfNew,
                "deviceType": release.deviceType,
                "archType": release.archType,
                "changeLog": release.changeLog,
                "requiredPerm": release.requiredPerm,
                "verCode": release.verCode,
            }
        )
    return render_template("releases.html",releases=releases,url=edit_url)

@app.route("/console/releases/<edit_url>/edit/<int:id>",methods=['POST','GET'])
@flask_login.login_required
def editrel(edit_url,id):
    right = False
    if int(edit_url) in json.loads(flask_login.current_user.myApps):
        for i in getApps2():
            if i["id"] == int(edit_url):
                right = True
                break
    if not right:
        abort(503, "No permission")
    app_data = App.query.filter_by(id=edit_url).first()
    appReleases = json.loads(app_data.appReleases)[::-1]
    if id in appReleases:
        release = ReleaseInfo.query.filter_by(id=id).first()
        if request.method == 'POST':
            # Update the values from the form(changelog,minapi,minoldver,devtype,archtype)
            release.changeLog = request.form["desc"]
            release.minimumAPI = request.form["minapi"]
            release.minimumOldVersion = request.form["miov"]
            release.deviceType = request.form["devtype"]
            release.archType = request.form["archtype"] 
            # Update to database
            db.session.commit()
            flash("OK")
            return redirect(url_for("ar",edit_url=edit_url))
        else:
            # get the app object from the database by the edit url
            return render_template("editrelease.html",release=release,url=edit_url,id=id)
    else:
        abort(404)

@app.route("/console/releases/<edit_url>/delete/<int:id>")
@flask_login.login_required
def delrel(edit_url,id):
    right = False
    if int(edit_url) in json.loads(flask_login.current_user.myApps):
        for i in getApps2():
            if i["id"] == int(edit_url):
                right = True
                break
    if not right:
        abort(503, "No permission")
    app_data = App.query.filter_by(id=edit_url).first()
    appReleases = json.loads(app_data.appReleases)[::-1]
    if id in appReleases:
        release = ReleaseInfo.query.filter_by(id=id).first()
        #delete file first
        if os.path.isfile(release.hapUrl):
            # delete
            os.remove(release.hapUrl)
        # Delete the release from the database
        db.session.delete(release)
        db.session.commit()
        # delete the release from the application 
        appReleases.remove(id)
        # push to DB
        app_data.appReleases = json.dumps(appReleases)
        db.session.commit()
        flash("OK")
        return redirect(url_for("ar",edit_url=edit_url))
    else:
        abort(404)

@app.route("/console/releases/new/<edit_url>", methods=["POST", "GET"])
@flask_login.login_required
def arn(edit_url):
    right = False
    if int(edit_url) in json.loads(flask_login.current_user.myApps):
        for i in getApps2():
            if i["id"] == int(edit_url):
                right = True
                break
    if not right:
        abort(503, "No permission")
    # get the app object from the database by the edit url
    app_data = App.query.filter_by(id=edit_url).first()
    if request.method == "GET":
        return render_template("upload.html")
    else:
        if not all(
            key in request.form
            for key in [
                "name",
                "namec",
                "desc",
                "minapi",
                "miov",
                "archtype",
                "devtype",
            ]
        ):
            abort(400, "Missing required fields")
        # check if the request has the icon and hap files
        if "hap" not in request.files:
            abort(400, "Missing icon or hap file")
        hap_file = request.files["hap"]
        # check if the files have valid names
        if hap_file.filename == "":
            abort(400, "No selected file")
        if not os.path.exists("data" + os.sep + app_data.packageName):
            os.mkdir("data" + os.sep + app_data.packageName)

        if not checkReleaseCollision(edit_url, request.form["namec"]):
            hap_filename = (
                app_data.packageName
                + os.sep
                + app_data.packageName
                + "-"
                + request.form["name"]
                + ".hap"
            )
            hap_file.save(os.path.join(app.config["UPLOAD_FOLDER"], hap_filename))
            dpack = decomposePack(
                packdir=os.path.join(app.config["UPLOAD_FOLDER"], hap_filename)
            )
            if dpack[0] != app_data.packageName:
                abort(400, "Bundle name does not match package name")
            db.session.add(
                ReleaseInfo(
                    version=dpack[3],
                    hapUrl=hap_filename,
                    releaseTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    minimumAPI=dpack[4],
                    minimumOldVersion=request.form["miov"],
                    downloadLatestIfNew=1,
                    deviceType=request.form["devtype"],
                    archType=request.form["archtype"],
                    changeLog=request.form["desc"],
                    requiredPerm=json.dumps(dpack[1]),
                    verCode=dpack[2],
                )
            )
            app_data.appReleases = json.dumps(
                json.loads(app_data.appReleases)
                + [
                    ReleaseInfo.query.filter_by(version=request.form["name"])
                    .first()
                    .id
                ]
            )
            db.session.commit()

        flash("OK")
        return redirect(url_for("consoleHome"))



@app.route("/edit2/<edit_url>", methods=["GET", "POST"])
@flask_login.login_required
def edit(edit_url):
    right = False
    if int(edit_url) in json.loads(flask_login.current_user.myApps):
        for i in getApps2():
            if i["id"] == int(edit_url):
                right = True
                break
    if not right:
        abort(503, "No permission")
    # get the app object from the database by the edit url
    app_data = App.query.filter_by(id=edit_url).first()

    # check if the app exists
    if app_data is None:
        abort(404, "App not found")

    # if the request is GET, return the app data as json
    if request.method == "GET":
        ss = json.loads(app_data.screenShots)
        return render_template("edit.html", s=app_data, ss=ss)

    # if the request is POST, update the app data with the new values from the request
    if request.method == "POST":
        # check if the request has any of the fields to update
        if any(
            key in request.form
            for key in ["name", "desc", "version", "openSourceAddress", "releaseTime"]
        ):
            # update the fields that are present in the request
            if "name" in request.form:
                app_data.name = request.form["name"]
            if "desc" in request.form:
                app_data.desc = request.form["desc"]
            if "desc2" in request.form:
                app_data.desc = request.form["desc"]
            if "openSourceAddress" in request.form:
                app_data.openSourceAddress = request.form["openSourceAddress"]
            if "releaseTime" in request.form:
                app_data.releaseTime = request.form["releaseTime"]
        if request.files["icon"].filename != "":
            icon_file = request.files["icon"]
            icon_filename = app_data.packageName + os.sep + "icon.png"
            icon_file.save(os.path.join(app.config["UPLOAD_FOLDER"], icon_filename))
            app_data.icon = "/" + os.path.join(
                app.config["UPLOAD_FOLDER"], icon_filename
            ).replace("\\", "/")
        # check if the request has new icon or hap files to update
        # commit the changes to the database
        db.session.commit()
        flash("更新成功")
        # return a success message
        return redirect(url_for("consoleHome"))


@app.route("/edit/screenshots/<edit_url>", methods=["GET", "POST"])
@flask_login.login_required
def scrsht(edit_url):
    # get the app object from the database by the edit url
    app_data = App.query.filter_by(id=edit_url).first()
    # check if the app exists
    if app_data is None:
        abort(404, "App not found")
    # if the request is GET, return the app data as json
    if request.method == "GET":
        return render_template("screenshot.html", s=app_data)
    # if the request is POST, update the app data with the new values from the request
    if request.method == "POST":
        # check if the request has any of the fields to update
        if request.files["screenshot"].filename != "":
            icon_file = request.files["screenshot"]
            icon_filename = (
                app_data.packageName
                + os.sep
                + str(uuid.uuid4())
                + "."
                + request.files["screenshot"].filename.split(".")[-1]
            )
            icon_file.save(os.path.join(app.config["UPLOAD_FOLDER"], icon_filename))
            ss = json.loads(app_data.screenShots)
            ss.append(
                "/"
                + os.path.join(app.config["UPLOAD_FOLDER"], icon_filename).replace(
                    "\\", "/"
                )
            )
            ss = json.dumps(ss)
            app_data.screenShots = ss
        # commit the changes to the database
        db.session.commit()
        flash("更新成功")
        # return a success message
        return redirect(url_for("consoleHome"))


@app.route("/edit/screenshots/delete/<edit_url>", methods=["GET", "POST"])
@flask_login.login_required
def scrshtdel(edit_url):
    # get the app object from the database by the edit url
    app_data = App.query.filter_by(id=edit_url).first()
    # check if the app exists
    if app_data is None:
        abort(404, "App not found")
    # if the request is GET, return the app data as json
    # wait


@login_manager.user_loader
def user_loader(username):
    return User.query.get(username)


@login_manager.unauthorized_handler
def not_logged_in():
    flash("You must login to view this page.")
    return redirect(url_for("login"))


@app.route("/homePageData")
@app.route("/homePageData.json")
def homepageData():
    return jsonify(homepageDataCfg)


@app.route("/console/home")
@flask_login.login_required
def consoleHome():
    apps = flask_login.current_user.myApps
    apps = json.loads(apps)

    return render_template("apps.html", myApps=apps, apps=getApps2())


@app.route("/console/addApp")
@flask_login.login_required
def consoleAddapp():
    return render_template("upload2.html")


@app.route("/allAppList")
@app.route("/allAppList.json")
def allApps():
    # query all apps(permitted) from the database
    apps = App.query.all()

    # convert each app object to a dictionary and store them in a list
    apps_list = [app.__dict__ for app in apps]
    apps = []
    for dicts in apps_list:
        dicts["screenShots"] = json.loads(dicts["screenShots"])
        dicts.pop("appReleases")
        dicts.pop("_sa_instance_state")
    # return the list as json
    return jsonify(apps_list)


@app.route("/console/newappup", methods=["POST"])
@flask_login.login_required
def newapp():
    # check if the request has all the required fields
    if not all(
        key in request.form
        for key in ["name", "desc", "desc2", "packageName", "tags", "openSourceAddress"]
    ):
        abort(400, "Missing required fields")

    # get the icon and hap files from the request
    icon_file = request.files["icon"]

    # hap_file = request.files['hap']
    if not os.path.exists("data" + os.sep + request.form["packageName"]):
        os.mkdir("data" + os.sep + request.form["packageName"])
    if icon_file.filename != "":
        icon_filename = request.form["packageName"] + os.sep + "icon.png"
        icon_file.save(os.path.join(app.config["UPLOAD_FOLDER"], icon_filename))
    else:
        icon_filename = "default_icon.png"
    # save the files to the upload folder with secure names
    # create a new app object with the data from the request and the files
    app_data = App(
        id=len(App.query.all()) + 1,
        name=request.form["name"],
        desc=request.form["desc"],
        maindesc=request.form["desc2"],
        icon="/"
        + os.path.join(app.config["UPLOAD_FOLDER"], icon_filename).replace("\\", "/"),
        vender=flask_login.current_user.username,
        packageName=request.form["packageName"],
        tags=request.form["tags"],
        website=request.form["openSourceAddress"],
        screenShots="[]",
        downloadCount=0,
        comments="[]",
        stars=0,
        appReleases="[]",
    )
    if not App.query.filter_by(packageName=request.form["packageName"]) == []:
        # add the app object to the database and commit the changes
        db.session.add(app_data)
        apps = json.loads(flask_login.current_user.myApps)
        apps.append(len(App.query.all()))
        User.query.filter_by(username=flask_login.current_user.username).update(
            dict(myApps=json.dumps(apps))
        )
        db.session.commit()
        flash("上传成功。")
    else:
        flash("包名称已存在。")
    return redirect(url_for("consoleHome"))
    # return a success message with the edit url
    # return jsonify({'message': 'App uploaded successfully', 'editUrl': app_data.editUrl})


@app.route("/console/logout")
@flask_login.login_required
def logout():
    flask_login.logout_user()
    flash("登出成功")
    return redirect(url_for("login"))


@app.route("/admin/login", methods=["POST", "GET"])
def adminLogin():
    if request.method == "POST":
        if request.form["floatingPassword"] == os.environ["ADMIN_PASSWORD"]:
            flash("Login Success")
            session["admin"] = "admin"
            return redirect(url_for("admin"))
        else:
            flash("Password Incorrect")
    return render_template("admlogin.html")


@app.route("/admin/home")
def admin():
    if "admin" not in session:
        flash("Login required")

        return redirect(url_for("adminLogin"))
    else:
        return render_template("permitlist.html", apps=getApps())
@app.route('/admin/sections')
def listsections():
    if "admin" not in session:
        flash("Login required")
        return redirect(url_for("adminLogin"))
    else:
        return render_template("admsections2.html", data=homepageDataCfg)
@app.route('/admin/del/section/<int:id>')
def listsection2s(id):
    global home_adpost
    if "admin" not in session:
        flash("Login required")
        return redirect(url_for("adminLogin"))
    else:
        flash("OK")
        del home_adpost[id]
        loadsections()
        return redirect(url_for("admin"))
@app.route("/admin/addsections",methods=['POST','GET'])
def admins():
    if "admin" not in session:
        flash("Login required")

        return redirect(url_for("adminLogin"))
    else:
        if request.method == "POST":
            apps = request.form.getlist("formDoor[]")
            # ID Of apps ^
            home_adpost.append({"name":request.form["name"],"apps":apps})
            loadsections()
            with open("data/home_adpost.json", "w") as f:
                f.write(json.dumps(home_adpost))
            flash("添加成功")
            return redirect(url_for("admins"))
        else:
            return render_template("admsections.html", apps=getApps())

@app.route("/admin/info/<int:id>")
def view(id: int):
    if "admin" not in session:
        flash("Login required")

        return redirect(url_for("adminLogin"))
    else:
        app_data = App.query.filter_by(id=id).first()
        # check if the app exists
        if app_data is None:
            abort(404, "App not found")
        ss = json.loads(app_data.screenShots)
        return render_template("appinfo.html", s=app_data,ss=ss)

@app.route("/admin/danger/removeapp/<int:id>")
def permde(id: int):
    if "admin" not in session:
        flash("Login required")

        return redirect(url_for("adminLogin"))
    else:
        app_data = App.query.filter_by(id=id).first()
        # delete app_data and all its release
        #get release first
        releases = json.loads(app_data.appReleases)
        # read the tables in the releaseinfo
        for release in releases:
            release_data = ReleaseInfo.query.filter_by(id=release).first()
            # delete the release info
            db.session.delete(release_data)
        # delete the app
        db.session.delete(app_data)
        # delete the app folder
        os.remove("data" + os.sep + app_data.packageName)
        # commit the changes
        db.session.commit()
        flash("删除成功")
        return redirect(url_for("admin"))

@app.route("/admin/logout")
def admLogout():
    if "admin" in session:
        session.pop("admin")
        return redirect(url_for("home"))
    else:
        return redirect(url_for("admin"))


@app.route("/data/default_icon.png")
def png():
    return send_file("static/default_icon.png")

@app.route("/data/<pkg>/<filename>")
def get3(pkg,filename):
    if ".hap" in filename:
        return {"error":"access denied"},403
    try:
        return send_file("data" + os.sep + pkg + os.sep + filename)
    except:
        return send_file("static/default_icon.png")
    
@app.route("/data/<pkg>/icon.png")
def get2(pkg):
    try:
        return send_file("data" + os.sep + pkg + os.sep + "icon.png")
    except:
        return send_file("static/default_icon.png")

@app.route('/fetchinfo/<pkg>',methods=['POST'])
def fetchinfo(pkg):
    #api arch curver devtyp
    currentApi = request.json["currentApi"]
    archType = request.json["archType"]
    curver = request.json["currentVersion"]
    devType = request.json["devType"]
    #print(currentApi,archType,curver,devType)
    if any((devType, archType, currentApi)) is None:
        return {"msg":"not enough info"},404
    try:
        app_data = App.query.filter_by(packageName=pkg).first()
        releases = json.loads(app_data.appReleases)[::-1]
        for rel in releases:
            # fetch from Releases DB(rel = ID of release)
            rel_data = ReleaseInfo.query.filter_by(id=rel).first()
            if rel_data.minimumAPI <= int(currentApi) and rel_data.archType == archType and rel_data.deviceType == devType:
                if curver == None:
                    if rel_data.downloadLatestIfNew:
                        #rel_data object convert to json
                        return rel_dat_cvt(rel_data)
                else:
                    # check if current version no larger than minium version
                    if rel_data.minimumOldVersion <= curver:
                        return rel_dat_cvt(rel_data)
    except:
        pass
    return { "id": -1, "version": "undefined-recevied-from-server", "hapUrl": "undefined", "releaseTime": "undefined", "minimumAPI": 9999, "minimumOldVersion": 9999, "downloadLatestIfNew": 0, "deviceType": "phone", "archType": "arm", "changeLog": "undefined", "requiredPerm": [], "verCode": -100 }
@app.route('/download/<uuid>.hap')
def downloadhaps(uuid):
    if uuid in download_urls:
        dl = download_urls[uuid]
        #download_urls.pop(uuid)
        app_data = App.query.filter_by(packageName=dl.split(os.sep)[0]).first()
        app_data.downloadCount += 1
        db.session.commit()
        return send_file("data" + os.sep + dl)
    else:
        return abort(404)
def rel_dat_cvt(rel_data:ReleaseInfo):
    out = rel_data.__dict__
    out.pop("_sa_instance_state")
    out["requiredPerm"] = json.loads(out["requiredPerm"])
    dluuid = uuid.uuid4().hex
    download_urls[dluuid] = rel_data.hapUrl
    out["hapUrl"] = '/download/'+dluuid+'.hap'
    #print(out)
    return out
@app.route("/data/<pkg>/<file>")
def get(pkg, file):
    if "hap" in file:
        abort(404)
    try:
        return send_file("data" + os.sep + pkg + os.sep + file)
    except Exception as e:
        abort(404)


def appCount():
    # query all apps(permitted) from the database
    apps = App.query.all()

    # convert each app object to a dictionary and store them in a list
    apps_list = [app.__dict__ for app in apps]
    apps = []
    games = 0
    apps = 0
    all = 0
    for dicts in apps_list:
        all += 1

    return [all, apps, games]


def getApps():
    # query all apps(permitted) from the database
    apps = App.query.all()

    # convert each app object to a dictionary and store them in a list
    apps_list = [app.__dict__ for app in apps]
    apps = []
    for dicts in apps_list:
        # dicts.pop('editUrl')
        dicts.pop("_sa_instance_state")
    # return the list as json
    return apps_list


def getApps2():
    # query all apps(permitted) from the database
    apps = App.query.all()

    # convert each app object to a dictionary and store them in a list
    apps_list = [app.__dict__ for app in apps]
    apps = []
    for dicts in apps_list:
        # dicts.pop('editUrl')
        dicts.pop("_sa_instance_state")
    # return the list as json
    return apps_list


@app.route("/")
def home():
    return render_template("home.html", data=homepageDataCfg, appcount=appCount())


@app.route("/apps")
def apps():
    return render_template("appslist.html", apps=getApps(), type="app")


@app.route("/games")
def games():
    return render_template("appslist.html", apps=getApps(), type="game")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        if "floatingInput" in request.form and "floatingPassword" in request.form:
            user = User.query.get(request.form["floatingInput"])
            if not user:
                hasher = Hashing()
                user = User(
                    username=request.form["floatingInput"],
                    password=hasher.hash(request.form["floatingPassword"]),
                    myApps="[]",
                )
                db.session.add(user)
                db.session.commit()
                flash("用户创建成功。")
            else:
                flash("用户已存在，请登录。")
            return redirect(url_for("login"))
        else:
            flash("输入无效")
    else:
        return redirect(url_for("login"))


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        if "floatingInput" in request.form and "floatingPassword" in request.form:
            user = User.query.get(request.form["floatingInput"])
            if user:
                if user.correct_password(request.form["floatingPassword"]):
                    user.auth = True
                    flask_login.login_user(user)
                    flash("登录成功。")
                    return redirect(url_for("consoleHome"))
                else:
                    flash("用户名或密码不正确。")
            else:
                flash("找不到用户。请检查拼写错误，然后重试。")
        else:
            flash("输入无效。")
    else:
        pass
    return render_template("login.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8889)
