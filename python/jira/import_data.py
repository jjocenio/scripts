#!/usr/bin/python2.7

from functions import *

def send(dictData):
	indexField = "field.customfield_10600" if "field.customfield_10600" in dictData else "field.customfield_10604"
	context["index"] = int(re.split("[-/]", dictData[indexField])[0])
	url = "%s/rest/api/2/issue" % (config.get("jira", "url"))
	jsonData=getData(dictData)
	response = requests.post(url, data=jsonData, headers=headers, auth=getAuth(dictData))
	verifyResponse(url, dictData, jsonData, response, "SEND")

if os.path.exists(csvFileName):
	with open(csvFileName, "r") as csvFile:
		data = csv.DictReader(csvFile)
		context["ln"] = 0
		for issue in data:
			context["ln"] = context["ln"] + 1
			send(issue)
