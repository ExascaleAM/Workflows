# RADICAL-EnTK-based application for AdditiveFOAM and ExaCA workflows

Original code is located here: https://code.ornl.gov/matitov/exaam-challenge-problem-entk.
Provided solution is based on the RADICAL-EnTK tool from the 
[RADICAL-Cybertools](https://github.com/radical-cybertools) stack (as part of 
the ECP [ExaWorks](https://exaworks.org) project)

NOTE: EnTK solution for Stage 3 is integrated into its corresponding scripts
([entk-base-class](../../Stage3/pre_main_post_script/entk_wf.py),
 [entk-config](../../Stage3/pre_main_post_script/entk_config.json),
 [script-with-integrated-entk-solution](../../Stage3/pre_main_post_script/job_creation.py))

## Early runs

Setup for early runs is presented in [/early-runs](./early-runs), 
which covers runs on Summit, Crusher and pre-production Frontier.

## Runs on Frontier

### 1. Execution environment setup

Corresponding virtual environment is located within the ExaAM project's 
allocation space `MAT190`
```shell
module load cray-python
source $WORLDWORK/mat190/workflow/frontier/ve_workflow/bin/activate
```

#### 1.1. Configure RADICAL tools for Frontier

Control SMT level (number of threads per core) and CoreSpec (number of cores
reserved for system processes)
```shell
mkdir -p ~/.radical/pilot/configs
cat > ~/.radical/pilot/configs/resource_ornl.json <<EOF
{
    "frontier": {

        "system_architecture" : {"smt"           : 1,
                                 "blocked_cores" : [0, 8, 16, 24, 32, 40, 48, 56]}
    }
}
EOF
```

**IN CASE** of `SMT=2`, please, use the following steps (this is a default 
configuration for releases of RADICAL-Pilot `>=1.34`, which is used as a 
runtime system for EnTK apps)
```shell
mkdir -p ~/.radical/pilot/configs
cat > ~/.radical/pilot/configs/resource_ornl.json <<EOF
{
    "frontier": {

        "system_architecture" : {"smt"           : 2,
                                 "blocked_cores" : [ 0,  8, 16, 24, 32,  40,  48,  56,
                                                    64, 72, 80, 88, 96, 104, 112, 120]}
    }
}
EOF
```

#### 1.2. Setup environment for AdditiveFOAM

```shell
source $WORLDWORK/mat190/colemanjs/OpenFOAM/Cray/OpenFOAM-10/etc/bashrc
mkdir -p $WM_PROJECT_USER_DIR
cd $WM_PROJECT_USER_DIR
cp -r $WORLDWORK/mat190/exaam-challenge-problem/CY22-DEMO/src/additiveFoam-10 .
cd additiveFoam-10
wclean
wmake
cd $WORK_DIR
```

### 1.3. Generate AdditiveFOAM and ExaCA cases

```shell
python setup.py
```

### 2. Run EnTK application

Run EnTK app in the background and collect output into `OUTPUT` file
```shell 
nohup python entk_app.py -c entk_config_frontier.json > OUTPUT 2>&1 </dev/null &
```

#### 2.a. Run AdditiveFOAM only

```shell 
nohup python entk_app.py -c entk_config_frontier_openfoam.json \
                         -s openfoam \
                         > OUTPUT 2>&1 </dev/null &
```

#### 2.b. Run ExaCA only

```shell 
nohup python entk_app.py -c entk_config_frontier_exaca.json \
                         -s exaca \
                         > OUTPUT 2>&1 </dev/null &
```

