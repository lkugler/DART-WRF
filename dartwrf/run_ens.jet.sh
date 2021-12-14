export SLURM_STEP_GRES=none

##  $SLURM_ARRAY_TASK_ID
echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID

EXPNAME="OSSE_v1.10_test"
NAMELIST="namelist.input"

USERDIR=/jetfs/home/lkugler/
DATADIR=$USERDIR
SRC_DIR=/jetfs/home/lkugler/compile/WRF/WRF-v4.2/run/
IDEAL_EXE=/jetfs/home/lkugler/compile/bin/ideal.exe
WRF_EXE=/jetfs/home/lkugler/compile/bin/wrf-v4.2_v1.10.dmpar.exe


# VSC support: be careful with correct pinning !
pinning=(0-11 12-23 24-35 36-47)
for ((n=1; n<=4; n++))
do
    RUNDIR=$USERDIR/run_WRF/$EXPNAME/$IENS
    cd $RUNDIR
    rm -r wrfout_d01_*
    echo 'mpirun -genv I_MPI_PIN_PROCESSOR_LIST=${pinning[$n]} -np 12 ./wrf.exe >/dev/null 2>&1'
    mpirun -genv I_MPI_PIN_PROCESSOR_LIST=${pinning[$n]} -np 12 ./wrf.exe >/dev/null 2>&1
    cd ../
done
wait
