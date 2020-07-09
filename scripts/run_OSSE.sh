#!/bin/bash
#
#SBATCH -J EnsWRF
#SBATCH -N 1
#SBATCH -p mem_0384
#SBATCH --qos p71386_0384
#SBATCH --ntasks-per-node 48
#SBATCH --ntasks-per-core  1
#SBATCH --account p71386 
#SBATCH --mail-type=END    # first have to state the type of event to occur 
#SBATCH --mail-user=lukas.kugler@univie.ac.at   # and then your email address

#module purge
#module load intel-mpi/2019.6 intel/19.1.0 netcdf-fortran/4.4.5-intel-19.0.5.281-qye4cqn zlib/1.2.11-intel-19.1.0.166-hs6m2qh  hdf5/1.10.5-intel-19.0.5.281-qyzojtm netcdf/4.7.0-intel-19.0.5.281-75t52g6

##  $SLURM_ARRAY_TASK_ID
SLURM_ARRAY_TASK_ID=1 #original
echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID

EXPNAME="OSSE_v1.10_test"
NAMELIST="namelist.input"

USERDIR=/jetfs/home/lkugler/
DATADIR=$USERDIR
SRC_DIR=/jetfs/home/lkugler/compile/WRF/WRF-v4.2/run/
IDEAL_EXE=/jetfs/home/lkugler/compile/bin/ideal.exe
WRF_EXE=/jetfs/home/lkugler/compile/bin/wrf-v4.2_v1.10.dmpar.exe

# VSC support: be careful with correct pinning !
pinning=(0-11 12-23 24-35 36-47 48-59 60-71)

for ((n=1; n<=12; n++))
do
   IENS="$(((($SLURM_ARRAY_TASK_ID - 1)* 12) + $n))"
   echo "ENSEMBLE NR:"$IENS

   #INPUT_PROF=$USERDIR"/wrf_sounding/data/wrf/ens/from_uwyo/06610_2008073000_uwyo."$(printf "%.3d" $IENS)".wrfprof"
   INPUT_PROF=$USERDIR"/wrf_sounding/data/wrf/ens/LMU+shear/raso.raso."$(printf "%.3d" $IENS)".wrfprof"
   echo "using "$INPUT_PROF
   RUNDIR=$USERDIR/run_WRF/$EXPNAME/$IENS
   mkdir -p $RUNDIR
   echo 'running in '$RUNDIR
   cd $RUNDIR
   cp $SRC_DIR/* .
   cp $WRF_EXE ./wrf.exe
   cp $IDEAL_EXE ./ideal.exe

   cp ~/config_files/$NAMELIST namelist.input
   ln -sf $INPUT_PROF input_sounding
   echo './ideal.exe >/dev/null 2>&1'
   mpirun -np 1 ./ideal.exe >/dev/null 2>&1
   mv rsl.out.0000 rsl.out.input
   echo 'mpirun -genv I_MPI_PIN_PROCESSOR_LIST=${pinning[$n]} -np 12 ./wrf.exe >/dev/null 2>&1'
   mpirun -genv I_MPI_PIN_PROCESSOR_LIST=${pinning[$n]} -np 12 ./wrf.exe >/dev/null 2>&1 
   cd ../
done
wait


exit            ##################
###########

#module purge
#module load intel-mpi/2019.3 intel/19.1.0 netcdf-fortran/4.4.5-intel-19.0.5.281-qye4cqn zlib/1.2.11-intel-19.1.0.166-hs6m2qh  hdf5/1.10.5-intel-19.0.5.281-qyzojtm netcdf/4.7.0-intel-19.0.5.281-75t52g6 py-numpy/1.16.4-intel-19.0.5.281-l42jh75
rttov_python="/opt/sw/spack-0.12.1/opt/spack/linux-centos7-x86_64/intel-19.0.5.281/miniconda3-4.6.14-he6cj4ytueiygecmiasewojny57sv67s/bin/python"

for ((n=1; n<=4; n++))
do
   IENS="$(((($SLURM_ARRAY_TASK_ID - 1)* 4) + $n))"
   echo "ENSEMBLE NR:"$IENS

   IMGW="/raid61/scratch/lkugler/VSC/"$EXPNAME"/"$IENS"/"
   RUNUSER=$USERDIR/run_WRF/$EXPNAME/$IENS
   RUNDATA=$DATADIR/sim_archive/$EXPNAME/$IENS
   mkdir -p $RUNDATA

   # move to datadir
   mv $RUNUSER/* $RUNDATA/

   # copy to srvx
   cd $RUNDATA
   ssh $HOST mkdir -p $IMGW
   scp './wrfout_d01*' $HOST:$IMGW
   scp "./wrfinput_d01" $HOST:$IMGW
   scp "./rsl.out.input" $HOST:$IMGW
   scp namelist.input $HOST:$IMGW
   scp input_sounding $HOST:$IMGW
   scp $SRC_DIR/../dyn_em/module_initialize_ideal.F $HOST:$IMGW

   cd $USERDIR/RTTOV/wrapper/

   $rttov_python pyrttov_IR+VIS.py $RUNDATA"/wrfout_d01_2008-07-30_06:00:00"

   scp -r $RUNDATA/rttov_output $HOST:$IMGW/
   rm -r rttov_input/$IENS
done
wait

