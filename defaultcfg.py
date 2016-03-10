#!/usr/bin/python
from datetime import timedelta

## Debug mode. This engages the web-based debug mode
DEBUG = False

## Enable the debug toolbar. DO NOT DO THIS ON A PRODUCTION SYSTEM. EVER. It exposes SECRET_KEY.
DEBUG_TOOLBAR = False

# Key used to sign/encrypt session data stored in cookies.
SECRET_KEY = ''

## File logging
FILE_LOG=True
LOG_FILE='cortex.log'
LOG_DIR='/tmp'
LOG_FILE_MAX_SIZE=1 * 1024 * 1024
LOG_FILE_MAX_FILES=10

EMAIL_ALERTS=False
ADMINS=['root']
SMTP_SERVER='localhost'
EMAIL_FROM='root'
EMAIL_SUBJECT='Cortex Runtime Error'
EMAIL_DOMAIN='localdomain'

## Redis
REDIS_HOST='localhost'
REDIS_PORT=6379

## MySQL
MYSQL_HOST='localhost'
MYSQL_USER='cortex'
MYSQL_PW=''
MYSQL_DB='cortex'
MYSQL_PORT=3306

## CMDB Integration
CMDB_URL_FORMAT="http://localhost/cmdb/%s"

## Cortex internal version number
VERSION_MAJOR='1.0'
VERSION_MINOR='2016031008'

## Flask defaults (changed to what we prefer)
SESSION_COOKIE_SECURE      = False
SESSION_COOKIE_HTTPONLY    = False
PREFERRED_URL_SCHEME       = 'http'
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

## LDAP AUTH
LDAP_URI            = 'ldaps://localhost.localdomain'
LDAP_SEARCH_BASE    = ''
LDAP_USER_ATTRIBUTE = 'sAMAccountName'
LDAP_ANON_BIND      = True
LDAP_BIND_USER      = ''
LDAP_BIND_PW        = ''
LDAP_ADMIN_GROUP    = "CN=groupname,OU=localhost,DC=localdomain"

# Number of seconds, into the future, to cache user's group memberships for.
LDAP_GROUPS_CACHE_EXPIRE = '900'

# Infoblox server
INFOBLOX_HOST = "" 
INFOBLOX_USER = ""
INFOBLOX_PASS = ""

# ServiceNow instance
SN_HOST = ''
SN_USER = ''
SN_PASS = ''
CMDB_URL_FORMAT = 'https://myinstance.service-now.com/nav_to.do?uri=cmdb_ci_server.do?sys_id=%s'
CMDB_CACHED_CLASSES={'cmdb_ci_server': 'Server'}

# VMware configuration
VMWARE={}

# Neocortex is a daemon 
NEOCORTEX_KEY='changeme'
WORKFLOWS_DIR='/data/cortex/workflows/'
NEOCORTEX_TASKS_DIR='/data/cortex/cortex/neocortex'

# Other
ENVIRONMENTS = []

## API pre-shared keys
# used by puppet master to get ENC data
ENC_API_AUTH_TOKEN    = 'changeme'
# used by all other API calls
CORTEX_API_AUTH_TOKEN = 'changeme'

# PuppetDB
PUPPETDB_HOST=''
PUPPETDB_PORT=8081
PUPPETDB_SSL_VERIFY=False
PUPPETDB_SSL_CERT=''
PUPPETDB_SSL_KEY=''

# Puppet Autosign server
PUPPET_AUTOSIGN_URL='https://yourserver.tld/getcert'
PUPPET_AUTOSIGN_KEY='changeme'
PUPPET_AUTOSIGN_VERIFY=False

# Red Hat Satellite Keys
SATELLITE_KEYS = {
	'el7s' : {
		'development': 'changeme'
	}
}
