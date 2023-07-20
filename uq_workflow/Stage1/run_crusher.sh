#!/bin/bash

#SBATCH -A MAT190_crusher
#SBTACH -p batch
#SBATCH -J workflow
#SBATCH -o log.out
#SBATCH -e log.err
#SBATCH --mem=0
#SBATCH --cpus-per-task=1
#SBATCH --threads-per-core=1
#SBATCH --exclusive

#SBATCH --nodes 20
#SBATCH -t 04:00:00

export OMP_NUM_THREADS=1

cd $SLURM_SUBMIT_DIR
baseDir="$PWD"

#------------------------------------------------------------------------------#
# STAGE 0 : SETUP
module load cray-python
source /gpfs/alpine/world-shared/mat190/workflow/ve_workflow/bin/activate
python setup.py
deactivate

#------------------------------------------------------------------------------#
# STAGE 1 : OPENFOAM
module reset

export WM_MPLIB=SYSTEMMPI
export MPI_ROOT=$MPICH_DIR
export MPI_ARCH_FLAGS="-DMPICH_SKIP_MPICXX"
export MPI_ARCH_INC="-I$MPI_ROOT/include"
export MPI_ARCH_LIBS="-L$MPI_ROOT/lib -lmpich -lrt"
source /gpfs/alpine/world-shared/mat190/coleman/OpenFOAM/crusher/OpenFOAM-8/etc/bashrc

# note : each user must build their own additiveFoam application
INST_DIR="$baseDir/src/additiveFoam"
cd $INST_DIR
./Allwclean
./Allwmake
cd $baseDir

nCores=224   # default on crusher (blocks 1 cores per 8 NUMA domains)
FLAGS_openfoam="--tasks-per-node=56 --cpus-per-task=1 --threads-per-core=1"
SRUN_openfoam="srun -N 4 -n $nCores -m *:fcyclic $FLAGS_openfoam"
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
    
    sleep 0.1

    # run even layer
    (
        cd $d/even

        decomposePar > log.decomposePar 2>&1
        foamDictionary -entry pathFile -set scanPath_even constant/heatSourceDict
	
        $SRUN_openfoam additiveFoam -parallel > log.additiveFoam 2>&1
    ) &

    sleep 0.1
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

#------------------------------------------------------------------------------#
# STAGE 2 : EXACA
module reset
module load craype-accel-amd-gfx908
module load rocm/5.1.0

export CRAYPE_LINK_TYPE=dynamic
export MPIR_CVAR_GPU_EAGER_DEVICE_MEM=0
export MPICH_GPU_SUPPORT_ENABLED=1

PATH_exaca="/gpfs/alpine/world-shared/mat190/rolchigo/ExaCA/build_vega90A_wf/install/bin"
EXE_exaca="$PATH_exaca/ExaCA-Kokkos"
EXE_exaca_analysis="$PATH_exaca/grain_analysis_amb"

FLAGS_exaca="--exclusive --cpus-per-task=1 --gpus-per-task=1 --gpu-bind=closest"
SRUN_exaca="srun -N 1 -n 8 -m *:fcyclic $FLAGS_exaca $EXE_exaca"
SRUN_exaca_analysis="srun -N 1 -n 1 -m *:fcyclic --exclusive --cpus-per-task=1 $EXE_exaca_analysis"

# execute exaca
for d in $baseDir/cases/exaca/*
do
    (
        cd $d

        $SRUN_exaca inputs.txt > log.exaca 2>&1
    ) &

    sleep 0.1
done

wait

# collect grain statistics for exaca cross-sections of interest
for d in $baseDir/cases/exaca/*
do
    (
        cd $d

        $SRUN_exaca_analysis d > log.exaca 2>&1
    ) &

    sleep 0.1
done

wait
#------------------------------------------------------------------------------#
