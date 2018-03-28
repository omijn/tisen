from flask import Flask
from flask import render_template
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient("localhost", 27017)
db = client.sensus
str_col = db.strings

@app.route('/')
def return_homepage():

	first = str_col.find_one({"msg_type": "first_ask"})["msg"]
	pos = str_col.find_one({"msg_type": "pos_res"})["msg"]
	neg = str_col.find_one({"msg_type": "neg_res"})["msg"]

	return render_template('dashboard.html', msg_ask=first, pos_res=pos, neg_res=neg)

