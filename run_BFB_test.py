#!/usr/bin/env python

import sys
import os
import shutil
import glob
import subprocess


nnodes_per_core = 40

pwd = os.getcwd()

start_date = '2012-10-01_00:00:00'
restart_date = '2012-10-02_00:00:00'
end_date = '2012-10-03_00:00:00'

max_nodes = 2

#variables = ['normalVelocity','layerThickness']
variables = ['ssh','ssh_sal']

#exe_opt = 'ocean_model_intel'
#exe_opt_openmp = 'ocean_model_intel_openmp'
#exe_opt = 'ocean_model_intel_debug'
exe_opt = 'ocean_model_intel_shtns'
exe_opt_openmp = 'ocean_model_intel_openmp_debug'

exact_restart = True
#exact_restart = False
exact_partition = True
#exact_tread = True
exact_tread = False

#restart_file = 'restarts/restart.'+end_date.replace(':','.')+'.nc'
restart_file = 'initial_state.nc'

########################################################################
########################################################################

def setup_namelist(restart):

  f = open('namelist.ocean','r')
  lines = f.read().splitlines()
  f.close()

  if restart:
    for i in range(len(lines)):
       if lines[i].find('config_do_restart') >= 0 :
         lines[i] = '    config_do_restart = .true.'
         print(lines[i])
       if lines[i].find('config_start_time') >= 0 :
         lines[i] = "    config_start_time = 'file'"
         print(lines[i])
       if lines[i].find('config_run_duration') >= 0 :
         lines[i] = "    config_run_duration = '00-00-01_00:00:00'"
         print(lines[i])
  else:
    for i in range(len(lines)):
       if lines[i].find('config_do_restart') >= 0 :
         lines[i] = '    config_do_restart = .false.'
         print(lines[i])
       if lines[i].find('config_start_time') >= 0 :
         lines[i] = "    config_start_time = '"+start_date+"'"
         print(lines[i])
       if lines[i].find('config_run_duration') >= 0 :
         lines[i] = "    config_run_duration = '00-00-02_00:00:00'"
         print(lines[i])
   
  f = open('namelist.ocean','w')
  f.write('\n'.join(lines))
  f.close()

  if restart:
    f = open('Restart_timestamp','w')
    f.write(restart_date)
    print(restart_date)
    f.close()

########################################################################
########################################################################

def setup_streams():

  f = open('streams.ocean','r')
  lines = f.read().splitlines()
  f.close()

  restart_stream = False
  for i in range(len(lines)):
     if lines[i].find('<immutable_stream name="restart"') >= 0 :
       restart_stream = True
     if restart_stream:
       if lines[i].find('output_interval=') >= 0 :
         line_split = lines[i].split('"')
         line_split[1] = '00-00-01_00:00:00'
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

def run(nds,exe='ocean_model',threads=1):
  np = nds*nnodes_per_core

  if exe != 'ocean_model':
    cmd = 'ln -sf '+exe+' ocean_model'
    subprocess.call(cmd,shell=True)
    print(cmd)
  
  cmd = ' '.join(['gpmetis', 'graph.info', str(np)])
  subprocess.call(cmd,shell=True)
  print(cmd)

  print("\n")
  print("     *****************************")
  print("     ** Starting model run step **")
  print("     *****************************")
  print("\n")

  os.environ['OMP_NUM_THREADS'] = str(threads)
  print('OMP_NUM_THREADS = '+str(threads))

  cmd = ' '.join(['srun', '--mpi=pmi2','-N',str(nds),'-n', str(np),'--kill-on-bad-exit','-l','--cpu_bind=cores','-c','1','-m','plane=40','./ocean_model', '-n', 'namelist.ocean', '-s', 'streams.ocean'])
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
  BFB = False 
  for line in lines:
    for var in variables:
      if line.find(var+' = ') >= 0:
        comparisons.append(line)
        if line.split('=')[1] == ' 0 ;':
          BFB = True

  print(comparisons)
  print('Pass: ',BFB)

########################################################################
########################################################################

if __name__ == '__main__':

  os.chdir(pwd)


  print('\n')
  print(72*'-')
  print('Base Run')
  print(72*'-')

  setup_streams()
  setup_namelist(restart=False)
  run(max_nodes,exe_opt)
  suffix_base = 'base_n'+str(max_nodes)
  rename(restart_file,suffix_base)


  if exact_restart:
    print('\n')
    print(72*'-')
    print('Restart Run')
    print(72*'-')

    setup_namelist(restart=True)
    run(max_nodes,exe_opt)
    suffix2 = 'restart_n'+str(max_nodes)
    rename(restart_file,suffix2)
  
    verify(restart_file,suffix_base,suffix2)


  if exact_partition:
    print('\n')
    print(72*'-')
    print('Partition Run: half nodes')
    print(72*'-')

    half_nodes = int(max_nodes/2)
    setup_namelist(restart=False)
    run(half_nodes,exe_opt)
    suffix3 = 'partition_n'+str(half_nodes)
    rename(restart_file,suffix3)
  
    verify(restart_file,suffix_base,suffix3)

    print('\n')
    print(72*'-')
    print('Partition Run: double nodes')
    print(72*'-')

    double_nodes = int(max_nodes*2)
    setup_namelist(restart=False)
    run(double_nodes,exe_opt)
    suffix3 = 'partition_n'+str(double_nodes)
    rename(restart_file,suffix3)
  
    verify(restart_file,suffix_base,suffix3)

  if exact_tread:
    print('\n')
    print(72*'-')
    print('Thread Run: 1')
    print(72*'-')

    threads = 1
    setup_namelist(restart=False)
    run(max_nodes,exe_opt_openmp,threads)
    suffix4 = 'thread_n'+str(max_nodes)+'_t'+str(threads)
    rename(restart_file,suffix4)
  
    verify(restart_file,suffix_base,suffix4)

    print('\n')
    print(72*'-')
    print('Thread Run: 2')
    print(72*'-')

    threads = 2
    setup_namelist(restart=False)
    run(max_nodes,exe_opt_openmp,threads)
    suffix4 = 'thread_n'+str(max_nodes)+'_t'+str(threads)
    rename(restart_file,suffix4)
  
    verify(restart_file,suffix_base,suffix4)

    print('\n')
    print(72*'-')
    print('Thread Run: 4')
    print(72*'-')

    threads = 4
    setup_namelist(restart=False)
    run(max_nodes,exe_opt_openmp,threads)
    suffix4 = 'thread_n'+str(max_nodes)+'_t'+str(threads)
    rename(restart_file,suffix4)
  
    verify(restart_file,suffix_base,suffix4)

