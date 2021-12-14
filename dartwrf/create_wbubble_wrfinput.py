import os, sys, shutil
import datetime as dt
import numpy as np

from config.cfg import exp, cluster
import netCDF4 as nc

dx_km = 2
cr = 15  # km horizontal relaxation distance
cz = 2000  # meters vertical relaxation distance

perturbations = False
if len(sys.argv) > 1:
    if 'perturb' == sys.argv[1]:
        perturbations = True
print('perturb wbubble = ', perturbations)

for iens in range(1, exp.n_ens+1):
    print('update state in wrfinput  wrfout file to DART background file')

    wrfin = cluster.wrf_rundir(iens)+'/wrfinput_d01'

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
            cx = (85 + 30*np.random.rand())*dx_km
            cy = (85 + 30*np.random.rand())*dx_km
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

        pert = 4*np.exp(-(dr/cr)**2)*np.exp(-(z/cz)**2)

        ds.variables['T'][0,...] += pert
        ds.variables['THM'][0,...] += pert

    print(wrfin, 'wbubble inserted.')
