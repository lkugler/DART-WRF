module purge
module load 
export SLURM_STEP_GRES=none

##  $SLURM_ARRAY_TASK_ID
echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID
EXPNAME=<exp.expname> 

MAINDIR=<cluster.wrf_rundir_base> 
pinning=(0-9 10-19 20-29 30-39)

for ((n=1; n<=4; n++))
do
    RUNDIR=$USERDIR/run_WRF/$EXPNAME/$IENS
    cd $RUNDIR
    rm -r wrfout_d01_*
    echo 'mpirun -genv I_MPI_PIN_PROCESSOR_LIST=${pinning[$n]} -np 10 ./wrf.exe >/dev/null 2>&1'
    mpirun -genv I_MPI_PIN_PROCESSOR_LIST=${pinning[$n]} -np 10 ./wrf.exe >/dev/null 2>&1
    cd ../
done
wait

# error checking
for ((n=1; n<=4; n++))
do
   IENS="$(((($SLURM_ARRAY_TASK_ID - 1)* 4) + $n))"
   RUNDIR=$MAINDIR/$EXPNAME/$IENS
   cd $RUNDIR
   line=`tail -n 1 rsl.out.0000`
   if [[ $line == *"SUCCESS COMPLETE WRF"* ]]; 
   then 
      echo $RUNDIR 'SUCCESS COMPLETE WRF'
   else  
      echo $RUNDIR $line
      exit 1
   fi
done
