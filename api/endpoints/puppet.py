import datetime
import json

import MySQLdb as mysql
from flask import abort, g, request
from flask_restplus import Resource

from cortex import app
from cortex.api import api_login_required, api_manager

puppet_modules_info_namespace = api_manager.namespace('puppet', description='Puppet API')
@puppet_modules_info_namespace.route('/modules_info')
class Puppet(Resource):
	"""
	API Handler for Puppet module info
	"""

	@app.disable_csrf_check
	@api_login_required(allow_api_token=True)
	@api_manager.doc(responses={200: "Success", 400: "Bad Request"})
	def post(self):
		"""Handle POST request from cortex-puppet-strings"""

		# Ensure the request container some valid data
		if not request.json:
			abort(400)

		# Last Updated
		last_updated = datetime.datetime.now()

		# Get the database cursor
		curd = g.db.cursor(mysql.cursors.DictCursor)
		# Turn off autocommit cause a lot of insertions are going to be used
		curd.connection.autocommit(False)
		curd.execute("TRUNCATE TABLE `puppet_docs_tags`;")

		# Iterate through the request data and insert
		for environment, modules in request.json.items():
			for module_name, classes in modules.items():
				curd.execute("INSERT INTO `puppet_modules` (`module_name`, `environment`, `last_updated`) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE `id`=LAST_INSERT_ID(`id`), `last_updated`=%s; SELECT LAST_INSERT_ID() INTO @puppet_module_id;", (module_name, environment, last_updated, last_updated))
				for class_name, docstring in classes.items():
					desc = docstring["text"] if "text" in docstring else ""
					tags = docstring["tags"] if "tags" in docstring else []
					curd.execute("INSERT INTO `puppet_classes` (`module_id`, `class_name`, `desc`) VALUES (@puppet_module_id, %s, %s) ON DUPLICATE KEY UPDATE `id`=LAST_INSERT_ID(`id`), `desc`=%s; SELECT LAST_INSERT_ID() INTO @puppet_class_id;", (class_name, desc, desc))
					for tag in tags:
						curd.execute("INSERT INTO `puppet_docs_tags` (`class_id`, `tag`, `name`, `text`, `types`) VALUES (@puppet_class_id, %s, %s, %s, %s)", (tag["tag_name"], tag.get("name", ""), tag.get("text"), json.dumps(tag.get("types", []))))

		# Commit the changes
		curd.connection.commit()
		# Return a 200
		return {}, 200
