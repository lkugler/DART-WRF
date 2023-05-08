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
    nml['&filter_nml']['ens_size'] = [[str(999)]]
    nml['&filter_nml']['num_output_state_members'] = [[str(999)]]
    nml['&filter_nml']['num_output_obs_members'] = [[str(999)]]

    # save the configuration as input.nml
    dart_nml.write_namelist_from_dict(nml, test_output)

    # compare the saved input.nml to the true input.nml
    # by reading both and comparing the dictionaries
    nml_desired = dart_nml.read_namelist(desired_output)
    nml_test = dart_nml.read_namelist(test_output)

    for section, _ in nml_desired.items():

        for param, value in nml_desired[section].items():

            should_have = nml_desired[section][param]
            should_have = [v.strip() for line in should_have for v in line]

            have = nml_test[section][param]
            have = [v.strip() for line in have for v in line]
            
            if should_have != have:

                raise ValueError(section, param, 'should be', should_have, 'but is', have)

    
    os.remove(test_output)

if __name__ == '__main__':
    test_input_nml()
