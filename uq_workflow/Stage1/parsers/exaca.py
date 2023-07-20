#!/usr/bin/python

import os
from shutil import copytree, ignore_patterns
import numpy as np

#------------------------------------------------------------------------------#
# parser for exaca inputs, assuming ":" delimited
def set_value(filename, keyword, value, enclose_quotes, append_comma) :
    keyword = '"' + keyword + '"'
    lines = open(filename, 'r').readlines()
    for i, line in enumerate(lines) :
        if keyword in line :
            old = line.strip().split(':')[-1].replace(' ','')
            strval = str(value)
            if enclose_quotes :
                strval = '"' + strval + '"'
            if append_comma :
                strval = strval + ','
            lines[i] = line.replace(old, strval)
    with open(filename, 'w') as f :
        for line in lines :
            f.write(str(line))

#------------------------------------------------------------------------------#
# parser for exaca temperature input
def set_temperature(filename, path) :
    lines = open(filename, 'r').readlines()
    for i, line in enumerate(lines) :
        if "TemperatureFiles" in line :
            odd_path = os.path.join(path, "odd.csv")
            even_path = os.path.join(path, "even.csv");
            paths = '["' + odd_path + '","' + even_path + '"]'
            old = line.strip().split(':')[-1].replace(' ','')
            lines[i] = line.replace(old, paths)
    with open(filename, 'w') as f :
        for line in lines :
            f.write(str(line))

#------------------------------------------------------------------------------#
# create exaca case directories
def create_cases(data) :
    for c, case in enumerate(data.cases) :
        source = os.path.join(data.templatePath, "exaca")
        target = os.path.join(data.casePath, "exaca", case)

        ignore_files = ['IN625.json', 'GrainOrientation*']

        copytree(source, target, ignore=ignore_patterns(*ignore_files))

        # update the input parameter file for each case
        parameters = np.array(data.parameters[c])[data.indices[1]]
        variables = [x["variable"] for x in data.exaca["inputs"]]

        for i, x in enumerate(parameters) :
            append_comma = True
            if variables[i] == "StDev":
               append_comma = False
            set_value(
                os.path.join(target, "inputs.json"),
                variables[i],
                x, False, append_comma)


            dependent = data.exaca["inputs"][i].get("dependent")
            if (dependent) :
                append_comma = True
                set_value(
                    os.path.join(target, "inputs.json"),
                    dependent["variable"],
                    dependent["scale"]*x, False, append_comma)

        # update file paths in inputs.txt for target case
        set_value(
            os.path.join(target, "inputs.json"),
            "PathToOutput",
            os.path.join(data.casePath, "exaca", case+"/"), True, True)

        set_value(
            os.path.join(target, "inputs.json"),
            "OutputFile",
            case, True, True)

        set_value(
            os.path.join(target, "inputs.json"),
            "MaterialFileName",
            os.path.join(source, "Inconel625.json"), True, True)

        set_value(
            os.path.join(target, "inputs.json"),
            "GrainOrientationFile",
            os.path.join(source, "GrainOrientationVectors_1e6.csv"), True, True)

        # specify the paths to the openfoam temperature data
        set_temperature(
           os.path.join(target, "inputs.json"),
           os.path.join(data.casePath, "openfoam", case.split(".")[0]))
#------------------------------------------------------------------------------#
