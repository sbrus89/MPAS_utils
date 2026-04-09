import argparse
import glob
import os
import re

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize


def get_block_id(filepath):
    """Extract block number from filename like output_debug_block_653.nc."""
    match = re.search(r'_(\d+)\.nc$', os.path.basename(filepath))
    return int(match.group(1)) if match else None


def read_block_coords(filepath):
    """Read cell and vertex coordinates from an MPAS debug block file."""
    ds = xr.open_dataset(filepath)

    lon_cell = np.degrees(ds['lonCell'].values)
    lat_cell = np.degrees(ds['latCell'].values)
    lon_cell[lon_cell > 180] -= 360

    lon_vertex = np.degrees(ds['lonVertex'].values)
    lat_vertex = np.degrees(ds['latVertex'].values)
    lon_vertex[lon_vertex > 180] -= 360

    vertices_on_cell = ds['verticesOnCell'].values - 1
    n_edges_on_cell = ds['nEdgesOnCell'].values
    bottom_depth = ds['bottomDepth'].values

    ds.close()

    return dict(lon_cell=lon_cell, lat_cell=lat_cell,
                lon_vertex=lon_vertex, lat_vertex=lat_vertex,
                vertices_on_cell=vertices_on_cell,
                n_edges_on_cell=n_edges_on_cell,
                bottom_depth=bottom_depth)


def build_cell_polygons(block):
    """Build polygon vertex arrays and bottomDepth values from block data."""
    patches = []
    depths = []
    for i in range(len(block['n_edges_on_cell'])):
        n = block['n_edges_on_cell'][i]
        vidx = block['vertices_on_cell'][i, :n]
        lons = block['lon_vertex'][vidx]
        lats = block['lat_vertex'][vidx]

        # Skip cells that wrap across the date line
        if np.ptp(lons) > 180:
            continue

        patches.append(np.column_stack([lons, lats]))
        depths.append(block['bottom_depth'][i])

    return patches, np.array(depths)


def plot_global_overview(blocks, output):
    """Plot a global map with labeled bounding-box regions for each block."""
    colors = mpl.colormaps['Dark2'].colors

    fig = plt.figure(figsize=(16, 8))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
    ax.set_global()
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightskyblue', alpha=0.3)

    for i, (block_id, block) in enumerate(sorted(blocks.items())):
        lon = block['lon_cell']
        lat = block['lat_cell']
        lon_min, lon_max = lon.min(), lon.max()
        lat_min, lat_max = lat.min(), lat.max()

        color = colors[i % len(colors)]

        # Bounding box
        box_lons = [lon_min, lon_max, lon_max, lon_min, lon_min]
        box_lats = [lat_min, lat_min, lat_max, lat_max, lat_min]
        ax.plot(box_lons, box_lats, color=color, linewidth=1.5,
                transform=ccrs.PlateCarree())
        ax.fill(box_lons, box_lats, color=color, alpha=0.2,
                transform=ccrs.PlateCarree())

        # Label at center of bounding box
        lon_center = 0.5 * (lon_min + lon_max)
        lat_center = 0.5 * (lat_min + lat_max)
        ax.text(lon_center, lat_center, str(block_id),
                transform=ccrs.PlateCarree(),
                fontsize=7, fontweight='bold', color=color,
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                          edgecolor=color, alpha=0.8))

    ax.set_title(f'Block stats regions ({len(blocks)} blocks)')
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                      alpha=0.25, linestyle='--')
    fig.savefig(output, bbox_inches='tight', dpi=150)
    print(f'Saved {output}')


def plot_block_detail(block_id, block, output):
    """Plot detailed cell polygons colored by bottomDepth for a single block."""
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.LAKES)

    patches, depths = build_cell_polygons(block)

    norm = Normalize(vmin=depths.min(), vmax=depths.max())
    collection = PolyCollection(patches, array=depths, cmap='viridis',
                                norm=norm, edgecolors='face', linewidths=0.1,
                                transform=ccrs.PlateCarree())
    ax.add_collection(collection)
    ax.autoscale_view()

    cbar = fig.colorbar(collection, ax=ax, orientation='vertical',
                        shrink=0.7, pad=0.02)
    cbar.set_label('Bottom depth (m)')

    ax.set_title(f'Block {block_id}')
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                      linewidth=1, color='gray', alpha=0.25, linestyle='--')
    fig.savefig(output, bbox_inches='tight', dpi=150)
    plt.close(fig)
    print(f'Saved {output}')


def plot_block_regions(directory, output, pattern='output_debug_block_*.nc'):

    files = sorted(glob.glob(f'{directory}/{pattern}'))
    if not files:
        print(f'No files found matching {directory}/{pattern}')
        return

    print(f'Found {len(files)} block file(s)')

    # Read all blocks
    blocks = {}
    for filepath in files:
        block_id = get_block_id(filepath)
        if block_id is None:
            continue
        blocks[block_id] = read_block_coords(filepath)

    # Global overview with labels
    base, ext = os.path.splitext(output)
    overview_output = f'{base}_global{ext}'
    plot_global_overview(blocks, overview_output)

    # Detailed polygon plot per block
    base, ext = os.path.splitext(output)
    for block_id, block in sorted(blocks.items()):
        detail_output = f'{base}_block_{block_id}{ext}'
        plot_block_detail(block_id, block, detail_output)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Plot MPAS-Ocean debug block regions on a map')
    parser.add_argument('directory',
                        help='Directory containing output_debug_block_*.nc files')
    parser.add_argument('-o', '--output', default='block_stats.png',
                        help='Output figure filename (default: block_stats.png)')
    parser.add_argument('-p', '--pattern', default='output_debug_block_*.nc',
                        help='Glob pattern for block files '
                             '(default: output_debug_block_*.nc)')
    args = parser.parse_args()

    plot_block_regions(args.directory, args.output, args.pattern)
