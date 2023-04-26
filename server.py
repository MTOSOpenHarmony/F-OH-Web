
from flask import Flask, request, jsonify, abort, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import uuid
from dotenv import load_dotenv
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///apps.db'
app.config['UPLOAD_FOLDER'] = '/data'
db = SQLAlchemy(app)


class App(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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

@app.route('/upload', methods=['POST'])
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
    if icon_file.filename == '' or hap_file.filename == '':
        abort(400, 'No selected file')
    if 'icon' in request.files:
        icon_filename = request.form['packageName']+os.sep+"icon.png"
        icon_file.save(os.path.join(app.config['UPLOAD_FOLDER'], icon_filename))
    else:
        icon_filename = os.path.join(app.config['UPLOAD_FOLDER'], "default_icon.png")
    hap_filename = request.form['packageName']+os.sep+"-"+request.form["name"]+request.form['version']+".hap"
    hap_file.save(os.path.join(app.config['UPLOAD_FOLDER'], hap_filename))
    # save the files to the upload folder with secure names
    
    # create a new app object with the data from the request and the files
    app_data = App(
        name=request.form['name'],
        desc=request.form['desc'],
        icon=os.path.join(app.config['UPLOAD_FOLDER'], icon_filename),
        vender=request.form['vender'],
        packageName=request.form['packageName'],
        version=request.form['version'],
        hapUrl=os.path.join(app.config['UPLOAD_FOLDER'], hap_filename),
        type=request.form['type'],
        tags=request.form['tags'],
        openSourceAddress=request.form['openSourceAddress'],
        releaseTime=request.form['releaseTime'],
        editUrl=str(uuid.uuid4()),  # generate a unique edit url
        permitted=0
    )

    # add the app object to the database and commit the changes
    db.session.add(app_data)
    db.session.commit()

    # return a success message with the edit url
    return jsonify({'message': 'App uploaded successfully', 'editUrl': app_data.editUrl})


@app.route('/edit/<edit_url>', methods=['GET', 'POST'])
def edit(edit_url):
    # get the app object from the database by the edit url
    app_data = App.query.filter_by(editUrl=edit_url).first()

    # check if the app exists
    if app_data is None:
        abort(404, 'App not found')

    # if the request is GET, return the app data as json
    if request.method == 'GET':
        return jsonify(app_data.__dict__)

    # if the request is POST, update the app data with the new values from the request
    if request.method == 'POST':
        # check if the request has any of the fields to update
        if any(key in request.form for key in ['name', 'desc', 'vender', 'packageName', 'version', 'type', 'tags', 'openSourceAddress', 'releaseTime']):
            # update the fields that are present in the request
            if 'name' in request.form:
                app_data.name = request.form['name']
            if 'desc' in request.form:
                app_data.desc = request.form['desc']
            if 'vender' in request.form:
                app_data.vender = request.form['vender']
            if 'packageName' in request.form:
                app_data.packageName = request.form['packageName']
            if 'version' in request.form:
                app_data.version = request.form['version']
            if 'type' in request.form:
                app_data.type = request.form['type']
            if 'tags' in request.form:
                app_data.tags = request.form['tags']
            if 'openSourceAddress' in request.form:
                app_data.openSourceAddress = request.form['openSourceAddress']
            if 'releaseTime' in request.form:
                app_data.releaseTime = request.form['releaseTime']

        # check if the request has new icon or hap files to update
        if 'icon' in request.files or 'hap' in request.files:
            # delete the old files from the upload folder
            os.remove(app_data.icon)
            os.remove(app_data.hapUrl)

            # get the new files from the request
            icon_file = request.files['icon']
            hap_file = request.files['hap']

            # check if the files have valid names
            if icon_file.filename == '' or hap_file.filename == '':
                abort(400, 'No selected file')

            # save the new files to the upload folder with secure names
            icon_filename = secure_filename(icon_file.filename)
            hap_filename = secure_filename(hap_file.filename)
            icon_file.save(os.path.join(
                app.config['UPLOAD_FOLDER'], icon_filename))
            hap_file.save(os.path.join(
                app.config['UPLOAD_FOLDER'], hap_filename))

            # update the app data with the new file paths
            app_data.icon = os.path.join(
                app.config['UPLOAD_FOLDER'], icon_filename)
            app_data.hapUrl = os.path.join(
                app.config['UPLOAD_FOLDER'], hap_filename)

        # commit the changes to the database
        db.session.commit()

        # return a success message
        return jsonify({'message': 'App updated successfully'})

@app.route('/homePageData')
@app.route('/homePageData.json')
def homepageData():
    return jsonify({"showAnnouncement":True,"announcement":"- Backend server beta 0.0.1\n- Internal Beta\n- Testing Purposes Only"})
@app.route('/allAppList')
@app.route('/allAppList.json')
def allApps():
    # query all apps(permitted) from the database
    apps = App.query.filter_by(permitted=1)

    # convert each app object to a dictionary and store them in a list
    apps_list = [app.__dict__ for app in apps]

    # return the list as json
    return jsonify(apps_list)

@app.route('/unpermitted',methods=['POST'])
def unpermitted():
    try:
        if request.form["password"] == os.environ("ADMIN_PASSWORD"):
            # query all apps(unpermitted) from the database
            apps = App.query.filter_by(permitted=0)

            # convert each app object to a dictionary and store them in a list
            apps_list = [app.__dict__ for app in apps]

            # return the list as json
            return jsonify(apps_list)
        else:
            abort(404)
    except:
        abort(404)
    
@app.route('/admin/permit',methods=['POST'])
def permit():
    try:
        if request.form["password"] == os.environ("ADMIN_PASSWORD"):
            if "appID" not in request.form:
                abort(400,'Missing appID')
            else:
                app_data = App.query.filter_by(id=request.formappID).first()
                if not app_data:
                    abort(404,'App not found')
                else:
                    app_data.permitted = 1
                    db.session.commit()
        else:
            abort(404)
    except:
        abort(404)


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')