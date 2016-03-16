#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: ecs_service_facts
short_description: list or describe services in ecs
notes:
    - for details of the parameters and returns see U(http://boto3.readthedocs.org/en/latest/reference/services/ecs.html)
description:
    - Lists or describes services in ecs.
version_added: "2.1"
author: Mark Chance (@java1guy)
options:
    details:
        description:
            - Set this to true if you want detailed information about the services.
        required: false
        default: 'false'
        choices: ['true', 'false']
    cluster:
        description:
            - The cluster ARNS in which to list the services.
        required: false
        default: 'default'
    service:
        description:
            - The service to get details for (required if details is true)
        required: false
extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Note: These examples do not set authentication details, see the AWS Guide for details.

# Basic listing example
- ecs_service_facts:
    cluster: test-cluster
    service: console-test-service
    details: "true"

# Basic listing example
- ecs_service_facts:
    cluster: test-cluster
'''

# Disabled the RETURN as it was breaking docs building.  Someone needs to fix
# this
RETURN = '''# '''
'''
services: When details is false, returns an array of service ARNs, else an array of these fields
    clusterArn: The Amazon Resource Name (ARN) of the of the cluster that hosts the service.
    desiredCount: The desired number of instantiations of the task definition to keep running on the service.
    loadBalancers: A list of load balancer objects
        loadBalancerName: the name
        containerName: The name of the container to associate with the load balancer.
        containerPort: The port on the container to associate with the load balancer.
    pendingCount: The number of tasks in the cluster that are in the PENDING state.
    runningCount: The number of tasks in the cluster that are in the RUNNING state.
    serviceArn: The Amazon Resource Name (ARN) that identifies the service. The ARN contains the arn:aws:ecs namespace, followed by the region of the service, the AWS account ID of the service owner, the service namespace, and then the service name. For example, arn:aws:ecs:region :012345678910 :service/my-service .
    serviceName: A user-generated string used to identify the service
    status: The valid values are ACTIVE, DRAINING, or INACTIVE.
    taskDefinition: The ARN of a task definition to use for tasks in the service.
'''
try:
    import boto
    import botocore
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

class EcsServiceManager:
    """Handles ECS Clusters"""

    def __init__(self, module):
        self.module = module

        try:
            # self.ecs = boto3.client('ecs')
            region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
            if not region:
                module.fail_json(msg="Region must be specified as a parameter, in EC2_REGION or AWS_REGION environment variables or in boto configuration file")
            self.ecs = boto3_conn(module, conn_type='client', resource='ecs', region=region, endpoint=ec2_url, **aws_connect_kwargs)
        except boto.exception.NoAuthHandlerFound, e:
            self.module.fail_json(msg="Can't authorize connection - "+str(e))

    # def list_clusters(self):
    #   return self.client.list_clusters()
    # {'failures': [],
    # 'ResponseMetadata': {'HTTPStatusCode': 200, 'RequestId': 'ce7b5880-1c41-11e5-8a31-47a93a8a98eb'},
    # 'clusters': [{'activeServicesCount': 0, 'clusterArn': 'arn:aws:ecs:us-west-2:777110527155:cluster/default', 'status': 'ACTIVE', 'pendingTasksCount': 0, 'runningTasksCount': 0, 'registeredContainerInstancesCount': 0, 'clusterName': 'default'}]}
    # {'failures': [{'arn': 'arn:aws:ecs:us-west-2:777110527155:cluster/bogus', 'reason': 'MISSING'}],
    # 'ResponseMetadata': {'HTTPStatusCode': 200, 'RequestId': '0f66c219-1c42-11e5-8a31-47a93a8a98eb'},
    # 'clusters': []}

    def list_services(self, cluster):
        fn_args = dict()
        if cluster and cluster is not None:
            fn_args['cluster'] = cluster
        response = self.ecs.list_services(**fn_args)
        relevant_response = dict(services = response['serviceArns'])
        return relevant_response

    def describe_services(self, cluster, services):
        fn_args = dict()
        if cluster and cluster is not None:
            fn_args['cluster'] = cluster
        fn_args['services']=services.split(",")
        response = self.ecs.describe_services(**fn_args)
        relevant_response = dict(services = response['services'])
        if 'failures' in response and len(response['failures'])>0:
            relevant_response['services_not_running'] = response['failures']
        return relevant_response

def main():

    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        details=dict(required=False, choices=['true', 'false'] ),
        cluster=dict(required=False, type='str' ),
        service=dict(required=False, type='str' )
    ))

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    if not HAS_BOTO:
      module.fail_json(msg='boto is required.')

    if not HAS_BOTO3:
      module.fail_json(msg='boto3 is required.')

    show_details = False
    if 'details' in module.params and module.params['details'] == 'true':
        show_details = True

    task_mgr = EcsServiceManager(module)
    if show_details:
        if 'service' not in module.params or not module.params['service']:
            module.fail_json(msg="service must be specified for ecs_service_facts")
        ecs_facts = task_mgr.describe_services(module.params['cluster'], module.params['service'])
        # the bad news is the result has datetime fields that aren't JSON serializable
        # nuk'em!
        for service in ecs_facts['services']:
            del service['deployments']
            del service['events']
    else:
        ecs_facts = task_mgr.list_services(module.params['cluster'])
    ecs_facts_result = dict(changed=False, ansible_facts=ecs_facts)
    module.exit_json(**ecs_facts_result)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
