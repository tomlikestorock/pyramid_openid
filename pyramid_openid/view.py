"""
TODO:
    Write sphinx docs
            explain user flow
            explain how callback works;
                     this is not an authn policy
            explain all options
    Write tests
            request with no openid field
            request with openid field that doesn't resolve
            request with openid field that comes back successful
            request with openid field that comes back successful
                    and calls callback
"""
import urlparse

import openid
from openid.store import memstore, filestore, sqlstore
from openid.consumer import consumer
from openid.oidutil import appendArgs
from openid.cryptutil import randomString
from openid.fetchers import setDefaultFetcher, Urllib2Fetcher
from openid.extensions import pape, sreg, ax

from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.security import remember

from itertools import chain

import logging

log = logging.getLogger(__name__)

def get_ax_required_from_settings(settings):
    ax_required = {}
    ax_required_string = settings.get('openid.ax_required', '')
    for item in ax_required_string.split():
        key, value = item.split("=")
        ax_required[key] = value
    return ax_required

def get_ax_optional_from_settings(settings):
    ax_optional = {}
    ax_optional_string = settings.get('openid.ax_optional', '')
    for item in ax_optional_string.split():
        key, value = item.split("=")
        ax_optional[key] = value
    return ax_optional

def get_sreg_required_from_settings(settings):
    sreg_required = settings.get('openid.sreg_required', '')
    sreg_required = [a.strip() for a in sreg_required.split()]
    return sreg_required

def get_sreg_optional_from_settings(settings):
    sreg_optional = settings.get('openid.sreg_optional', '')
    sreg_optional = [a.strip() for a in sreg_optional.split()]
    return sreg_optional


def verify_openid(context, request):
    settings = request.registry.settings
    openid_field = settings.get('openid.param_field_name', 'openid')
    log.info('OpenID Field to search for: %s' % openid_field)
    incoming_openid_url = request.params.get(openid_field, None)
    openid_mode = request.params.get('openid.mode', None)
    if incoming_openid_url is not None:
        return process_incoming_request(context, request, incoming_openid_url)
    elif openid_mode == 'id_res':
        return process_provider_response(context, request)
    return HTTPBadRequest()


def worthless_callback(request, success_dict, success_dict = {}):
    pass


def build_consumer_from_request(request):
    settings = request.registry.settings
    store_type = settings.get('openid.store.type')
    log.info('Store type to use: %s' % store_type)
    store = None
    if store_type == 'file':
        store_file_path = settings.get('openid.store.file.path')
        log.info('File Store Path: %s' % store_file_path)
        store = filestore.FileOpenIDStore(store_file_path)
    elif store_type == 'mem':
        store = memstore.MemoryStore()
    elif store_type == 'sql':
        # TODO: This does not work as we need a connection, not a string
        sql_connstring = settings.get('openid.store.sql.connection_string')
        sql_associations_table = settings.get(
                'openid.store.sql.associations_table')
        store = sqlstore.SQLStore(sql_connstring,
                sql_associations_table,
                sql_connstring)
    log.info('Store: %s' % store)
    openid_consumer = consumer.Consumer(request.session, store)
    return openid_consumer


def process_incoming_request(context, request, incoming_openid_url):
    settings = request.registry.settings
    log.info('OpenID URL supplied by user: %s' % incoming_openid_url)
    openid_consumer = build_consumer_from_request(request)
    try:
        openid_request = openid_consumer.begin(incoming_openid_url)
        ax_required = get_ax_required_from_settings(settings)
        ax_optional = get_ax_optional_from_settings(settings)
        log.info('ax_required: %s' % ax_required)
        log.info('ax_optional: %s' % ax_optional)
        if len(ax_required.values()) or len(ax_optional.values()):
            fetch_request = ax.FetchRequest()
            for value in ax_required.values():
                fetch_request.add(ax.AttrInfo(value, required=True))
            for value in ax_optional.values():
                fetch_request.add(ax.AttrInfo(value, required=False))
            openid_request.addExtension(fetch_request)

        sreg_required = get_sreg_required_from_settings(settings)
        sreg_optional = get_sreg_optional_from_settings(settings)
        log.info('sreg_required: %s' % sreg_required)
        log.info('sreg_optional: %s' % sreg_optional)
        if len(sreg_required) or len(sreg_optional):
            sreq = sreg.SRegRequest(required=sreg_required,
                    optional=sreg_optional)
            openid_request.addExtension(sreq)
    except consumer.DiscoveryFailure, exc:
        # eventually no openid server could be found
        return error_to_login_form(request, 'Error in discovery: %s' % exc[0])
    except KeyError, exc:
        # TODO: when does that happen, why does plone.openid use "pass" here?
        return error_to_login_form(request, 'Error in discovery: %s' % exc[0])
    # not sure this can still happen but we are making sure.
    # should actually been handled by the DiscoveryFailure exception above
    if openid_request is None:
        return error_to_login_form(
                request,
                'No OpenID services found for %s' % incoming_openid_url)
    #Not sure what the point of setting this to anything else is
    realm_name = settings.get('openid.realm_name', request.host_url)
    temp_url = urlparse.urlparse(request.url)
    temp_url_qs = urlparse.parse_qs(temp_url.query)
    temp_url_qs.pop(settings.get('openid.param_field_name', 'openid'))
    return_url = urlparse.urlunsplit((temp_url.scheme, temp_url.netloc, \
                 temp_url.path, temp_url_qs, temp_url.fragment))
    redirect_url = openid_request.redirectURL(realm_name, return_url)
    log.info('Realm Name: %s' % realm_name)
    log.info('Return URL from provider will be: %s' % return_url)
    log.info('Redirecting to: %s' % redirect_url)
    return HTTPFound(location=redirect_url)


def process_provider_response(context, request):
    settings = request.registry.settings
    openid_consumer = build_consumer_from_request(request)
    info = openid_consumer.complete(request.params, request.url)
    log.info('OpenID Info Status: %s' % info.status)
    if info.status == consumer.SUCCESS:
        log.info('OpenID login successful.')
        success_dict = {
                'identity_url': info.identity_url,
                'ax': {},
                'sreg': {}}
        fr = ax.FetchResponse.fromSuccessResponse(info)
        if fr is not None:
            ax_required = get_ax_required_from_settings(settings)
            ax_optional = get_ax_optional_from_settings(settings)
            items = chain(ax_required.items(), ax_optional.items())
            for key, value in items:
                try:
                    success_dict['ax'][key] = fr.get(value)
                except KeyError:
                    pass
        fr = sreg.SRegResponse.fromSuccessResponse(info)
        if fr is not None:
            sreg_required = get_sreg_required_from_settings(settings)
            sreg_optional = get_sreg_optional_from_settings(settings)
            items = chain(sreg_required, sreg_optional)
            for key in items:
                try:
                    success_dict['sreg'][key] = fr.get(key)
                except KeyError:
                    pass

        callback = settings.get('openid.success_callback', None)
        if callback is not None:
            log.info('Callback for storing result: %s' % callback)
            #Isn't there a better/standard way to parse
            #module.submodule:functions, or is this it?
            callback_function = get_callback(callback)
        else:
            callback_function = worthless_callback
        return callback_function(context, request, success_dict)

def get_callback(callback_string):
    callback = callback_string.split(':')
    #TODO: Use pyramid.util.DottedNameResolver?
    try:
        callback_module = __import__(callback[0], fromlist=[callback[1]])
    except ImportError:
        return None
    try:
        callback_function = getattr(callback_module, callback[1])
    except AttributeError:
        return None
    return callback_function

def error_to_login_form(request, message):
    log.info('OpenID ERROR: %s' % message)
    settings = request.registry.settings
    error_url = settings.get('openid.error_destination', request.referrer)
    if error_url is None:
        error_url = '/'
    error_flash_queue = settings.get('openid.error_flash_queue', '')
    request.session.flash(message, error_flash_queue)
    return HTTPFound(location=error_url)
