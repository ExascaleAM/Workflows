#!/bin/bash

#SBATCH -A MAT190
#SBTACH -p batch
#SBATCH -J workflow
#SBATCH -o log.out
#SBATCH -e log.err
#SBATCH --mem=0
#SBATCH --cpus-per-task=1
#SBATCH --threads-per-core=1
#SBATCH --exclusive

#SBATCH --nodes 40
#SBATCH -t 2:00:00

export OMP_NUM_THREADS=1

cd $SLURM_SUBMIT_DIR
baseDir="$PWD"

#------------------------------------------------------------------------------#
# STAGE 0 : SETUP
module load cray-python
source /lustre/orion/mat190/world-shared/workflow/frontier/ve_workflow/bin/activate
python setup.py
deactivate

#------------------------------------------------------------------------------#
# STAGE 1 : OPENFOAM
module reset

of_version=10
source /lustre/orion/mat190/world-shared/colemanjs/OpenFOAM/Cray/OpenFOAM-$of_version/etc/bashrc

# note : each user must build their own additiveFoam application
INST_DIR=$baseDir/src/additiveFoam-$of_version
cd $INST_DIR
wclean
wmake
cd $baseDir

nCores=224   # default on crusher (blocks 1 cores per 8 NUMA domains)
FLAGS_openfoam="--tasks-per-node=56 --cpus-per-task=1 --threads-per-core=1"
SRUN_openfoam="srun -N 4 -n $nCores $FLAGS_openfoam"
foamDictionary -entry numberOfSubdomains -set $nCores templates/openfoam/system/decomposeParDict

for d in $baseDir/cases/openfoam/*
do
    (
        foamCloneCase $d $d/odd
        foamCloneCase $d $d/even
    ) &
done

wait

# execute openfoam
for d in $baseDir/cases/openfoam/*
do
    # run odd layer
    (
        cd $d/odd

        decomposePar > log.decomposePar 2>&1
        foamDictionary -entry pathFile -set scanPath_odd constant/heatSourceDict
	
        $SRUN_openfoam additiveFoam -parallel > log.additiveFoam 2>&1
    ) &
    
    sleep 1

    # run even layer
    (
        cd $d/even

        decomposePar > log.decomposePar 2>&1
        foamDictionary -entry pathFile -set scanPath_even constant/heatSourceDict
	
        $SRUN_openfoam additiveFoam -parallel > log.additiveFoam 2>&1
    ) &

    sleep 1
done

wait

# reconstruct the solidification data into a single file
for d in $baseDir/cases/openfoam/*
do
    cd $d

    echo "x,y,z,tm,ts,cr" > even.csv
    cat even/exaca* >> even.csv

    echo "x,y,z,tm,ts,cr" > odd.csv
    cat odd/exaca* >> odd.csv
done

wait
