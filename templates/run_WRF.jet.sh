<wrf_modules>
export SLURM_STEP_GRES=none

echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID
IENS=$SLURM_ARRAY_TASK_ID

RUNDIR=<dir_wrf_run>
echo "ENSEMBLE NR: "$IENS" in "$RUNDIR

cd $RUNDIR
rm -rf rsl.out.0*
echo "mpirun -np <WRF_number_of_processors> ./wrf.exe"
mpirun -np <WRF_number_of_processors> ./wrf.exe


# error checking
line=`tail -n 2 rsl.out.0000`
if [[ $line == *"SUCCESS COMPLETE WRF"* ]]; 
then 
   echo $RUNDIR 'SUCCESS COMPLETE WRF'
else  
   echo $RUNDIR $line
   exit 1
fi
