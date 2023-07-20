#!/usr/bin/python

import os
from shutil import copytree, ignore_patterns
from os import symlink
import numpy as np

def set_value(filename, keyword, value, cmpt) :

    if cmpt == "x" : cmpt = 0
    if cmpt == "y" : cmpt = 1
    if cmpt == "z" : cmpt = 2

    lines = open(filename, 'r').readlines()
    for i, line in enumerate(lines) : 
        if keyword in line :
            o = line.replace("(","").replace(")","").replace(";","").split()[1:]
            lines[i] = line.replace(o[cmpt], str(np.round(value,8)))

    with open(filename, 'w') as f : 
        for line in lines :
            f.write(str(line))

#------------------------------------------------------------------------------#
# create openfoam case directories
def create_cases(data) :
    for case in np.unique([case.split(".")[0] for case in data.cases]) :
        source = os.path.join(data.templatePath, "openfoam")
        target = os.path.join(data.casePath, "openfoam", case)

        copytree(source, target, ignore=ignore_patterns("polyMesh", "preMesh"))

        symlink(
            os.path.join(source, "constant", "polyMesh"),
            os.path.join(target, "constant", "polyMesh"))

        parameters = np.array(data.inputs[0][int(case)])
        variables = [x["variable"] for x in data.openfoam["inputs"]]

        for i, x in enumerate(parameters) :
            # can be scalar or vector, so a cmpt must be passed to set_value
            try :
                cmpt = data.openfoam["inputs"][i]["component"]
            except :
                cmpt = "x"

            set_value(
                os.path.join(target, data.openfoam["inputs"][i]["file"]),
                variables[i],
                x,
                cmpt)

#------------------------------------------------------------------------------#
