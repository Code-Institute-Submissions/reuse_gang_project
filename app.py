import os
from flask import Flask, render_template, redirect, request, url_for, jsonify, flash, session, Response
from flask_session import Session
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from bson.json_util import dumps
from werkzeug.security import generate_password_hash, check_password_hash

from os import path
# import file where username and password of MongoDB is saved
if path.exists("env.py"):
    import env

app = Flask(__name__)  # create instance of flask

# add configuration to Flask app
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["MONGODB_NAME"] = "reuse-gang"
app.config["MONGO_URI"] = os.environ["MONGODB_URI"]

# create an instance of Pymongo with app object being pushed as argument
mongo = PyMongo(app)

@app.route('/')
def home():
    return render_template('/pages/home.html', items=mongo.db.items.find(),
                           users=mongo.db.users.find(), title="Re-Use Gang")


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == "POST":
        users = mongo.db.users
        used_name = users.find_one({'username': request.form["username"]})
        print(used_name)
        used_email = users.find_one({'email': request.form["email"]})
        print(used_email)
        # trick found here to write if statement https://stackoverflow.com/questions/19400115/python-difference-between-x-is-not-none-and-y-is-not-none-and-x-and-y-is-n
        if (used_email or used_name) is None:
            user_pwd = generate_password_hash(request.form["password"])
            users.insert_one({
                "username": request.form["username"],
                "email": request.form["email"], 
                "password": user_pwd
                })
            session['username'] = request.form["username"]
            flash("Welcome to the Gang, " + session['username'] + "!")
            return redirect(url_for('home'))
        elif used_name is not None:
            flash("This username already exists, please choose another one")
            return redirect(url_for('register'))
        else:
            flash("This email address is already registered, would you like to log in instead?")
            return redirect(url_for('login'))
        
    return render_template('/components/register.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        users = mongo.db.users
        matched_user = users.find_one({'email': request.form["email"]})
        
        if matched_user:
            if check_password_hash(matched_user["password"], request.form["password"]):
                flash("Welcome back " + matched_user["username"])
                session['username'] = matched_user["username"]
                return redirect(url_for('home'))
            else:
                flash("You've entered the wrong password")
                return redirect(url_for('login'))
        else:
            flash("This email address is unknown to our records.")
            return redirect(url_for('login'))
                    
    return render_template('/components/login.html')


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    # remove the username from the session if it's there
    [session.pop(key) for key in list(session.keys())]
    flash('You have successfully logged out!')
    return redirect(url_for('home'))


@app.route('/items/filter', methods=["POST", "GET"])
def filter_items():
    cat = request.get_json()
    if cat == 'default':
        all_items = mongo.db.items.find()
        return dumps(all_items)
    else:
        found_items = mongo.db.items.find({'item_category': cat})
        return dumps(found_items)


@app.route('/items/add', methods=["POST", "GET"])
def add_item():
    categories = ["Kids", "Outdoor", "Household", "Other"]

    if request.method == "POST":
        items = mongo.db.items
        item_owner = mongo.db.users.find_one({'username': session['username']})
        items.insert_one({
            'username': session['username'],
            'item_contact': item_owner['email'],
            'item_name': request.form['item_name'],
            'item_category': request.form['item_category'],
            'item_description': request.form['item_description'],
            'item_location': request.form['item_location'],
            'item_img': request.form['item_img']
        })
        flash("Thanks!Your free stuff will be shared immediately with the gang.")
        return redirect(url_for('home'))
    else:
        if "username" not in session:
            return redirect(url_for('login'))
        else:
            return render_template('/pages/additem.html', categories=categories)


@app.route('/items/update/<item_id>', methods=["POST", "GET"])
def update_item(item_id):
    if request.method == "POST":
        items = mongo.db.items
        item_owner = mongo.db.users.find_one({'username': session['username']})
        items.update({'_id': ObjectId(item_id)},
                     {
            'username': session['username'],
            'item_name': request.form.get('item_name'),
            'item_contact': item_owner['email'],
            'item_category': request.form.get('item_category'),
            'item_description': request.form.get('item_description'),
            'item_location': request.form.get('item_location'),
            'item_img': request.form.get('item_img')
            })
        flash("We've successfully updated your stuff.")
        return redirect(url_for('home'))
    else:
        clicked_item = mongo.db.items.find_one({'_id': ObjectId(item_id)})
        if "username" not in session:
            return redirect(url_for('login'))
        else:
            return render_template('/pages/updateitem.html', item=clicked_item)


@app.route('/items/delete/<item_id>', methods=["POST"])
def delete_item(item_id):
    if request.method == "POST":
        item = mongo.db.items.find({'_id': ObjectId(item_id)})
        for i in item:
            itemName = i['item_name']
        mongo.db.items.remove({'_id': ObjectId(item_id)})
        flash(itemName + "has been deleted")
        return redirect(url_for('home'))


@app.errorhandler(500)
def internal_error(e):
    return "500 error"


@app.errorhandler(404)
def not_found(error):
    return render_template("/pages/404.html")


if __name__ == "__main__":
    app.run(host=os.getenv("IP", "0.0.0.0"),
            port=int(os.getenv("PORT", "5000")),
            debug=True)
