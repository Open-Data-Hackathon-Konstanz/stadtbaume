#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Tree detect
-----------

Detect trees on ortho images

"""

import sys
import rasterio
import logging
import argparse
import geopy.distance
from pathlib import Path
from typing import NoReturn
from deepforest import main
from deepforest.utilities import annotations_to_shapefile


def tree_detect(
    args: argparse.Namespace,
    logger: logging.Logger
) -> NoReturn:
    """
    Detect trees on ortho images

    :return: NoReturn
    """

    logger.info(f"Starting detecting trees with arguments {args}")

    # model
    logger.info(f"Starting loading model")
    model = main.deepforest()
    model.use_release()

    # predict trees
    logger.info(f"Starting predicting trees")
    trees = model.predict_tile(
        raster_path=args.raster_path,
        patch_size=args.patch_size,
        patch_overlap=args.patch_overlap,
        use_soft_nms=args.use_soft_nms,
        sigma=0.01,
        thresh=0.1,
        return_plot=False
    )

    # transform to coordinates
    logger.info(f"Starting transforming coordinates")
    r = rasterio.open(args.raster_path)
    transform = r.transform
    crs = r.crs
    trees = annotations_to_shapefile(trees, transform=transform, crs=crs)
    trees["xmin_coord"] = trees["geometry"].bounds.minx
    trees["xmax_coord"] = trees["geometry"].bounds.maxx
    trees["ymin_coord"] = trees["geometry"].bounds.miny
    trees["ymax_coord"] = trees["geometry"].bounds.maxy

    # compute centroids
    logger.info(f"Starting computing centroids")
    trees["xcenter_coord"] = trees["geometry"].centroid.x
    trees["ycenter_coord"] = trees["geometry"].centroid.y

    # compute diameter
    trees["diameter"] = trees.apply(lambda tree: (geopy.distance.distance((tree["xmin_coord"], tree["ymin_coord"]), (tree["xmax_coord"], tree["ymin_coord"])).m + geopy.distance.distance((tree["xmin_coord"], tree["ymin_coord"]), (tree["xmin_coord"], tree["ymax_coord"])).m) / 2, axis=1)

    # outputs
    trees = trees.astype({"xmin": int, "ymin": int, "xmax": int, "ymax": int})
    columns = ["xmin", "ymin", "xmax", "ymax", "xmin_coord", "ymin_coord", "xmax_coord", "ymax_coord", "xcenter_coord", "ycenter_coord", "diameter", "score"]
    trees.to_csv(args.outputs, columns=columns, index=True, float_format="%.8f")

    logger.info("Finished detecting trees")

    return


def get_logger():
    # logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # formatter
    formatter = logging.Formatter(fmt="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")

    # handler
    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def get_parser():
    parser = argparse.ArgumentParser(description="Predict protest from segments")
    parser.add_argument(
        "--raster-path",
        type=Path,
        help="Path to raster"
    )
    parser.add_argument(
        "--patch-size",
        type=int,
        default=500,
        help="Patch size for tiles (default: 500)"
    )
    parser.add_argument(
        "--patch-overlap",
        type=float,
        default=0.3,
        help="Patch overlap for tiles (default: 0.3)"
    )
    parser.add_argument(
        "--use-soft-nms",
        type=bool,
        default=True,
        help="Use Soft NMS (default: False)"
    )
    parser.add_argument(
        "--outputs",
        type=Path,
        help="Path to outputs"
    )

    return parser


if __name__ == "__main__":
    # logger
    logger = get_logger()

    # args
    args = get_parser().parse_args()

    # tree detect
    tree_detect(args=args, logger=logger)
