import subprocess

file1 = 'input.nc'
file2 = 'output.nc'

variables = [ "latCell",
              "lonCell",
              "xCell",
              "yCell",
              "zCell",
              "indexToCellID",
              "latEdge",
              "lonEdge",
              "xEdge",
              "yEdge",
              "zEdge",
              "indexToEdgeID",
              "latVertex",
              "lonVertex",
              "xVertex",
              "yVertex",
              "zVertex",
              "indexToVertexID",
              "meshDensity",
              "cellsOnEdge",
              "nEdgesOnCell",
              "nEdgesOnEdge",
              "edgesOnCell",
              "edgesOnEdge",
              "weightsOnEdge",
              "dvEdge",
              "dcEdge",
              "angleEdge",
              "areaCell",
              "areaTriangle",
              "cellsOnCell",
              "verticesOnCell",
              "verticesOnEdge",
              "edgesOnVertex",
              "cellsOnVertex",
              "kiteAreasOnVertex",
              "fEdge",
              "fVertex",
              "fCell",
              "bottomDepth",
              "maxLevelCell",
              "refBottomDepth" ,
              "restingThickness"]


cmd = 'ncks -A -v '+','.join(variables)+ ' '+file1+' '+file2

print(cmd)
subprocess.call(cmd,shell=True)
