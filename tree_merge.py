#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Tree merge
-----------

Merge trees from kataster and detection

"""

import pandas as pd
import geopandas as gpd
from shapely import geometry


# load city trees
trees_city = gpd.read_file("data/raw/KN_Baumkataster_2020S.geojson")
trees_city = trees_city.drop(columns=["OBJECTID"])

# create bounding boxes for trees
trees_city["geometry_city"] = trees_city.geometry
trees_city.geometry = trees_city.apply(lambda tree: geometry.box(tree.geometry.x - (tree.kronendurchmesserM/2)*9.041375464338667e-06, tree.geometry.y - (tree.kronendurchmesserM/2)*9.099335504202068e-06, tree.geometry.x + (tree.kronendurchmesserM/2)*9.041375464338667e-06, tree.geometry.y + (tree.kronendurchmesserM/2)*9.099335504202068e-06), axis=1)

# tree detected by us
trees_detected = pd.read_csv("data/processed/DOP_20_C_EPSG_4326.csv")
trees_detected = trees_detected.rename( columns={'Unnamed: 0':'detectId'})
trees_detected = gpd.GeoDataFrame(trees_detected, geometry=gpd.points_from_xy(trees_detected["xcenter_coord"], trees_detected["ycenter_coord"], crs="EPSG:4326"))

# add box as geometry
trees_detected["geometry_detect"] = trees_detected.geometry
trees_detected.geometry = trees_detected.apply(lambda tree: geometry.box(tree.xmin_coord, tree.ymin_coord, tree.xmax_coord, tree.ymax_coord), axis=1)


# merge tiles
trees_detected = trees_detected.loc[(trees_detected.score>=0.00000)&(trees_detected.diameter<=50)]

# tree set 1
trees_1 = gpd.sjoin(trees_city, trees_detected, how="inner", op='intersects')
trees_1 = trees_1.drop_duplicates(subset = ["baumId"], keep="first")
trees_1.geometry = trees_1.geometry_city
trees_1["maintained"] = 1
trees_1["detected"] = 1

# tree set 2
# trees in kataster
trees_2 = trees_city.loc[~trees_city.baumId.isin(trees_1.baumId)]
trees_2.geometry = trees_2.geometry_city
trees_2["maintained"] = 1
trees_2["detected"] = 0

# tree set 3
trees_3 = trees_detected.loc[~trees_detected.detectId.isin(trees_1.detectId)]
trees_3.geometry = trees_3.geometry_detect
trees_3["maintained"] = 0
trees_3["detected"] = 1

trees = pd.concat([trees_1, trees_2, trees_3], ignore_index=True)

trees = trees.rename(columns={"detectId": "detect_id", "xmin": "detect_x_min", "ymin": "detect_y_min",
    "xmax": "detect_x_max", "ymax": "detect_y_max", "xmin_coord": "detect_x_min_coord", "ymin_coord": "detect_y_min_coord",
    "xmax_coord": "detect_x_max_coord", "ymax_coord": "detect_y_max_coord", 'xcenter_coord': "detect_x_center_coord",
    'ycenter_coord': "detect_y_center_coord", "diameter": "detect_diameter", "score": "detect_score"
})

trees = trees.astype({
    "baumId": pd.Int64Dtype(),
    "baumNr": pd.Int64Dtype(),
    "baumart": pd.Int64Dtype(),
    "hoeheM": pd.Int64Dtype(),
    "kronendurchmesserM": pd.Int64Dtype(),
    "stammumfangCM": pd.Int64Dtype(),
    "detect_id": pd.Int64Dtype(),
    "detect_x_min": pd.Int64Dtype(),
    "detect_y_min": pd.Int64Dtype(),
    "detect_x_max": pd.Int64Dtype(),
    "detect_y_max": pd.Int64Dtype()
})

cols = [
    'baumId', 'baumNr', 'baumart', 'hoeheM', 'kronendurchmesserM', 'stammumfangCM',
    'location', 'Name_dt', 'Name_lat', 'Name_Sym', 'detect_id', 'detect_x_min',
       'detect_y_min', 'detect_x_max', 'detect_y_max', 'detect_x_min_coord',
       'detect_y_min_coord', 'detect_x_max_coord', 'detect_y_max_coord',
       'detect_x_center_coord', 'detect_y_center_coord', 'detect_diameter',
       'detect_score', 'maintained', 'detected', "geometry"
]

trees.loc[:, cols].to_file("data/processed/DOP_20_C_EPSG_4326.geojson", driver="GeoJSON", float_format="%.8f")

