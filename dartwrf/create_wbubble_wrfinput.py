import os, sys, shutil
from re import U
import datetime as dt
import numpy as np

from dartwrf.utils import Config
import netCDF4 as nc


def main(cfg):
    
    dx_km = 2  # km model resolution
    cr = 15  # km horizontal relaxation distance
    cz = 2000  # meters vertical relaxation distance
    plot = False

    if plot:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5,5))

    perturbations = True  # if 'perturb' in args else False
    print('update state in wrfinput  wrfout file to DART background file')
    print('perturb wbubble = ', perturbations)


    for iens in range(1, cfg.ensemble_size+1):
        print('iens', iens)
        wrfin = cfg.dir_wrf_run+'/'+str(iens)+'/wrfinput_d01'

        # insert wbubble
        with nc.Dataset(wrfin, 'r+') as ds:
            t = ds.variables['T'][:]
            nt, nz, ny, nx = t.shape
            z = ds.variables['PHB'][0,:,100,100]/9.81
            z = np.array(z)
            z = z - z[0]
            z = (z[1:]+z[:-1])/2
            z = z[:, np.newaxis, np.newaxis]

            if perturbations:
                cx = (70 + 60*np.random.rand())*dx_km
                cy = (70 + 60*np.random.rand())*dx_km
            else:
                cx = 100*dx_km
                cy = 100*dx_km
            print('wbubble center is', cx, cy)
            x = np.arange(0,nx)*dx_km
            y = np.arange(0,ny)*dx_km
            dx = x-cx
            dy = y-cy
            xx, yy = np.meshgrid(dx, dy)
            dr = np.sqrt(xx**2 + yy**2)[np.newaxis, :, :]

            amplitude = 3 
            if perturbations:
                amplitude += np.random.rand()*2 - 1  # Uniformly random +/- 1 K
            increment = amplitude*np.exp(-(dr/cr)**2)*np.exp(-(z/cz)**2)

            # now perturbations are centered in domain
            # to shift it in direction NW
            shift = 50
            incr2 = increment.copy()*0.
            incr2[:, :-shift, :-shift] = increment[:, shift:, shift:]  # main area
            incr2[:, -shift:, :-shift] = increment[:, :shift, shift:]  # lower part
            incr2[:, :-shift, -shift:] = increment[:, shift:, :shift]  # right part
            incr2[:, -shift:, -shift:] = increment[:, :shift, :shift]  # bottom right corner

            if plot:
                pdata = incr2[0,:,:]  # select lowest level
                pdata = pdata - pdata.min()  
                c = next(ax._get_lines.prop_cycler)['color'] # type: ignore
                ax.contour(pdata, levels=[2.,], linewidths=1, colors=[c], zorder=3)
                ax.contour(pdata, levels=[1.,], linewidths=0.5, colors=[c], zorder=3)
        
            ds.variables['T'][0,...] += incr2
            ds.variables['THM'][0,...] += incr2
        print(wrfin, 'wbubble inserted.')

    if plot:
        ax.set_aspect(1)
        ax.plot([], [], color='k', lw=1, label='+2 K perturbation')
        ax.plot([], [], color='k', lw=0.5, label='+1 K perturbation')
        ax.legend()
        
        fout = '/home/fs71386/lkugler/data/analysis/'+cfg.name+'/shiftedbubbles.png'
        os.makedirs(os.path.dirname(fout), exist_ok=True)
        fig.savefig(fout, dpi=200) 
        print(fout, 'saved.')


if __name__ == '__main__':
    cfg = Config.from_file(sys.argv[1])
    main(cfg)