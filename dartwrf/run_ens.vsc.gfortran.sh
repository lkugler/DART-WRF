
module purge
#module load intel-mpi/2019.6 intel/19.1.0 netcdf-fortran/4.4.5-intel-19.0.5.281-qye4cqn zlib/1.2.11-intel-19.1.0.166-hs6m2qh  hdf5/1.10.5-intel-19.0.5.281-qyzojtm netcdf/4.7.0-intel-19.0.5.281-75t52g6
module load gcc/12.2.0-gcc-8.5.0-aal4zp2 openmpi/4.1.4-gcc-12.2.0-khtxitv
export SLURM_STEP_GRES=none

##  $SLURM_ARRAY_TASK_ID
echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID
EXPNAME=<exp.expname> 

MAINDIR=<cluster.wrf_rundir_base> 
#pinning=(0-11 12-23 24-35 36-47)
pinning=(0,1,2,3,4,5,6,7,8,9,10,11 12,13,14,15,16,17,18,19,20,21,22,23 24,25,26,27,28,29,30,31,32,33,34,35 36,37,38,39,40,41,42,43,44,45,46,47)

for ((n=1; n<=4; n++))
do
   IENS="$(((($SLURM_ARRAY_TASK_ID - 1)* 4) + $n))"
   RUNDIR=$MAINDIR/$EXPNAME/$IENS
   echo "ENSEMBLE NR: "$IENS" in "$RUNDIR
   cd $RUNDIR
   rm -rf rsl.out.0* 
   echo "mpirun -np 12  --cpu-set ${pinning[$n-1]} /home/fs71386/lkugler/run_container.sh python.gcc9.5.0.vsc4.sif ./wrf.exe"
   mpirun -np 12  --cpu-set ${pinning[$n-1]} /home/fs71386/lkugler/run_container.sh python.gcc9.5.0.vsc4.sif ./wrf.exe &
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
