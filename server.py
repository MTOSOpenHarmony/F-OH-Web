
import json
from flask import Flask, flash, request, jsonify, abort, redirect, send_file, session, url_for, render_template, Markup, redirect
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///apps.db'
app.config['UPLOAD_FOLDER'] = 'data'
db = SQLAlchemy(app)
app.secret_key = "ABCDEFGOH-F"
homepageDataCfg = {"showAnnouncement": True,
                   "announcement": "- Backend server beta 0.0.1\n- Internal Beta\n- Testing Purposes Only"}
login_manager = flask_login.LoginManager()
login_manager.init_app(app)


class App(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    desc = db.Column(db.String(200), nullable=False)
    icon = db.Column(db.String(200), nullable=False)
    vender = db.Column(db.String(80), nullable=False)
    packageName = db.Column(db.String(80), nullable=False)
    version = db.Column(db.String(20), nullable=False)
    hapUrl = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    tags = db.Column(db.String(200), nullable=False)
    openSourceAddress = db.Column(db.String(200), nullable=False)
    releaseTime = db.Column(db.String(20), nullable=False)
    editUrl = db.Column(db.String(200), unique=True, nullable=False)
    permitted = db.Column(db.Integer, primary_key=True)


class User(db.Model):
    username = db.Column(db.String, unique=True,
                         nullable=False, primary_key=True)
    password = db.Column(db.String, nullable=False)
    myApps = db.Column(db.String, nullable=False)

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
        return '<User %r>' % self.username


# db.create_all()


@app.route('/favicon.ico')
def favicon():
    return send_file('static/favicon.ico')


@app.route('/edit2/<int:id>')
def edit2(id: int):
    if id in json.loads(flask_login.current_user.myApps):
        for i in getApps2():
            if i["id"] == int(id):
                return redirect(url_for("edit", edit_url=i["editUrl"]))


@app.route('/upload', methods=['POST'])
@flask_login.login_required
def upload():

    # check if the request has all the required fields
    if not all(key in request.form for key in ['name', 'desc', 'vender', 'packageName', 'version', 'type', 'tags', 'openSourceAddress', 'releaseTime']):
        abort(400, 'Missing required fields')

    # check if the request has the icon and hap files
    if 'hap' not in request.files:
        abort(400, 'Missing icon or hap file')

    # get the icon and hap files from the request
    icon_file = request.files['icon']

    hap_file = request.files['hap']

    # check if the files have valid names
    if hap_file.filename == '':
        abort(400, 'No selected file')
    if not os.path.exists('data'+os.sep+request.form['packageName']):
        os.mkdir('data'+os.sep+request.form['packageName'])
    if icon_file.filename != "":
        icon_filename = request.form['packageName']+os.sep+"icon.png"
        icon_file.save(os.path.join(
            app.config['UPLOAD_FOLDER'], icon_filename))
    else:
        icon_filename = "default_icon.png"
    hap_filename = request.form['packageName']+os.sep + \
        request.form["name"]+"-"+request.form['version']+".hap"
    hap_file.save(os.path.join(app.config['UPLOAD_FOLDER'], hap_filename))
    # save the files to the upload folder with secure names

    # create a new app object with the data from the request and the files
    app_data = App(
        id=len(App.query.all())+1,
        name=request.form['name'],
        desc=request.form['desc'],
        icon="/" +
        os.path.join(app.config['UPLOAD_FOLDER'],
                     icon_filename).replace("\\", "/"),
        vender=flask_login.current_user.username,
        packageName=request.form['packageName'],
        version=request.form['version'],
        hapUrl="/" +
        os.path.join(app.config['UPLOAD_FOLDER'],
                     hap_filename).replace("\\", "/"),
        type=request.form['type'],
        tags=request.form['tags'],
        openSourceAddress=request.form['openSourceAddress'],
        releaseTime=request.form['releaseTime'],
        editUrl=str(uuid.uuid4()),  # generate a unique edit url
        permitted=0
    )
    if not App.query.filter_by(packageName=request.form['packageName']) == []:
        # add the app object to the database and commit the changes
        db.session.add(app_data)
        apps = json.loads(flask_login.current_user.myApps)
        apps.append(len(App.query.all()))
        User.query.filter_by(username=flask_login.current_user.username).update(
            dict(myApps=json.dumps(apps)))
        db.session.commit()
        flash("上传成功，等待审核通过。")
    else:
        flash("包名称已存在。")
    return redirect(url_for("consoleHome"))
    # return a success message with the edit url
    # return jsonify({'message': 'App uploaded successfully', 'editUrl': app_data.editUrl})


@app.route('/edit/<edit_url>', methods=['GET', 'POST'])
def edit(edit_url):
    # get the app object from the database by the edit url
    app_data = App.query.filter_by(editUrl=edit_url).first()

    # check if the app exists
    if app_data is None:
        abort(404, 'App not found')

    # if the request is GET, return the app data as json
    if request.method == 'GET':
        return render_template("edit.html", s=app_data)

    # if the request is POST, update the app data with the new values from the request
    if request.method == 'POST':
        # check if the request has any of the fields to update
        if any(key in request.form for key in ['name', 'desc', 'version',  'openSourceAddress', 'releaseTime']):
            # update the fields that are present in the request
            if 'name' in request.form:
                app_data.name = request.form['name']
            if 'desc' in request.form:
                app_data.desc = request.form['desc']
            if 'version' in request.form:
                app_data.version = request.form['version']
            if 'openSourceAddress' in request.form:
                app_data.openSourceAddress = request.form['openSourceAddress']
            if 'releaseTime' in request.form:
                app_data.releaseTime = request.form['releaseTime']
        if request.files['icon'].filename != "":
            icon_file = request.files['icon']
            icon_filename = app_data.packageName+os.sep+"icon.png"
            icon_file.save(os.path.join(
                app.config['UPLOAD_FOLDER'], icon_filename))
            app_data.icon = "/"+os.path.join(
                app.config['UPLOAD_FOLDER'], icon_filename).replace("\\", "/")
        # check if the request has new icon or hap files to update
        if request.files['hap'].filename != "":
            # delete the old files from the upload folder

            # os.remove(app_data.hapUrl)

            # get the new files from the request

            hap_file = request.files['hap']

            # check if the files have valid names
            if hap_file.filename == '':
                abort(400, 'No selected file')

            # save the new files to the upload folder with secure names

            hap_filename = app_data.packageName+os.sep + \
                request.form["name"]+"-"+request.form['version']+".hap"
            hap_file.save(os.path.join(
                app.config['UPLOAD_FOLDER'], hap_filename))

            # update the app data with the new file paths

            app_data.hapUrl = "/"+os.path.join(
                app.config['UPLOAD_FOLDER'], hap_filename).replace("\\", "/")

        # commit the changes to the database
        db.session.commit()
        flash("更新成功")
        # return a success message
        return redirect(url_for("consoleHome"))


@login_manager.user_loader
def user_loader(username):
    return User.query.get(username)


@login_manager.unauthorized_handler
def not_logged_in():
    flash("You must login to view this page.")
    return redirect(url_for("login"))


@app.route('/homePageData')
@app.route('/homePageData.json')
def homepageData():
    return jsonify(homepageDataCfg)


@app.route('/console/home')
@flask_login.login_required
def consoleHome():
    apps = flask_login.current_user.myApps
    apps = json.loads(apps)

    return render_template("apps.html", myApps=apps, apps=getApps2())


@app.route('/console/addApp')
@flask_login.login_required
def consoleAddapp():
    return render_template("upload.html")


@app.route('/allAppList')
@app.route('/allAppList.json')
def allApps():
    # query all apps(permitted) from the database
    apps = App.query.filter_by(permitted=1)

    # convert each app object to a dictionary and store them in a list
    apps_list = [app.__dict__ for app in apps]
    apps = []
    for dicts in apps_list:
        dicts.pop('editUrl')
        dicts.pop('_sa_instance_state')
    # return the list as json
    return jsonify(apps_list)


def unpermitted():
    apps = App.query.filter_by(permitted=0)

    # convert each app object to a dictionary and store them in a list
    apps_list = [app.__dict__ for app in apps]
    for dicts in apps_list:
        dicts.pop('editUrl')
        dicts.pop('_sa_instance_state')
    # return the list as json
    return apps_list


@app.route('/console/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    flash("登出成功")
    return redirect(url_for("login"))


@app.route('/admin/login', methods=['POST', 'GET'])
def adminLogin():
    if request.method == 'POST':
        if request.form["floatingPassword"] == os.environ["ADMIN_PASSWORD"]:
            flash("Login Success")
            session['admin'] = 'admin'
            return redirect(url_for("admin"))
        else:
            flash("Password Incorrect")
    return render_template("admlogin.html")


@app.route('/admin/home')
def admin():
    if "admin" not in session:
        flash("Login required")

        return redirect(url_for("adminLogin"))
    else:
        return render_template("permitlist.html", apps=unpermitted(), apps2=getApps())


@app.route('/admin/info/<int:id>')
def view(id: int):
    if "admin" not in session:
        flash("Login required")

        return redirect(url_for("adminLogin"))
    else:
        app_data = App.query.filter_by(id=id).first()
        # check if the app exists
        if app_data is None:
            abort(404, 'App not found')
        return render_template("appinfo.html", s=app_data)

@app.route('/admin/logout')
def admLogout():
    if "admin" in session:
        session.pop("admin")
        return redirect(url_for("home"))
    else:
        return redirect(url_for("admin"))

@app.route('/admin/permit/<int:id>')
def permit(id: int):
    if "admin" in session:
        app_data = App.query.filter_by(
            id=id).first()
        if not app_data:
            abort(404, 'App not found')
        else:
            if app_data.permitted == 1:
                app_data.permitted = 0
            else:
                app_data.permitted = 1
            db.session.commit()
            flash("修改成功")
            return redirect(url_for("admin"))
    else:
        flash("Login required")
        return redirect(url_for("adminLogin"))


@app.route('/data/default_icon.png')
def png():
    return send_file('static/default_icon.png')


@app.route('/data/<pkg>/icon.png')
def get2(pkg):
    try:
        return send_file("data"+os.sep+pkg+os.sep+'icon.png')
    except:
        return send_file('static/default_icon.png')


@app.route('/data/<pkg>/<file>')
def get(pkg, file):
    try:
        return send_file("data"+os.sep+pkg+os.sep+file)
    except:
        abort(404)


def appCount():
    # query all apps(permitted) from the database
    apps = App.query.filter_by(permitted=1)

    # convert each app object to a dictionary and store them in a list
    apps_list = [app.__dict__ for app in apps]
    apps = []
    games = 0
    apps = 0
    all = 0
    for dicts in apps_list:
        all += 1
        if dicts['type'] == 'app':
            apps += 1
        else:
            games += 1
    return [all, apps, games]


def getApps():
    # query all apps(permitted) from the database
    apps = App.query.filter_by(permitted=1)

    # convert each app object to a dictionary and store them in a list
    apps_list = [app.__dict__ for app in apps]
    apps = []
    for dicts in apps_list:
        dicts.pop('editUrl')
        dicts.pop('_sa_instance_state')
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
        dicts.pop('_sa_instance_state')
    # return the list as json
    return apps_list


@app.route('/')
def home():
    return render_template('home.html', data=homepageDataCfg, appcount=appCount())


@app.route('/apps')
def apps():
    return render_template('appslist.html', apps=getApps(), type='app')


@app.route('/games')
def games():
    return render_template('appslist.html', apps=getApps(), type='game')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        if "floatingInput" in request.form and "floatingPassword" in request.form:
            user = User.query.get(request.form["floatingInput"])
            if not user:
                hasher = Hashing()
                user = User(
                    username=request.form["floatingInput"],
                    password=hasher.hash(request.form["floatingPassword"]), myApps=[])
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


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
