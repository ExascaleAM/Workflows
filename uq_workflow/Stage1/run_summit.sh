#!/bin/bash

#BSUB -P MAT190
#BSUB -q batch
#BSUB -W 2:00
#BSUB -nnodes 10
#BSUB -J workflow
#BSUB -o log.out
#BSUB -e log.err

baseDir="$PWD"

export OMP_NUM_THREADS=1

#------------------------------------------------------------------------------#
# STAGE 1 : ADDITIVEFOAM
source /gpfs/alpine/world-shared/mat190/coleman/OpenFOAM/summit/OpenFOAM-8/etc/bashrc

foamDictionary -entry numberOfSubdomains -set 42 templates/openfoam/system/decomposeParDict
RUN_additivefoam="jsrun -n 42 additiveFoam -parallel"

for d in $baseDir/cases/openfoam/*
do
    (
        foamCloneCase $d $d/odd
        foamCloneCase $d $d/even
    ) &
done

wait

# execute additivefoam
for d in $baseDir/cases/openfoam/*
do
    #run odd layer
    (
        cd $d/odd

        decomposePar > log.decomposePar 2>&1
        foamDictionary -entry pathFile -set scanPath_odd constant/heatSourceDict
        $RUN_additivefoam > log.additiveFoam 2>&1

        echo "x,y,z,tm,ts,cr" > $d/odd.csv
        cat exaca* >> $d/odd.csv
    ) &

    sleep 1

    #run even layer
    (
        cd $d/even

        decomposePar > log.decomposePar 2>&1
        foamDictionary -entry pathFile -set scanPath_odd constant/heatSourceDict
        $RUN_additivefoam > log.additiveFoam 2>&1

        echo "x,y,z,tm,ts,cr" > $d/even.csv
        cat exaca* >> $d/even.csv
    ) &

    sleep 1
done

wait

#------------------------------------------------------------------------------#
# STAGE 2 : EXACA

module load cuda
module load gcc

PATH_exaca="/gpfs/alpine/world-shared/mat190/rolchigo/ExaCA"
EXE_exaca="$PATH_exaca/build_v100_wf/install/bin/ExaCA-Kokkos"
FLAGS_exaca="--smpiargs="'"'-gpu'"'""
RUN_exaca="jsrun $FLAGS_exaca -n 6 -a 1 -c 1 -g 1 $EXE_exaca"

# execute exaca
for d in $baseDir/cases/exaca/*
do
    (
        echo "Running case: $d"
        cd $d

        $RUN_exaca inputs.txt > log.exaca 2>&1
    ) &
    
    sleep 1
done

wait

#------------------------------------------------------------------------------#
