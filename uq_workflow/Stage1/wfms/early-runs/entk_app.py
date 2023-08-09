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
        self.cases_dir  = kwargs.get('cases_dir') or os.getcwd()

    # --------------------------------------------------------------------------
    #
    def get_stages(self):

        if 'crusher' in self._mgr._rmgr.resource or \
                'frontier' in self._mgr._rmgr.resource:
            return self._get_stages_frontier()

        if 'summit' in self._mgr._rmgr.resource:
            return self._get_stages_summit()

        super().get_stages()

    # --------------------------------------------------------------------------
    #
    def _get_stages_frontier(self):

        stages = [re.Stage(), re.Stage(), re.Stage(), re.Stage()]

        # OpenFOAM preparation steps

        case_types     = ['odd', 'even']
        num_subdomains = 60

        tag_idx = 0
        for case in glob.glob('%s/cases/openfoam/*' % self.cases_dir):
            for case_type in case_types:
                sub_case = '%s/%s' % (case, case_type)

                stages[0].add_tasks(re.Task({
                    'executable' : ':',
                    'pre_exec'   : [
                        'export WM_MPLIB=SYSTEMMPI',
                        'export MPI_ROOT=$MPICH_DIR',
                        'export MPI_ARCH_FLAGS="-DMPICH_SKIP_MPICXX"',
                        'export MPI_ARCH_INC="-I$MPI_ROOT/include"',
                        'export MPI_ARCH_LIBS="-L$MPI_ROOT/lib -lmpich -lrt"',
                        # required for OpenFOAM bashrc-script
                        'export USER=$SLURM_JOB_USER',
                        'source /gpfs/alpine/world-shared/mat190/coleman/'
                        'OpenFOAM/crusher/OpenFOAM-8/etc/bashrc',
                        'foamCloneCase %s %s' % (case, sub_case),
                        'cd %s' % sub_case,
                        'foamDictionary -entry numberOfSubdomains '
                        '-set %d system/decomposeParDict' % num_subdomains,
                        'decomposePar > log.decomposePar 2>&1',
                        'foamDictionary -entry pathFile '
                        '-set scanPath_%s constant/heatSourceDict' % case_type
                    ],
                    'tags'       : {'colocate'  : str(tag_idx),
                                    'exclusive' : True}
                }))
                tag_idx += 1

        # OpenFOAM

        tag_idx = 0
        for case in glob.glob('%s/cases/openfoam/*' % self.cases_dir):
            for case_type in case_types:
                sub_case = '%s/%s' % (case, case_type)

                stages[1].add_tasks(re.Task({
                    'executable' : 'additiveFoam',
                    'arguments'  : ['-parallel'],
                    'pre_exec'   : [
                        'export WM_MPLIB=SYSTEMMPI',
                        'export MPI_ROOT=$MPICH_DIR',
                        'export MPI_ARCH_FLAGS="-DMPICH_SKIP_MPICXX"',
                        'export MPI_ARCH_INC="-I$MPI_ROOT/include"',
                        'export MPI_ARCH_LIBS="-L$MPI_ROOT/lib -lmpich -lrt"',
                        # required for OpenFOAM bashrc-script
                        'export USER=$SLURM_JOB_USER',
                        'source /gpfs/alpine/world-shared/mat190/coleman/'
                        'OpenFOAM/crusher/OpenFOAM-8/etc/bashrc',
                        'cd %s' % sub_case
                    ],
                    'post_launch': [
                        'cd %s' % sub_case,
                        'echo "x,y,z,tm,ts,cr" > %s.csv' % sub_case,
                        'cat exaca* >> %s.csv' % sub_case
                        # in case of the header "x,y,z,tm,ts,cr" duplication,
                        # use the following line instead of lines above:
                        #    'cp %s/exaca.csv %s.csv' % (sub_case, sub_case)
                    ],
                    'cpu_reqs'   : {'cpu_processes'   : num_subdomains,
                                    'cpu_threads'     : 1,
                                    'cpu_thread_type' : rp.OpenMP},
                    'tags'       : {'colocate'        : str(tag_idx),
                                    'exclusive'       : True}
                }))
                tag_idx += 1

        # ExaCA

        exaca_path = '/gpfs/alpine/world-shared/mat190/rolchigo/ExaCA' + \
                     '/build_vega90A_wf/install/bin'

        tag_idx = 0
        for case in glob.glob('%s/cases/exaca/*' % self.cases_dir):

            stages[2].add_tasks(re.Task({
                'executable' : '%s/ExaCA-Kokkos' % exaca_path,
                'arguments'  : ['inputs.txt'],
                'pre_exec'   : [
                    'module load craype-accel-amd-gfx908',       # GPU aware MPI
                    'module load rocm/5.1.0',
                    'export CRAYPE_LINK_TYPE=dynamic',
                    'export MPIR_CVAR_GPU_EAGER_DEVICE_MEM=0',   # GPU aware MPI
                    'export MPICH_GPU_SUPPORT_ENABLED=1',        # GPU aware MPI
                    'cd %s' % case
                ],
                'cpu_reqs'   : {'cpu_processes'   : 8,
                                'cpu_threads'     : 1,
                                'cpu_thread_type' : rp.OpenMP},
                'gpu_reqs'   : {'gpu_processes'   : 1},
                'tags'       : {'colocate'        : str(tag_idx),
                                'exclusive'       : True}
            }))
            tag_idx += 1

        # ExaCA analysis

        tag_idx = 0
        for case in glob.glob('%s/cases/exaca/*' % self.cases_dir):

            stages[3].add_tasks(re.Task({
                'executable' : '%s/grain_analysis_amb' % exaca_path,
                'arguments'  : ['%s/%s' % (case, os.path.basename(case))],
                'pre_exec'   : [
                    'cd %s' % case
                ],
                'tags'       : {'colocate'  : str(tag_idx),
                                'exclusive' : True}
            }))
            tag_idx += 1

        return stages

    # --------------------------------------------------------------------------
    #
    def _get_stages_summit(self):

        stages = [re.Stage(), re.Stage(), re.Stage()]

        # OpenFOAM preparation steps

        case_types     = ['odd', 'even']
        num_subdomains = 42

        for case in glob.glob('%s/cases/openfoam/*' % self.cases_dir):
            for case_type in case_types:
                sub_case = '%s/%s' % (case, case_type)

                stages[0].add_tasks(re.Task({
                    'executable' : ':',
                    'pre_exec'   : [
                        # required for OpenFOAM bashrc-script
                        'export USER=$LSFUSER',
                        'source /gpfs/alpine/world-shared/mat190/coleman/'
                        'OpenFOAM/summit/OpenFOAM-8/etc/bashrc',
                        'foamCloneCase %s %s'  % (case, sub_case),
                        'cd %s' % sub_case,
                        'foamDictionary -entry numberOfSubdomains '
                        '-set %d system/decomposeParDict' % num_subdomains,
                        'decomposePar > log.decomposePar 2>&1',
                        'foamDictionary -entry pathFile '
                        '-set scanPath_%s constant/heatSourceDict' % case_type
                    ]
                }))

        # OpenFOAM

        for case in glob.glob('%s/cases/openfoam/*' % self.cases_dir):
            for case_type in case_types:
                sub_case = '%s/%s' % (case, case_type)

                stages[1].add_tasks(re.Task({
                    'executable' : 'additiveFoam',
                    'arguments'  : ['-parallel'],
                    'pre_exec'   : [
                        # required for OpenFOAM bashrc-script
                        'export USER=$LSFUSER',
                        'source /gpfs/alpine/world-shared/mat190/coleman/'
                        'OpenFOAM/summit/OpenFOAM-8/etc/bashrc',
                        'cd %s' % sub_case
                    ],
                    'post_launch': [
                        'cd %s' % sub_case,
                        'echo "x,y,z,tm,ts,cr" > %s.csv' % sub_case,
                        'cat exaca* >> %s.csv' % sub_case
                        # in case of the header "x,y,z,tm,ts,cr" duplication,
                        # use the following line instead of lines above:
                        #    'cp %s/exaca.csv %s.csv' % (sub_case, sub_case)
                    ],
                    'cpu_reqs'   : {'cpu_processes'  : num_subdomains,
                                    'cpu_threads'    : 1,
                                    'cpu_thread_type': rp.OpenMP}
                }))

        # ExaCA

        for case in glob.glob('%s/cases/exaca/*' % self.cases_dir):

            stages[2].add_tasks(re.Task({
                'executable' : '/gpfs/alpine/world-shared/mat190/rolchigo/ExaCA'
                               '/build_v100/install/bin/ExaCA-Kokkos',
                'arguments'  : ['inputs.txt'],
                'pre_exec'   : [
                    '. /sw/summit/lmod/lmod/init/profile',
                    'module load gcc cuda',
                    'cd %s' % case
                ],
                'cpu_reqs'   : {'cpu_processes'   : 6,
                                'cpu_threads'     : 1,
                                'cpu_thread_type' : rp.OpenMP},
                'gpu_reqs'   : {'gpu_processes'   : 1,
                                'gpu_process_type': rp.CUDA}

            }))

        return stages


# ------------------------------------------------------------------------------
#
if __name__ == '__main__':

    input_options = get_args()
    DemoWF(**{'config_file': input_options.config_file,
              'cases_dir'  : os.path.abspath('..')}).run(num_reruns=1)

# ------------------------------------------------------------------------------

