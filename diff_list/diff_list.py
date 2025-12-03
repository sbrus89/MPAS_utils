# Program to check NML diffs against expected set


# Copy/paste warnings into warnings.txt
f = open('warnings.txt')
warnings = f.read().split('CMake Warning:')

# List of expected extra NLM variables  
extra_variables = ['wav_atm_coup', 'wav_ice_coup', 'wav2atm_smapname', 'wav2atm_smaptype', 'wav2ocn_fmapname', 'wav2ocn_fmaptype', 'config_momentum_use_active_wave']

# TODO: handle removed variables:
removed_variables = []

ndiffs = 0
tests = []
for warning in warnings:

    warning_sp = warning.splitlines()

    # Find name of test and extra variables
    variables = []
    name = ''
    for line in warning_sp:
        if line.find('found extra variable:') >= 0:
           variables.append(line.split(': ')[1].strip("'"))
        if line.find('NML DIFF:') >= 0:
           name = line.split(' ')[0]

    # skip to next warning if no variables found
    if variables == []:
        continue

    # check if found variables are in expected list
    if set(variables).issubset(extra_variables):
        tests.append(name)
        ndiffs = ndiffs + 1
    else:
        print(f"test: {name} diffs not a subset of expected diffs")

# Print results
for test in tests:
    print(test)
print(ndiffs)
    
