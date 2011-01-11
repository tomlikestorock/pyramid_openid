pyramid_openid provides a view for the Pyramid framework that acts as an OpenID consumer.

This code is offered under the BSD-derived Repoze Public License.

Much of this code was inspired by (read: 'lifted from') the repoze.who.plugins.openid
code which can be found here:
http://quantumcore.org/docs/repoze.who.plugins.openid

In your Pyramid app, add the pyramid_openid.verify_openid view_callable to your
view_configuration, and add the needed settings to your .ini file.

Here is a barebones setup:
openid.store.type = file
openid.store.file.path = %(here)s/sstore
openid.success_callback = myapp.lib:remember_me

This setup requires you have a folder in your app directory called 'sstore',
and that you have a callback function in your lib module named "remember_me".
Remember me will receive the current request and the other information returned
from the OpenID provider, and will then do whatever is needed to remember the user,
load metadata into the session - that part is completely up to the coder.

This setup will then assume the defaults for the rest of the keys.

Once the configuration is in place, it's time to hook up the view to the application.
You can do this however you want to.

Example:
In your app config setup code, add this line before 'return config.make_wsgi_app()'

config.add_route('verity_openid', 
	pattern='/dologin.html',
	view='pyramid_openid.verify_openid')

Now you have a url to submit your OpenID form to: /dologin.html.
Based on the configuration above, it expects to find the user's OpenID URL
in request.params['openid'].


REQUIRED SETTINGS
=================
OpenID Data Store
-----------------
Key:
openid.store.type

Description:
This determines the type of store python-openid will use
to track nonces and other cross request data. Note that
this defaults to None, which has python-openid use a
stateless request type. Stateless mode isn't reliable;
something else should be chosen. File and mem are
recommended.

The SQL store has yet to be tested or even verified
working. It is also not recommended.

Default:
None

Examples:
To use a file store:
(openid.store.file.path must also be specified)
openid.store.type = file

To use a memory store:
openid.store.type = mem

To use a sql store:
(openid.store.sql.connection_string and
openid.store.sql.associations_table must also
be specified)
THIS IS NOT TESTED AND DOES NOT WORK
openid.store.type = sql


OPTIONAL SETTINGS:
==================
Successful Login Destination URL
--------------------------------
Key:
openid.success_destination

Description:
This is the url that the user will be sent to after they've
successfully been verified by the OpenID provider.

Default:
/

Example:
To have your user be sent to their profile page upon successful
login:
openid.success_destination = http://www.example.com/profile.html

Successful Login Callback
-------------------------
Key:
openid.success_callback

Description:
This is a callable that will be called upon successful verification
by the OpenID provider. The callable will be passed two parameters;
the current request, and a dictionary with the following structure:
{
	'identity_url': The user's unique URL from the provider,
	'ax':		A dictionary containing all the returned
			active exchange parameters requested,
	'sreg':		A list containing all the returned
			simple registration parameters requested
}

This callback is required to have the following format:
module.optional_submodules:function

Default:
None

Example:
If the callback is in the lib module of the my app package, and
is named openid_callback, then this is the setting to be used:
openid.success_callback = myapp.lib:openid_callback

AX
--
Keys:
openid.ax_required
openid.ax_optional

Description:
These represent user data requested via OpenID Attribute Exchange.

Default:
None

Example:
To require that the provider respond with the user's email:
openid.ax_required = email=http://schema.openid.net/contact/email

SX
--
Keys:
openid.sreg_required
openid.sreg_optional

Description:
These represent user data requested via OpenID Simple Registration.

Default:
None

Example:
To require that the provider respond with the user's email:
openid.sreg_required = email

Incoming OpenID Param Name:
---------------------------
Key:
openid.param_field_name

Description:
When a request is first submitted with the user's OpenID URL,
it must be retrieved from request.params with a key.
This is the name of that key in request.params.

Default:
openid

Examples:
Once submitted, the user's OpenID URL will be found in
request.params['users_openid_url']:
openid.param_field_name = users_openid_url

Error Destination
-----------------
Key:
openid.error_destination

Description:
When something in the OpenID verification process fails,
the user will be sent to this url. The error message
will be stored in the request.session.flash queue
as specified by openid.error_flash_queue

Default:
request.referrer

Example:
To send the user to a http://www.example.com/sorry.html upon failure:
openid.error_destination = http://www.example.com/sorry.html

Error Flash Queue
-----------------
Key:
openid.error_flash_queue

Description:
If something goes awry in the OpenID process, the error message
will be put in the request.session.flash message queue, and this
is the name of that queue.

Default:
The default flash queue ('')

Example:
To put the error messages in the 'OpenIDErrors' flash queue:
openid.error_flash_queue=OpenIDErrors

Realm Name
----------
Key:
openid.realm_name

Description:
This is the value of the realm parameter passed to the OpenID
provider. It's here for the sake of completeness, but unless
you know what you're doing there's no reason to change it.

Default:
request.host_url

Example:
To set the Realm to 'www.example.com':
openid.realm_name = http://www.example.com

Note:
Changing the realm_name will most likely cause your request
to fail.


CONDITIONAL SETTINGS
====================
File Store Path
---------------
Key:
openid.store.file.path

Description:
If the file store path is to be used, then it needs
a writable folder to store data into. This is that path.

Default:
No default

Example:
To store data in the folder named "sstore" in the same
folder as your development.ini:
(Note that you must make this directory as well)
openid.store.file.path = %(here)s/sstore

SQL Connection String
---------------------
Key:
openid.store.sql.connection_string

Description:
This is the connection string for the database for
python-openid to store its temporary data in.
THIS HAS NOT BEEN TESTED AND DOES NOT WORK YET.

Default:
No default

SQL Associations Table
----------------------
Key:
openid.store.sql.associations_table

Description:
This is the name of the table that python-openid
will store is temporary data in.
THIS HAS NOT BEEN TESTED AND DOES NOT WORK YET.

Default:
No default
