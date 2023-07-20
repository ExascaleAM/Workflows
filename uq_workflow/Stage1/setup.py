#!/usr/bin/python

import Tasmanian
import numpy as np
import pandas as pd
import os
import json
from parsers.exaca import create_cases as setup_exaca
from parsers.openfoam import create_cases as setup_openfoam

basePath = os.getcwd()

#-----------------------------------------------------------------------------#
# read JSON formatted input file
def readInputs(filename="inputs.json"):
  try:
    with open(filename) as f:
      data = f.read()
      inputs = json.loads(data)
  except:
    raise Exception(f"Error trying to parse inputs from {filename}")
  return inputs

# data manager to track case id and input parameters
# case_id = 'case_openfoam'.'case_exaca'
class Data:
    def __init__(self, openfoam, exaca):
        self.openfoam = openfoam
        self.exaca = exaca
        self.templatePath = os.path.join(basePath, "templates")
        self.casePath = os.path.join(basePath, "cases")
        self.cases = []
        self.parameters = []
        self.nInputs = len(self.openfoam["inputs"]) + len(self.exaca["inputs"])
        self.setIndices()

    def setIndices(self) :
        # list indices: 0 = openfoam, 1 = exaca
        self.indices = 2*[[]]
        self.indices[0] = np.arange(0, len(self.openfoam["inputs"]), 1)
        self.indices[1] = np.arange(len(self.openfoam["inputs"]), self.nInputs, 1)

    def setPoints(self, points):
        # unique sets of inputs: 0 = openfoam, 1 = exaca
        self.inputs  = 2*[[]]
        self.inputs[0] = np.unique(points[:, self.indices[0]], axis=0)
        self.inputs[1] = np.unique(points[:, self.indices[1]], axis=0)

        # create case ids and match to inputs parameters
        for id, point in enumerate(points) :
            i = 0
            for p in self.inputs[0] : 
                if np.allclose(point[self.indices[0]], p) :
                    break
                else :
                    i = i + 1

            j = 0
            for p in self.inputs[1] : 
                if np.allclose(point[self.indices[1]], p) :
                    break
                else : 
                    j = j + 1

            id = str(i)+'.'+str(j)
            self.cases.append(id)

            p = np.concatenate([self.inputs[0][i], self.inputs[1][j]])
            self.parameters.append(p.tolist())

    def to_csv(self, filename):
        v0 = [x["variable"] for x in self.openfoam["inputs"]]
        v1 = [x["variable"] for x in self.exaca["inputs"]]
        variables = v0 + v1
        df = pd.DataFrame(np.round(self.parameters, 8), columns=variables)
        df.insert(0, "caseID", self.cases)
        df.to_csv(filename, index=False)

#-----------------------------------------------------------------------------#
# read inputs and initialize data manager
inputs    = readInputs()
openfoam  = inputs["openfoam"]
exaca     = inputs["exaca"]
tasmanian = inputs["tasmanian"]

# create data manager
data = Data(openfoam, exaca)

# create a uniform grid for initial surrogate construction
nInputs      = data.nInputs
level_limits = nInputs*[tasmanian["iLevel"]]
depth        = sum(level_limits)

grid = Tasmanian.makeLocalPolynomialGrid(
    iDimension=data.nInputs,
    iOutputs=0,
    iDepth=depth,
    iOrder=1,
    sRule="localp",
    liLevelLimits=level_limits)

# set domain transform using data bounds
bounds = np.append(
    np.array([x["bounds"] for x in openfoam["inputs"]]),
    np.array([x["bounds"] for x in exaca["inputs"]]),
    axis=0)

grid.setDomainTransform(bounds)

# set sparse grid points in data manager and write state to csv file
points = grid.getPoints()
data.setPoints(points)
data.to_csv("parameters.csv")

# create case directories
setup_exaca(data)
setup_openfoam(data)
