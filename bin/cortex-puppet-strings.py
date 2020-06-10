import json
import os
import subprocess
import sys
import tempfile

import requests

# The cortex-puppet-strngs.json file is in the same folder as our binary
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cortex-puppet-strings.json')
CONFIG_KEYS = ["PUPPET_BINARY", "FIND_BINARY", "PUPPET_ENVIRONMENT_PATHS", "API_URL", "API_TOKEN", "API_SSL_VERIFY"]

def load_config(config_file):
	"""Load JSON Config"""
	with open(config_file, "r") as fp:
		try:
			return json.loads(fp.read())
		except ValueError as ex:
			print("Error: Failed to decode config file {f}: {ex}".format(f=config_file, ex=ex))
			sys.exit(1)

def validate_config(config, keys):
	"""Validate JSON Config"""
	return all(k in config for k in keys)

def puppet_strings(config, environment_path):
	"""Generate JSON using the Puppet strings binary"""
	# Generate a tempfile to write the data to, this is the most reliable way to capture JSON, as puppet-strings sometimes outputs errors to stdout.
	tmp_fd, tmp_path = tempfile.mkstemp()

	try:
		# Run puppet-string with the resulting .pp files from find (this prevents us needing to iterate over all the directories)
		# The command below is equivalent to the following:
		# /bin/find /puppet/production -type f -name '*.pp' -exec /opt/puppetlabs/bin/puppet strings generate --format json --out /tmp/tempfile {} +
		cmd = [config["FIND_BINARY"], str(environment_path), "-type", "f", "-name", "*.pp", "-exec", config["PUPPET_BINARY"], "strings", "generate", "--format", "json", "--out", tmp_path, "{}", "+"]
		process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
		_, stderr = process.communicate()

		if process.returncode != 0:
			raise RuntimeError("Error: puppet-strings returned non-zero exit code ({rc}): {stderr}".format(rc=process.returncode, stderr=stderr))

		with open(tmp_path, "r") as fp:
			file_data = fp.read()

		return json.loads(file_data) if file_data else {}

	# Clean up the tempfile
	finally:
		os.close(tmp_fd)
		os.remove(tmp_path)

	# Logically we should never end up here
	return {}

def generate_puppet_strings_json(config, environment_path):
	"""Generate Puppet strings JSON for a given environment"""

	puppet_strings_json = puppet_strings(config, environment_path)

	if not puppet_strings_json or "puppet_classes" not in puppet_strings_json:
		return {}

	environment_data = {}
	for obj in puppet_strings_json["puppet_classes"]:
		module_name = obj["name"].split("::", 1)[0]
		# Check the module level dict exists
		if module_name not in environment_data:
			environment_data[module_name] = {}
		# Create this class under the module
		environment_data[module_name][obj["name"]] = obj["docstring"] if obj.get("docstring") else {}

	return environment_data

if __name__ == "__main__":
	config = load_config(CONFIG_FILE)
	if not validate_config(config, CONFIG_KEYS):
		print("Error: Missing configuration keys, require: {}".format(CONFIG_KEYS.join(",")))
		sys.exit(1)

	data = {}
	for env in config["PUPPET_ENVIRONMENT_PATHS"]:
		try:
			data[env["name"]] = generate_puppet_strings_json(config, env["path"])
		except ValueError as ex:
			print("Error: Failed to decode response from puppet-strings: {ex}".format(ex=ex))
			sys.exit(1)
		except RuntimeError as ex:
			print("Error: Failed to call puppet-strings: {ex}".format(ex=ex))
			sys.exit(1)

	# POST data to Cortex
	if not config["API_SSL_VERIFY"]:
		import urllib3
		urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

	r = requests.post(
		config["API_URL"],
		headers={'Accept': 'application/json', 'Content-Type': 'application/json', 'X-Auth-Token': config['API_TOKEN']},
		json=data,
		verify=config["API_SSL_VERIFY"]
	)

	try:
		r.raise_for_status()
	except Exception as ex:
		print("Error: Failed to post data to Cortex: {ex}".format(ex=ex))
	else:
		sys.exit(0)
