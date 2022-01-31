#!/usr/bin/env python

import sys
import os
import shutil
import glob
import subprocess
import datetime
import math


ncores_per_core = 40

start_date = '2012-10-01_00:00:00'
#end_date = '2012-10-02_00:00:00'
end_date = '2012-10-01_01:00:00'

#base_cores = 1280 
base_cores = 20 

variables = ['normalVelocity','layerThickness']
#variables = ['ssh','ssh_sal']

exe = 'ocean_model_intel_shtns_9de43d0'
exe_openmp = 'ocean_model_intel_openmp_9de43d0'

#exact_restart = True
exact_restart = False

exact_partition = True
#exact_partition = False
#partition_cores = [2560,640]
partition_cores = [40]

#exact_thread = True
exact_thread = False
threads = [1,2,4]

restart_file = 'restarts/restart.'+end_date.replace(':','.')+'.nc'
#restart_file = 'initial_state.nc'

namelist_options = {
                    #'config_use_self_attraction_loading':'.false.',
                    'config_use_self_attraction_loading':'.true.',
                    'config_self_attraction_loading_compute_interval':'00:00:30',
                    #'config_use_parallel_self_attraction_loading':'.false.'
                    'config_use_parallel_self_attraction_loading':'.true.'
                   }

frmt = '%Y-%m-%d_%H:%M:%S'
########################################################################
########################################################################

def setup_namelist(restart):

  start_datetime = datetime.datetime.strptime(start_date,frmt)
  end_datetime = datetime.datetime.strptime(end_date,frmt)
  length = end_datetime - start_datetime

  if restart:

    restart_length = length/2
    restart_date = start_datetime + restart_length
    duration = strfdelta(restart_length)

    # Set namelist options for restart run
    options = {
               'config_do_restart':'.true',
               'config_start_time':"'file'",
               'config_run_duration':duration
              }

    f = open('Restart_timestamp','w')
    f.write(restart_date.strftime(frmt))
    print(restart_date.strftime(frmt))
    f.close()

  else:

    duration = strfdelta(length)
    # Set namelist options for full run 
    options = {
               'config_do_restart':'.false.',
               'config_start_time':"'"+start_date+"'",
               'config_run_duration':duration
              }

  modify_namelist(options)


########################################################################
########################################################################

def strfdelta(tdelta):

  d = {"D": tdelta.days}
  hours, rem = divmod(tdelta.seconds, 3600)
  minutes, seconds = divmod(rem, 60)
  d["H"] = '{:02d}'.format(hours)
  d["M"] = '{:02d}'.format(minutes)
  d["S"] = '{:02d}'.format(seconds)

  return "'00-00-{D}_{H}:{M}:{S}'".format(**d)

########################################################################
########################################################################

def modify_namelist(options):

  print('namelist.ocean update:')

  f = open('namelist.ocean','r')
  lines = f.read().splitlines()
  f.close()

  for opt in options:
    for i in range(len(lines)):
      if lines[i].find(opt) >= 0:
        lines[i] = '    ' + opt + ' = '+options[opt]
        print(lines[i])

  f = open('namelist.ocean','w')
  f.write('\n'.join(lines))
  f.close()

########################################################################
########################################################################

def setup_streams():

  start_datetime = datetime.datetime.strptime(start_date,frmt)
  end_datetime = datetime.datetime.strptime(end_date,frmt)
  length = end_datetime - start_datetime

  restart_length = length/2
  duration = strfdelta(restart_length)
  duration = duration.replace("'",'')

  f = open('streams.ocean','r')
  lines = f.read().splitlines()
  f.close()

  print('streams.ocean update:')
  restart_stream = False
  for i in range(len(lines)):
     if lines[i].find('<immutable_stream name="restart"') >= 0 :
       restart_stream = True
     if restart_stream:
       if lines[i].find('output_interval=') >= 0 :
         line_split = lines[i].split('"')
         line_split[1] = duration
         lines[i] = '"'.join(line_split)
         print(lines[i])
       if lines[i].find('filename_template=') >= 0 :
         lines[i] = '                  filename_template="restarts/restart.$Y-$M-$D_$h.$m.$s.nc"'
         print(lines[i])
       if lines[i].find('filename_interval=') >= 0 :
         lines[i] = '                  filename_interval="output_interval"'
         print(lines[i])
     if restart_stream and (lines[i].find('/>') >= 0):
       restart_stream = False
   
  f = open('streams.ocean','w')
  f.write('\n'.join(lines))
  f.close()

########################################################################
########################################################################

def run(cores,exe='ocean_model',threads=1):
  nodes = int(math.ceil(cores/ncores_per_core))

  if exe != 'ocean_model':
    cmd = 'ln -sf '+exe+' ocean_model'
    subprocess.call(cmd,shell=True)
    print(cmd)
  
  cmd = ' '.join(['gpmetis', 'graph.info', str(cores)])
  subprocess.call(cmd,shell=True,stdout=subprocess.DEVNULL)
  print(cmd)

  print("\n")
  print("     *****************************")
  print("     ** Starting model run step **")
  print("     *****************************")
  print("\n")

  os.environ['OMP_NUM_THREADS'] = str(threads)
  print('OMP_NUM_THREADS = '+str(threads))

  cmd = ' '.join(['srun', '--mpi=pmi2',
                          '-N',str(nodes),'-n', str(cores),
                          '--kill-on-bad-exit','-l','--cpu_bind=cores','-c','1','-m','plane=40',
                          './ocean_model', '-n', 'namelist.ocean', '-s', 'streams.ocean'])
  subprocess.check_call(cmd,shell=True)
  print(cmd)

  print("\n")
  print("     *****************************")
  print("     ** Finished model run step **")
  print("     *****************************")
  print("\n")

########################################################################
########################################################################

def rename(restart_file,suffix):

  log_file = 'log.ocean.0000.out'
  cmd = ' '.join(['mv', log_file , log_file+'_'+suffix])
  subprocess.check_call(cmd,shell=True)
  print(cmd)
  cmd = ' '.join(['mv', restart_file, restart_file+'_'+suffix])
  subprocess.check_call(cmd,shell=True)
  print(cmd)

########################################################################
########################################################################

def verify(restart_file,suffix_base,suffix2):

  diff_file = suffix_base+'-'+suffix2+'.diff.nc'
  diffmabs_file = suffix_base+'-'+suffix2+'.diffmabs.nc'

  ncdiff = 'ncdiff -O '+restart_file+'_'+suffix_base+' '+restart_file+'_'+suffix2+' '+ diff_file
  print(ncdiff)
  subprocess.call(ncdiff, shell=True)
  ncwa = 'ncwa -O -y mabs -v '+','.join(variables)+' '+diff_file+' '+diffmabs_file
  print(ncwa)
  subprocess.call(ncwa, shell=True)
  output = subprocess.check_output(['ncdump', diffmabs_file])
  lines = output.decode('utf-8').splitlines()

  comparisons = []
  BFB = True 
  for line in lines:
    for var in variables:
      if line.find(var+' = ') >= 0:
        comparisons.append(line)
        if line.split('=')[1] != ' 0 ;':
          BFB = False

  print(comparisons)
  print('Pass: '+str(BFB), flush=True)

########################################################################
########################################################################

if __name__ == '__main__':

  pwd = os.getcwd()
  os.chdir(pwd)

  modify_namelist(namelist_options)

  print('\n')
  print(72*'-')
  print('Base Run')
  print(72*'-')

  setup_streams()
  setup_namelist(restart=False)
  run(base_cores,exe)
  suffix_base = 'base_n'+str(base_cores)
  rename(restart_file,suffix_base)


  if exact_restart:

    print('\n')
    print(72*'-')
    print('Restart Run')
    print(72*'-')

    setup_namelist(restart=True)
    run(base_cores,exe)
    suffix2 = 'restart_n'+str(base_cores)
    rename(restart_file,suffix2)
  
    verify(restart_file,suffix_base,suffix2)


  if exact_partition:

    for cores in partition_cores:

      print('\n')
      print(72*'-')
      print('Partition Run: '+str(cores)+' cores')
      print(72*'-')

      setup_namelist(restart=False)
      run(cores,exe)
      suffix = 'partition_n'+str(cores)
      rename(restart_file,suffix)
  
      verify(restart_file,suffix_base,suffix)


  if exact_thread:

    for thrds in threads:

      print('\n')
      print(72*'-')
      print('Thread Run: '+str(thrds)+' threads')
      print(72*'-')

      setup_namelist(restart=False)
      run(base_cores,exe_openmp,thrds)
      suffix = 'thread_n'+str(base_cores)+'_t'+str(thrds)
      rename(restart_file,suffix)
  
      verify(restart_file,suffix_base,suffix)


