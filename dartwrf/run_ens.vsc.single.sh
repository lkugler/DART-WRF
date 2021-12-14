
module purge
module load intel-mpi/2019.6 intel/19.1.0 netcdf-fortran/4.4.5-intel-19.0.5.281-qye4cqn zlib/1.2.11-intel-19.1.0.166-hs6m2qh  hdf5/1.10.5-intel-19.0.5.281-qyzojtm netcdf/4.7.0-intel-19.0.5.281-75t52g6

##  $SLURM_ARRAY_TASK_ID
echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID
EXPNAME=<exp.expname> 

MAINDIR=<cluster.wrf_rundir_base> 
IENS=$SLURM_ARRAY_TASK_ID
RUNDIR=$MAINDIR/$EXPNAME/$IENS
echo "ENSEMBLE NR: "$IENS" in "$RUNDIR
cd $RUNDIR
rm -rf rsl.out.0* 
mpirun -genv I_MPI_PIN_PROCESSOR_LIST=0-19 -np 20 ./wrf.exe
