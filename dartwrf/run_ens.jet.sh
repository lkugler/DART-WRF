<cluster.wrf_modules>
export SLURM_STEP_GRES=none

echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID
EXPNAME=<exp.expname> 
MAINDIR=<cluster.wrf_rundir_base> 

IENS=$SLURM_ARRAY_TASK_ID
RUNDIR=$MAINDIR/$EXPNAME/$IENS
echo "ENSEMBLE NR: "$IENS" in "$RUNDIR
cd $RUNDIR
rm -rf rsl.out.0*
echo "mpirun -np <exp.np_WRF> ./wrf.exe"
mpirun -np <exp.np_WRF> ./wrf.exe


# error checking
line=`tail -n 2 rsl.out.0000`
if [[ $line == *"SUCCESS COMPLETE WRF"* ]]; 
then 
   echo $RUNDIR 'SUCCESS COMPLETE WRF'
else  
   echo $RUNDIR $line
   exit 1
fi
