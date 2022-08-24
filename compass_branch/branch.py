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
testcases = cfg['testcases']
workdir = cfg['workdir']
run = cfg['run']



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

print('\n')
print('------------------------------------------')
print('Updating branch')
print('------------------------------------------')
local = subprocess.check_output(f'module load git; git log -1 --oneline', shell=True)
remote = subprocess.check_output(f'module load git; git log -1 --oneline {remote_branch}', shell=True)
if local.split()[0].decode('utf-8') != remote.split()[0].decode('utf-8'):
    print(local)
    print(remote)
    update = input('local and remote branches differ, update?: (y/n) ')
    if update == 'y':
        subprocess.check_call(f'module load git; git reset --hard {remote_branch}', shell=True)
else:
    print('local and remote branches match')

print('\n')
print('------------------------------------------')
print('Perform local merge')
print('------------------------------------------')

subprocess.check_call(f'module load git; git reset --hard {master_branch}', shell=True)
subprocess.check_call(f'module load git; git merge --no-ff {remote_branch}', shell=True)
#subprocess.check_call(f'module load git; git rebase {master_branch}', shell=True)

print('\n')
print('------------------------------------------')
print('Configuring conda environment')
print('------------------------------------------')
load_scripts = glob.glob('load_dev_compass*.sh')
if len(load_scripts) > 0:
    configure_compass = input('load_dev_compass script exists, run configure_compass_env.py again?: (y/n) ')
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

print('\n')
print('------------------------------------------')
print('Compile mpas-ocean')
print('------------------------------------------')
os.chdir('E3SM-Project/components/mpas-ocean')
if os.path.exists('ocean_model'):
    build = input('ocean_model executable exists, re-compile?: (y/n) ')
else:
    build = 'y'

if build == 'y':
    subprocess.check_call(f'source ../../../{load_script}; make clean; make {make_target}', shell=True)

print('\n')
print('------------------------------------------')
print('Setup testcases')
print('------------------------------------------')
os.chdir('../../../')
command = f'source ./{load_script}' 
ntest = 0
for test in testcases:
    if os.path.exists(f'{workdir}/{test}'):
        setup = input(f'Test {test} already exists, setup again?: (y/n)')
    else:
        setup = 'y'
    if setup == 'y':
      ntest = ntest + 1
      command = command + f'; compass setup -t {test} -w {workdir}'
if ntest > 1:
    subprocess.check_call(command, shell=True)

print('\n')
print('------------------------------------------')
print('Run testcases')
print('------------------------------------------')
if run:
    dependency = ''
    for test in testcases:
            os.chdir(f'{workdir}/{test}')
            output = subprocess.check_output(f'sbatch {dependency} compass_job_script.sh', shell=True)
            print(output) 
            jobid = output.split()[-1].decode('utf-8')
            dependency = f'--dependency=afterok:{jobid}'
    


