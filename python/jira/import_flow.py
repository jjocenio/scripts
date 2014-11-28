import ConfigParser
import csv
import json
import os
import requests
import sys

from requests.auth import HTTPBasicAuth

config=ConfigParser.ConfigParser()
config.readfp(open("config.ini"))
csvFileName="jira.csv" if len(sys.argv) < 2 else sys.argv[1]

def getAuth(dictData):
	username = dictData["username"] if "username" in dictData else "admin"
	password = config.get("passwords", username) if config.has_option("passwords", username) else "123"
	return HTTPBasicAuth(username, password)

def getData(dictData):
	jsonData = { "transition" : config.get("transitions", dictData.get("transition")) }
	fields = {}

	listFields = filter(lambda key : key.startswith("field."), dictData.keys())
	for field in listFields:
		fields[field.replace("field.", "")] = dictData[field]
	
	if len(fields) > 0:	
		jsonData["fields"] = fields

	print jsonData
	return json.dumps(jsonData, ensure_ascii=False)

def send(dictData):
	url = "%s/rest/api/2/issue/%s/transitions" % (config.get("jira", "url"), dictData["key"])	
	print dictData["key"]
	response = requests.post(url, data=getData(dictData), headers={'content-type': 'application/json'}, auth=getAuth(dictData))
	print response.text

if os.path.exists(csvFileName):
	with open(csvFileName, "r") as csvFile:
		data = csv.DictReader(csvFile)
		for transiction in data:
			send(transiction)
