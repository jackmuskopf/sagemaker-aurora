#!/usr/bin/env python
import logging
import yaml
import argparse
import boto3
import json

from run_cmd import run_cmd
from hcl import HCLBlock


def preconfiguredLogger(name):
    logger=logging.getLogger(name)
    logger.handlers = list()
    _formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(_formatter)
    logger.addHandler(_stream_handler)
    logger.setLevel(logging.INFO)
    return logger

class InfraMgr:

    default_args = {
        'aws_profile' : 'default',
        'state_bucket' : None,
        'state_key' : None,
        'aws_region' : 'us-east-1',
        'app_name' : 'aurora-sgmkr',
        'stage' : 'develop',
        'vpc_id' : None,
        'sgmkr_subnet' : 'None',
        'aurora_subnets' : list(),
        'db_name' : 'main',
        'db_port' : 5432,
        'db_username' : 'postgres',
        'db_password' : None
    }

    logger = preconfiguredLogger(__name__)

    @classmethod
    def get_command_line_args(cls):

        parser = argparse.ArgumentParser(description='Process some integers.')
        
        parser.add_argument('action', nargs='?')

        parser.add_argument('--no-prompts', 
                            nargs='?',
                            const=True, default=False,
                            help="Use configuration file args or default args")

        return parser.parse_args()

    @classmethod
    def get_static_args(cls):

        config_file_name = 'configuration.yaml'

        # load configuration from a file
        file_args = dict()

        try:
            with open(config_file_name, 'r') as f:
                file_args = yaml.load(f, Loader=yaml.Loader)
                if isinstance(file_args, str):
                    raise Exception("Invalid YAML in configuration file: {}".format(config_file_name))
        except FileNotFoundError:
            logging.warning("No configuration file: {}".format(config_file_name))
        except Exception as e:
            cls.logger.error("[{}] {}".format(type(e), e))

        # use file args -- use default args where not specified
        args = {
            arg: file_args.get(arg) or cls.default_args[arg]
                for arg in cls.default_args
            }

        return args

    @classmethod
    def write_configuration(cls):

        cl_args = cls.get_command_line_args()

        args = cls.get_static_args()

        # prompt for args if no --no-prompts flag
        if not cl_args.no_prompts:

            for arg in args:
                _in = input("{} ({}):".format(arg, args.get(arg)))
                if _in:
                    args[arg] = _in

        for var, val in args.items():
            if val is None:
                raise Exception("Configuration variable: {} is null".format(var))

        # write HCL
        blocks = [
            HCLBlock(
                Class='provider',
                Name='aws',
                Attributes=dict(
                    profile=args['aws_profile'],
                    region=args['aws_region']
                    )
                ),

            HCLBlock(
                Class='terraform',
                Blocks=[
                    HCLBlock(
                        Class='backend',
                        Subclass='s3',
                        Attributes=dict(
                            bucket=args['state_bucket'],
                            key=args['state_key'],
                            region=args['aws_region'],
                            profile=args['aws_profile']
                            )
                        )
                    ]
                )
            ]

        with open("backend.tf", "w") as f:
            f.write("\n\n".join([b.render() for b in blocks]))


        local_keys = [
            'app_name', 'stage', 'vpc_id', 
            'sgmkr_subnet', 'aurora_subnets',
            'db_port', 'db_password', 'db_username', 'db_name'
        ]
        local_attrs = { k : args.get(k) for k in local_keys}
        local_attrs['prefix'] = "${local.app_name}-${local.stage}"
        locals = HCLBlock(
            Class='locals',
            Attributes=local_attrs
            )

        with open("locals.tf", "w") as f:
            f.write(locals.render())

    @classmethod
    def get_session(cls):
        static_args = cls.get_static_args()
        return boto3.session.Session(
            profile_name=static_args['aws_profile'],
            region_name=static_args['aws_region']
        )

    @classmethod
    def get_tf_output(cls, name):

        res = run_cmd('terraform', 'output', '-json', name)

        cls.logger.debug(json.dumps(res))

        if res['exit_code'] != 0:
            cls.logger.error("Failed to get {} from Terraform outputs".format(name))
            return None

        try:
            return json.loads(res['stdout'])
        except json.JSONDecodeError:
            return res['stdout'].strip().strip('"')

    @classmethod
    def get_rds_cluster_status(cls, cluster_identifier):
        session = cls.get_session()
        rds = session.client('rds')
        cluster = None
        for _cluster in rds.describe_db_clusters()['DBClusters']:
            if _cluster['DBClusterIdentifier'] == cluster_identifier:
                cluster = _cluster
                break

        if cluster is None:
            raise Exception("Cluster not found: {}".format(cluster_name))

        return cluster['Status']

    @classmethod
    def get_sgmkr_notebook_status(cls, instance_name):
        session = cls.get_session()
        sgmkr = session.client('sagemaker')
        instance = sgmkr.describe_notebook_instance(NotebookInstanceName=instance_name)
        return instance['NotebookInstanceStatus']


    @classmethod
    def stop_instances(cls):

        session = cls.get_session()

        rds_instance_ids = cls.get_tf_output('rds_instance_ids')

        cluster_name = cls.get_tf_output('rds_cluster_name')

        rds = session.client('rds')

        try:

            rds_status = cls.get_rds_cluster_status(cluster_name)
            if rds_status.lower() not in [ 'stopped', 'stopping' ]:
                rds.stop_db_cluster(
                    DBClusterIdentifier=cluster_name
                )
                rds_status = cls.get_rds_cluster_status(cluster_name)

            cls.logger.info("cluster {} is {}".format(cluster_name, rds_status.lower()))
        except Exception as e:
            cls.logger.error("Failed to stop cluster: {} \n[{}] {}".format(cluster_name, type(e), e))


        sgmkr_name = cls.get_tf_output('sgmkr_name')

        sgmkr = session.client('sagemaker')

        try:
            sgmkr_status = cls.get_sgmkr_notebook_status(sgmkr_name)
            if sgmkr_status.lower() not in ['stopped', 'stopping']: 
                response = sgmkr.stop_notebook_instance(
                    NotebookInstanceName=sgmkr_name
                )
                sgmkr_status = cls.get_sgmkr_notebook_status(sgmkr_name)
            cls.logger.info("Notebook instance {} is {}".format(sgmkr_name, sgmkr_status.lower()))
        except Exception as e:
            cls.logger.error("Failed to stop sagemaker notebook: {} \n[{}] {}".format(sgmkr_name, type(e), e))


    @classmethod
    def start_instances(cls):

        session = cls.get_session()

        rds_instance_ids = cls.get_tf_output('rds_instance_ids')

        cluster_name = cls.get_tf_output('rds_cluster_name')

        rds = session.client('rds')

        try:

            rds_status = cls.get_rds_cluster_status(cluster_name)
            if rds_status.lower() in [ 'stopped' ]:
                rds.start_db_cluster(
                    DBClusterIdentifier=cluster_name
                )
                rds_status = cls.get_rds_cluster_status(cluster_name)

            cls.logger.info("cluster {} is {}".format(cluster_name, rds_status.lower()))
        except Exception as e:
            cls.logger.error("Failed to start cluster: {} \n[{}] {}".format(cluster_name, type(e), e))


        sgmkr_name = cls.get_tf_output('sgmkr_name')

        sgmkr = session.client('sagemaker')

        try:
            sgmkr_status = cls.get_sgmkr_notebook_status(sgmkr_name)
            if sgmkr_status.lower() in ['stopped']: 
                response = sgmkr.start_notebook_instance(
                    NotebookInstanceName=sgmkr_name
                )
                sgmkr_status = cls.get_sgmkr_notebook_status(sgmkr_name)
            cls.logger.info("notebook instance {} is {}".format(sgmkr_name, sgmkr_status.lower()))
        except Exception as e:
            cls.logger.error("Failed to start sagemaker notebook: {} \n[{}] {}".format(sgmkr_name, type(e), e))


    



if __name__ == '__main__':

    cl_args = InfraMgr.get_command_line_args()
    
    if cl_args.action == 'setup':
        InfraMgr.write_configuration()

    elif cl_args.action == 'stop':
        InfraMgr.stop_instances()

    elif cl_args.action == 'start':
        InfraMgr.start_instances()

    else:
        raise Exception("Usage: python mgr.py <action> (--opt1 <val1>, ...)")

