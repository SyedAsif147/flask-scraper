from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify, send_from_directory, render_template_string, stream_with_context, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
import os
from functools import wraps
import pandas as pd
from wtforms import SelectField
from flask_wtf import FlaskForm
import numpy as np
import requests
from bs4 import BeautifulSoup
import pandas as pd
from lxml import html
import re
import sys
import random
import json
import time

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
upload_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname((__file__)))))

UPLOAD_DIRECTORY_MENU = os.path.join(basedir, 'menu_generated_data')
UPLOAD_DIRECTORY_REVIEW = os.path.join(basedir, 'review_generated_data')

app.config['SECRET_KEY'] ='jbfkesnbfkenfkjwnfkj' #os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+os.path.join(basedir,'details.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=False)
db = SQLAlchemy(app)

if not os.path.exists(UPLOAD_DIRECTORY_MENU):
    os.makedirs(UPLOAD_DIRECTORY_MENU)

if not os.path.exists(UPLOAD_DIRECTORY_REVIEW):
    os.makedirs(UPLOAD_DIRECTORY_REVIEW)

temp = 'ANDHRAPRADESH_Visakhapatnam_Kancharapalem_menu.json'

data={}

def gen_unique(data):
    data1 = np.array(data)
    return np.unique(data1)

header={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Accept-Encoding": "*",
    "Connection": "keep-alive",
    "Accept": "application/json", 
    "user-key": "API_KEY"
    } 

# Menu Scraper
def scraper_links(link):
    # link gen
    links=[]
    with requests.Session() as s:
        nums=6
        i=1
        while i<nums:
            url=s.get("{}?page={}&sort=best&nearby=0".format(link,i), headers=header)
            url_content=url.content
            soup=BeautifulSoup(url_content,"html.parser")
            div=soup.find("div",attrs={"class":"col-l-4 mtop pagination-number"})
            num =int(div.text.split("of")[-1])
            if num<nums:
                nums=num+1
            else:
                nums=6
            a=soup.find_all("a",attrs={"data-result-type":"ResCard_Name"})
            for k in a:
                links.append(k["href"])
            i=i+1
    links=list(set(links))
    return links

# Menu Scraper
def scraper_menu(links):
    # menu gen
    output=[]
    for a in links:
        main=[]
        with requests.Session() as s:
            url=s.get(a+"/order", headers=header)
            tree=html.fromstring(url.content)
            url_content=url.content
            soup=BeautifulSoup(url_content,"html.parser")
            items=soup.find_all("h4",attrs={"class":"sc-1s0saks-13 btodhQ"})
            price=soup.find_all("span",attrs={"class":"sc-17hyc2s-1 fnhnBd"})
            
            category=[]
            cats=tree.xpath("//*[@id='root']/main/div/section[4]/section/section[1]/p")
            category.extend([i.text for i in cats])
            c=[]
            for j in category:
                words=" ".join(re.findall('\w+',j)[:-1])
                numbers=int(re.findall('\w+',j)[-1])
                c.extend([words for t in range(numbers)])
            for x,y,z in zip(items,price,c):
                main.append([x.text,y.text,z])
            output.append({a.split("/")[-1]:main})
    return output

# Review Scraper
def scraper_review(links):
    # review gen
    output=[]
    with requests.Session() as s:
        for i in links:
            result=[]
            j=1
            t=1
            while(t!=0):
                url=s.get(i+"/reviews?page={}&sort=dd&filter=reviews-dd".format(j),headers=header)
                url_content=url.content
                soup=BeautifulSoup(url_content,"html.parser")
                button=soup.find_all("button",attrs={"class":"sc-1kx5g6g-1 elxuhW sc-jUiVId hMOkj"})
                if "Add Review" in [y.text for y in button]:
                    break
                r=soup.find_all("p")
                a=soup.find_all("a")
                if "Chevron Right iconIt is an icon with title Chevron Rightchevron-right" in [g.text for g in a] : 
                    t=1
                else:
                    t=0
                content=""
                for m in r:
                    content=content+"\n"+m.text
                main=content[content.find("Newest First")+len("Newest First")+1:]
                main = re.sub(r"Comment[s]+", "Comment",main)
                for k in main.split("Comment")[:-1]:
                    data=k.strip().split("\n")
                    name=data[0]
                    rate=data[1]
                    review="\n".join(data[3:-1])
                    result.append({"name":data[0],"rate":data[1],"review":"\n".join(data[3:-1])})
                j+=1
            output.append({i.split("/")[-1]:result})   
    return output

# database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(80))
    
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(100))
    city = db.Column(db.String(100))
    locality = db.Column(db.String(100))
    link = db.Column(db.String(300))

zomato_data = Location.query.all()

# creating decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['login']==True:
            return f(*args, **kwargs)
        else:
            flash("You need to login first", "danger")
            return redirect(url_for('login'))
    return wrap

# routes - views
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == "POST":
        uname = request.form['uname']
        mail = request.form['mail']
        passw = request.form['passw']
        register = User(username = uname, email = mail, password = generate_password_hash(passw))
        db.session.add(register)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/login/', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uname = request.form["uname"]
        passw = request.form["passw"]
        
        login = User.query.filter_by(username=uname).first()
        if login is not None:
            if check_password_hash(login.password, passw):
                session['login'] = True
                session['username'] = login.username
                session['email'] = login.email
                flash('Welcome ' + session['username'] +'! You have been successfully logged in', 'success')
                return redirect(url_for("index"))
            else:
                flash('Password does not match', 'danger')
                return render_template('login.html')
        else:
            flash('User does not exist', 'danger')
    return render_template("login.html")

@app.route('/logout/')
@login_required
def logout():
    session['login']=False
    session.pop('username')
    session.pop('email')
    flash("You have been logged out", 'info')
    return redirect(url_for('login'))

@app.route("/form-data", methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        return redirect(url_for('scrap_data'))
    return render_template('index.html')

@app.route("/output-gen/", methods=['GET'])
def scrap_data():    
    def generate_output():
        global temp
        template = '''{% extends 'base.html' %}

                        {% block new_content %}
                        <br>
                        <h3>Generated Data:</h3>
                        <p>
                            {% if menu %}
                                
                                {{ menu }}
                                
                            {% endif %}
                        </p>
                        <br>
                        <p>
                            {% if review %}
                                
                                {{ review }}
                                
                            {% endif %}
                        </p>
                        <hr>
                        <br>
                        {% endblock %}'''
        context={}
        for data in zomato_data:
            filename = data.state+'_'+data.city+'_'+data.locality
            filename = filename.replace(" ", "")
            menu_filename = filename+'_menu.json'
            context['menu'] = menu_filename
            review_filename = filename+'_review.json'
            context['review'] = review_filename
            scraped_links = scraper_links(data.link)
            menu_data = scraper_menu(scraped_links)
            review_data = scraper_review(scraped_links)
            # menu_data
            with open(os.path.join(UPLOAD_DIRECTORY_MENU, menu_filename), "w") as fp:
                json.dump(menu_data, fp)
            # review_data
            with open(os.path.join(UPLOAD_DIRECTORY_REVIEW, review_filename), "w") as fp:
                json.dump(review_data, fp)
            yield render_template_string(template, **context)
            if context['menu'] != temp:
                time.sleep(60)
                temp = menu_filename
            print(menu_filename)
            print(review_filename)
    return Response(stream_with_context(generate_output()))

@app.route("/")
def home():
    return render_template('home.html')

sys.stdout.flush()

if __name__ == "__main__":
    app.run(debug=True)


