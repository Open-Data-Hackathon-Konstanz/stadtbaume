#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Ortho images convert
--------------------

Convert ortho images from slippy map to tiff

Source: https://github.com/jimutt/tiles-to-tiff

"""

import argparse
import urllib.request
import os
import glob
import shutil
from osgeo import gdal
from math import log, tan, radians, cos, pi, floor, degrees, atan, sinh

temp_dir = os.path.join(os.path.dirname(__file__), 'temp')


def sec(x):
    return(1/cos(x))


def latlon_to_xyz(lat, lon, z):
    tile_count = pow(2, z)
    x = (lon + 180) / 360
    y = (1 - log(tan(radians(lat)) + sec(radians(lat))) / pi) / 2
    return(tile_count*x, tile_count*y)


def bbox_to_xyz(lon_min, lon_max, lat_min, lat_max, z):
    x_min, y_max = latlon_to_xyz(lat_min, lon_min, z)
    x_max, y_min = latlon_to_xyz(lat_max, lon_max, z)
    return(floor(x_min), floor(x_max),
           floor(y_min), floor(y_max))


def mercatorToLat(mercatorY):
    return(degrees(atan(sinh(mercatorY))))


def y_to_lat_edges(y, z):
    tile_count = pow(2, z)
    unit = 1 / tile_count
    relative_y1 = y * unit
    relative_y2 = relative_y1 + unit
    lat1 = mercatorToLat(pi * (1 - 2 * relative_y1))
    lat2 = mercatorToLat(pi * (1 - 2 * relative_y2))
    return(lat1, lat2)


def x_to_lon_edges(x, z):
    tile_count = pow(2, z)
    unit = 360 / tile_count
    lon1 = -180 + x * unit
    lon2 = lon1 + unit
    return(lon1, lon2)


def tile_edges(x, y, z):
    lat1, lat2 = y_to_lat_edges(y, z)
    lon1, lon2 = x_to_lon_edges(x, z)
    return[lon1, lat1, lon2, lat2]


def fetch_tile(x, y, z, tile_source):
    url = tile_source.replace(
        "{x}", str(x)).replace(
        "{y}", str(y)).replace(
        "{z}", str(z))

    if not tile_source.startswith("http"):
        return url.replace("file:///", "")

    path = f'{temp_dir}/{x}_{y}_{z}.png'
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) tiles-to-tiff/1.0 (+https://github.com/jimutt/tiles-to-tiff)'
        }
    )
    g = urllib.request.urlopen(req)
    with open(path, 'b+w') as f:
        f.write(g.read())
    return path


def merge_tiles(input_pattern, output_path):
    vrt_path = temp_dir + "/tiles.vrt"
    gdal.BuildVRT(vrt_path, glob.glob(input_pattern))
    gdal.Translate(output_path, vrt_path)


def georeference_raster_tile(x, y, z, path):
    bounds = tile_edges(x, y, z)
    gdal.Translate(os.path.join(temp_dir, f'{temp_dir}/{x}_{y}_{z}.tif'),
                   path,
                   outputSRS='EPSG:4326',
                   outputBounds=bounds,
                   rgbExpand='rgb')

def convert(tile_source, output_dir, bounding_box, zoom):
    lon_min, lat_min, lon_max, lat_max = bounding_box

    # Script start:
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    x_min, x_max, y_min, y_max = bbox_to_xyz(
        lon_min, lon_max, lat_min, lat_max, zoom)

    # TODO: fix issue with wrong determination of x_min, x_max, y_min, y_max
    print(lon_min, lat_min, lon_max, lat_max)
    print(x_min, x_max, y_min, y_max)
    x_min, x_max, y_min, y_max = 14457, 14718, 26460, 26776
    print(x_min, x_max, y_min, y_max)

    print(f"Fetching & georeferencing {(x_max - x_min + 1) * (y_max - y_min + 1)} tiles")

    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            try:
                png_path = fetch_tile(x, y, zoom, tile_source)
                print(f"{x},{y} fetched")
                georeference_raster_tile(x, y, zoom, png_path)
            except OSError:
                print(f"Error, failed to get {x},{y}")
                pass

    print("Resolving and georeferencing of raster tiles complete")

    print("Merging tiles")
    merge_tiles(temp_dir + '/*.tif', output_dir + '/merged.tif')
    print("Merge complete")

    shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser("tiles_to_tiff", "python tiles_to_tiff https://tileserver-url.com/{z}/{x}/{y}.png 21.49147 65.31016 21.5 65.31688 -o output -z 17")
    parser.add_argument("tile_source", type=str, help="Local directory pattern or URL pattern to a slippy maps tile source.", )
    parser.add_argument("lng_min", type=float, help="Min longitude of bounding box")
    parser.add_argument("lat_min", type=float, help="Min latitude of bounding box")
    parser.add_argument("lng_max", type=float, help="Max longitude of bounding box")
    parser.add_argument("lat_max", type=float, help="Max latitude of bounding box")
    parser.add_argument("-z", "--zoom", type=int, help="Tilesource zoom level", default=14)
    parser.add_argument("-o", "--output", type=str, help="Output directory", required=True)

    args = parser.parse_args()

    tile_source = args.tile_source if args.tile_source.startswith("http") else "file:///" + args.tile_source

    convert(tile_source, args.output, [args.lng_min, args.lat_min, args.lng_max, args.lat_max], args.zoom)

main()
