
module purge
module load intel-mpi/2019.6 intel/19.1.0 netcdf-fortran/4.4.5-intel-19.0.5.281-qye4cqn zlib/1.2.11-intel-19.1.0.166-hs6m2qh  hdf5/1.10.5-intel-19.0.5.281-qyzojtm netcdf/4.7.0-intel-19.0.5.281-75t52g6
export SLURM_STEP_GRES=none

##  $SLURM_ARRAY_TASK_ID
echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID
EXPNAME=<expname>

MAINDIR=/gpfs/data/fs71386/lkugler/run_WRF
pinning=(0-11 12-23 24-35 36-47)

for ((n=1; n<=4; n++))
do
   IENS="$(((($SLURM_ARRAY_TASK_ID - 1)* 4) + $n))"
   RUNDIR=$MAINDIR/$EXPNAME/$IENS
   echo "ENSEMBLE NR: "$IENS" in "$RUNDIR
   cd $RUNDIR
   rm -rf wrfrst_d01_* wrfout_d01_* rsl.out.0* 
   echo "mpirun -genv I_MPI_PIN_PROCESSOR_LIST="${pinning[$n-1]}" -np 12 ./wrf.exe"
   mpirun -genv I_MPI_PIN_PROCESSOR_LIST=${pinning[$n-1]} -np 12 ./wrf.exe &
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
