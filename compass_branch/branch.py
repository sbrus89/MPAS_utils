import os
import subprocess
import yaml
import glob

f = open('branch.config','r')
cfg = yaml.load(f, Loader=yaml.Loader)

compass_master = cfg['compass_master']
branch_name = cfg['branch_name']
remote_branch = cfg['remote_branch']
master_branch = cfg['master_branch']
miniconda_path = cfg['miniconda_path']
mpi = cfg['mpi']
make_target = cfg['make_target']
debug = cfg['debug']
testcases = cfg['testcases']
workdir = cfg['workdir']
run = cfg['run']
e3sm_remote = cfg['e3sm_remote']
e3sm_branch = cfg['e3sm_branch']
e3sm_commit= cfg['e3sm_commit']

update_branch = ''
if 'update_branch' in cfg:
    update_branch = cfg['update_branch']
local_merge = True
if 'local_merge' in cfg:
    local_merge = cfg['local_merge']
configure_conda = ''
if 'configure_conda' in cfg:
    configure_conda = cfg['configure_conda']
compile_mpas = ''
if 'compile_mpas' in cfg:
    compile_mpas = cfg['compile_mpas']
setup_testcases = ''
if 'setup_testcases' in cfg:
    setup_testcases = cfg['setup_testcases']
e3sm_remote= ''
if 'e3sm_remote' in cfg:
    e3sm_remote= cfg['e3sm_remote']
e3sm_branch= ''
if 'e3sm_branch' in cfg:
    e3sm_branch= cfg['e3sm_branch']
e3sm_commit= ''
if 'e3sm_commit' in cfg:
    e3sm_commit= cfg['e3sm_commit']



os.chdir(compass_master)

print('\n')
print('------------------------------------------')
print('Fetching remote branches')
print('------------------------------------------')
subprocess.check_call('git fetch --all', shell=True)



print('\n')
print('------------------------------------------')
print('Creating worktree branch')
print('------------------------------------------')
try:
    subprocess.check_call(f'module load git; git worktree add -b {branch_name} ../{branch_name} {remote_branch}', shell=True)
except:
    pass
os.chdir(f'../{branch_name}')



if update_branch == '' or update_branch == True:
    print('\n')
    print('------------------------------------------')
    print('Updating branch')
    print('------------------------------------------')
    local = subprocess.check_output(f'module load git; git log -1 --oneline', shell=True)
    remote = subprocess.check_output(f'module load git; git log -1 --oneline {remote_branch}', shell=True)
    if local.split()[0].decode('utf-8') != remote.split()[0].decode('utf-8'):
        print(local)
        print(remote)
        if update_branch == '':
            update = input('local and remote branches differ, update?: (y/n) ')
        else:
            update = 'y'
        if update == 'y':
            subprocess.check_call(f'module load git; git reset --hard {remote_branch}', shell=True)
    else:
        print('local and remote branches match')



if local_merge == True:
    print('\n')
    print('------------------------------------------')
    print('Perform local merge')
    print('------------------------------------------')
    
    #subprocess.check_call(f'module load git; git reset --hard {master_branch}', shell=True)
    #subprocess.check_call(f'module load git; git merge --no-ff {remote_branch}', shell=True)
    subprocess.check_call(f'module load git; git rebase {master_branch}', shell=True)



load_scripts = glob.glob('load_dev_compass*.sh')
if len(load_scripts) == 0:
    configure_conda = True
if configure_conda == '' or configure_conda == True:
    print('\n')
    print('------------------------------------------')
    print('Configuring conda environment')
    print('------------------------------------------')
    if len(load_scripts) > 0:
        if configure_conda == '':
            configure_compass = input('load_dev_compass script exists, run configure_compass_env.py again?: (y/n) ')
        else:
            configure_compass = 'y'
    else:
        configure_compass = 'y'
      
    if configure_compass == 'y':
        subprocess.check_call(f'./conda/configure_compass_env.py --conda {miniconda_path} --mpi {mpi}', shell=True)

load_scripts = glob.glob('load_dev_compass*.sh')
load_script = max(load_scripts, key=os.path.getctime)



print('\n')
print('------------------------------------------')
print('Submodule checkout')
print('------------------------------------------')
subprocess.check_call('module load git; git submodule update --init --recursive', shell=True)



os.chdir('E3SM-Project/components/mpas-ocean')
if e3sm_remote != '' and e3sm_branch != '':
  print('\n')
  print('------------------------------------------')
  print('E3SM remote checkout')
  print('------------------------------------------')
  subprocess.check_call(f'module load git; git fetch {e3sm_remote} {e3sm_branch}; git checkout FETCH_HEAD', shell=True)



if e3sm_commit != '':
  print('\n')
  print('------------------------------------------')
  print('E3SM commit checkout')
  print('------------------------------------------')
  subprocess.check_call(f'git checkout {e3sm_commit}', shell=True)



if not os.path.exists('ocean_model'):
    compile_mpas = True
if compile_mpas == '' or compile_mpas == True:
    print('\n')
    print('------------------------------------------')
    print('Compile mpas-ocean')
    print('------------------------------------------')
    if compile_mpas == '':
        if os.path.exists('ocean_model'):
            build = input('ocean_model executable exists, re-compile?: (y/n) ')
        else:
            build = 'y'
    else:
        build = 'y'
    
    if debug:
        use_debug = 'true'
    else:
        use_debug = 'false'

    if build == 'y':
        subprocess.check_call(f'source ../../../{load_script}; make clean; make {make_target} DEBUG={use_debug}', shell=True)



if setup_testcases == '' or setup_testcases == True:
    print('\n')
    print('------------------------------------------')
    print('Setup testcases')
    print('------------------------------------------')
    os.chdir('../../../')
    command = f'source ./{load_script}' 
    ntest = 0
    for test in testcases:
        if setup_testcases == '':
            if os.path.exists(f'{workdir}/{test}'):
                setup = input(f'Test {test} already exists, setup again?: (y/n)')
            else:
                setup = 'y'
        else:
            setup = 'y'
        if setup == 'y':
          ntest = ntest + 1
          command = command + f'; compass setup -t {test} -w {workdir}'
    if ntest > 1:
        subprocess.check_call(command, shell=True)



if run:
    print('\n')
    print('------------------------------------------')
    print('Run testcases')
    print('------------------------------------------')
    dependency = ''
    for test in testcases:
            os.chdir(f'{workdir}/{test}')
            output = subprocess.check_output(f'sbatch {dependency} compass_job_script.sh', shell=True)
            print(output) 
            jobid = output.split()[-1].decode('utf-8')
            dependency = f'--dependency=afterok:{jobid}' 
