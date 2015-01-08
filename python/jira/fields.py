#!/usr/bin/python2.7

import re
import random

datePattern = re.compile("([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})")

def field_assignee_name(dictData, config, context):	
	return getUserGroup(dictData, config, "field.assignee.name", context["index"])

def field_timetracking_originalEstimate(dictData, config, context):
	return "%d" % (int(dictData["field.timetracking.originalEstimate"]) * 60 * 8) if dictData["field.timetracking.originalEstimate"] else ""

def update_comment(dictData, config, context):
	return [ { "add" : { "body" : dictData["update.comment"] } } ]

def update_worklog(dictData, config, context):
	value = dictData["update.worklog"]
	if value:
		started = getStartedDate(dictData["worklog.startdate"])
		worklog = [ { "add" : { "started" : "%s" % started, "timeSpent" : "%sh" % value } } ]
		return worklog

def username(dictData, config, context):
	return getUserGroup(dictData, config, "username", context["index"])

def getStartedDate(dateStr):
	match = datePattern.match(dateStr)
	return "%s-%s-%sT%d:%d:%d.000-0300" % (match.group(3), match.group(1), match.group(2), random.randint(16, 17), random.randint(0, 59), random.randint(0,59))

def getUserGroup(dictData, config, fieldName, index):
	value = dictData[fieldName]
	if not config.has_option("groups", value):
		return value	
	users = config.get("groups", value).split(",")
	return users[index % len(users)]
