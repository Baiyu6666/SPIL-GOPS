#  Copyright (c). All Rights Reserved.
#  General Optimal control Problem Solver (GOPS)
#  Intelligent Driving Lab(iDLab), Tsinghua University
#
#  Creator: Yang GUAN
#  Description: Create sampler
import ray
import importlib


def create_sampler(**kwargs):
    sampler_file_name = kwargs['sampler_name'].lower()
    trainer = kwargs['trainer']
    try:
        module = importlib.import_module('modules.trainer.sampler.'+sampler_file_name)
    except NotImplementedError:
        raise NotImplementedError('This sampler does not exist')
    sampler_name = formatter(sampler_file_name)

    if hasattr(module, sampler_name):  #
        sampler_cls = getattr(module, sampler_name)
        if trainer == 'off_serial_trainer' or trainer == 'on_serial_trainer':
            sampler = sampler_cls(**kwargs)
        elif trainer == 'off_async_trainer' or trainer == 'on_sync_trainer':
            sampler = [ray.remote(num_cpus=1)(sampler_cls).remote(**kwargs) for _ in range(kwargs['num_samplers'])]
        else:
            raise NotImplementedError("This trainer is not properly defined")
    else:
        raise NotImplementedError("This sampler is not properly defined")

    print("Create sampler successfully!")
    return sampler


def formatter(src: str, firstUpper: bool = True):
    arr = src.split('_')
    res = ''
    for i in arr:
        res = res + i[0].upper() + i[1:]

    if not firstUpper:
        res = res[0].lower() + res[1:]
    return res
