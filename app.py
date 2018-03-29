# flask
from flask import Flask
from flask import render_template
from flask import request

# mongo
from pymongo import MongoClient

# twilio
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# miscellaneous
import re
import requests

app = Flask(__name__)
client = MongoClient("localhost", 27017)
db = client.sensus
str_col = db.strings
cust_col = db.customer_products

def get_strings():
	""" Retrieve the three messages from the DB """

	first = str_col.find_one({"msg_type": "first_ask"})["msg"]
	pos = str_col.find_one({"msg_type": "pos_res"})["msg"]
	neg = str_col.find_one({"msg_type": "neg_res"})["msg"]

	return first, pos, neg

@app.route('/')
def render_dashboard():
	# get strings from DB	
	first, pos, neg = get_strings()

	# return dashboard template with dynamic strings
	return render_template('dashboard.html', msg_ask=first, pos_res=pos, neg_res=neg)

def validate_phone(phone):	
	""" Check whether phone number entered is valid """

	# remove all spaces, hyphens and parentheses
	stripped_phone = re.sub(r"[\s()\-]", "", phone)

	# match against +xxxxxxxxxx.. (not considering number of digits because it might be different for different countries)
	if re.match(r"^\+\d+$", stripped_phone):
		return stripped_phone
	raise Exception("Invalid phone number format")

def validate_coke(coke):
	""" Check whether coke type entered is valid """

	if coke.lower() in ["lime", "cherry", "vanilla"]:
		return coke.title()
	raise Exception("Invalid coke type")

def send_sms(phone, coke, name, msg=0):
	first_msg, _1, _2 = get_strings()

	# replace placeholders with actual values
	first_msg = re.sub(r"<firstName>", name, first_msg)
	first_msg = re.sub(r"<productType>", coke + " coke", first_msg)

	# config stuff
	account_sid = "ACa5c9b62d4e697d295393c8462076e563"
	auth_token = "b6c1121aed83fee21e83be2a72c6b994"

	client = Client(account_sid, auth_token)

	# send SMS
	try:
		client.api.account.messages.create(to=phone, from_="+15012145537", body=first_msg)
	except:
		raise Exception("There was a problem with the Twilio SMS service. Make sure the phone number you entered is verified, or try again later.")	

	# save customer phone numbers with product type so that we know what product they ordered when they respond
	cust_col.update_one({"phone": phone}, {"$set": {"coke": coke}}, upsert=True)

@app.route('/send_sms', methods=['POST'])
def receive_sms_data():
	""" Receive form data from dashboard and validate it before sending SMS to user"""

	sms_req_data = request.get_json()

	try:
		phone = validate_phone(sms_req_data['phone'])		
		coke = validate_coke(sms_req_data['coke'])
		name = sms_req_data['name']
		send_sms(phone, coke, name, msg=0)

	except Exception as e:
		return e.args[0], 400
	
	return "SMS successfully sent!"


def detect_sentiment(msg):
	""" Call Microsoft sentiment analysis API"""

	# config stuff
	subscription_key = "c38c4f42f767442faffd8c425aa1687a"	
	text_analytics_base_url = "https://westcentralus.api.cognitive.microsoft.com/text/analytics/v2.0/"
	sentiment_api_url = text_analytics_base_url + "sentiment"
	documents = {'documents' : [{'id': '1', 'language': 'en', 'text': msg}]}
	headers = {"Ocp-Apim-Subscription-Key": subscription_key}

	# call API
	response = requests.post(sentiment_api_url, headers=headers, json=documents)
	sentiments = response.json()
	
	return sentiments['documents'][0]['score']


@app.route('/webhook', methods=["POST"])
def receive_user_sms():
	""" Receive user response to initial SMS through this webhook and respond appropriately""" 

	customer_response_data = request.form
	msg = customer_response_data["Body"]
	phone = customer_response_data["From"]

	# get coke type associated with a phone number
	q = cust_col.find_one({"phone": phone})
	if q != None:
		coke = q['coke'] + " coke"
	else:
		coke = " it"

	# analyze sentiment of user message
	sentiment_score = detect_sentiment(msg)
	
	_, pos_res, neg_res = get_strings()
	
	resp = MessagingResponse()
	if sentiment_score >= 0.5:
		pos_res = re.sub(r"<productType>", coke, pos_res)
		resp.message(pos_res)
	else:
		neg_res = re.sub(r"<productType>", coke, neg_res)
		resp.message(neg_res)

	return str(resp)

@app.route('/edit_msg', methods=["POST"])
def edit_msg():
	msg_mapping = {"1": "first_ask", "2": "pos_res", "3": "neg_res"}
	edit_req = request.get_json()
	new_msg = edit_req['new_msg']
	msg_id = edit_req['id']	
	if int(msg_id) not in range(1, 4):
		return "Invalid message type", 400
	msg_type = msg_mapping[msg_id]
	str_col.update_one({"msg_type": msg_type}, { "$set": {"msg": new_msg}})

	return "Updated message!"