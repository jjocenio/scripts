#!/usr/bin/python2.7

from functions import *

def assign(dictData):
	url = "%s/rest/api/2/issue/%s/assignee" % (config.get("jira", "url"), getKey(dictData))
	jsonData = { "name" : getValue(dictData, "field.assignee.name") }
	response = requests.put(url, data=json.dumps(jsonData, ensure_ascii=False), headers=headers, auth=getAuth(dictData))
	verifyResponse(url, dictData, jsonData, response, "ASSIGNEE")

def comment(dictData):
	url = "%s/rest/api/2/issue/%s/comment" % (config.get("jira", "url"), getKey(dictData))
	jsonData = { "body" : getValue(dictData, "update.comment")[0]["add"]["body"] }
	response = requests.post(url, data=json.dumps(jsonData, ensure_ascii=False), headers=headers, auth=getAuth(dictData))
	verifyResponse(url, dictData, jsonData, response, "COMMENT")	

def timesheet(dictData):
	url = "%s/rest/api/2/issue/%s/worklog" % (config.get("jira", "url"), getKey(dictData))
	jsonData = getValue(dictData, "update.worklog")[0]["add"]
	merge(jsonData, { "comment" : getValue(dictData, "update.comment")[0]["add"]["body"] })
	response = requests.post(url, data=json.dumps(jsonData, ensure_ascii=False), headers=headers, auth=getAuth(dictData))
	verifyResponse(url, dictData, jsonData, response, "TIMESHEET")

def send(dictData):
	context["index"] = int(re.split("[-/]", getKeyValue(dictData))[0])
	if "key" in context:
		context.pop("key")
	if dictData["transition"] == "IN_PROGRESS":
		assign(dictData)
		comment(dictData)
		dictData["username"] = dictData["field.assignee.name"]
		dictData.pop("update.comment")
		dictData.pop("field.assignee.name")
	elif dictData["transition"] == "LANCAR_HORAS":
		timesheet(dictData)
		return
	url = "%s/rest/api/2/issue/%s/transitions" % (config.get("jira", "url"), getKey(dictData))
	jsonData = { "transition" : getTransition(dictData) }
	response = requests.post(url, data=getData(dictData, jsonData=jsonData) , headers=headers, auth=getAuth(dictData))
	verifyResponse(url, dictData, jsonData, response, "SEND")

if os.path.exists(csvFileName):
	with open(csvFileName, "r") as csvFile:
		data = csv.DictReader(csvFile)
		context["ln"] = 0
		for transiction in data:
			context["ln"] = context["ln"] + 1
			send(transiction)
