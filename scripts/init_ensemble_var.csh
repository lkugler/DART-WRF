#!/bin/csh
#
# DART software - Copyright UCAR. This open source software is provided
# by UCAR, "as is", without charge, subject to all terms of use at
# http://www.image.ucar.edu/DAReS/DART/DART_download
#
# DART $Id$
# example call: tcsh ./init_ensemble_var.csh 2017042700 param.csh

# init_ensemble_var.csh - script that creates perturbed initial
#                         conditions from the WRF-VAR system.
#                         (perts are drawn from the perturbation bank)
#
# created Nov. 2007, Ryan Torn NCAR/MMM
# modified by G. Romine 2011-2018

set initial_date = ${1}
setenv paramfile  ${2}  # `readlink -f $BASE_DIR"/scripts/param.csh"` # Get absolute path for param.csh from command line arg
source $paramfile

echo "using ${PERTS_DIR}"
cd ${RUN_DIR}

# KRF Generate the i/o lists in rundir automatically when initializing the ensemble
set num_ens = ${NUM_ENS}
set input_file_name  = "input_list_d01.txt"
set input_file_path  = "./advance_temp"
set output_file_name = "output_list_d01.txt"

set n = 1

if ( -e $input_file_name )  rm $input_file_name
if ( -e $output_file_name ) rm $output_file_name

while ($n <= $num_ens)

   set     ensstring = `printf %04d $n`
   set  in_file_name = ${input_file_path}${n}"/wrfinput_d01"
   set out_file_name = "filter_restart_d01."$ensstring

   echo $in_file_name  >> $input_file_name
   echo $out_file_name >> $output_file_name

   @ n++
end
###


set gdate  = (`echo $initial_date 0h -g | ${DART_DIR}/models/wrf/work/advance_time`)
set gdatef = (`echo $initial_date ${ASSIM_INT_HOURS}h -g | ${DART_DIR}/models/wrf/work/advance_time`)
set wdate  =  `echo $initial_date 0h -w | ${DART_DIR}/models/wrf/work/advance_time`
set yyyy   = `echo $initial_date | cut -b1-4`
set mm     = `echo $initial_date | cut -b5-6`
set dd     = `echo $initial_date | cut -b7-8`
set hh     = `echo $initial_date | cut -b9-10`

${COPY} ${TEMPLATE_DIR}/namelist.input.meso namelist.input
${COPY} ${TEMPLATE_DIR}/input.nml.template input.nml
${REMOVE} ${RUN_DIR}/WRF
${LINK} ${OUTPUT_DIR}/${initial_date} WRF

set n = 9
#set NUM_ENS = 8  # for debug
while ( $n <= $NUM_ENS )

   echo " 1/2 prepare to ADD PERTURBATIONS FOR ENSEMBLE MEMBER $n at `date`"

   mkdir -p ${RUN_DIR}/advance_temp${n}

   # TJH why does the run_dir/*/input.nml come from the template_dir and not the rundir?
   # TJH furthermore, template_dir/input.nml.template and rundir/input.nml are identical. SIMPLIFY.

   ${LINK} ${RUN_DIR}/WRF_RUN/* ${RUN_DIR}/advance_temp${n}/.
   ${LINK} ${TEMPLATE_DIR}/input.nml.template ${RUN_DIR}/advance_temp${n}/input.nml

   ${COPY} ${OUTPUT_DIR}/${initial_date}/wrfinput_d01_${gdate[1]}_${gdate[2]}_mean \
           ${RUN_DIR}/advance_temp${n}/wrfvar_output.nc
   sleep 3
   ${COPY} ${SHELL_SCRIPTS_DIR}/add_bank_perts.ncl ${RUN_DIR}/advance_temp${n}/.

   set cmd3 = "ncl 'MEM_NUM=${n}' 'PERTS_DIR="\""${PERTS_DIR}"\""' ${RUN_DIR}/advance_temp${n}/add_bank_perts.ncl"
   ${REMOVE} ${RUN_DIR}/advance_temp${n}/nclrun3.out
          cat >!    ${RUN_DIR}/advance_temp${n}/nclrun3.out << EOF
          $cmd3
EOF
   echo $cmd3 >! ${RUN_DIR}/advance_temp${n}/nclrun3.out.tim   # TJH replace cat above
   @ n++

end

echo "      2/2  Submit advancing ensembles to scheduler  "
${COPY} ${SHELL_SCRIPTS_DIR}/rt_assim_init.sh ${RUN_DIR}/rt_assim_init.sh
sed -i 's/$NUM_ENS/'${NUM_ENS}'/g' ${RUN_DIR}/rt_assim_init.sh  # affects size of SLURM job array
source ${SHELL_SCRIPTS_DIR}/param.csh
sbatch --export=initial_date=${initial_date},RUN_DIR=${RUN_DIR},SHELL_SCRIPTS_DIR=${SHELL_SCRIPTS_DIR},paramfile=${paramfile} ${RUN_DIR}/rt_assim_init.sh

#   @ n++

# end

exit 0

# <next few lines under version control, do not edit>
# $URL$
# $Revision$
# $Date$
