import netCDF4
import numpy as np
import argparse

namelist_file = '/pscratch/sd/s/sbrus/vr45to5_tides/namelist.ocean'
output_nc = '/pscratch/sd/k/knbarton/runs/twd_tuning_45to5km/ZAE/fwd/0p3/output.nc'


if __name__ == '__main__':

  parser = argparse.ArgumentParser()
  parser.add_argument('--namelist-file', dest='namelist_file', type=str,
                      required=True, help='Path to MPAS namelist file')
  parser.add_argument('--output-nc', dest='output_nc', type=str,
                      required=True, help='Path to MPAS output file')
  args = parser.parse_args()
  namelist_file = args.namelist_file
  output_nc = args.output_nc

  # Parse namelist file
  lines = open(namelist_file).readlines()
  configs = []
  for line in lines:
    if line.find('=') > 0:
      configs.append(line.strip())

  # open MPAS netcdf output file
  out_nc = netCDF4.Dataset(output_nc)
  
  for config in configs:

    name = config.split('=')[0].strip()
    value_nml = config.split('=')[-1].strip().replace("'","")
    value_nc = out_nc.getncattr(name)

    # Compare string configs
    same = value_nml == value_nc

    # Compare true/false configs
    true_list = ['.true.', 'true', 'YES', 'yes']
    false_list = ['.false.', 'false', 'NO', 'no']
    if (value_nml in true_list) or (value_nml in false_list):
      same = False
      if (value_nml in true_list) and (value_nc in true_list):
        same = True
      if (value_nml in false_list) and (value_nc in false_list):
        same = True

    # Compare float configs
    try:
      same = '{:0.6e}'.format(np.float64(value_nml)) == '{:0.6e}'.format(np.float64(value_nc))
    except:
      pass

    # Indicate differences      
    if not same:
      print(name)
      print(f'   namelist_file: {value_nml}')
      print(f'   output_nc:     {value_nc}')
 
