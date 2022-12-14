#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Ortho images download
---------------------

Download ortho images as slippy map

Source: https://github.com/GastonZalba/wmts-downloader

"""

import os
import time
import math
import shutil
import tempfile
import argparse
import traceback
from owslib.wmts import WebMapTileService


tmp_folder = f'{tempfile.gettempdir()}/wmts-downloader'
output_folder = 'output'

zoom = 15
format = 'image/png'
url = ''
proj = 'EPSG:3857'
limit_requests = 0
bbox = None

sleep = 0  # sleep time between request

parser = argparse.ArgumentParser(
    description='Script to download images from a WMTS service')
parser.add_argument('url', type=str, metavar='WMTS server url',
                    help='Server url (default: %(default)s)')
parser.add_argument('--username', type=str, metavar='Username', required=True,
                    help='Username (default: %(default)s)')
parser.add_argument('--password', type=str, metavar='Password', required=True,
                    help='Password (default: %(default)s)')
parser.add_argument('--layer', type=str, metavar='Layer name', required=True,
                    help='Layer name (default: %(default)s)')
parser.add_argument('--format', type=str, metavar='Image format', default=format,
                    help='Image format supported by the geoserver (default: %(default)s)')
parser.add_argument('--zoom', type=int, metavar='Zoom level', default=zoom,
                    help='Zoom level. Higher number is more detail, and more images (default: %(default)s)')
parser.add_argument('--proj', type=str, metavar='EPSG projection code', default=proj,
                    help='EPSG projection code existing in the geoserver (default: %(default)s)')
parser.add_argument('--output', type=str, metavar='Output folder',
                    default=output_folder,
                    help='Folder path to save the images (default: %(default)s)')
parser.add_argument('--limit', type=int, metavar='Limit requests number',
                    default=limit_requests,
                    help='Limit the number of requests to avoid overloading the server (default: %(default)s)')
parser.add_argument('--removeold', action='store_true',
                    help='Remove already downloaded files (default: %(default)s)')
parser.add_argument('--sleep', type=float, metavar='Sleep time', default=sleep,
                    help='Sleep time (in seconds) betweeen each reques to avoid overloading the server (default: %(default)s)')
parser.add_argument('--bbox', type=str, metavar='Bounding Box', nargs='+', default=bbox,
                    help='Bounding Box of interest to filter the requests. Separate each value with a space (default: %(default)s)')

args = parser.parse_args()


def init():
    global output_folder

    try:

        print('--> PROCESS STARTED <--')

        print('\t')

        # check if output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if not os.path.exists(tmp_folder):
            os.makedirs(tmp_folder)

        url = args.url
        username = args.username
        password = args.password
        format = args.format
        zoom = int(args.zoom)
        proj = args.proj
        layer_id = args.layer
        output_folder = args.output
        limit_requests = args.limit
        remove_old = args.removeold
        sleep = args.sleep
        bbox = args.bbox

        download_count = 1
        skip_count = 0

        print(f'Connecting to server: {url}')

        try:
            wmts = WebMapTileService(url, username=username, password=password)
        except Exception as error:
            print(f"-> Can't connect to server")
            print(f'--> PROCESS WAS ABORTED WITH ERRORS <--')
            return

        print(f'-> Connection successful')
        print(f'-> Title: {wmts.identification.title}')
        print(f'-> Access constraints: {wmts.identification.accessconstraints}')

        contents = wmts.contents

        print('\t')

        for layer in wmts.contents:
            layer = contents[layer]

            if layer.id == layer_id:

                print(f'-> Layer {layer_id} found')

                title = layer.title
                abstract = layer.abstract
                extent = layer.boundingBoxWGS84
                formats = layer.formats

                print(f'--> Title: {title}')
                print(f'--> Abstract: {abstract}')
                print(f'--> Bounding Box WGS84: {extent}')
                print(f'--> Available formats: {formats}')

                tile_matrixs_links = layer.tilematrixsetlinks

                print(f'--> Available tile matrix sets: {layer._tilematrixsets}')

                for tile_matrix_set in tile_matrixs_links:

                    if tile_matrix_set == proj:

                        tile_matrix_link = tile_matrixs_links[tile_matrix_set]

                        tile_matrix = wmts.tilematrixsets[tile_matrix_set].tilematrix

                        for tml in tile_matrix:

                            z = int(tml.split(":")[-1])

                            if z == zoom:
                                limit = tml

                        matrix_limits = tile_matrix_link.tilematrixlimits[limit]

                        # important
                        matrix = tile_matrix[limit]

                        min_row = matrix_limits.mintilerow
                        max_row = matrix_limits.maxtilerow

                        min_col = matrix_limits.mintilecol
                        max_col = matrix_limits.maxtilecol

                        print(min_col, max_col, min_row, max_row)

                        # check if output folder exists
                        output_folder = f'{output_folder}/{layer_id}/{proj.replace(":", "-")}/{zoom}'

                        if remove_old:
                            if os.path.exists(output_folder):
                                print('Removing old files...')
                                shutil.rmtree(output_folder)

                        # create folder if not exists
                        if not os.path.exists(output_folder):
                            os.makedirs(output_folder)

                        print('\t')
                        print('Downloading images...')

                        if bbox:
                            (f_min_col, f_max_col, f_min_row,
                             f_max_row) = filter_row_cols_by_bbox(matrix, bbox)

                            print(f_min_col, f_max_col, f_min_row, f_max_row)

                            # clamp values
                            min_col = f_min_col if f_min_col >= min_col else min_col
                            max_col = f_max_col if f_max_col <= max_col else max_col
                            min_row = f_min_row if f_min_row >= min_row else min_row
                            max_row = f_max_row if f_max_row <= max_row else max_row

                        print(min_col, max_col, min_row, max_row)
                        print((max_row-min_row)*(max_col-min_col), " tiles")

                        for row in range(min_row, max_row):

                            for col in range(min_col, max_col):

                                extension = format.split("/")[-1]
                                #file_name = f'{layer_id}_{proj.replace(":", "-")}_row-{row}_col-{col}_zoom-{zoom}'
                                file_name = f'{col}/{row}'
                                if not os.path.exists(f"{output_folder}/{col}"):
                                    os.makedirs(f"{output_folder}/{col}")
                                # skip already downloaded files
                                if tile_already_exists(file_name, extension):
                                    print(
                                        f'--> Skipped existing tile: Column {col} - Row {row} - Zoom {zoom}')
                                    skip_count += 1
                                    continue

                                print(
                                    f'--> Downloading tile ({download_count}): Column {col} - Row {row} - Zoom {zoom}')

                                img = wmts.gettile(
                                    url,
                                    layer=layer_id,
                                    tilematrixset=tile_matrix_set,
                                    tilematrix=limit,
                                    row=row,
                                    column=col,
                                    format=format
                                )

                                #write_world_file(file_name, extension, col, row, matrix)

                                write_image(file_name, extension, img)

                                if limit_requests:
                                    if download_count >= limit_requests:
                                        break

                                download_count += 1

                                if sleep:
                                    time.sleep(sleep)

                            else:
                                continue  # only executed if the inner loop did NOT break
                            break  # only executed if the inner loop DID break

        if os.path.exists(tmp_folder):
            print(f'-> Removing tmp files...')
            shutil.rmtree(tmp_folder)

        print('\t')
        print('--> PROCESS WAS COMPLETED <--')
        print('------------------------------')
        print(f'-> Layer: {layer_id}')
        print(f'-> Format: {format}')
        print(f'-> Projection: {proj}')
        print(f'-> Zoom: {zoom}')
        print('------------------------------')

        if skip_count:
            print(f'-> Skipped images: {skip_count}')

        if download_count:
            print(f'-> Downloaded files: {download_count}')
        else:
            print(f'-> No files downloaded')

        print('------------------------------')

        total_tiles = (max_row - min_row) * (max_col - min_col)

        print(f'-> Total tiles in layer: {total_tiles}')
        print(f'-> Tiles remaining: {total_tiles - (skip_count + download_count)}')

        print('------------------------------')

    except Exception as error:
        print(f'{error}')
        print(traceback.format_exc())


def filter_row_cols_by_bbox(matrix, bbox):
    a = matrix.scaledenominator * 0.00028
    e = matrix.scaledenominator * -0.00028

    column_orig = math.floor(
        (float(bbox[0]) - matrix.topleftcorner[0]) / (a * matrix.tilewidth))
    row_orig = math.floor(
        (float(bbox[1]) - matrix.topleftcorner[1]) / (e * matrix.tilewidth))

    column_dest = math.floor(
        (float(bbox[2]) - matrix.topleftcorner[0]) / (a * matrix.tilewidth))
    row_dest = math.floor(
        (float(bbox[3]) - matrix.topleftcorner[1]) / (e * matrix.tilewidth))

    if (column_orig > column_dest):
        t = column_orig
        column_orig = column_dest
        column_dest = t

    if (row_orig > row_dest):
        t = row_orig
        row_orig = row_dest
        row_dest = t

    column_dest += 1
    row_dest += 1

    return (column_orig, column_dest, row_orig, row_dest)


def tile_already_exists(file_name, extension):
    file_path = f'{output_folder}/{file_name}.{extension}'
    return os.path.exists(file_path)


def write_image(file_name, extension, img):
    '''
    Writes images
    '''
    file_path = f'{output_folder}/{file_name}.{extension}'

    out = open(file_path, 'wb')
    out.write(img.read())
    out.close()


init()
