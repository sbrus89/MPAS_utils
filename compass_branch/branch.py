import os
import subprocess
import yaml
import glob


####################################################
# Handle input options
####################################################

f = open('branch.config','r')
cfg = yaml.load(f, Loader=yaml.Loader)

# Path to master subtree branch directory
compass_master = cfg['compass_master']

# Name of subtree branch to create
branch_name = cfg['branch_name']

# Remote compass branch to checkout  
remote_branch = cfg['remote_branch']

# Master compass branch to use for local merge
master_branch = cfg['master_branch']

# Path to miniconda installation
miniconda_path = cfg['miniconda_path']

# MPI implementation to use for conda package install
mpi = cfg['mpi']

# Compiler for conda package install
compiler = cfg['compiler']

# Make target for MPAS-O compilation
make_target = cfg['make_target']

# Option for using debug flags for MPAS-O compilation
debug = cfg['debug']

# List of testcases to setup
testcases = cfg['testcases']

# Work directory to use for test case setup
workdir = cfg['workdir']

# Option to update the subtree branch with the remote branch HEAD
update_branch = ''
if 'update_branch' in cfg:
    update_branch = cfg['update_branch']

# Option to perform local merge to master compass branch
local_merge = True
if 'local_merge' in cfg:
    local_merge = cfg['local_merge']

# Option to configure the conda environment
configure_conda = ''
if 'configure_conda' in cfg:
    configure_conda = cfg['configure_conda']

# Option to compile MPAS-O
compile_mpas = ''
if 'compile_mpas' in cfg:
    compile_mpas = cfg['compile_mpas']

# Option to setup list of testcases
setup_testcases = ''
if 'setup_testcases' in cfg:
    setup_testcases = cfg['setup_testcases']

# Option to submit test case jobs
run = ''
if 'run' in cfg:
    run = cfg['run']

# Remote to use for E3SM checkout (optional)
e3sm_remote= ''
if 'e3sm_remote' in cfg:
    e3sm_remote= cfg['e3sm_remote']

# Branch to use for E3SM checkout (optional)
e3sm_branch= ''
if 'e3sm_branch' in cfg:
    e3sm_branch= cfg['e3sm_branch']

# Commit to use for E3SM checkout (optional)
e3sm_commit= ''
if 'e3sm_commit' in cfg:
    e3sm_commit= cfg['e3sm_commit']



####################################################
# Begin setup  
####################################################


# Enter the master branch subtree directory
os.chdir(compass_master)

# Fetch all remote compass branches
#   (It is assumed that the remote for the compass branch
#    that is to be checked out in the next step has been 
#    added previously)
print('\n')
print('------------------------------------------')
print('Fetching remote branches')
print('------------------------------------------')
subprocess.check_call('git fetch --all', shell=True)


# Create a worktree compass branch to be used for testing 
print('\n')
print('------------------------------------------')
print('Creating worktree branch')
print('------------------------------------------')
try:
    subprocess.check_call(f'module load git; git worktree add -b {branch_name} ../{branch_name} {remote_branch}', shell=True)
except:
    pass
os.chdir(f'../{branch_name}')


# Optionally update compass branch if a worktree branch has been previously created
# and the remote branch has newer commits
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


# Optionally rebase remote compass branch onto master 
if local_merge == True:
    print('\n')
    print('------------------------------------------')
    print('Perform local merge')
    print('------------------------------------------')
    
    #subprocess.check_call(f'module load git; git reset --hard {master_branch}', shell=True)
    #subprocess.check_call(f'module load git; git merge --no-ff {remote_branch}', shell=True)
    subprocess.check_call(f'module load git; git rebase {master_branch}', shell=True)


# Configure the conda environment for the worktree branch
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
        subprocess.check_call(f'./conda/configure_compass_env.py --conda {miniconda_path} --mpi {mpi} --compiler {compiler}', shell=True)

load_scripts = glob.glob('load_dev_compass*.sh')
load_script = max(load_scripts, key=os.path.getctime)


# Perform E3SM submodule checkout 
print('\n')
print('------------------------------------------')
print('Compass submodule checkout')
print('------------------------------------------')
subprocess.check_call('module load git; git submodule update --init --recursive', shell=True)
update_e3sm_submodules = False


# Optionally checkout a specific remote E3SM branch to be used in testing
os.chdir('E3SM-Project')
if e3sm_remote != '' and e3sm_branch != '':
  print('\n')
  print('------------------------------------------')
  print('E3SM remote checkout')
  print('------------------------------------------')
  subprocess.check_call(f'module load git; git fetch {e3sm_remote} {e3sm_branch}; git checkout FETCH_HEAD', shell=True)
  update_e3sm_submodules = True

if e3sm_remote != '' and e3sm_branch != '':
  print('\n')
  print('------------------------------------------')
  print('E3SM local merge')
  print('------------------------------------------')
  subprocess.check_call(f'module load git; git fetch --all; git rebase origin/master', shell=True)
  update_e3sm_submodules = True

# Optionally checkout a specific remote E3SM commit
if e3sm_commit != '':
  print('\n')
  print('------------------------------------------')
  print('E3SM commit checkout')
  print('------------------------------------------')
  subprocess.check_call(f'git checkout {e3sm_commit}', shell=True)
  update_e3sm_submodules = True


# Perform E3SM submodule checkout if E3SM commit has been updated
if update_e3sm_submodules:
    print('\n')
    print('------------------------------------------')
    print('E3SM submodule update')
    print('------------------------------------------')
    subprocess.check_call('module load git; git submodule update --init --recursive', shell=True)
os.chdir('../')


# Compile MPAS-Ocean
os.chdir('E3SM-Project/components/mpas-ocean')
if not os.path.exists('ocean_model'):
    compile_mpas = True
if compile_mpas == '' or compile_mpas == True:
    print('\n')
    print('------------------------------------------')
    print('Compile MPAS-Ocean')
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


# Setup specified testcases
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


# Run specified testcases as batch jobs with dependencies
if run:
    print('\n')
    print('------------------------------------------')
    print('Run testcases')
    print('------------------------------------------')
    dependency = ''
    for test in testcases:
            os.chdir(f'{workdir}/{test}')
            output = subprocess.check_output(f'sbatch {dependency} job_script.sh', shell=True)
            print(output) 
            jobid = output.split()[-1].decode('utf-8')
            dependency = f'--dependency=afterok:{jobid}' 
