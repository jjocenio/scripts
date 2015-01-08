#!/usr/bin/python2.7

from functions import *

def send(dictData):
	context["index"] = context["ln"]
	url = "%s/rest/api/2/user?username=%s" % (config.get("jira", "url"), dictData["username"])
	response = requests.get(url, headers=headers, auth=getAuth(dictData))
	verifyResponse(url, {}, {}, response, "GETUSER")

if os.path.exists(csvFileName):
	with open(csvFileName, "r") as csvFile:
		data = csv.DictReader(csvFile)
		context["ln"] = 0
		for user in data:
			context["ln"] = context["ln"] + 1
			send(user)
