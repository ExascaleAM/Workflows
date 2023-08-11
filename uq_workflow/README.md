# ExaAM Uncertainty Quantification Workflow

This directory contains the necessary files needed to run Stages 1 and 3 of the ExaAM UQ pipeline. In order to run each stage, users will need to build `AdditiveFOAM`, `ExaCA`, and `ExaConstit`. Each of their repos contain information regarding how to build each one. We do include for convenience a set of build scripts for ExaConstit and its TPLs for Frontier in the `Stage3/exaconstit_build` directory. For `AdditiveFOAM`, the Stage 1 repo does contains it as a git submodule so the user just needs to have a valid `OpenFOAM-10` build from which to point the `run_frontier_additivefoam.sh` script at.

Some of the scripts will need to have their file directory locations edited to point towards the users own locations. Since, they currently point towards the locations the ExaAM team used to run the UQ pipeline on Frontier.

## Running the workflows

Stage 1 workflows* on Frontier will require you first running the `Stage1/run_frontier_additivefoam.sh` script. This will generate all the UQ grids, set-up all the problems to be run, and then run all the melt pool simulations to generate the necessary thermal histories required by ExaCA. After the AdditiveFOAM runs are finished, one can then run the `Stage1/run_frontier_exaca.sh` script which will generate all the process-aware built microstructures and then carve out the appropriate representative volume element microstructures for Stage 3.

**(*)** Alternative Stage 1 workflow using RADICAL-EnTK is available in the [Stage1/wfms](Stage1/wfms) directory.

Stage 3 workflows are largely driven by the python scripts in `Stage3/pre_main_post_script`. We've provided the exact ones used to run the full UQ workflow in `Stage3/pre_main_post_script/chal_prob_full.py` and `Stage3/pre_main_post_script/chal_prob_mini.py` which runs only the monotonic loading conditions which can be used for comparisons. Since those scripts can be long running, you'll likely want to do something like: `nohup python chal_prob_mini.py > OUTPUT_chal_mini_run_xyz 2>&1 </dev/null &` to create a background task that will survive if the ssh pipe breaks. For the comparisons to the macroscopic compression experiments done on the IN625 AMB2018-01 sample, one would first run the `Stage3/postprocessing/chal_ss_vals.py` script to retrieve all the necessary information from all the simulations and generate a python pickle file for later analysis. Afterwards, the `Stage3/postprocessing/chal_postprocess.py` script can be run which will do some basic analysis of the simulation data to the experimental macroscopic stress-strain data points.

## Notes

Data required for the Stage 1 workflow is contained in the Workflows_data (https://github.com/ExascaleAM/Workflows_data). This data would be the `Stage1/templates` directory. So, you'll need to clone that repo and then move the associated folder into the `uq_workflows` location. You'll also need to untar the few `*.tar.gz` files from that repo in here as well. They should be the `uq_workflow/Stage1/templates/openfoam/constant/polyMesh.tar.gz`, `uq_workflow/Stage1/templates/exaca/uni_cubic_1e6_quats.tar.gz`, and `uq_workflow/Stage1/templates/exaca/GrainOrientationVectors_1e6.tar.gz` files.

Additionally, you'll note we make use of a different python virtual environment for each stage. We've listed the packages required for each one. So, you could combine them into one virtual env if you'd like.

Stage 3's virtual env looks like:

```bash
python -m venv entk
source entk/bin/activate
pip install wheel setuptools-rust numpy pandas scipy
pip install git+https://github.com/radical-cybertools/radical.utils.git@devel
pip install git+https://github.com/radical-cybertools/radical.saga.git@devel
pip install git+https://github.com/radical-cybertools/radical.pilot.git@devel
pip install git+https://github.com/radical-cybertools/radical.entk.git@devel
pip install numpy scipy pandas matplotlib seaborn
pip install --upgrade "jax[cpu]"
```

and Stage 1 is largely the same minus the JAX package. It will also require the user to install the TASMANIAN python package found here: https://github.com/ORNL/TASMANIAN .

Stage 3's workflow requires a working Rust compiler to build some of the underlying python libraries required to coarsen microstructures from Stage 1.

For the Stage 1 directory, this workflow belongs to the ExaCA repo and therefore its LICENSE file is the same as the ExaCA repo.

For the Stage 3 directory, this workflow belongs to the ExaConstit repo and therefore its LICENSE file is the same as the ExaConstit repo.
