<wrf_modules>
export SLURM_STEP_GRES=none

echo "SLURM_ARRAY_TASK_ID:"$SLURM_ARRAY_TASK_ID
EXPNAME=<expname> 
MAINDIR=<wrf_rundir_base> 

IENS=$SLURM_ARRAY_TASK_ID
RUNDIR=$MAINDIR/$EXPNAME/$IENS
echo "ENSEMBLE NR: "$IENS" in "$RUNDIR

cd $RUNDIR
rm -rf rsl.out.0*
mpirun -np 1 ./ideal.exe

# move log file to sim_archive
touch -a $RUNDIR/rsl.out.0000  # create log file if it doesnt exist, to avoid error in mv if it doesnt exist
mv $RUNDIR/rsl.out.0000 $RUNDIR/rsl.out.input

