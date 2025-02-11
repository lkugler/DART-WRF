import warnings
import os

# author: gthalassinos

class WRF_namelist():
    """Class to read and write WRF namelist files

    Example:
        n = WRF_namelist('/path_to_existing/namelist.input')
        n.read()
        
        n.namelist  # is a dictionary
        n.namelist['time_control']['run_days'] = 1
        
        n.write('/path_to_new/namelist.input')
    """
    def __init__(self):
        self.namelist = {}

    def read(self, fname: str) -> None:
        """Read a WRF namelist file and store it in a dictionary
        """
        with open(fname, 'r') as f:
            lines  = f.readlines()
        
        subdomains = True
        block_name = None
        for l in lines:
            l = l.strip()
            if l.startswith("&"):
                block_name = l.split("&")[1]
                self.namelist[block_name] = {}
            elif l.startswith("/"):
                block_name = None
            elif l.startswith("!") and block_name:
                continue
            elif (block_name) and ("=" in l):
                variable, value = l.split("=")
                variable = variable.strip()
                value = value.strip().rstrip(",")

                if "," in value:
                    try:
                        values = eval(value)
                    except:
                        raise ValueError(f"{variable} is not a tuple!")
                    subdomains = True
                    value = values
                # check if we have single numbers
                if not isinstance(value, tuple):
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass

                self.namelist[
                    block_name][
                        variable] = value    

            subdomains = False            
                
        pass

    def write(self, fname: str) -> None:
        """Write a WRF namelist file
        """
        if os.path.exists(fname):
            warnings.warn(f"{fname} already exists!")
            if input('Continue? (Y/n) ') in ['Y', 'y']:
                pass      
            else:
                raise FileExistsError  
        
        with open(fname, 'w') as file:
            for block, variables in self.namelist.items():
                file.write(f" &{block}\n")
                for variable, value in variables.items():
                    if isinstance(value, str) and not value.startswith('.'):
                        value = f'{value}'
                    if isinstance(value, tuple):
                        value = str(value)[1:-1]
                    file.write(f" {variable:<35} = {value},\n")
                file.write(" /\n\n")
        pass    