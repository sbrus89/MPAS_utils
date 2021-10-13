import subprocess 

USE_PIO2 = True

exes = {
          'intel'             :{'target':'intel-mpi','options':''},
          'intel_debug'       :{'target':'intel-mpi','options':'DEBUG=true'},
          'intel_openmp'      :{'target':'intel-mpi','options':'OPENMP=true'},
          'intel_debug_openmp':{'target':'intel-mpi','options':'OPENMP=true DEBUG=true'},
          'intel_shtns'       :{'target':'intel-mpi','options':'USE_SHTNS=true'},
          #'intel_shtns_debug' :{'target':'intel-mpi','options':'DEBUG=true USE_SHTNS=true'},
       }

git_hash = subprocess.check_output('git rev-parse --short HEAD', shell=True).strip()

for exe in exes:

  target = exes[exe]['target']
  options = exes[exe]['options']
  ocean_model_exe_name = 'ocean_model_'+exe+'_'+git_hash
  
  if USE_PIO2:
    options = options + ' USE_PIO2=true'

  subprocess.call('make clean CORE=ocean', shell=True)
  subprocess.call('make '+target+' CORE=ocean '+options, shell=True)
  subprocess.call('mv ocean_model '+ocean_model_exe_name, shell=True)
