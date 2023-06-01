import os, shutil
import datetime as dt

from dartwrf import dart_nml



def test_input_nml():
    test_input = './input.nml.original'
    test_output = './input.nml.output'
    desired_output = './input.nml.desired_output'

    # read an existing input.nml
    nml = dart_nml.read_namelist(test_input)

    # modify one parameter
    nml['&filter_nml']['ens_size'] = [[999,]]
    nml['&filter_nml']['num_output_state_members'] = [[999,]]
    nml['&filter_nml']['num_output_obs_members'] = [[999,]]
    nml['&filter_nml']['compute_posterior'] = [['.false.']]

    # save the configuration as input.nml
    dart_nml.write_namelist_from_dict(nml, test_output)

    # compare the saved input.nml to the true input.nml
    # by reading both and comparing the dictionaries
    nml_desired = dart_nml.read_namelist(desired_output)
    nml_test = dart_nml.read_namelist(test_output)

    # section e.g. '&preprocess_nml'
    for section, _ in nml_desired.items():

        # param e.g. 'filter_kind'
        for param, value in nml_desired[section].items():

            should_have = nml_desired[section][param]
            have = nml_test[section][param]

            for i, line in enumerate(should_have):

                for j, expected in enumerate(line):

                    if expected != have[i][j]:

                        # if one has "wrfinput" and other has 'wrfinput'
                        # thats ok
                        this = "'"+have[i][j].strip('"')+"'"
                        if this == expected:
                            pass
                            # print(this, expected)
                        else:
                            raise ValueError('expected', expected, 'got', have[i][j])
    
    os.remove(test_output)

def test_get_list_of_localizations():

    output = dart_nml._get_list_of_localizations()
    assert (['SYNOP_TEMPERATURE'], [0.0015698587127158557], [1274000.0], [-1]) == output


if __name__ == '__main__':
    test_input_nml()

    test_get_list_of_localizations()