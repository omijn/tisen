from flask import Flask
from flask import render_template
from flask import request

from pymongo import MongoClient

import re

app = Flask(__name__)
client = MongoClient("localhost", 27017)
db = client.sensus
str_col = db.strings

def get_strings():
	first = str_col.find_one({"msg_type": "first_ask"})["msg"]
	pos = str_col.find_one({"msg_type": "pos_res"})["msg"]
	neg = str_col.find_one({"msg_type": "neg_res"})["msg"]

	return first, pos, neg

@app.route('/')
def return_homepage():

	# get strings from DB	
	first, pos, neg = get_strings()

	# return dashboard template with dynamic strings
	return render_template('dashboard.html', msg_ask=first, pos_res=pos, neg_res=neg)

def validate_phone(phone):	
	stripped_phone = re.sub(r"[\s()\-]", "", phone)
	if re.match(r"\+\d+", stripped_phone):
		return stripped_phone
	raise Exception("Invalid phone number format")

def validate_coke(coke):
	if coke.lower() in ["lime", "cherry", "vanilla"]:
		return coke.title()
	raise Exception("Invalid coke type")

def send_sms(phone, coke, name):
	pass

@app.route('/send_sms', methods=['POST'])
def receive_sms_data():
	sms_req_data = request.get_json()

	try:
		phone = validate_phone(sms_req_data['phone'])		
		coke = validate_coke(sms_req_data['coke'])
		name = sms_req_data['name']
	except Exception as e:
		return e.args[0], 400

	return "Valid data"

