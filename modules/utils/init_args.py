import copy
import datetime
import json
import os
import torch
import warnings

from modules.utils.utils import change_type


def init_args(env, **args):
    if args['enable_cuda']:
        if torch.cuda.is_available():
            args['use_gpu'] = True
        else:
            warning_msg = 'cuda is not available, use CPU instead'
            warnings.warn(warning_msg)
            args['use_gpu'] = False
    else:
        args['use_gpu'] = False

    if len(env.observation_space.shape) == 1:
        args['obsv_dim'] = env.observation_space.shape[0]
    else:
        args['obsv_dim'] = env.observation_space.shape

    if args['action_type'] == 'continu':  # get the dimension of continuous action or the num of discrete action
        args['action_dim'] = env.action_space.shape[0] if len(env.action_space.shape) == 1 else env.action_space.shape
        args['action_high_limit'] = env.action_space.high
        args['action_low_limit'] = env.action_space.low
    else:
        args['action_num'] = env.action_space.n
        args['noise_params']['action_num'] = args['action_num']

    if hasattr(env, 'constraint_dim'):  # get the dimension of constrain
        args['constraint_dim'] = env.constraint_dim

    # Create save arguments
    if args['save_folder'] is None:
        dir_path = os.path.dirname(__file__)
        dir_path = os.path.dirname(dir_path)
        dir_path = os.path.dirname(dir_path)
        args['save_folder'] = os.path.join(dir_path+'/results/',
                                           args['algorithm'],
                                           datetime.datetime.now().strftime("%m%d-%H%M%S"))
    os.makedirs(args['save_folder'], exist_ok=True)
    os.makedirs(args['save_folder'] + '/apprfunc', exist_ok=True)
    os.makedirs(args['save_folder'] + '/evaluator', exist_ok=True)

    with open(args['save_folder'] + '/config.json', 'w', encoding='utf-8') as f:
        json.dump(change_type(copy.deepcopy(args)), f, ensure_ascii=False, indent=4)
    return args
