import glob
import os
import subprocess

run_name = '20221027.submeso.langmuir.momentum.piControl.ne30pg2_EC30to60E2r2_wQU225EC30to60E2r2.anvil'
run_direc = '/lcrc/group/acme/sbrus/scratch/anvil/20221027.submeso.langmuir.momentum.piControl.ne30pg2_EC30to60E2r2_wQU225EC30to60E2r2.anvil/run/'
keep_years = ['0025','0050','0101','125','137']

rest_files = {'atm':'*.eam.r.*.nc',
              'drv':'*cpl.r.*.nc',
              'lnd':'*elm.r.*.nc',
              'ice':'*mpassi.rst.????-??-??_?????.nc',
              'ocn':'*mpaso.rst.????-??-??_?????.nc',
              'rof':'*mosart.r.*.nc',  
              'wav':'*.restart.ww3'}

other_del_files = ['*waveOutput.*_00.00.00.nc']


for comp in rest_files:
  print(comp)

  files = glob.glob(run_direc+rest_files[comp])  
  files.sort()


  keep_files = []
  del_files = []
  for i, f in enumerate(files):

    keep = False
    for yr in keep_years:

      fname = f.split('/')[-1]
      if comp == 'wav':
        year = fname.split('.')[0]
      else:
        year = fname.split('.')[-2]

      if year[0:4].find(yr) >= 0:
        keep = True

    if i == len(files)-1:
      keep = True

    if keep == False:
      del_files.append(f)
    else: 
      keep_files.append(f)

  print('deleted files')
  print(del_files)
  size = 0
  for f in del_files:
    size = size + os.path.getsize(f)
    subprocess.call('rm '+f, shell=True)

  print(size/1e9)
  print('keep files:')
  print(keep_files)


  
  print()


for files in other_del_files:

  filenames = glob.glob(run_direc+files)

  size = 0
  for f in filenames:
    size = size + os.path.getsize(f)
    subprocess.call('rm '+f, shell=True)

  print(size/1e9)
  print(filenames)
              
