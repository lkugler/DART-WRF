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
vis = dict(plotname='VIS 0.6µm',  plotunits='[1]',
        kind='MSG_4_SEVIRI_BDRF', sat_channel=1, n_obs=n_obs, 
        error_generate=0, error_assimilate=0.05,
        cov_loc_radius_km=20)
wv73 = dict(plotname='Brightness temperature WV 7.3µm',  plotunits='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=6, n_obs=n_obs, 
            error_generate=0, error_assimilate=False, 
            cov_loc_radius_km=20)

def test_rttov():

    times = pd.date_range(start=dt.datetime(2008, 7, 30, 13,30),
                              end=dt.datetime(2008, 7, 30, 15,30),
                              freq=dt.timedelta(minutes=15))

    case = 'exp_v1.18_P1_nature'
    # case = 'exp_v1.19_P3_wbub7_nat'
    for obsvar in ['VIS06']: #'WV73',

        for time in times:

            fname = '/home/fs71386/lkugler/data/analysis/'+case+'/dart-rttov-compare_'+obsvar+time.strftime('_%H:%M')+'-2.png'

            # if os.path.isfile(fname):
            #     print(fname, 'skipping...')
            #     continue

            ds = xr.open_dataset('/home/fs71386/lkugler/data/sim_archive/'+case+'/2008-07-30_06:00/1/'+time.strftime('RT2_wrfout_d01_2008-07-30_%H:%M:00.nc'))
            # 
            da = ds[obsvar].squeeze()


            shutil.copy('/home/fs71386/lkugler/data/sim_archive/'+case+'/2008-07-30_06:00/1/'+time.strftime('wrfout_d01_2008-07-30_%H:%M:00'), 
                        cluster.dartrundir + "/wrfout_d01")

            wrfout_add_geo.run(
                cluster.dartrundir + "/../geo_em.d01.nc", cluster.dartrundir + "/wrfout_d01"
            )
           

            error_generate = np.zeros(n_obs)
            if obsvar == 'VIS06':
                osq.create_obsseqin_alltypes(time, [vis])
            else:
                osq.create_obsseqin_alltypes(time, [wv73])
            aso.set_DART_nml()
            aso.run_perfect_model_obs() 


            obs = obsseq.ObsSeq(cluster.dartrundir+'/obs_seq.out')
            obs_map = obs.df.truth.values.reshape(150,150)


            fig, ax = plt.subplots(ncols=2)

            if obsvar == 'VIS06':
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

            # norm = mpl.colors.Normalize(vmin=0, vmax=1)
            # levels = plt.arange(0, 1, .05)
            # norm = mpl.colors.Normalize(vmin=210, vmax=260)
            # levels = plt.arange(200, 260, 5)

            diff =  da.values[25:175,25:175] - obs_map

            ax[0].pcolormesh(diff, norm=norm, levels=levels)
            ax[0].set_title('pyRTTOV - DART-RTTOV')
            fig.colorbar(m1, loc='r')
            fig.suptitle(time.strftime('%H:%M'))
            
            fname = '/home/fs71386/lkugler/data/analysis/'+case+'/dart-rttov-compare_'+obsvar+time.strftime('_%H:%M')+'-diff.png'
            fig.savefig(fname)
            print(fname)

            #from IPython import embed; embed()

            
            # shutil.copy(cluster.dartrundir+'/obs_seq.out', 
            #     '/home/fs71386/lkugler/data/analysis/'+case+time.strftime('/obs_seq_'+obsvar+'_%H:%M.out'))


            # fig, ax = plt.subplots()
            # m = ax.pcolormesh(obs_map)
            # ax.colorbar(m, loc='r')
            # ax.set_title(time.strftime('%H:%M'))
            # fname = '/home/fs71386/lkugler/data/analysis/exp_v1.18_P1_nature/dart-rttov-output_'+time.strftime('%H:%M')+'.png'
            # fig.savefig(fname)
            # print(fname)


if __name__ == '__main__':
    test_rttov()
    pass
    # case = 'test_IR+VIS'
    # time = dt.datetime(2008,7,30,13,30)



    # error_generate = np.zeros(n_obs)
    # osq.create_obsseqin_alltypes(time, [vis])
    # aso.set_DART_nml()
    # aso.run_perfect_model_obs() 


    # obs = obsseq.ObsSeq(cluster.dartrundir+'/obs_seq.out')
    # obs_map = obs.df.truth.values.reshape(150,150)


    # ds = xr.open_dataset('/home/fs71386/lkugler/data/run_DART/test_IR+VIS/RT_wrfout_d01_cloudy.nc')
    # da = ds['VIS06'].squeeze()
    # pyrttov = da.values[25:175,25:175]

    # diff = pyrttov - obs_map

    # i, j = np.unravel_index(diff.argmax(), (150,150))
    # print(i,j)

    # print(pyrttov[i,j], obs_map[i,j])

    # from IPython import embed; embed()
