import glob
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


def find_min_max(value, lines):
    for i in range(len(lines)):
        if lines[i].find(f'Field: {value}') >= 0:
           min_val = float(lines[i + 1].split()[1])
           max_val = float(lines[i + 2].split()[1])
           break 

    bounds = np.degrees([min_val, max_val])
    if value == 'lonCell':
        bounds = bounds[bounds>180] - 360

    return bounds

if __name__ == '__main__':

    colors = mpl.colormaps['Dark2'].colors

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.LAKES)

    files = glob.glob('mpas_ocean_block_stats*')
    for i,file in enumerate(files):
    
        f = open(file)
        lines = f.readlines()
        lon = find_min_max('lonCell', lines)   
        lat = find_min_max('latCell', lines)   

        ax.plot([lon[0], lon[0]], [lat[0], lat[1]], color=colors[i])
        ax.plot([lon[1], lon[1]], [lat[0], lat[1]], color=colors[i])
        ax.plot([lon[0], lon[1]], [lat[0], lat[0]], color=colors[i])
        ax.plot([lon[0], lon[1]], [lat[1], lat[1]], color=colors[i])

    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                      linewidth=1, color='gray', alpha=0.25, linestyle='--')
    fig.savefig('block_stats.png', bbox_inches='tight')
    
