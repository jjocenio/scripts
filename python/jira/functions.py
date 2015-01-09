#!/usr/bin/python2.7

import ConfigParser
import csv
import json
import os
import re
import requests
import sys

import fields

from requests.auth import HTTPBasicAuth

config = ConfigParser.ConfigParser()
config.readfp(open("config.ini"))
csvFileName = "jira.csv" if len(sys.argv) < 2 else sys.argv[1]

context = {}
headers = {'content-type': 'application/json'}

datePattern = re.compile("([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})")
refPattern = re.compile(".+\.ref_(.*)$")

def addData(data, name, partData):
	if len(partData) > 0:	
		data[name] = partData

def getAuth(dictData):
	username = getValue(dictData, "username") if "username" in dictData else "admin"
	password = config.get("passwords", username) if config.has_option("passwords", username) else "emifer_716717"
	return HTTPBasicAuth(username, password)

def getData(dictData, jsonData = {}):
	addData(jsonData, "update", getUpdates(dictData))
	addData(jsonData, "fields", getFields(dictData))
	return json.dumps(jsonData, ensure_ascii=True)

def getFields(dictData):
	return getFieldsOrUpdates(dictData, "field")

def getFieldsOrUpdates(dictData, fou):
	fields = {}
	listFields = filter(lambda key : key.startswith("%s." % fou), dictData.keys())
	for field in listFields:
		refMatch = refPattern.match(field)
		if refMatch:
			refField = refMatch.group(1)
			fieldName = field.replace("%s." % fou, "").replace(".ref_" + refField, "")
			ref = getReference(refField, dictData[field])
			if "issue" in ref and "id" in ref["issue"]:
				merge(fields, toJson(fieldName, ref["issue"]["id"]))
		else:
			value = getValue(dictData, field)
			if value:
				merge(fields, toJson(field.replace("%s." % fou, ""), value))
	return fields

def getKey(dictData):
	if "key" in context:
		return context["key"]["issues"][0]["key"]

	lstFieldKey = filter(lambda key : key.startswith("key."), dictData.keys())
	if len(lstFieldKey) > 0:
		fieldKey = lstFieldKey[0]
		key = dictData[fieldKey]
		if isReference(fieldKey):
			refField = getReferenceField(fieldKey)
			keyRef = getReference("%s ~ '%s'" % (refField["field"], dictData[fieldKey]), dictData)
			context["key"] = keyRef
			key = keyRef["issues"][0]["key"]
		return key

def getKeyValue(dictData):
	fieldKey = filter(lambda key : key.startswith("key."), dictData.keys())
	return dictData[fieldKey[0]] if len(fieldKey) > 0 else ""

def getReference(jql, dictData):
	jsonDataPost = '{ "jql": "%s", "startAt": 0, "maxResults": 1, "fields": [ "id", "key" ] }' % jql
	url = "%s/rest/api/2/search" % (config.get("jira", "url"))
	response = requests.post(url, data=jsonDataPost, headers=headers, auth=getAuth(dictData))
	if response.status_code == 200:
		jsonResponse = json.loads(response.text)
		return jsonResponse if jsonResponse["total"] >= 1 else None

def getReferenceField(refPath):
	match = refPattern.match(refPath)
	if match:
		response = {}
		response["field"] = match.group(1)
		response["name"] = refPath.replace("key.", "").replace("field.", "").replace(".ref_" + match.group(1), "")
		return response

def getTransition(dictData):
	url = "%s/rest/api/2/issue/%s/transitions" % (config.get("jira", "url"), getKey(dictData))
	response = requests.get(url, headers=headers, auth=getAuth(dictData))
	if response.status_code == 200:
		jsonResponse = json.loads(response.text)
		for t in jsonResponse["transitions"]:
			if t["to"]["name"].upper() == dictData.get("transition").replace("_", " ").upper():
				return t["id"]

def getUpdates(dictData):
	return getFieldsOrUpdates(dictData, "update")

def getValue(dictData, fieldName):
	value = dictData[fieldName]
	methodName = fieldName.replace(".", "_");
	if hasattr(fields, methodName):
		fieldMethod = getattr(fields, methodName)
		value = fieldMethod(dictData, config, context)
	if isinstance(value, basestring):
		dateMatch = datePattern.match(value)
		if dateMatch:
			return "%s-%s-%s" % (dateMatch.group(3), dateMatch.group(1), dateMatch.group(2))
		return config.get("replaces", value) if config.has_option("replaces", value) else value.strip()
	return value	

def isReference(fieldName):
	return refPattern.match(fieldName) != None

def merge(dictOriginal, newDict, originalParent = {}, fieldName = None):
	if isinstance(newDict, dict):
		for i in newDict:
			if i in dictOriginal:
				merge(dictOriginal[i], newDict[i], originalParent = dictOriginal, fieldName = i)
			else:
				dictOriginal[i] = newDict[i]
	else:
		if isinstance(dictOriginal, list):
			dictOriginal.append(newDict)
		else:
			originalParent[fieldName] = [ dictOriginal, newDict ]

def toJson(fieldName, value):
	json = {}
	root = json
	parent = root
	for node in fieldName.split("."):
		parent = root
		root[node] = {}
		root = root[node]
	parent[node] = value
	return json

def verifyResponse(url, dictData, jsonData, response, identifier):
	if response.status_code in range(200, 206):
		print "%s - OK" % identifier
	else:
		print "-" * 80
		print "ERROR - %s - %d" % (identifier, response.status_code)
		print "%s - %s" % (url, getAuth(dictData).username)
		print dictData
		print jsonData
		print response.text
		print "-" * 80

