# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from charmhelpers.contrib.openstack import context
from charmhelpers.core.hookenv import config, leader_get
from charmhelpers.contrib.hahelpers.cluster import (
    determine_apache_port,
    determine_api_port,
)

HEAT_PATH = '/var/lib/heat/'
API_PORTS = {
    'heat-api-cfn': 8000,
    'heat-api': 8004
}


def generate_ec2_tokens(protocol, host, port):
    ec2_tokens = '%s://%s:%s/v2.0/ec2tokens' % (protocol, host, port)
    return ec2_tokens


class HeatIdentityServiceContext(context.IdentityServiceContext):
    def __call__(self):
        ctxt = super(HeatIdentityServiceContext, self).__call__()
        if not ctxt:
            return

        # the ec2 api needs to know the location of the keystone ec2
        # tokens endpoint, set in nova.conf
        ec2_tokens = generate_ec2_tokens(ctxt['service_protocol'] or 'http',
                                         ctxt['service_host'],
                                         ctxt['service_port'])
        ctxt['keystone_ec2_url'] = ec2_tokens
        ctxt['region'] = config('region')
        return ctxt


def get_encryption_key():
    encryption_key = config("encryption-key")
    if not encryption_key:
        encryption_key = leader_get('heat-auth-encryption-key')
    return encryption_key


class HeatSecurityContext(context.OSContextGenerator):

    def __call__(self):
        ctxt = {}
        # check if we have stored encryption key
        ctxt['encryption_key'] = get_encryption_key()
        ctxt['heat_domain_admin_passwd'] = (
            leader_get('heat-domain-admin-passwd'))
        return ctxt


class HeatHAProxyContext(context.OSContextGenerator):
    interfaces = ['heat-haproxy']

    def __call__(self):
        """Extends the main charmhelpers HAProxyContext with a port mapping
        specific to this charm.
        Also used to extend cinder.conf context with correct api_listening_port
        """
        haproxy_port = API_PORTS['heat-api']
        api_port = determine_api_port(haproxy_port, singlenode_mode=True)
        apache_port = determine_apache_port(haproxy_port, singlenode_mode=True)

        haproxy_cfn_port = API_PORTS['heat-api-cfn']
        api_cfn_port = determine_api_port(haproxy_cfn_port,
                                          singlenode_mode=True)
        apache_cfn_port = determine_apache_port(haproxy_cfn_port,
                                                singlenode_mode=True)

        ctxt = {
            'service_ports': {'heat_api': [haproxy_port, apache_port],
                              'heat_cfn_api': [haproxy_cfn_port,
                                               apache_cfn_port]},
            'api_listen_port': api_port,
            'api_cfn_listen_port': api_cfn_port,
        }
        return ctxt


class HeatApacheSSLContext(context.ApacheSSLContext):

    external_ports = API_PORTS.values()
    service_namespace = 'heat'


class InstanceUserContext(context.OSContextGenerator):

    def __call__(self):
        ctxt = {}

        instance_user = ''
        if config('instance-user'):
            instance_user = config('instance-user')
        ctxt['instance_user'] = instance_user
        return ctxt

class HeatLoggingContext(context.OSContextGenerator):

    def __call__(self):
        ctxt = {}
        debug = config('debug')
        if debug:
            ctxt['root_level'] = 'DEBUG'
        log_level = config('log-level')
        log_level_accepted_params = ['WARNING', 'INFO', 'DEBUG', 'ERROR']
        if log_level in log_level_accepted_params:
            ctxt['log_level'] = config('log-level')
        else:
            log("log-level must be one of the following states "
                "(WARNING, INFO, DEBUG, ERROR) keeping the current state.")
            ctxt['log_level'] = None

        return ctxt
