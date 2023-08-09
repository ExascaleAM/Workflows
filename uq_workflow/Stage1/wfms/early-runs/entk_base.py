#!/usr/bin/env python3

"""
Base RADICAL-EnTK application for ExaAM workflows
https://code.ornl.gov/ecpcitest/exaam/workflow
"""

import argparse
import json
import os
import sys
import time

import radical.entk  as re
import radical.pilot as rp

BASE_PATH           = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE_DEFAULT = 'entk_config.json'
TASK_ATTRS_BASE     = ['executable', 'arguments', 'pre_exec', 'post_launch',
                       'cpu_reqs', 'gpu_reqs', 'tags']


# ------------------------------------------------------------------------------
#
class BaseWF:

    def __init__(self, config_file=None):

        os.environ['RADICAL_LOG_LVL'] = 'DEBUG'
        os.environ['RADICAL_PROFILE'] = 'TRUE'

        config_file = config_file or CONFIG_FILE_DEFAULT
        if '/' not in config_file:
            config_file = os.path.join(BASE_PATH, config_file)

        with open(config_file, encoding='utf8') as f:
            cfg = json.load(f)

        if not os.environ.get('RADICAL_PILOT_DBURL'):
            os.environ['RADICAL_PILOT_DBURL'] = cfg['mongodb']['url']

        self._resource_description = cfg['resource_description']

    def get_stages(self):
        raise NotImplementedError('Stages are not provided')

    @staticmethod
    def get_stages_rerun(origin_stages):

        stages = [re.Stage()]
        for s in origin_stages:
            for t in s.tasks:
                if t.state == rp.FAILED:
                    # create a new task
                    t_new = re.Task()
                    for attr in TASK_ATTRS_BASE:
                        t_new[attr] = t[attr]
                    stages[-1].add_tasks(t_new)

            if stages[-1].tasks:
                # if stage is empty, then it will be reused for the next
                # set of tasks, otherwise a new one is added
                stages.append(re.Stage())

        if not stages[-1].tasks:
            del stages[-1]

        return stages

    def get_pipeline(self, origin_pipeline=None):

        stages = self.get_stages() if not origin_pipeline else \
                 self.get_stages_rerun(origin_pipeline.stages)

        if stages:
            pipeline = re.Pipeline()
            pipeline.add_stages(stages)
            return pipeline

    def run(self, num_reruns=0, origin_pipeline=None):

        pipeline = self.get_pipeline(origin_pipeline)
        if pipeline:

            amgr = re.AppManager(reattempts=1)
            amgr.resource_desc = self._resource_description
            amgr.workflow = [pipeline]
            amgr.run()

            if num_reruns:
                time.sleep(20)  # let the previous run to get finalized
                num_reruns -= 1
                self.run(num_reruns=num_reruns,
                         origin_pipeline=amgr.workflow[0])


# ------------------------------------------------------------------------------


def get_args():
    """
    Get arguments.
    :return: Arguments namespace.
    :rtype: _AttributeHolder
    """
    parser = argparse.ArgumentParser(
        description='Run the EnTK application with provided config file',
        usage='<entk app> [-c/--config <config file>]')

    parser.add_argument(
        '-c', '--config',
        dest='config_file',
        type=str,
        help='config file',
        required=False)

    return parser.parse_args(sys.argv[1:])


# ------------------------------------------------------------------------------
