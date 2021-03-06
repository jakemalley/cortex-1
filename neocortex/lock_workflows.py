
import datetime
import json

import MySQLdb as mysql


def run(helper, _options):

	# Set up cursor to access the DB
	curd = helper.db.cursor(mysql.cursors.DictCursor)

	# lock the table in read mode
	helper.event('get_current_status', 'Getting the current status of workflows')
	curd.execute('LOCK TABLES `kv_settings` READ;')
	curd.execute('SELECT `value` FROM `kv_settings` WHERE `key`=%s;', ('workflow_lock_status',))
	current_value = curd.fetchone()

	# unlock the table once run
	curd.execute('UNLOCK TABLES;')

	if current_value is None:
		current_status = 'Unlocked'
	else:
		try:
			jsonobj = json.loads(current_value['value'])
			if 'status' not in jsonobj:
				current_status = 'Unlocked'
			else:
				current_status = jsonobj['status']
		except Exception:
			current_status = 'Locked'

	# get the new value to set the table to
	helper.end_event(description="Current status is " + current_status)

	key = 'workflow_lock_status'

	new_lock_state = 'Locked' if current_status == 'Unlocked' else 'Unlocked'
	value = json.dumps({
		'username': helper.username,
		'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
		'status': new_lock_state
	})

	# setting new status
	helper.event('set_new_status', 'Setting new status to ' + new_lock_state)
	query = 'INSERT INTO `kv_settings` (`key`, `value`) VALUES (%s, %s)'
	params = (key, value,)
	query = query + 'ON DUPLICATE KEY UPDATE `value` = %s'
	params = params + (value,)

	# lock table in read mode
	curd.execute('LOCK TABLES `kv_settings` WRITE;')
	curd.execute(query, params)
	curd.execute('UNLOCK TABLES ;')

	# commit changes
	helper.event('commit_changes', 'Committing changes')
	helper.db.commit()
	helper.end_event(description="Commiting Changes")
