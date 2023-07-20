# Copy ExaCA output files of interest to a consolidated directory
baseDir="$PWD"
mkdir ca_artifacts
cd ca_artifacts
mkdir grain_stats
mkdir mtex
mkdir logs
cd ..
for d in $baseDir/cases/exaca/*
do
    (
        cd $d
        caseid="${d##*/}"
	scp $d/$caseid*_grains.csv $baseDir/ca_artifacts/grain_stats
	scp $d/$caseid*_QoIs.txt $baseDir/ca_artifacts/grain_stats
	scp $d/$caseid*IPFCrossSectionData.txt $baseDir/ca_artifacts/mtex
	scp $d/$caseid*PoleFigureData.txt $baseDir/ca_artifacts/mtex
	scp $d/$caseid*.json $baseDir/ca_artifacts/logs
    ) 
done
