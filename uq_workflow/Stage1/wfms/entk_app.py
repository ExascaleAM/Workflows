#!/usr/bin/env python3

"""
RADICAL-EnTK application for the ExaAM challenge problem case
https://code.ornl.gov/8s2/exaam-challenge-problem
"""

import glob
import os

from entk_base import re, rp, BaseWF, get_args


# ------------------------------------------------------------------------------
#
class DemoWF(BaseWF):

    # --------------------------------------------------------------------------
    #
    def __init__(self, **kwargs):

        super().__init__(config_file=kwargs.get('config_file'))
        self.cases_dir   = kwargs.get('cases_dir') or os.getcwd()
        self.stage_group = (kwargs.get('stage_group') or '').lower()

    # --------------------------------------------------------------------------
    #
    def get_stages(self):

        stages = []

        if not self.stage_group or self.stage_group == 'additivefoam':
            stages.extend(self._stages_additivefoam())

        if not self.stage_group or self.stage_group == 'exaca':
            stages.extend(self._stages_exaca())

        return stages

    # --------------------------------------------------------------------------
    #
    def _stages_additivefoam(self):

        stages = [re.Stage(), re.Stage()]

        # AdditiveFOAM preparation steps

        case_types = ['odd', 'even']
        num_subdomains = 224  # 4 nodes (with blocked 8 cores per node)

        for case in glob.glob('%s/additivefoam/*' % self.cases_dir):
            for case_type in case_types:
                sub_case = '%s/%s' % (case, case_type)

                stages[0].add_tasks(re.Task({
                    'executable': ':',
                    'pre_exec': [
                        # required for AdditiveFOAM bashrc-script
                        'export USER=$SLURM_JOB_USER',
                        'source $WORLDWORK/mat190/colemanjs/OpenFOAM/Cray/'
                        'OpenFOAM-10/etc/bashrc',
                        'foamCloneCase %s %s' % (case, sub_case),
                        'cd %s' % sub_case,
                        'foamDictionary -entry numberOfSubdomains '
                        '-set %d system/decomposeParDict' % num_subdomains,
                        'decomposePar > log.decomposePar 2>&1',
                        'foamDictionary -entry pathFile '
                        '-set scanPath_%s constant/heatSourceDict' % case_type
                    ]
                }))

        # AdditiveFOAM

        for case in glob.glob('%s/additivefoam/*' % self.cases_dir):
            for case_type in case_types:
                sub_case = '%s/%s' % (case, case_type)

                stages[1].add_tasks(re.Task({
                    'executable': 'additiveFoam',
                    'arguments': ['-parallel'],
                    'pre_exec': [
                        # required for AdditiveFOAM bashrc-script
                        'export USER=$SLURM_JOB_USER',
                        'source $WORLDWORK/mat190/colemanjs/OpenFOAM/Cray/'
                        'OpenFOAM-10/etc/bashrc',
                        'cd %s' % sub_case
                    ],
                    'post_launch': [
                        'cd %s' % case,
                        'echo "x,y,z,tm,ts,cr" > %s.csv' % case_type,
                        'cat %s/exaca* >> %s.csv' % (case_type, case_type)
                    ],
                    'cpu_reqs': {'cpu_processes': num_subdomains,
                                 'cpu_threads': 1,
                                 'cpu_thread_type': rp.OpenMP}
                }))

        return stages

    # --------------------------------------------------------------------------
    #
    def _stages_exaca(self):

        stages = [re.Stage(), re.Stage()]

        # ExaCA

        exaca_path = '/lustre/orion/mat190/world-shared/rolchigo/ExaCA/' + \
                     'build_amd_cp/install/bin'

        for case in glob.glob('%s/exaca/*' % self.cases_dir):

            stages[0].add_tasks(re.Task({
                'executable' : '%s/ExaCA-Kokkos' % exaca_path,
                'arguments'  : ['inputs.json'],
                'pre_exec'   : [
                    'module load craype-accel-amd-gfx90a',       # GPU aware MPI
                    'module load rocm/5.4.0',
                    'export CRAYPE_LINK_TYPE=dynamic',
                    'export MPIR_CVAR_GPU_EAGER_DEVICE_MEM=0',   # GPU aware MPI
                    'export MPICH_GPU_SUPPORT_ENABLED=1',        # GPU aware MPI
                    'cd %s' % case
                ],
                'cpu_reqs'   : {'cpu_processes'   : 8,
                                'cpu_threads'     : 7,
                                'cpu_thread_type' : rp.OpenMP},
                'gpu_reqs'   : {'gpu_processes'   : 1}
            }))

        # ExaCA analysis

        for case in glob.glob('%s/exaca/*' % self.cases_dir):

            stages[1].add_tasks(re.Task({
                'executable' : '%s/grain_analysis' % exaca_path,
                'arguments'  : [
                    '%s/../templates/exaca/AnalyzeAMB.json' % self.cases_dir,
                    '%s/%s' % (case, os.path.basename(case))],
                'pre_exec'   : [
                    'module load rocm/5.4.0',
                    'cd %s' % case
                ]
            }))

        return stages


# ------------------------------------------------------------------------------
#
if __name__ == '__main__':

    input_options = get_args()
    DemoWF(**{'config_file': input_options.config_file,
              'cases_dir'  : os.path.abspath('../cases'),
              'stage_group': input_options.stage_group}).run(num_reruns=1)

# ------------------------------------------------------------------------------

