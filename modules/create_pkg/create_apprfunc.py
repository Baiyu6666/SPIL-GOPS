#  Copyright (c). All Rights Reserved.
#  General Optimal control Problem Solver (GOPS)
#  Intelligent Driving Lab(iDLab), Tsinghua University
#
#  Creator: Hao SUN
#  Description: Create apprfunc
"""

"""

#  Update Date: 2020-12-26, Hao SUN:  add create_apprfunc function


def create_apprfunc(**kwargs):
    apprfunc_name = kwargs['apprfunc']
    apprfunc_file_name = apprfunc_name.lower()
    try:
        file = __import__(apprfunc_file_name)
    except NotImplementedError:
        raise NotImplementedError('This apprfunc does not exist')

    #name = kwargs['name'].upper()

    name = formatter( kwargs['name'])
    # print(name)
    # print(kwargs)

    if hasattr(file,name): #
        apprfunc_cls = getattr(file, name)
        apprfunc = apprfunc_cls(**kwargs)
    else:
        raise NotImplementedError("This apprfunc is not properly defined")

    # print("--Initialize appr func: " + name + "...")
    return apprfunc



def formatter(src: str, firstUpper: bool = True):
    arr = src.split('_')
    res = ''
    for i in arr:
        res = res + i[0].upper() + i[1:]

    if not firstUpper:
        res = res[0].lower() + res[1:]
    return res