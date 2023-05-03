"""Read, modify and save DART obs_seq files.

Not usable for creating obs_seq, since it does not know which metadata is necessary for each type
"""

import os, sys, shutil, warnings
import numpy as np
import pandas as pd

def plot_box(m, lat, lon, label="", **kwargs):
    """"Draw bounding box

    Args:
        m (mpl_toolkits.basemap.Basemap)
        lat, lon (np.array)     2-dimensional arrays of longitudes, latitudes
    """

    m.drawgreatcircle(
        lon[0, -1], lat[0, -1], lon[0, 0], lat[0, 0], del_s=20, zorder=4, **kwargs
    )
    m.drawgreatcircle(
        lon[0, -1], lat[0, -1], lon[-1, -1], lat[-1, -1], del_s=20, zorder=4, **kwargs
    )
    m.drawgreatcircle(
        lon[-1, 0], lat[-1, 0], lon[-1, -1], lat[-1, -1], del_s=20, zorder=4, **kwargs
    )
    m.drawgreatcircle(
        lon[0, 0],
        lat[0, 0],
        lon[-1, 0],
        lat[-1, 0],
        del_s=20,
        zorder=4,
        label=label,
        **kwargs
    )


def degrees_to_rad(degr):
    """Convert to DART convention = radians"""
    if degr < 0:
        degr += 360
    return degr / 360 * 2 * np.pi


def rad_to_degrees(rad):
    """Convert to degrees from DART convention (radians)"""
    assert rad >= 0, "no negative radians allowed"
    degr = rad / np.pi * 180

    # convert degr (180,360) to (-180,0)
    if degr > 180:
        degr -= 360
    return degr




class ObsRecord(pd.DataFrame):
    """Content of obsseq.ObsSeq instances
    provides additional methods for pd.DataFrame
    created inside an ObsSeq instance
    """
    @property
    def _constructor(self):
        # This ensures that pandas operations return ObsRecord instances
        # e.g. subsetting df with df[3:4] returns ObsRecord
        return ObsRecord

    def get_prior_Hx(self):
        """Return prior Hx array (n_obs, n_ens)"""
        return self._get_model_Hx('prior')

    def get_posterior_Hx(self):
        """Return posterior Hx array (n_obs, n_ens)"""
        return self._get_model_Hx('posterior')

    def get_truth_Hx(self):
        return self['truth'].values

    def _get_model_Hx(self, what):
        """Return ensemble member info

        Args:
            self (pd.DataFrame):      usually self.self
            what (str):             'prior' or 'posterior'

        Returns:
            np.array

        Works with all observations (self = self.self) 
        or a subset of observations (self = self.self[343:348])
        """
        if what not in  ['prior', 'posterior']:
            raise ValueError(what, 'must be prior or posterior')

        # which columns do we need?
        keys = self.columns
        keys_bool = np.array([what+' ensemble member' in a for a in keys])

        # select columns in DataFrame
        Hx = self.iloc[:, keys_bool]

        # consistency check: compute mean over ens - compare with value from file
        assert np.allclose(Hx.mean(axis=1), self[what+' ensemble mean'])
        return Hx.values

    def get_lon_lat(self):
        lats = np.empty(len(self), np.float32)
        lons = lats.copy()

        for i, (i_obs, values) in enumerate(self.loc3d.items()):
            x, y, z, z_coord = values

            # convert radian to degrees lon/lat
            lon = rad_to_degrees(x)
            lat = rad_to_degrees(y)
            lons[i] = lon
            lats[i] = lat

        return pd.DataFrame(index=self.index, data=dict(lat=lats, lon=lons))

    def get_from_cartesian_grid(self, i, j, k):
        """Get the observation using cartesian grid indices (ix, iy, iz)
        """
        # find indices of observations within pandas.DataFrame
        return self.iloc[self.i_obs_grid[i, j, k].ravel()]

    def determine_nlayers(self):
        nlayers = 1  # first guess
        from config.cfg import exp

        if len(exp.observations) == 1:
            # obscfg = exp.observations[0]
            # if 'heights' in obscfg:
            #     nlayers = len(obscfg['heights'])

            heights = [loc_xyz[2] for loc_xyz in self['loc3d']]
            heights = sorted(heights)
            h0 = heights[0]
            for i, h in enumerate(heights):
                if h != h0:
                    break
            obs_per_layer = i  # if it fails at 1, there is 1 obs per layer

            nlayers = int(len(self)/obs_per_layer)
        else:
            warnings.warn('I can only guess the number of layers from this file.')
        return nlayers

    def superob(self, window_km):
        """Select subset, average, overwrite existing obs with average

        TODO: allow different obs types (KIND)
        TODO: loc3d overwrite with mean
        Metadata is copied from the first obs in a superob-box

        Note:
            This routine discards observations (round off)
            e.g. 31 obs with 5 obs-window => obs #31 is not processed

        Args:
            window_km (numeric):        horizontal window edge length
                                        includes obs on edge
                                        25x25 km with 5 km obs density
                                        = average 5 x 5 observations
        """
        def calc_deg_from_km(distance_km, center_lat):
            """Approximately calculate distance in degrees from meters
            Input: distance in km; degree latitude
            Output: distance in degrees of latitude, longitude
            """
            assert distance_km > 0, "window size <= 0, must be > 0"
            dist_deg_lat = distance_km / km_per_degrees
            dist_deg_lon = dist_deg_lat * np.cos(center_lat * np.pi / 180)
            return dist_deg_lat, dist_deg_lon

        def calc_km_from_deg(deg_lat, deg_lon, center_lat):
            dist_km_lat = deg_lat * km_per_degrees
            dist_km_lon = deg_lon * km_per_degrees * np.cos(center_lat * np.pi / 180)
            return dist_km_lat, dist_km_lon


        debug = False
        radius_earth_meters = 6.371 * 1e6
        m_per_degrees = np.pi * radius_earth_meters / 180  # m per degree latitude
        km_per_degrees = m_per_degrees / 1000

        # determine obs density (approx)
        # TODO: error prone section
        # from IPython import embed; embed()
        coords = self.get_lon_lat()
        dx_obs_lat_deg = coords.lat.diff().max()
        km_lat, _ = calc_km_from_deg(dx_obs_lat_deg, np.nan, 45)
        obs_spacing_km = int(km_lat)

        # how many observations in x/y direction in one superob box
        # in total there are win_obs**2 many observations inside
        win_obs = int(window_km / obs_spacing_km)
        if debug:
            print('window_km=', window_km)
            print('obs spacing=', obs_spacing_km)
            print("window (#obs in x/y)=", win_obs)

        # superob in case of multiple layers, only implemented for single obstype
        nlayers = self.determine_nlayers()
        
        # indices of observations (starting from 0)
        i_obs_grid = self.index.values  

        # get the observation indices from obs_seq (list)
        # onto a cartesian grid (ix, iy, iz)
        gridpoints_per_layer = len(i_obs_grid)/nlayers
        nx = int(gridpoints_per_layer ** 0.5)
        self.nx = nx
        i_obs_grid = i_obs_grid.reshape(nx, nx, nlayers)
        self.i_obs_grid = i_obs_grid

        # loop through columns/rows
        # avoid loop in (lat,lon) space as coordinates are non-cartesian
        # i.e. first column of observations has different longitudes!

        out = self.drop(self.index)  # this df will be filled
        boxes = []

        for i in range(0, nx+1 - win_obs, win_obs):
            for j in range(0, nx+1 - win_obs, win_obs):
                for k in range(0, nlayers):
                    if debug: print(i,j,k)

                    # find indices of observations within superob window
                    # i_obs_box = i_obs_grid[i : i + win_obs, j : j + win_obs, k].ravel()

                    if debug:
                        print("index x from", i, 'to', i + win_obs)
                        print("index y from", j, 'to', j + win_obs)
                        print("obs indices box=", i_obs_grid[i : i + win_obs, j : j + win_obs, k])

                    # find observations within superob window
                    obs_box = self.get_from_cartesian_grid(slice(i, i + win_obs),
                                                           slice(j, j + win_obs),
                                                           k)

                    
                    # save boundary of box to list, for plotting later
                    eps = dx_obs_lat_deg/2  # for plotting
                    eps2 = eps*0.8  # for plotting
                    lat1, lon1 = self.get_from_cartesian_grid(i, j, k).get_lon_lat().values[0]
                    lat2, lon2 = self.get_from_cartesian_grid(i+win_obs-1, j, k).get_lon_lat().values[0]
                    lat3, lon3 = self.get_from_cartesian_grid(i, j+win_obs-1, k).get_lon_lat().values[0]
                    lat4, lon4 = self.get_from_cartesian_grid(i+win_obs-1, j+win_obs-1, k).get_lon_lat().values[0]

                    boxes.append(([lat1-eps2, lat2+eps2, lat3-eps2, lat4+eps2],
                                [lon1-eps, lon2-eps, lon3+eps, lon4+eps]))

                    # average the subset
                    # metadata are assumed to be equal
                    obs_mean = obs_box.iloc[0]

                    # average spread and other values
                    for key in obs_box:
                        if key in ['loc3d', 'kind', 'metadata', 'time']:
                            pass
                        elif 'spread' in key:
                            # stdev of mean of values = sqrt(mean of variances)
                            obs_mean.at[key] = np.sqrt((obs_box[key]**2).mean())
                        elif key == 'variance':
                            # variance of mean = sum(variances)/n^2
                            obs_mean.at[key] = obs_box[key].sum()/obs_box[key].size**2
                        else:
                            obs_mean.at[key] = obs_box[key].mean()

                    # define location of superobservation
                    if win_obs % 2 == 0:
                        # even number of observations in x-direction
                        # there is no center obs
                        raise NotImplementedError()
                    else:
                        # odd number of observations in x-direction
                        # -> there is an observation in the middle
                        # take the location of that obs
                        # int(win_obs/2) is the index of the center element when indices start at 0
                        i_obs_center = i_obs_grid[i + int(win_obs/2), j + int(win_obs/2), k]
                        obs_mean.at['loc3d'] = self.iloc[i_obs_center]['loc3d']

                    # check if all obs share the same vertical position
                    heights_in_box = np.array([a[2] for a in obs_box['loc3d']])
                    assert np.allclose(heights_in_box, obs_mean['loc3d'][2])

                    if debug:
                        print("pre_avg:", obs_box.head())
                        print("avg:", obs_mean)

                    out = out.append(obs_mean)

        n_pre_superob = len(self)
        n_post_superob = len(out)
        out.attrs['boxes'] = boxes

        # quick after check - does the output obs number match with the expected number?
        n_windows_x = int((n_pre_superob/nlayers)**.5/win_obs)  # assume square of obs
        n_target_post = n_windows_x**2 * nlayers  # number of windows
        print('superob from', n_pre_superob, 'obs to', n_post_superob, 'obs')
        if n_post_superob != n_target_post:
            raise RuntimeError('expected', n_target_post, 'superobservations, but created', 
                                n_post_superob)

        out.attrs['df_pre_superob'] = self  # original data
        self = out  # overwrite dataframe
        return self  # output itself (allows to write it to a new name)


class ObsSeq(object):
    """Read, manipulate, save obs_seq.out / final files
    """

    def __init__(self, filepath):
        self.ascii = open(filepath, "r").readlines()

        self.get_preamble_content()
        self.read_preamble()

        self.df = ObsRecord(self.to_pandas())

    def __str__(self):
        return self.df.__str__()

    def get_preamble_content(self):
        """Split the obs_seq.out file into two parts
        1) First lines of obs_seq.out file until the first observation message
        2) Observation contents
        """
        for i, line in enumerate(self.ascii):
            if "OBS " in line:
                break
        if i == len(self.ascii)-1:
            raise RuntimeError('did not find `OBS ` in file!')

        self.preamble = self.ascii[:i]
        self.content = self.ascii[i:]

    def read_preamble(self):
        """Defines 
        self.obstypes (tuple(kind_nr, kind_descriptor)) for each obs type
        """
        # how many obstypes
        for i, line in enumerate(self.preamble):
            if "obs_type_definitions" in line or "obs_kind_definitions" in line:
                break

        # check if we found definitions before end of file
        if i == len(self.preamble)-1:  # end of file
            raise RuntimeError('did not find `obs_type_definitions` or `obs_kind_definitions` in file')

        line_n_obstypes = i + 1
        n_obstypes = int(self.preamble[line_n_obstypes])  # read integer from file

        # read obs type kind (number and description)
        obstypes = []
        for k in range(1, n_obstypes + 1):
            kind_nr, kind_type = self.preamble[line_n_obstypes + k].split()
            kind_nr = int(kind_nr)
            obstypes.append((kind_nr, kind_type))
        self.obstypes = obstypes

        # read num_copies (2 for obs_seq.out, 44 for obs_seq.final with 40 ens members)
        num_copies = False
        for line in self.preamble:
            if 'num_copies:' in line:
                _, num_copies, _, num_qc = line.split()
                break
        if not num_copies:
            raise RuntimeError('did not find `num_copies:` in '+str(self.preamble))
        num_copies = int(num_copies)
        num_qc = int(num_qc)

        # read num_obs
        num_obs = False
        for i, line in enumerate(self.preamble):
            if 'num_obs:' in line:
                _, num_obs, _, max_num_obs = line.split()
                break
        if not num_obs:
            raise RuntimeError('did not find `num_obs:` in '+str(self.preamble))
        assert num_obs == max_num_obs, NotImplementedError()
        self.num_obs = int(num_obs)

        # read keys for values (e.g. 'observations', 'truth', 'prior ensemble mean',)
        keys = []
        line_start_keys = i+1
        for j in range(line_start_keys, line_start_keys+num_copies+num_qc):
            line = self.preamble[j]
            keys.append(line.strip())

        self.keys_for_values = keys

    def obs_to_dict(self):
        """Convert an obs_seq.out file to a dictionary"""
        obs_begin_str = "OBS  "

        def check_obs_begin(line):
            if not obs_begin_str in line:
                raise RuntimeError("This is not the first line: "+str(line))

        def content_to_list(content):
            """Split obs_seq.out content (lines of str) into list of observation-sections

            Args:
                content (list of str) : contains lines of file
            
            Returns 
                list of list of str
            """
            obs_list = []
            i = 0
            try:
                check_obs_begin(content[0])
            except:
                print(content)
                raise
            obs_begin = 0

            for i, line in enumerate(content):
                if i == 0:
                    continue

                if obs_begin_str in line:  # then this line is beginning of obs
                    obs_end = i - 1  # previous line
                    obs_list.append(content[obs_begin : obs_end + 1])
                    obs_begin = i  # next obs starts here

                if i == len(content) - 1:  # last line
                    obs_end = i
                    obs_list.append(content[obs_begin : obs_end + 1])

            if not len(obs_list) > 1:
                warnings.warn('len(obs_list)='+str(len(obs_list)))

            # consistency check to ensure that all observations have been detected
            if len(obs_list) != self.num_obs:
                raise RuntimeError('num_obs read in does not match preamble num_obs '
                                   +str(len(obs_list))+' != '+str(self.num_obs))
            return obs_list

        def one_obs_to_dict(obs_list_entry):
            """"""
            out = dict()
            lines = obs_list_entry

            try:
                check_obs_begin(lines[0])
            except:
                print(lines)
                raise

            for i, line in enumerate(lines):
                if "loc3d" in line:  # find location
                    line_loc = i + 1

                if "kind" in line:  # find obs kind
                    line_kind = i + 1

            for k, key in enumerate(self.keys_for_values):
                out[key] = float(lines[1+k].strip())

            x, y, z, z_coord = lines[line_loc].split()
            out["loc3d"] = float(x), float(y), float(z), int(z_coord)
            out["kind"] = int(lines[line_kind].strip())
            out["metadata"] = lines[line_kind + 1 : -2]
            out["time"] = tuple(lines[-2].split())
            out["variance"] = float(lines[-1].strip())
            return out

        def obs_list_to_dict(obs_list):
            # wraps `one_obs_to_dict`
            obs_list_dict = []  # list of dict
            for entry in obs_list:

                # convert list of lines to dictionary
                # with (kind, loc3d, values, ...) as keys
                obs_dict = one_obs_to_dict(entry)

                obs_list_dict.append(obs_dict)  # append dict to list
            return obs_list_dict

        # content = [line1, ...]
        # obs_list = [obs1, obs2, obs3, ...]
        # where obs1 = [line1, line2, ...]; all lines pertaining to one obs
        obs_list = content_to_list(self.content)

        # each obs is one dictionary
        list_of_obsdict = obs_list_to_dict(obs_list)
        return list_of_obsdict

    def to_pandas(self):
        """Create pd.DataFrame with rows=observations
        """
        obs_dict_list = self.obs_to_dict()

        # convert to pandas.DataFrame
        # each observation is one line
        # columns: all observation contents

        # set keys from first obs (kind, loc3d, values)
        keys = obs_dict_list[0].keys()
        data = {key: [] for key in keys}

        # fill the data lists for each column of the DataFrame
        for obs in obs_dict_list:
            for key in keys:
                data[key].append(obs[key])

        return pd.DataFrame(index=range(len(obs_dict_list)), data=data)

    def to_dart(self, f):
        """Write to obs_seq.out file in DART format

        Args:
            f (str):    path of file to write
        """

        def write_file(msg, output_path="./"):
            try:
                os.remove(output_path)
            except OSError:
                pass

            with open(output_path, "w") as f:
                f.write(msg)
                print(output_path, "saved.")

        def write_preamble(n_obs):

            num_obstypes = str(len(self.obstypes))
            txt = " obs_sequence \n obs_kind_definitions \n     " + num_obstypes

            for (nr, obstype) in self.obstypes:
                txt += "\n         " + str(nr) + " " + obstype
            nobs = str(n_obs)
            txt += "\n num_copies:            2  num_qc:            1"
            txt += "\n num_obs:           " + nobs
            txt += "   max_num_obs:            " + nobs
            txt += "\n observations \n truth \n Quality Control \n"
            txt += " first:            1  last:            " + nobs
            return txt

        def write_obs(i, obs, next_i_obs=None, prev_i_obs=None):
            """Write the observation section of a obs_seq.out file

            Args:
                i   (int):      index of observation
                obs (dict):     observation data

                next_i_obs (int):   index of next observation
                prev_i_obs (int):   index of previous observation
                                    (in case it is the last)

            Returns
                str
            """

            if next_i_obs:
                line_link = "        -1           " + str(next_i_obs) + "          -1"
            else:  # last observation in file
                line_link = "          " + str(prev_i_obs) + "           -1          -1"

            lon_rad = str(obs["loc3d"][0])
            lat_rad = str(obs["loc3d"][1])

            out = (
                " \n".join(
                    [
                        "\nOBS         " + str(i),
                        str(obs["observations"]),
                        str(obs["truth"]),
                        str(obs["Quality Control"]),
                        line_link,
                        "obdef",
                        "loc3d", "    ".join(
                            [
                                lon_rad, lat_rad,
                                str(obs["loc3d"][2]), 
                                str(obs["loc3d"][3]),
                            ]
                        ),
                        "kind", "         " + str(int(obs["kind"])),
                        "".join(obs["metadata"]),
                    ]
                )
                + " \n " + obs["time"][0] + "     " + obs["time"][1]
                + " \n " + str(obs["variance"])
            )
            return out

        n_obs = len(self.df)
        outstr = write_preamble(n_obs)

        # loop through observations, concatenate obs sections
        # DART format is linked list, needs index of next observation
        # k     ...         0, ..., len(df)-1
        # i_obs_this ...    starts at 1
        for k, (_, obs) in enumerate(self.df.iterrows()):
            i_obs_this = k + 1

            if k < len(self.df) - 1:
                i_obs_next = k + 2
                outstr += write_obs(i_obs_this, obs, next_i_obs=i_obs_next)
            else:  # last obs in file
                i_obs_prev = k
                outstr += write_obs(i_obs_this, obs, prev_i_obs=i_obs_prev)

        write_file(outstr, output_path=f)


    def plot(self, f_out="./map_obs_superobs.png"):
        print('plotting obs...')
        import matplotlib as mpl

        mpl.use("agg")
        import matplotlib.pyplot as plt
        import xarray as xr

        georef = xr.open_dataset("/gpfs/data/fs71386/lkugler/run_DART/geo_em.d01.nc")
        lon = georef.XLONG_M.values.squeeze()
        lat = georef.XLAT_M.values.squeeze()

        from mpl_toolkits.basemap import Basemap

        fig, ax = plt.subplots(figsize=(12, 12))

        # m = Basemap(projection='geos', lon_0=lon[100,100], resolution='i',
        #             llcrnrlon=lon[0,0]-1,llcrnrlat=lat[0,0]-3,
        #             urcrnrlon=lon[-1,-1]+1,urcrnrlat=lat[-1,-1]+3)
        m = Basemap(
            projection="lcc",
            resolution="h",
            lon_0=lon[100, 100],
            lat_0=lat[25, 25],
            lat_1=lat[100, 100],
            lat_2=lat[175, 175],
            llcrnrlon=lon[0, 0] - 2,
            llcrnrlat=lat[0, 0] - 2,
            urcrnrlon=lon[-1, -1] + 2,
            urcrnrlat=lat[-1, -1] + 2,
        )
        # m.fillcontinents(color='0.1', lake_color='0.2')

        m.drawlsmask(land_color="0.1", ocean_color="0.1")
        m.drawcoastlines(color="white")
        m.drawcountries(color="white")

        plot_box(m, lat, lon, label="domain", color="green", lw=1) #4)

        # OBSERVATIONS
        original_df = self.df.attrs['df_pre_superob']
        coords = original_df.get_lon_lat()
        lats = coords.lat.values
        longs = coords.lon.values
        coords = zip(lats, longs)

        label="observed pixel"
        for lati, long in coords:
            m.plot(long, lati, ".",
                markersize=0.4, #4,
                latlon=True,
                color="grey",
                label=label,
                zorder=4,
            )
            label=''

        # after superob
        coords = self.df.get_lon_lat()
        lats = coords.lat.values
        longs = coords.lon.values
        coords = zip(lats, longs)

        label = 'superobservation'
        for lati, long in coords:
            m.plot(long, lati, ".",
                markersize=0.5, #5,
                latlon=True,
                color="red",
                label=label,
                zorder=4,
            )
            label = ''


        #from IPython import embed; embed()
        if self.df.attrs['boxes']:
            label = 'superob'
            for lats, lons in self.df.attrs['boxes']:
                lats, lons = np.meshgrid(lats, lons)

                plot_box(m, lats, lons, label=label, color="white", lw=0.1) #1)
                label = ''

        plt.legend()
        plt.tight_layout()
        plt.savefig(f_out, dpi=600)
        print(f_out, "saved.")


if __name__ == "__main__":
    from config.cluster import cluster
    # for testing purposes

    # f = cluster.scriptsdir + "/../tests/obs_seq.orig.out"
    f = "/home/fs71386/lkugler/data/sim_archive/exp_v1.21_P3_wbub7_VIS_obs2-10_loc20/obs_seq_out/2008-07-30_12:30_obs_seq.out-orig"
    obs = ObsSeq(f)

    # select a subset (lat-lon)
    obs.df = obs.df.superob(window_km=10)
    # print(type(obs.df))

    obs.plot(f_out="./map_obs_superobs.png")

    # write to obs_seq.out in DART format
    # obs.to_dart(f=cluster.dart_rundir + "/obs_seq.out")
