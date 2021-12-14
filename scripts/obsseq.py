import os, sys, shutil, warnings
import numpy as np
import pandas as pd

from config.cfg import exp, cluster
from utils import symlink, copy, sed_inplace, append_file, mkdir, try_remove


def plot_box(m, lat, lon, label="", **kwargs):

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


class ObsSeq(object):
    """Read, manipulate, save obs_seq.out / final files
    """

    def __init__(self, filepath):
        self.ascii = open(filepath, "r").readlines()

        self.get_preamble_content()
        self.read_preamble()

        self.dict = self.obs_to_dict()
        self.df = self.to_pandas()

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

            assert len(obs_list) > 1
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
            #out["obs"] = float(lines[1].strip())
            #out["truth"] = float(lines[2].strip())
            #out["qc"] = float(lines[3].strip())
            x, y, z, z_coord = lines[line_loc].split()
            out["loc3d"] = float(x), float(y), float(z), int(z_coord)
            out["kind"] = int(lines[line_kind].strip())
            out["metadata"] = lines[line_kind + 1 : -3]
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

    def get_prior_Hx_matrix(self):
        """Return prior Hx array (n_obs, n_ens)"""

        # which columns do we need?
        keys = self.df.columns
        keys_bool = np.array(['prior ensemble member' in a for a in keys])

        # select columns in DataFrame
        prior_Hx = self.df.iloc[:, keys_bool]

        # consistency check: compute mean over ens - compare with value from file
        assert np.allclose(prior_Hx.mean(axis=1), self.df['prior ensemble mean'])

        return prior_Hx.values

    def get_truth_Hx(self):
        return self.df['truth'].values

    def get_lon_lat(self):
        lats = np.empty(len(self.df), np.float32)
        lons = lats.copy()

        for i_obs, values in self.df.loc3d.items():
            x, y, z, z_coord = values

            # convert radian to degrees lon/lat
            lon = rad_to_degrees(x)
            lat = rad_to_degrees(y)
            lons[i_obs] = lon
            lats[i_obs] = lat

        return pd.DataFrame(index=self.df.index, data=dict(lat=lats, lon=lons))

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
        debug = False
        radius_earth_meters = 6.371 * 1e6
        m_per_degrees = np.pi * radius_earth_meters / 180  # m per degree latitude
        km_per_degrees = m_per_degrees / 1000

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

        # assume cartesian grid of observations
        i_obs_grid = self.df.index.values
        nx = int(len(i_obs_grid) ** 0.5)
        i_obs_grid = i_obs_grid.reshape(nx, nx)

        # loop through columns/rows
        # avoid loop in (lat,lon) space as coordinates are non-cartesian
        # i.e. first column of observations does not have same longitude

        # determine obs density (approx)
        coords = self.get_lon_lat()
        dx_obs_lat_deg = coords.lat.diff().max()
        km_lat, _ = calc_km_from_deg(dx_obs_lat_deg, np.nan, 45)
        obs_spacing_km = int(km_lat)

        # how many observations in x/y direction?
        win_obs = int(window_km / obs_spacing_km)
        if debug:
            print('window_km=', window_km)
            print('obs spacing=', obs_spacing_km)
            print("window (#obs in x/y)=", win_obs)

        out = self.df.drop(self.df.index)  # this df will be filled

        for i in range(0, nx - win_obs, win_obs):
            for j in range(0, nx - win_obs, win_obs):

                # find indices of observations which lie in the superob box
                i_obs_box = i_obs_grid[i : i + win_obs, j : j + win_obs].ravel()

                if debug:
                    print("index x from", i, 'to', i + win_obs)
                    print("index y from", j, 'to', j + win_obs)
                    print("obs indices box=", i_obs_grid[i : i + win_obs, j : j + win_obs])

                # average the subset
                # metadata are assumed to be equal
                obs_box = self.df.iloc[i_obs_box]

                obs_mean = obs_box.iloc[0]
                # despite its name, 'observations' is a single value
                for key in obs_box:
                    if key in ['loc3d', 'kind', 'metadata', 'time']:
                        pass
                    elif 'spread' in key:  # mean of std deviations
                        obs_mean.at[key] = np.sqrt((obs_box[key]**2).mean())
                    else:
                        obs_mean.at[key] = obs_box[key].mean()

                if debug:
                    print("pre_avg:", obs_box.head())
                    print("avg:", obs_mean)

                out = out.append(obs_mean)

        self.df = out  # overwrite input
        n_pre_superob = self.num_obs
        n_post_superob = len(self.df)

        # assume square of obs
        n_windows_x = int(n_pre_superob**.5/win_obs)  # in x-direction
        n_target_post = n_windows_x**2  # number of windows
        print('superob from', n_pre_superob, 'obs to', n_post_superob, 'obs')
        assert n_post_superob == n_target_post, RuntimeError()

    def to_pandas(self):
        """Create xr.Dataset containing observations
        Variables = observation types
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
                        "kind", "         " + str(obs["kind"]),
                        "".join(obs["metadata"]),
                    ]
                )
                + str(i)
                + "\n "
                + obs["time"][0]
                + "     "
                + obs["time"][1]
                + "\n"
                + str(obs["variance"])
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


    def plot(self, box=None):
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

        plot_box(m, lat, lon, label="domain", color="green", lw=4)

        # OBSERVATIONS
        coords = self.get_lon_lat()
        lats = coords.lat.values
        longs = coords.lon.values
        coords = zip(lats, longs)

        for lati, long in coords:
            m.plot(
                long,
                lati,
                ".",
                markersize=5,
                latlon=True,
                color="red",
                zorder=4,
            )

        m.plot(
            [],
            [],
            "s",
            markersize=0.3,
            label="observations",
            color="red",
            zorder=4,
        )

        if box:
            lats = box["lat"]
            longs = box["lon"]
            lats, longs = np.meshgrid(lats, longs)
            print(lats, longs)

            plot_box(m, lats, longs, label="superob", color="white", lw=1)

        plt.legend()
        plt.tight_layout()
        f = "/home/fs71386/lkugler/data/analysis/map_obs_superobs.png"
        plt.savefig(f, dpi=300)
        print(f, "saved.")


if __name__ == "__main__":
    # for testing purposes

    obs = ObsSeqOut(cluster.scriptsdir + "/../tests/obs_seq.orig.out")

    # select a subset (lat-lon)
    obs.superob(window_km=50)

    # write to obs_seq.out in DART format
    obs.to_dart(f=cluster.dartrundir + "/obs_seq.out")
