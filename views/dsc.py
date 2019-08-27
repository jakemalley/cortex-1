from cortex import app
import cortex.lib.dsc
import Pyro4.errors
from cortex.lib.user import does_user_have_permission, does_user_have_system_permission, does_user_have_any_system_permission, is_system_enrolled
from cortex.corpus import Corpus
from flask import Flask, request, session, redirect, url_for, flash, g, abort, make_response, render_template, jsonify, Response
import MySQLdb as mysql
import json
import yaml

def generate_new_yaml(proxy, oldRole, oldConfig, newRole, newConfig):
	#configs should be passed in as dictionary
	roles_info = cortex.lib.dsc.get_roles(proxy)

	if newRole == "":
		return json.dumps("")

	# modified_config = json.loads(generate_reset_yaml(proxy, json.dumps(newRole)))


	old_keys = list(oldRole.keys())
	new_keys = list(newRole.keys())

	roles_to_add = list(set(new_keys) - set(old_keys))
	roles_to_remove = list(set(old_keys) - set(new_keys))

	# finds the roles which haven't been added or removed because they are the ones we need to check
	roles_to_check = [role for role in new_keys if role not in (roles_to_add + roles_to_remove) ]

	# rebuild the config according to the modifications
	modified_config = {}

	# we have to keep allnodes the same because its being shared to all nodes 
	modified_config['AllNodes'] = newConfig['AllNodes']

	#now check the roles
	for role in roles_to_check:
		if newRole[role]['length'] == 0:
			#don't bother if the length is 0, we can skip it
			continue
		modified_config[role] = []
		prop_in_new = []
		prop_in_old = []
		#make the required modifications
		for x in range(newRole[role]['length']):
			prop_in_new.append(newRole[role][str(x)])
		for x in range(oldRole[role]['length']):
			prop_in_old.append(oldRole[role][str(x)])
		
		# find the added, removed and unchanged values
		# generate the details for the new ones
		# retrieve old values for the old one

		#find the new and old properties
		added_props = list(set(prop_in_new) - set(prop_in_old))
		removed_props = list(set(prop_in_old) - set(prop_in_new))
		#these are the properties which haven't changed
		props_unchanged = [prop for prop in prop_in_new if prop not in (added_props + removed_props) ]

		#add the new properties
		for prop in added_props:
			for existing_prop in roles_info[role]:
				name = existing_prop.get('Name')
				task_name = existing_prop.get('TaskName')
				group_name = existing_prop.get('GroupName')
				displayed_tag = name if name != None else (task_name if task_name != None else group_name)
				if displayed_tag == prop:
					modified_config[role].append(existing_prop)

		#maintain the old properties
		for prop in props_unchanged:
			if role == 'AllNodes':
				continue
			try:
				for existing_prop in newConfig[role]:
					name = existing_prop.get('Name')
					task_name = existing_prop.get('TaskName')
					group_name = existing_prop.get('GroupName')
					displayed_tag = name if name != None else (task_name if task_name != None else group_name)
					if displayed_tag == prop:
						modified_config[role].append(existing_prop)
			except Exception as e:
				print(e)
				flash('No config found for ' + role + ':' + existing_prop['Name'] + '. If you want to remove this role, please unselect it.','alert-danger')
				continue

	return json.dumps(modified_config)


###########################################################################

def generate_reset_yaml(proxy, roles):
	# read the roles in
	roles = json.loads(roles)
	roles_info = cortex.lib.dsc.get_roles(proxy)
	#create the new config
	config = {}
	#the only part that can be kept is the allNodes section
	config['AllNodes'] = roles_info['AllNodes']
	for role in roles:
		# can move on if nothing is inside the role
		if roles[role]['length'] == 0:
			continue
		# get the correct details from the roles and include it
		config[role] = []
		for x in range(roles[role]['length']):
			name = roles[role][str(x)]
			for settings in roles_info[role]:
				if settings['Name'] == name:
					config[role].append(settings)
	return json.dumps(config)


###########################################################################


@app.route('/dsc/classify/<id>', methods=['GET', 'POST'])
@cortex.lib.user.login_required
def dsc_classify_machine(id):

	#ADD in test to see if the dsc machine is responding

	system = cortex.lib.systems.get_system_by_id(id)

	if system == None:
		abort(404)
	
	curd = g.db.cursor(mysql.cursors.DictCursor)

	# get a proxy to connect to dsc
	dsc_proxy = cortex.lib.dsc.dsc_connect()
	roles_info = cortex.lib.dsc.get_roles(dsc_proxy)
	# get a list of the roles
	default_roles = [role for role in roles_info.keys()]
	
	# generates set of jobs
	# removes UOS from the job and takes the part of the string before the '_'
	# if the job is generic or allnodes (the special 2 that we don't need as they're applied to every box), it ignores it 
	jobs = list({((r.replace('UOS', '')).split('_'))[0] for r in default_roles if not any(special_role in r for special_role in ['AllNodes', 'Generic'])})

	role_selections = {}
	for job in jobs + ['Generic']:
		role_selections[job] = [r for r in default_roles if job in r]


	# retrieve all the systems
	curd.execute("SELECT `roles`, `config` FROM `dsc_config` WHERE `system_id` = %s", (id, ))
	existing_data = curd.fetchone()

	exist_role = ""
	exist_config = ""
	# get existing info
	if existing_data is not None:
		exist_role = json.loads(existing_data['roles'])
		try:
			exist_config = yaml.dump(json.loads(existing_data['config']))
		except json.decoder.JSONDecodeError as e:
			exist_config = yaml.dump("")
	
	for generic in role_selections['Generic']:
		if generic not in exist_role.keys():
			exist_role[generic] = {'length':0}


	values_to_tick = { ((l.replace("UOS","")).split("_"))[0] for l in exist_role }
	
	if request.method == 'GET':
		
		if does_user_have_permission('dsc.view'):
			return render_template('dsc/classify.html', title="DSC", system=system, active='dsc', roles=jobs, yaml=exist_config, set_roles=exist_role, role_info=roles_info, selectpicker_tick=list(values_to_tick))
		else:
			abort(403)

	elif request.method == 'POST':
		if request.form['button'] == 'push_to_dsc':
			curd.execute('SELECT system_id, roles, config FROM dsc_config WHERE system_id = "%s";', (id, ))
			box_details = curd.fetchone()
			
			system_name = system['name']
			cortex.lib.dsc.send_config(dsc_proxy, system_name,json.loads(existing_data['config']))
		else:
			checked_boxes = json.loads(request.form['checked_values'])
			expanded_selected_values = []

			# if request.form['selected_values'] != '':
			for val in ((request.form['selected_values']).split(',') + ['Generic']):
				if val == '':
					continue
				expanded_selected_values += role_selections[val]

			# remove unnecessary detail from the dictionary

			for group in checked_boxes:
				del checked_boxes[group]['prevObject']
				del checked_boxes[group]['context']
			

			for val in expanded_selected_values:
				if val not in checked_boxes.keys():
					checked_boxes[val] = {'length':0}

			keys_to_remove = []

			for key in checked_boxes.keys():
				if key not in expanded_selected_values:
					keys_to_remove.append(key)

			for key in keys_to_remove:
				del checked_boxes[key]
			if request.form['button'] == 'save_changes':
				#check for permissions
				if not does_user_have_permission('dsc.edit'):
					abort(403)
									
				# get the new role and configuration entered
				configuration = request.form['configurations']
				role = json.dumps(checked_boxes)
				try:
					data = yaml.safe_load(configuration)
				except Exception as e:
					flash('Invalid YAML syntax for classes: ' + str(e), 'alert-danger')
					error = True
					raise e

				if data != None:
					roles = json.dumps((data))
					if roles != exist_role:
						new_yaml = generate_new_yaml(dsc_proxy, exist_role, yaml.safe_load(exist_config), json.loads(role), yaml.safe_load(configuration))
					curd.execute('REPLACE INTO dsc_config (system_id, roles, config) VALUES (%s, %s, %s)', (id, role, new_yaml))
					g.db.commit()

			elif request.form['button'] == 'reset':
				role = json.dumps(checked_boxes)
				new_config = generate_reset_yaml(dsc_proxy, role)
				curd.execute('REPLACE INTO dsc_config (system_id, roles, config) VALUES (%s, %s, %s)', (id, role, new_config))
				g.db.commit()


	curd.execute("SELECT roles, config FROM dsc_config WHERE system_id = %s", (id, ))
	existing_data = curd.fetchone()
	exist_role = {}
	exist_config = ""
	if existing_data is not None:
		exist_role = json.loads(existing_data['roles'])
		try:
			exist_config = yaml.dump(json.loads(existing_data['config']))
		except json.decoder.JSONDecodeError as e:
			exist_config = yaml.dump("")

	for generic in role_selections['Generic']:
		if generic not in exist_role.keys():
			exist_role[generic] = {'length':0}

	values_to_tick = { ((l.replace("UOS","")).split("_"))[0] for l in exist_role if 'UOSGeneric' not in l}


	return render_template('dsc/classify.html', title="DSC", system=system, active='dsc', roles=jobs, yaml=exist_config, set_roles=exist_role, role_info=roles_info , selectpicker_tick=list(values_to_tick))