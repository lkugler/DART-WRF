#!/bin/tcsh
#
##SBATCH -J assim_init
#SBATCH -N 1
#SBATCH -p mem_0384
#SBATCH --qos p71386_0384
#SBATCH --ntasks-per-node 48
#SBATCH --ntasks-per-core  1
#SBATCH --account p71386 
#SBATCH --mail-type=END    # first have to state the type of event to occur 
#SBATCH --mail-user=lukas.kugler@univie.ac.at   # and then your email address
#SBATCH --array 1-$NUM_ENS

#set SLURM_ARRAY_TASK_ID = 1
echo "SLURM_ARRAY_TASK_ID=ENS_NR:"${SLURM_ARRAY_TASK_ID}
set iens = ${SLURM_ARRAY_TASK_ID}

echo "rt_assim_init.sh is running in `pwd`"
cd ${RUN_DIR}/advance_temp${iens}
echo ${RUN_DIR}/advance_temp${iens}

if (-e wrfvar_output.nc) then
  echo "Running nclrun3.out to create wrfinput_d01 for member ${iens} at `date`"

  chmod +x nclrun3.out
  ./nclrun3.out >& add_perts.out

  if ( -z add_perts.err ) then
     echo "Perts added to member ${iens}"
  else
     echo "ERROR! Non-zero status returned from add_bank_perts.ncl. Check ${RUN_DIR}/advance_temp${iens}/add_perts.err."
     cat add_perts.err
     exit
  endif

  mv -f wrfvar_output.nc wrfinput_d01
endif

cd ${SHELL_SCRIPTS_DIR}
echo "Running first_advance.bash for member ${iens} at `date`"
${SHELL_SCRIPTS_DIR}/first_advance.csh ${initial_date} ${iens} ${paramfile}

wait
