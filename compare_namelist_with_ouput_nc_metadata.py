import netCDF4
import numpy as np
import argparse


def nc_val_to_nml(value_nc):
    """Convert a netCDF attribute value to Fortran namelist format."""
    true_list  = ['YES', 'yes', 'true',  '.true.' ]
    false_list = ['NO',  'no',  'false', '.false.']
    if isinstance(value_nc, str):
        if value_nc in true_list:
            return '.true.'
        elif value_nc in false_list:
            return '.false.'
        else:
            return f"'{value_nc}'"
    elif isinstance(value_nc, np.bool_):
        return '.true.' if value_nc else '.false.'
    elif isinstance(value_nc, (np.integer, int)):
        return str(int(value_nc))
    elif isinstance(value_nc, (np.floating, float)):
        return '{:.6g}'.format(float(value_nc))
    else:
        return f"'{value_nc}'"


def compare_values(value_nml, value_nc):
    """Compare a namelist value string to a netCDF attribute value."""
    true_list  = ['.true.',  'true',  'YES', 'yes']
    false_list = ['.false.', 'false', 'NO',  'no' ]

    value_nc_str = str(value_nc)

    # Boolean comparison (don't fall through to float)
    if value_nml in true_list or value_nml in false_list:
        if value_nml in true_list and value_nc_str in true_list:
            return True
        if value_nml in false_list and value_nc_str in false_list:
            return True
        return False

    # Float comparison with tolerance to absorb float32 round-off
    try:
        return np.isclose(np.float64(value_nml), np.float64(value_nc), rtol=1e-5)
    except (ValueError, TypeError):
        pass

    # String comparison
    return value_nml == value_nc_str


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Compare an MPAS Fortran namelist against netCDF output metadata.')
    parser.add_argument('--namelist-file', dest='namelist_file', type=str,
                        required=True, help='Path to MPAS namelist file')
    parser.add_argument('--output-nc', dest='output_nc', type=str,
                        required=True, help='Path to MPAS output netCDF file')
    parser.add_argument('--write-namelist', dest='write_namelist', type=str,
                        default=None, metavar='PATH',
                        help='Write a corrected namelist with values from the netCDF file')
    args = parser.parse_args()

    # Parse namelist file, preserving section structure
    raw_lines = open(args.namelist_file).readlines()
    current_section = None
    entries = []  # list of (line_index, section, name, value_nml) or None for non-config lines

    for i, line in enumerate(raw_lines):
        stripped = line.strip()
        if stripped.startswith('&'):
            current_section = stripped[1:]
        if '=' in stripped:
            name = stripped.split('=')[0].strip()
            value_nml = stripped.split('=', 1)[-1].strip().rstrip(',').replace("'", "")
            entries.append((i, current_section, name, value_nml))

    # Open MPAS netCDF output file
    out_nc = netCDF4.Dataset(args.output_nc)

    n_same    = 0
    n_diff    = 0
    n_missing = 0
    diffs = []

    for i, section, name, value_nml in entries:

        try:
            value_nc = out_nc.getncattr(name)
        except AttributeError:
            n_missing += 1
            print(f'[missing in NC] {name}  (section: {section})')
            continue

        if compare_values(value_nml, value_nc):
            n_same += 1
        else:
            n_diff += 1
            diffs.append((section, name, value_nml, value_nc))

    for section, name, value_nml, value_nc in diffs:
        print(f'[{section}] {name}')
        print(f'   namelist_file: {value_nml}')
        print(f'   output_nc:     {value_nc}')

    print()
    print(f'Summary: {n_same} matching, {n_diff} different, {n_missing} missing from NC')

    # Write corrected namelist
    if args.write_namelist:
        config_lookup = {name: (i, value_nml) for i, section, name, value_nml in entries}
        out_lines = list(raw_lines)
        for i, section, name, value_nml in entries:
            try:
                value_nc = out_nc.getncattr(name)
            except AttributeError:
                continue
            # Only substitute if values genuinely differ; preserve original formatting otherwise
            if compare_values(value_nml, value_nc):
                continue
            nc_str = nc_val_to_nml(value_nc)
            indent = raw_lines[i][:len(raw_lines[i]) - len(raw_lines[i].lstrip())]
            out_lines[i] = f'{indent}{name} = {nc_str}\n'

        with open(args.write_namelist, 'w') as f:
            f.writelines(out_lines)
        print(f'Corrected namelist written to: {args.write_namelist}')
