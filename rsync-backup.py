#!/usr/bin/env python3

import time 
import subprocess
import json
import logging
import smtplib
import ssl
import sys

# Read Configuration
with open(sys.path[0] + "config.json") as json_data_file:
    cfg = json.load(json_data_file)

# Set Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',filename=cfg['log']['path'],level=logging.DEBUG)

# Read Mail template
f=open(sys.path[0] + "mailtemplate.html","r")
mailtemplate = f.read()
f.close()

logging.info("Start Backup Jobs")

# Create a secure SSL context for SMTP Sendmail
context = ssl.create_default_context()

for job in cfg['jobs']:
	logging.info("-----------------------------------------")
	logging.info("Starting job '%s'",job['name'])
	# Command
	cmd = ["rsync","-azrh","--delete","--stats"]
	
	# If defined, include Exclusions paths
	if(len(job['excludes']) > 0):
		for exclude in job['excludes']:
			cmd.append("--exclude="+exclude)

	if(job['protocol'] == "ssh"):
		# If Protocol SSH is used, modify Destination Syntax
		cmd.append("-e")
		cmd.append("ssh")
		tmpdest = list(job['destination'])
		if(tmpdest[0] == "/"):
			tmpdest[0] = ""

		destination = job["user"] + "@" + job['host'] + "::" + "".join(tmpdest)
	else:
		# Otherwise, leave it
		destination = job['destination']

	if(job['dry-run']):
		cmd.append("--dry-run")

	cmd.append(job['source'])
	cmd.append(destination)

	if(cfg['log']['debug']):
		logging.debug("  Source: %s",job['source'])
		logging.debug("  Destination: %s",destination)
		logging.debug(" Command: %s"," ".join(cmd))

	# Starting the Backup Process
	logging.info("Launching rsync...")
	start = time.time()
	cp = subprocess.Popen(cmd,universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	#cp = subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = cp.communicate()
	elapsed = (time.time() - start)
	logging.info("Backup duration: %s seconds","{0:.2f}".format(elapsed))
	duration = "{0:.2f}".format(elapsed)
	logging.info("RSYNC Result:")
	if(cp.returncode == 0):
		for line in stdout.split('\n'):
			logging.info(line)
		resultdetails = "was successfull"
		result = "<font style='color:#25D665'>Success</font>"
		details = stdout
	else:
		logging.error("The backup job could not be completed")
		for line in stderr.split("\n"):
			logging.error("Error details: %s",line)
		resultdetails = "has failed"
		result = "<font style='color:#D62525'>Error</font>"
		details = stderr
	
	if(job['notification']):
		# Send mail
		logging.info("Sending E-Mail notification")

		with smtplib.SMTP(cfg['notification']['SMTP']['host'], cfg['notification']['SMTP']['port']) as server:
			server.ehlo()  # Can be omitted
			server.starttls(context=context)
			server.login(cfg['notification']['SMTP']['user'], cfg['notification']['SMTP']['password'])
			for recipient in cfg['notification']['recipients']:
				logging.info("Sending mail to '%s'",recipient)
				message = mailtemplate				

				server.sendmail(cfg['notification']['SMTP']['from'], recipient, message.format(host=cfg['hostname'],name=job['name'],result=result,resultdetails=resultdetails,duration=duration,details=details.replace("\n","<br/>"),frommail=cfg['notification']['SMTP']['from'],tomail=recipient))


logging.info("Script done")


