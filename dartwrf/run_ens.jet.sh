module purge
module load intel-oneapi-compilers/2022.2.1-zkofgc5 hdf5/1.12.2-intel-2021.7.1-w5sw2dq netcdf-fortran/4.5.3-intel-2021.7.1-27ldrnt netcdf-c/4.7.4-intel-2021.7.1-lnfs5zz intel-oneapi-mpi/2021.7.1-intel-2021.7.1-pt3unoz
export HDF5=/jetfs/spack/opt/spack/linux-rhel8-skylake_avx512/intel-2021.7.1/hdf5-1.12.2-w5sw2dqpcq2orlmeowleamoxr65dhhdc
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
