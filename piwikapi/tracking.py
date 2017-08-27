#!/usr/bin/env python

u"""
Copyright (c) 2012-2013, Nicolas Kuttler.
All rights reserved.

License: BSD, see LICENSE for details

Source and development at https://github.com/piwik/piwik-python-api
"""

import sys
import datetime
from hashlib import md5
import math
import logging
import os
import random
try:
    import json
except ImportError:
    import simplejson as json
try:
    from urllib.parse import urlencode, urlparse, quote
except ImportError:
    from urllib import urlencode, quote
    from urlparse import urlparse
import urllib3
import requests

from .exceptions import ConfigurationError
from .exceptions import InvalidParameter
from .pycompat import is_string, use_string_type, to_string


class PiwikTracker(object):
    u"""
    The Piwik tracker class
    """
    ## Piwik API version
    VERSION = 1

    ## Length of the visitor ID
    LENGTH_VISITOR_ID = 16

    ## List of plugins Piwik knows
    KNOWN_PLUGINS = {
        u"flash": u"fla",
        u"java": u"java",
        u"director": u"dir",
        u"quick_time": u"qt",
        u"real_player": u"realp",
        u"pdf": u"pdf",
        u"windows_media": u"wma",
        u"gears": u"gears",
        u"silverlight": u"ag"
    }

    UNSUPPORTED_WARNING = (
        u"%s: The code that is just running is untested and "
        u"probably does not work as expected anyway."
    )

    action_name = None
    ecommerce_items = None
    id_site = None
    api_url = None
    request_cookie = None
    user_agent = None
    accept_language = None
    ip = None
    token_auth = None
    local_time = None
    forced_datetime = None
    local_time = None
    page_url = None
    cookie_support = None
    has_cookies = None
    width = None
    height = None
    visitor_id = None
    debug_append_url = None
    event_custom_var = None
    page_custom_var = None
    event_tracking = None
    visitor_custom_var = None
    dimensions = None
    plugins = None
    attribution_info = None
    user_id = None
    send_image = None
    id_goal = None
    revenue = None
    debug = None
    ssl_verify = None

    def __init__(self, id_site):
        u"""
        :param id_site: Site ID
        :type id_site: int
        :param request: Request
        :type request: A Django-like request object
        :rtype: None
        """
        random.seed()
        self.action_name = None
        self.ecommerce_items = {}
        self.id_site = id_site
        self.api_url = None
        self.request_cookies = None
        self.user_agent = None
        self.accept_language = None
        self.ip = None
        self.token_auth = None
        self.forced_datetime = None
        self.local_time = None
        self.page_url = None
        self.cookie_support = True
        self.has_cookies = False
        self.width = None
        self.height = None
        self.visitor_id = None
        self.debug_append_url = False
        self.event_custom_var = {}
        self.page_custom_var = {}
        self.visitor_custom_var = {}
        self.event_tracking = {}
        self.dimensions = {}
        self.plugins = {}
        self.attribution_info = {}
        self.user_id = None
        self.send_image = False
        self.id_goal = None
        self.revenue = None
        self.debug = False
        self.ssl_verify = True
        return

    def set_local_time(self, datetime):
        u"""
        Set the time

        :param datetime: Time
        :type datetime: datetime.datetime object
        :rtype: bool
        """
        self.local_time = datetime
        return True

    def set_token_auth(self, token_auth):
        u"""
        Set the auth token for the request. The token can be viewed in the
        user management section of your Piwik install.

        :param token_auth: Auth token
        :type token_auth: str
        :rtype: bool
        """
        self.token_auth = token_auth
        return True

    def set_api_url(self, api_url):
        u"""
        Set which Piwik API URL to use

        :param api_url: API URL
        :type api_url: str
        :rtype: bool
        """
        self.api_url = api_url
        return True

    def set_ip(self, ip):
        u"""
        Set the IP to be tracked. You probably want to use this as the
        request comes from your own server.

        Requires setting the auth token.

        :param ip: IP
        :type ip: str
        :rtype: bool
        """
        self.ip = ip
        return True

    def set_browser_has_cookies(self):
        u"""
        Call this is the browser supports cookies

        :rtype: bool
        """
        self.has_cookies = True
        return True

    def set_browser_language(self, language):
        u"""
        Set the browser language. Piwik uses this to guess the visitor"s
        origin when GeoIP is not enabled

        :param language: Accept-Language
        :type language: str
        :rtype: bool
        """
        self.accept_language = language
        return True

    def set_user_agent(self, user_agent):
        u"""
        Set the user agent. By default the original request"s UA is used.

        :param user_agent: User agent
        :type user_agent: str
        :rtype: bool
        """
        self.user_agent = user_agent
        return True

    def set_resolution(self, width, height):
        u"""
        Set the visitor"s screen width and height

        :param width: Screen width
        :type width: int or str
        :param height: Screen height
        :type height: int or str
        :rtype: bool
        """
        self.width = width
        self.height = height
        return True

    def set_new_visitor_id(self):
        u"""
        Sets the current visitor ID to a random new one.
        """
        self.visitor_id = self.build_random_visitor_id()
        return True

    def set_visitor_id(self, visitor_id):
        u"""
        Set the visitor's unique User ID. See https://piwik.org/docs/user-id/

        :param visitor_id: Visitor I
        :type visitor_id: str
        :raises: InvalidParameter if the visitor_id has an incorrect length
        :rtype: bool
        """
        if len(visitor_id) != self.LENGTH_VISITOR_ID:
            raise InvalidParameter(
                u"set_visitor_id() expects a visitor ID of "
                u"length %s" % self.LENGTH_VISITOR_ID
            )
        self.visitor_id = visitor_id
        return True

    def set_user_id(self, user_id):
        u"""
        Force the action to be recorded for a specific User.

        :param user_id:
            The User ID is a string representing a given user in your system.
            A User ID can be a username, UUID or an email address, or any number
            or string that uniquely identifies a user or client.
        :rtype: bool
        """
        if not is_string(user_id) and (type(user_id) != int):
            raise InvalidParameter(
                u"user_id must be %s" % use_string_type()
            )
        self.user_id = user_id
        return True

    def set_send_image_response(self, should_send):
        u"""
        If image response is disabled Piwik will respond with a
        HTTP 204 header instead of responding with a gif.

        :rtype: bool
        """
        self.send_image = should_send
        return True

    def set_debug(self, should_debug):
        u"""
        :param string: str to append
        :type string: str
        :rtype: bool
        """
        self.debug = should_debug
        return True

    def set_url_referer(self, referer):
        u"""
        Set the referer URL

        :param referer: Referer
        :type referer: str
        :rtype: bool
        """
        self.referer = referer
        return True

    def set_url(self, url):
        u"""
        Set URL being tracked

        :param url: URL
        :type url: str
        :rtype: bool
        """
        self.page_url = url
        return True

    def set_attribution_info(
            self,
            campaign_name,
            campaign_keyword,
            referral_datetime,
            referral_url
    ):
        u"""
        Set the attribution info for the visit, so that subsequent goal
        conversions are properly attributed to the right referer, timestamp,
        campaign name and keyword.

        This must be a JSON encoded string that you would normally fetch from
        the Javascript API, see function getAttributionInfo() in
        http://dev.piwik.org/trac/browser/trunk/js/piwik.js

        :param json_encoded: JSON encoded list containing attribution info
        :type json_encoded: string
        :raises: InvalidParameter if the json_encoded data is incorrect
        :rtype: bool
        """
        self.attribution_info = {
            u"campaign_name" = campaign_name,
            u"campaign_keyword" = campaign_keyword,
            u"referral_datetime" = referral_datetime,
            u"referral_url" = referral_url
        }
        return True

    def set_force_visit_date_time(self, datetime):
        u"""
        Override the server date and time for the tracking request.

        By default Piwik tracks requests for the "current" datetime, but
        this method allows you to track visits in the past. Time are in
        UTC.

        Requires setting the auth token.

        :param datetime: datetime
        :type datetime: datetime.datetime object
        :rtype: bool
        """
        self.forced_datetime = datetime
        return True

    def set_request_cookie(self, cookies):
        u"""
        Set the request cookie, for testing purposes

        :param cookies: Dict
        :rtype: bool
        """
        self.request_cookies = cookies
        return True

    def _get_timestamp(self):
        u"""
        Returns the timestamp for the request

        Defaults to current datetime but can be set through
        set_force_visit_date_time().

        :rtype: datetime.datetime object
        """
        if self.forced_datetime is not None:
            return self.forced_datetime
        return datetime.datetime.now()

    def _get_request(self, id_site):
        u"""
        This oddly named method returns the query var string.

        :param id_site: Site ID
        :type id_site: int
        :rtype: str
        """
        query_vars = {}
        query_vars[u"idsite"] = id_site
        query_vars[u"rec"] = "1"
        query_vars[u"url"] = self.page_url
        query_vars[u"apiv"] = self.VERSION
        query_vars[u"rand"] = random.randint(0, 99999)
        if self.referer is not None:
            query_vars[u"referer"] = self.referer
        if self.action_name is not None:
            query_vars[u"action_name"] = self.action_name
        if self.local_time is not None:
            query_vars[u"h"] = self.local_time.hour
            query_vars[u"m"] = self.local_time.minute
            query_vars[u"s"] = self.local_time.second
        if self.ip is not None:
            query_vars[u"cip"] = self.ip
        if self.token_auth is not None:
            query_vars[u"token_auth"] = self.token_auth
        if self.has_cookies:
            query_vars[u"cookie"] = 1
        if self.width is not None and self.height is not None:
            query_vars[u"res"] = u"%dx%d" % (self.width, self.height)
        if self.visitor_id is not None:
            query_vars[u"cid"] = self.visitor_id
            query_vars[u"_id"] = self.visitor_id
        if self.user_id is not None:
            query_vars[u"uid"] = to_string(self.user_id)
        if self.send_image is not None:
            query_vars[u"send_image"] = u"1" if self.send_image else u"0"
        if self.event_custom_var is not None and len(self.page_custom_var) > 0:
            query_vars[u"e_cvar"] = json.dumps(self.event_custom_var)
        if self.page_custom_var is not None and len(self.page_custom_var) > 0:
            query_vars[u"cvar"] = json.dumps(self.page_custom_var)
        if (
                self.visitor_custom_var is not None and
                len(self.visitor_custom_var) > 0
        ):
            query_vars[u"_cvar"] = json.dumps(self.visitor_custom_var)
        if self.event_tracking is not None and len(self.event_tracking) > 0:
            query_vars[u"e_c"] = self.event_tracking[u"category"]
            query_vars[u"e_a"] = self.event_tracking[u"action"]
            query_vars[u"e_n"] = self.event_tracking[u"name"]
            query_vars[u"e_v"] = self.event_tracking[u"value"]
        if self.dimensions is not None and len(self.dimensions) > 0:
            for dimension, value in self.dimensions.items():
                query_vars[dimension] = value
        if self.plugins is not None and len(self.plugins) > 0:
            for plugin, version in self.plugins.items():
                query_vars[plugin] = version
        if self.attribution_info is not None and len(self.attribution_info) > 0:
            query_vars[u"_rcn"] = self.attribution_info[u"campaign_name"]
            query_vars[u"_rck"] = self.attribution_info[u"campaign_keyword"]
            query_vars[u"_refts"] = (
                math.floor(
                    self.attribution_info[u"referral_datetime"].timestamp()
                )
            )
            query_vars[u"_ref"] = self.attribution_info[u"referral_url"]
        if self.id_goal is not None:
            query_vars[u"idgoal"] = self.id_goal
            if self.revenue is not None:
                query_vars[u"revenue"] = self.revenue
        if self.debug is True:
            query_vars[u"debug"] = "1"
        return query_vars

    def __get_url_track_action(self, action_url, action_type):
        u"""
        :param action_url: URL of the download or outlink
        :type action_url: str
        :param action_type: Type of the action, either "download" or "link"
        :type action_type: str
        """
        url = self._get_request(self.id_site)
        url += u"&%s" % urlencode({action_type: action_url})
        return url

    def __get_url_track_site_search(
            self,
            search,
            search_cat=None,
            search_count=None
    ):
        u"""
        param search: Search query
        :type search: str
        :param search_cat: optional search category
        :type search_cat: str
        :param search_count: umber of search results displayed in the page. If
            search_count=0, the request will appear in
            "No Result Search Keyword"
        :type search_count: int
        :rtype: None
        """
        url = self._get_request(self.id_site)
        url += u"&%s" % urlencode({u"search": search})
        if search_cat is not None:
            url += u"&%s" % urlencode({u"search_cat": search_cat})
        if search_count is not None:
            url += u"&%s" % urlencode({u"search_count": search_count})
        return url

    def __get_url_track_event(self, category, action, name, value):
        url = self._get_request(self.id_site)
        url += u"&%s" % urlencode({u"e_c": category})
        url += u"&%s" % urlencode({u"e_a": action})
        if name:
            url += u"&%s" % urlencode({u"e_n": name})
        if value:
            url += u"&%s" % urlencode({u"e_v": value})
        return url

    def __get_url_track_content(
            self,
            content_name,
            content_piece,
            content_target,
            content_interaction
    ):
        url = self._get_request(self.id_site)
        url += u"&%s" % urlencode({u"c_n": content_name})
        if content_piece:
            url += u"&%s" % urlencode({u"c_p": content_piece})
        if name:
            url += u"&%s" % urlencode({u"c_t": content_target})
        if value:
            url += u"&%s" % urlencode({u"c_i": content_interaction})
        return url

    def __get_cookie_matching_name(self, name):
        u"""
        **NOT SUPPORTED**

        Get a cookie"s value by name

        :param name: Cookie name
        :type name: str
        :rtype: str
        """
        logging.warn(self.UNSUPPORTED_WARNING % u"__get_cookie_matching_name()")
        cookie_value = False
        if self.request.COOKIES:
            for name in self.request.COOKIES:
                #print "cookie name", name
                #print "cookie is", cookie_value
                cookie_value = self.request.COOKIES[name]
        #print self.request.COOKIES
        return cookie_value

    def get_visitor_id(self):
        u"""
        **PARTIAL, no cookie support**

        If the user initiating the request has the Piwik first party cookie,
        this function will try and return the ID parsed from this first party
        cookie.

        If you call this function from a server, where the call is triggered by
        a cron or script not initiated by the actual visitor being tracked,
        then it will return the random Visitor ID that was assigned to this
        visit object.

        This can be used if you wish to record more visits, actions or goals
        for this visitor ID later on.

        :rtype: str
        """
        return self.visitor_id

    def get_attribution_info(self):
        u"""
        **NOT SUPPORTED**

        To support this we"d need to parse the cookies in the request obejct.
        Not sure if this makes sense...

        Return the currently assigned attribution info stored in a first party
        cookie.

        This method only works if the user is initiating the current request
        and his cookies can be read by this API.

        :rtype: string, JSON encoded string containing the referer info for
            goal conversion attribution
        """
        logging.warn(self.UNSUPPORTED_WARNING % u"get_attribution_info()")
        attribution_cookie_name = u"ref.%d." % self.id_site
        return self.__get_cookie_matching_name(attribution_cookie_name)

    def __get_random_string(self, length=500):
        u"""
        Return a random string

        :param length: Length
        :type length: inte
        :rtype: str
        """
        return md5(os.urandom(length)).hexdigest()

    def build_random_visitor_id(self):
        u"""
        Return a random visitor ID

        :rtype: str
        """
        visitor_id = self.__get_random_string()
        return visitor_id[:self.LENGTH_VISITOR_ID]

    def disable_cookie_support(self):
        u"""
        **NOT TESTED**

        By default, PiwikTracker will read third party cookies from the
        response and sets them in the next request.

        :rtype: bool
        """
        logging.warn(self.UNSUPPORTED_WARNING % u"disable_cookie_support()")
        self.cookie_support = False
        return True

    def set_action_name(self, action_name):
        u"""
        Track a page view, return the request body

        :param document_title: The title of the page the user is on
        :type document_title: str
        :rtype: str
        """
        self.action_name = action_name
        return True

    def execute(self):
        url = self._get_request(self.id_site)
        return self._send_request(url)

    def set_event_tracking(self, category, action, name, value):
        self.event_tracking = {
            u"category": category,
            u"action": action,
            u"name": name,
            u"value": value
        }
        return True

    def do_track_action(self, action_url, action_type):
        u"""
        Track a download or outlink

        :param action_url: URL of the download or outlink
        :type action_url: str
        :param action_type: Type of the action, either "download" or "link"
        :type action_type: str
        :raises: InvalidParameter if action type is unknown
        :rtype: str
        """
        if action_type not in [u"download", u"link"]:
            raise InvalidParameter(u"Illegal action parameter %s" % action_type)
        url = self.__get_url_track_action(action_url, action_type)
        return self._send_request(url)

    def do_track_site_search(self, search, search_cat=None, search_count=None):
        """
        Track a Site Search query.

        param search: Search query
        :type search: str
        :param search_cat: optional search category
        :type search_cat: str
        :param search_count: umber of search results displayed in the page. If
        search_count=0, the request will appear in "No Result Search Keyword"
        :type search_count: int
        :rtype: None
        """
        url = self.__get_url_track_site_search(search, search_cat, search_count)
        return self._send_request(url)

    def do_track_content(
            self,
            content_name,
            content_piece=None,
            content_target=None,
            content_interaction=None
    ):
        u"""
        Track the performance of pieces of content on a page.

        To track a content impression set content_name and optionally
        content_piece and content_target. To track a content interaction
        set content_interaction and content_name and optionally
        content_piece and content_target. To map an interaction to an
        impression make sure to set the same value for content_name and
        content_piece. It is recommended to set a value for content_piece.

        :param content_name:
            The name of the content. Must not be empty.
            For instance "Ad Foo Bar"
        :type content_name: str
        :param content_piece:
            The actual content piece. For instance the path to an
            image, video, audio, any text
        :type content_piece: str
        :param content_target:
            The target of the content.
            For instance the URL of a landing page
        :type content_target: str
        :param content_interaction:
            The name of the interaction with the content. For instance a "click"
        :type content_interaction: str
        :rtype: str
        """
        url = self.__get_url_track_event(category, action, name, value)
        return self._send_request(url)

    def _send_request(self, query_vars):
        """
        Make the tracking API request, return the request body

        :param url: TODO
        :type url: str
        :raises: ConfigurationError if the API URL was not set
        :rtype: str
        """
        if self.api_url is None:
            raise ConfigurationError(u"API URL not set")
        req_headers = {}
        req_cookies = {}
        if self.user_agent is not None:
            req_headers[u"User-Agent"] = self.user_agent
        if self.accept_language is not None:
            req_headers[u"Accept-Language"] = self.accept_language
        if self.cookie_support:
            if (
                    self.request_cookies is not None and
                    len(self.request_cookies) > 0
            ):
                req_cookies = self.request_cookies
        req = (
            requests.Request(
                method="GET",
                url=self.api_url,
                headers=req_headers,
                cookies=req_cookies,
                params=query_vars
            )
        )
        sess = requests.Session()
        if not self.ssl_verify:
            ##
            ## See: https://stackoverflow.com/a/28002687
            ##
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            sess.verify = False
        prep = sess.prepare_request(req)
        response = sess.send(prep)
        ok = response.status_code in [200, 204]
        err = (not ok)
        ret = {
            "body_bytes": response.content,
            "body_str": response.text,
            "status": response.status_code,
            "ok": ok,
            "error": err
        }
        return ret

    def set_ssl_verify(self, verify):
        self.ssl_verify = verify
        return True

    def set_custom_variable(self, id, name, value, scope="visit"):
        u"""
        Set a custom variable

        See http://piwik.org/docs/custom-variables/

        :param id: Custom variable slot ID, 1-5
        :type id: int
        :param name: Variable name
        :type name: str
        :param value: Variable value
        :type value: str
        :param scope: Variable scope, either visit or page,
            defaults to visit
        :type scope: str or None
        :rtype: bool
        """
        if type(id) != type(int()):
            raise InvalidParameter(
                u"Parameter id must be int, not %s" %
                type(id)
            )
        if scope == u"page":
            self.page_custom_var[id] = (name, value)
        elif scopr == u"event":
            self.event_custom_var[id] = (name, value)
        elif scope == u"visit":
            self.visitor_custom_var[id] = (name, value)
        else:
            raise InvalidParameter(u"Invalid scope parameter value %s" % scope)
        return True

    def set_dimension(self, name, value):
        u"""
        Set a custom dimension

        See http://piwik.org/docs/custom-dimensions/

        :param name: Variable name
        :type name: str
        :param value: Variable value
        :type value: str
        :rtype: None
        """
        self.dimensions[name] = value
        return True

    def set_plugins(self, **kwargs):
        u"""
        Set supported plugins

        >>> piwiktrackerinstance.set_plugins(flash=True)

        See KNOWN_PLUGINS keys for valid values.

        :param kwargs: A plugin: version dict, e.g. {"java": 6}, see also
            KNOWN_PLUGINS
        :type kwargs: dict of {str: int}
        :rtype: bool
        """
        for plugin, version in kwargs.items():
            if plugin not in list(self.KNOWN_PLUGINS.keys()):
                raise ConfigurationError(
                    u"Unknown plugin %s, please use one "
                    u"of %s" %
                    (plugin, list(self.KNOWN_PLUGINS.keys()))
                )
            self.plugins[self.KNOWN_PLUGINS[plugin]] = int(version)
        return True

    def get_custom_variable(self, id, scope):
        u"""
        Returns the current custom variable stored in a first party cookie.

        :param id: Custom variable slot ID, 1-5
        :type id: int
        :param scope: Variable scope, either visit or page
        :type scope: str
        :rtype: mixed stuff TODO
        """
        var_map = None
        if scope == u"visit":
            var_map = self.visitor_custom_var
        elif scope == u"event":
            var_map = self.event_custom_var
        elif scope == u"page":
            var_map = self.page_custom_var
        else:
            raise InvalidParameter(
                u"Bad scope: %s" % scope
            )
        if id not in var_map:
            return None
        return var_map[id]

    def __get_url_track_ecommerce_order(
            self,
            order_id,
            grand_total,
            sub_total=False,
            tax=False,
            shipping=False,
            discount=False
    ):
        u"""
        Returns an URL used to track ecommerce orders

        Calling this method will reinitialize the property ecommerce_items to
        an empty list. So items will have to be added again via
        add_ecommerce_item().

        :param order_id: Unique order ID (required). Used to avoid
            re-recording an order on page reload.
        :type order_id: str
        :param grand_total: Grand total revenue of the transaction,
            including taxes, shipping, etc.
        :type grand_total: float
        :param sub_total: Sub total amount, typicalle the sum of
            item prices for all items in this order, before tax and shipping
        :type sub_total: float or None
        :param tax: Tax amount for this order
        :type tax: float or None
        :param shipping: Shipping amount for this order
        :type shipping: float or None
        :param discount: Discount for this order
        :type discount: float or None
        :rtype: str
        """
        url = (
            self.__get_url_track_ecommerce(
                grand_total,
                sub_total,
                tax,
                shipping,
                discount
            )
        )
        url += u"&%s" % urlencode({u"ec_id": order_id})
        self.ecommerce_last_order_timestamp = self._get_timestamp()
        return url

    def __get_url_track_ecommerce(
            self,
            grand_total,
            sub_total=False,
            tax=False,
            shipping=False,
            discount=False
    ):
        u"""
        Returns the URL used to track ecommerce orders

        Calling this method reinitializes the property ecommerce_items, so
        items will have to be added again via add_ecommerce_item()

        :param grand_total: Grand total revenue of the transaction,
            including taxes, shipping, etc.
        :type grand_total: float
        :param sub_total: Sub total amount, typicalle the sum of
            item prices for all items in this order, before tax and shipping
        :type sub_total: float or None
        :param tax: Tax amount for this order
        :type tax: float or None
        :param shipping: Shipping amount for this order
        :type shipping: float or None
        :param discount: Discount for this order
        :type discount: float or None
        :rtype: str
        """
        ## FIXME fix what?
        url = self._get_request(self.id_site)
        args = {
            u"idgoal": 0,
        }
        args[u"revenue"] = grand_total
        if sub_total:
            args[u"ec_st"] = sub_total
        if tax:
            args[u"ec_tx"] = tax
        if shipping:
            args[u"ec_sh"] = shipping
        if discount:
            args[u"ec_dt"] = discount
        if self.ecommerce_items is not None and len(self.ecommerce_items) > 0:
            # Remove the SKU index in the list before JSON encoding
            items = list(self.ecommerce_items.values())
            args[u"ec_items"] = json.dumps(items)
        self.ecommerce_items.clear()
        url += u"&%s" % urlencode(args)
        return url

    def __get_url_track_ecommerce_cart_update(self, grand_total):
        u"""
        Returns the URL to track a cart update

        :type grand_total: float
        :param grand_total: Grand total revenue of the transaction,
            including taxes, shipping, etc.
        :type grand_total: float
        :rtype: str
        """
        url = self.__get_url_track_ecommerce(grand_total)
        return url

    def add_ecommerce_item(
            self,
            sku,
            name=False,
            category=False,
            price=False,
            quantity=1
    ):
        u"""
        Add an item to the ecommerce order.

        This should be called before do_track_ecommerce_order() or before
        do_track_ecommerce_cart_update().

        This method can be called for all individual products in the
        cart/order.

        :param sku: Product SKU
        :type SKU: str or None
        :param name: Name of the product
        :type name: str or None
        :param category: Name of the category for the current
            category page or the product
        :type category: str, list or None
        :param price: Price of the product
        :type price: float or None
        :param quantity: Product quantity, defaults to 1
        :type price: int or None
        :rtype: bool
        """
        self.ecommerce_items[sku] = (
            sku,
            name,
            category,
            price,
            quantity,
        )
        return True

    def do_track_ecommerce_cart_update(self, grand_total):
        u"""
        Track a cart update (add/remove/update item)

        On every cart update you must call add_ecommerce_item() for each item
        in the cart, including items which were in the previous cart. Items
        get deleted until they are re-submitted.

        :type grand_total: float
        :param grand_total: Grand total revenue of the transaction,
            including taxes, shipping, etc.
        :type grand_total: float
        :rtype: str
        """
        # FIXME
        url = self.__get_url_track_ecommerce_cart_update(grand_total)
        return self._send_request(url)

    def do_track_ecommerce_order(
            self,
            order_id,
            grand_total,
            sub_total=False,
            tax=False,
            shipping=False,
            discount=False
    ):
        u"""
        Track an ecommerce order

        If the order contains items you must call add_ecommerce_item() first
        for each item.

        All revenues will be individually summed and reported by Piwik.

        :param order_id: Unique order ID (required). Used to avoid
            re-recording an order on page reload.
        :type order_id: str
        :param grand_total: Grand total revenue of the transaction,
            including taxes, shipping, etc.
        :type grand_total: float
        :param sub_total: Sub total amount, typicalle the sum of
            item prices for all items in this order, before tax and shipping
        :type sub_total: float or None
        :param tax: Tax amount for this order
        :type tax: float or None
        :param shipping: Shipping amount for this order
        :type shipping: float or None
        :param discount: Discount for this order
        :type discount: float or None
        :rtype: str
        """
        url = (
            self.__get_url_track_ecommerce_order(
                order_id,
                grand_total,
                sub_total,
                tax,
                shipping,
                discount
            )
        )
        return self._send_request(url)

    def set_track_goal(self, id_goal, revenue=None):
        u"""
        Record a goal conversion

        :param id_goal: Goal ID
        :type id_goal: int
        :param revenue: Revenue for this conversion
        :type revenue: int (TODO why int here and not float!?)
        :rtype: str
        """
        self.id_goal = id_goal
        if revenue is not None:
            self.revenue = revenue
        return True

    def set_ecommerce_view(
            self,
            sku=False,
            name=False,
            category=False,
            price=False
    ):
        u"""
        Set the page view as an item/product page view, or an ecommerce
        category page view.

        This method will set three custom variables of "page" scope with the
        SKU, name and category for this page view.

        On a category page you may set the category argument only.

        Tracking product/category page views will allow Piwik to report on
        product and category conversion rates.

        To enable ecommerce tracking see doc/install.rst

        :param SKU: Product SKU being viewed
        :type SKU: str or None
        :param name: Name of the product
        :type name: str or None
        :param category: Name of the category for the current
            category page or the product
        :type category: str, list or None
        :param price: Price of the product
        :type price: float or None
        :rtype: bool
        """
        if category:
            if type(category) == type(list()):
                category = json.dumps(category)
        else:
            category = u""
        self.page_custom_var[5] = (u"_pkc", category)
        if price:
            self.page_custom_var[2] = (u"_pkp", price)
        # On a category page do not record "Product name not defined"
        if sku and name:
            if sku:
                self.page_custom_var[3] = (u"_pks", sku)
            if name:
                self.page_custom_var[4] = (u"_pkn", name)
        return True
