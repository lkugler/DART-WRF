module purge
module load intel-parallel-studio/composer.2020.2-intel-20.0.2-zuot22y \
 netcdf-fortran/4.5.3-intel-20.0.2-irdm5gq
export SLURM_STEP_GRES=none

echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID
EXPNAME=<exp.expname> 
MAINDIR=<cluster.wrf_rundir_base> 

IENS=$SLURM_ARRAY_TASK_ID
RUNDIR=$MAINDIR/$EXPNAME/$IENS
echo "ENSEMBLE NR: "$IENS" in "$RUNDIR
cd $RUNDIR
rm -rf rsl.out.0*
echo "mpirun -np 10 ./wrf.exe"
mpirun -np 10 ./wrf.exe


# error checking
line=`tail -n 2 rsl.out.0000`
if [[ $line == *"SUCCESS COMPLETE WRF"* ]]; 
then 
   echo $RUNDIR 'SUCCESS COMPLETE WRF'
else  
   echo $RUNDIR $line
   exit 1
fi
