# Filter data from predictions
import os
import numpy as np
import pandas as pd
import rasterio as rio
from deepforest import visualize
from matplotlib import pyplot as plt

# Import Data
fPath =  r"C:\Hackathon Stadtbaeume\Data\DOP_20_C_EPSG_4326_S.csv"
iPath = r"C:\Hackathon Stadtbaeume\Data\DOP_20_C_EPSG_4326_S.tif"


rawData = pd.read_csv(fPath)
label = ['tree']*len(rawData)

header = pd.read_csv(fPath, nrows=1)

# Build Dataframe
df = rawData[["xmin","ymin","xmax","ymax","score"]].copy()
labelDF = pd.DataFrame(label, columns=["label"])
pd.concat((df,labelDF),axis=1)

# Load raster as image
image = rio.open(iPath).read()
image = np.moveaxis(image,0,2) 

# Filters:
#plt.plot(df["xmax"],df["score"],'x')
#plt.show()


# Score
#scoreCond = (df["score"] > 0.01)
#df = df[scoreCond]

# Formfactor
formFactors = np.round(np.linspace(0,0.8,21),2)

xl = df["xmax"]-df["xmin"]
yl = df["ymax"]-df["ymin"]
print(pd.DataFrame.abs((xl/yl)-1))

for fF in formFactors:
    #formCond = ((xl-yl)/xl*yl < fF)
    formCond = (pd.DataFrame.abs((xl/yl)-1) < fF)
    #print(formCond)
    df_filter = df[formCond]

    # Visualisation: 
    #image = image[:,:,::-1]
    image = visualize.plot_predictions(image, df_filter, color=(0, 165, 255), thickness=2)
    plt.imshow(image)#[:,:,::-1]
    plt.savefig(r"C:\Hackathon Stadtbaeume\Results\Formfactor_"+str(fF)+".png",dpi=1000)

#plt.show()
