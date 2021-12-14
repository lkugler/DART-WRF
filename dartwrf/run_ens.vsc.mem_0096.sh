
module purge
module load intel-mpi/2019.6 intel/19.1.0 netcdf-fortran/4.4.5-intel-19.0.5.281-qye4cqn zlib/1.2.11-intel-19.1.0.166-hs6m2qh  hdf5/1.10.5-intel-19.0.5.281-qyzojtm netcdf/4.7.0-intel-19.0.5.281-75t52g6
export I_MPI_DEBUG=4
export OMP_NUM_THREADS=1
mem_per_task=10G
cpu_per_task=12

echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID
EXPNAME=<exp.expname> 

MAINDIR=<cluster.wrf_rundir_base> 
pinning=(0-11 12-23 24-35 36-47)

mytasks=4
for i in `seq 1 $mytasks`
do
   IENS="$(((($SLURM_ARRAY_TASK_ID - 1)* 4) + $n))"  # ensemble number (5,6,7,8 for job array element 2)
   RUNDIR=$MAINDIR/$EXPNAME/$IENS
   echo "ENSEMBLE NR: "$IENS" in "$RUNDIR
   cd $RUNDIR
   rm -rf rsl.out.0* 
   echo "srun --mem=$mem_per_task --cpus-per-task=$cpu_per_task --cpu_bind=map_cpu:${pinning[$n-1]} --ntasks=1 ./wrf.exe &"
   srun --mem=$mem_per_task --cpus-per-task=$cpu_per_task --cpu_bind=map_cpu:${pinning[$n-1]} --ntasks=1 ./wrf.exe &
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
