# -*- coding: utf-8 -*-
'''
Return data to Logentries logging service. This driver is meant to be used
by the minions to return information to the logentries logging service.

:maintainer:  Jimmy Tang (jimmy_tang@rapid7.com)
:maturity:    New
:depends:     ssl, certifi
:platform:    all

To enable this returner the minion will need the following python
libraries

    ssl
    certifi

If you are running a new enough version of python then the ssl library
will be present already.

You will also need the following values configured in the minion or
master config.

    logentries.endpoint: data.logentries.com
    logentries.port: 10000
    logentries.token: 057af3e2-1c05-47c5-882a-5cd644655dbf

The 'token' can be obtained from the Logentries service.

To use this returner

    .. code-block:: bash

         salt '*' test.ping --return logentries cmd.run uptime

'''

from __future__ import absolute_import
# Import Salt libs
import salt.utils.jid
import salt.returners

# Import third party libs
try:
    import certifi
    HAS_CERTIFI = True
except ImportError:
    HAS_CERTIFI = False

# This is here for older python installs, it is needed to setup an
# encrypted tcp connection
try:
    import ssl
    HAS_SSL = True
except ImportError:  # for systems without TLS support.
    HAS_SSL = False

# Import Python libs
import os
import socket
import random
import time
import codecs
import ConfigParser
import uuid
import logging

log = logging.getLogger(__name__)

# Define the module's virtual name
__virtualname__ = 'logentries'


def __virtual__():
    if not HAS_CERTIFI:
        return False
    if not HAS_SSL:
        return False
    return __virtualname__


def _to_unicode(ch):
    return codecs.unicode_escape_decode(ch)[0]


def _is_unicode(ch):
    return isinstance(ch, unicode)


def _create_unicode(ch):
    return unicode(ch, 'utf-8')


class PlainTextSocketAppender(object):
    def __init__(self,
                 verbose=True,
                 LE_API='data.logentries.com',
                 LE_PORT=80,
                 LE_TLS_PORT=443):

        self.LE_API = LE_API
        self.LE_PORT = LE_PORT
        self.LE_TLS_PORT = LE_TLS_PORT
        self.MIN_DELAY = 0.1
        self.MAX_DELAY = 10
        # Error message displayed when an incorrect Token has been detected
        self.INVALID_TOKEN = ("\n\nIt appears the LOGENTRIES_TOKEN "
                              "parameter you entered is incorrect!\n\n")
        # Unicode Line separator character   \u2028
        self.LINE_SEP = _to_unicode('\u2028')

        self.verbose = verbose
        self._conn = None

    def open_connection(self):
        self._conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._conn.connect((self.LE_API, self.LE_PORT))

    def reopen_connection(self):
        self.close_connection()

        root_delay = self.MIN_DELAY
        while True:
            try:
                self.open_connection()
                return
            except Exception:
                if self.verbose:
                    log.warning("Unable to connect to Logentries")

            root_delay *= 2
            if (root_delay > self.MAX_DELAY):
                root_delay = self.MAX_DELAY

            wait_for = root_delay + random.uniform(0, root_delay)

            try:
                time.sleep(wait_for)
            except KeyboardInterrupt:
                raise

    def close_connection(self):
        if self._conn is not None:
            self._conn.close()

    def put(self, data):
        # Replace newlines with Unicode line separator
        # for multi-line events
        if not _is_unicode(data):
            multiline = _create_unicode(data).replace('\n', self.LINE_SEP)
        else:
            multiline = data.replace('\n', self.LINE_SEP)
        multiline += "\n"
        # Send data, reconnect if needed
        while True:
            try:
                self._conn.send(multiline.encode('utf-8'))
            except socket.error:
                self.reopen_connection()
                continue
            break

        self.close_connection()


try:
    import ssl
    HAS_SSL = True
except ImportError:  # for systems without TLS support.
    SocketAppender = PlainTextSocketAppender
    HAS_SSL = False
else:

    class TLSSocketAppender(PlainTextSocketAppender):
        def open_connection(self):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock = ssl.wrap_socket(
                sock=sock,
                keyfile=None,
                certfile=None,
                server_side=False,
                cert_reqs=ssl.CERT_REQUIRED,
                ssl_version=getattr(
                    ssl, 'PROTOCOL_TLSv1_2', ssl.PROTOCOL_TLSv1),
                ca_certs=certifi.where(),
                do_handshake_on_connect=True,
                suppress_ragged_eofs=True, )
            sock.connect((self.LE_API, self.LE_TLS_PORT))
            self._conn = sock

    SocketAppender = TLSSocketAppender


def _get_options(ret=None):
    '''
    Get the logentries options from salt.
    '''
    attrs = {'endpoint': 'endpoint', 'port': 'port', 'token': 'token'}

    _options = salt.returners.get_returner_options(__virtualname__,
                                                   ret,
                                                   attrs,
                                                   __salt__=__salt__,
                                                   __opts__=__opts__)
    log.debug('attrs {0}'.format(attrs))
    return _options


def _get_appender(ret=None, _options=None):
    return SocketAppender(verbose=False,
                          LE_API=_options.get('endpoint'),
                          LE_PORT=_options.get('port'))


def _emit(token, msg):
    return "{} {}".format(token, msg)


def returner(ret):

    _options = _get_options(ret)
    log.debug('endpoint={} port={} token={}'.format(_options.get('endpoint'), _options.get('port'), _options.get('token')))

    appender = _get_appender(ret, _options)
    appender.reopen_connection()
    appender.put(_emit(_options.get('token'), ret))
    appender.close_connection()
