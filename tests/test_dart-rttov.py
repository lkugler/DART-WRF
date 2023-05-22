import os, filecmp, shutil
import numpy as np
import datetime as dt
import pandas as pd

from config.cfg import exp, cluster
from dartwrf import obsseq
import dartwrf.create_obsseq as osq
import dartwrf.assim_synth_obs as aso
from dartwrf import wrfout_add_geo

import matplotlib as mpl
import proplot as plt
import xarray as xr

n_obs = 22500
vis = dict(plotname='VIS06',  plotunits='[1]',
        kind='MSG_4_SEVIRI_BDRF', sat_channel=1, n_obs=n_obs, 
        error_generate=0, error_assimilate=0.12,
        cov_loc_radius_km=20)
wv62 = dict(plotname='WV62',  plotunits='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=5, n_obs=n_obs, 
            error_generate=0, error_assimilate=False, 
            cov_loc_radius_km=20)
wv73 = dict(plotname='WV73',  plotunits='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=6, n_obs=n_obs, 
            error_generate=0, error_assimilate=False, 
            cov_loc_radius_km=20)

vsc = True if 'jet' not in os.uname().nodename else False
if vsc:
    datadir = '/gpfs/data/fs71386/lkugler/sim_archive/'
    img_dir = '/gpfs/data/fs71386/lkugler/analysis/'
else:
    datadir = '/jetfs/home/lkugler/data/sim_archive/'
    img_dir = '/jetfs/home/lkugler/analysis_plots/'

dart_rundir = datadir+'/../run_DART/test_jet'

def test_rttov():

    times = pd.date_range(start=dt.datetime(2008, 7, 30, 13,30),
                              end=dt.datetime(2008, 7, 30, 14,30),
                              freq=dt.timedelta(minutes=30))

    case = 'exp_v1.19_P3_wbub7_nat'


    for obscfg in [wv73, vis, wv62]:

        for time in times:

            fname = img_dir+'/'+case+'/dart-rttov-compare_'+obscfg['plotname']+time.strftime('_%H:%M')+'.png'

            ds = xr.open_dataset(datadir+'/'+case+'/2008-07-30_12:00/1/'+time.strftime('RT_wrfout_d01_2008-07-30_%H:%M:00.nc'))
            if obscfg['plotname'] not in ds.data_vars:
                raise KeyError(obscfg['plotname']+' not in dataset')
            da = ds[obscfg['plotname']].squeeze()


            shutil.copy(datadir+'/'+case+'/2008-07-30_12:00/1/'+time.strftime('wrfout_d01_2008-07-30_%H:%M:00'), 
                        dart_rundir + "/wrfout_d01")

            wrfout_add_geo.run(datadir+ "/geo_em.d01.nc", dart_rundir + "/wrfout_d01")
           

            osq.create_obsseqin_alltypes(time, [obscfg])
            aso.set_DART_nml()
            aso.run_perfect_model_obs(nproc=1) 


            obs = obsseq.ObsSeq(dart_rundir+'/obs_seq.out')
            obs_map = obs.df.truth.values.reshape(150,150)


            fig, ax = plt.subplots(ncols=2)

            if obscfg['plotname'] == 'VIS06':
                norm = mpl.colors.Normalize(vmin=0, vmax=1)
                levels = plt.arange(0, 1, .05)
            else:
                norm = mpl.colors.Normalize(vmin=210, vmax=260)
                levels = plt.arange(200, 260, 5)

            ax[0].pcolormesh(obs_map, norm=norm, levels=levels)
            ax[0].set_title('DART-RTTOV')
            m1 = ax[1].pcolormesh(da.values[24:175,24:175], norm=norm, levels=levels) 
            ax[1].set_title('py-RTTOV')
            fig.colorbar(m1, loc='r')
            fig.suptitle(time.strftime('%H:%M'))
            
            fig.savefig(fname)
            print(fname)



            fig, ax = plt.subplots()
            diff =  da.values[25:175,25:175] - obs_map

            ax[0].pcolormesh(diff, cmap='RdBu_r')
            ax[0].set_title('pyRTTOV - DART-RTTOV')
            fig.colorbar(m1, loc='r')
            fig.suptitle(time.strftime('%H:%M'))
            
            fname = img_dir+'/'+case+'/dart-rttov-compare_'+obscfg['plotname']+time.strftime('_%H:%M')+'-diff.png'
            fig.savefig(fname)
            print(fname)




if __name__ == '__main__':
    test_rttov()
    pass
