import os, sys, shutil
import datetime as dt

from config.cfg import exp, cluster
from utils import symlink, copy_scp_srvx8, copy
import prepare_namelist

exppath = str(sys.argv[1])
# time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
# background_init_time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')

#update_vars = ['Times', 'U', 'V', 'PH', 'T', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'PSFC', 'TSK']
# vars = 'Times,U,V,T,THM,CLDFRA,P,PH,PHB,MU,QVAPOR,QCLOUD,QRAIN,QICE,QSNOW,QGRAUP,QNICE,QNRAIN,U10,V10,T2,Q2,PSFC,TSLB,SMOIS,TSK'  # ','.join(update_vars)
# vars = 'Times,LU_INDEX,ZNU,ZNW,ZS,DZS,VAR_SSO,U,V,W,PH,PHB,T,THM,MU,MUB,P,PB,FNM,FNP,RDNW,RDN,DNW,DN,CFN,CFN1,THIS_IS_AN_IDEAL_RUN,P_HYD,Q2,T2,TH2,PSFC,U10,V10,RDX,RDY,RESM,ZETATOP,CF1,CF2,CF3,QVAPOR,QCLOUD,QRAIN,QICE,QSNOW,QGRAUP,QNICE,QNRAIN,SHDMAX,SHDMIN,SNOALB,TSLB,SMOIS,SH2O,SMCREL,SEAICE,IVGTYP,ISLTYP,VEGFRA,SNOW,SNOWH,CANWAT,LAI,QKE,VAR,F,E,SINALPHA,COSALPHA,HGT,TSK,P_TOP,T00,P00,TLP,TISO,TLP_STRAT,P_STRAT,CLDFRA,CLAT,ALBBCK,TMN,XLAND,SNOWC,SR,SAVE_TOPO_FROM_REAL,C1H,C2H,C1F,C2F,C3H,C4H,C3F,C4F,PCB,PC,LANDMASK,LAKEMASK,SST'  # these are all variables, that are in wrfout and wrfinput

for iens in range(1, exp.n_ens+1):
    print('update state in wrfinput  wrfout file to DART background file')
    wrfout = exppath.replace('*iens*', str(iens))
    wrfin = cluster.wrf_rundir(iens)+'/wrfinput_d01'

    print('updating', wrfin, 'to state in', wrfout)
    assert os.path.isfile(wrfout), wrfout

    # overwrite variables in wrfinput file
    # os.system(cluster.ncks+' -A -v '+vars+' '+wrfout+' '+wrfin)
    copy(wrfout, wrfin) 
