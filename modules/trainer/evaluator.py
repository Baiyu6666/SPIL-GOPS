#  Copyright (c). All Rights Reserved.
#  General Optimal control Problem Solver (GOPS)
#  Intelligent Driving Lab(iDLab), Tsinghua University
#
#  Creator: Yang GUAN
#  Description: Evaluation of trained policy
#
#  Update Date: 2021-05-10, Shengbo LI: renew env para

import datetime
import os

import time

import numpy as np
import torch
from modules.create_pkg.create_env import create_env

from modules.utils.action_distributions import GaussDistribution, DiracDistribution, ValueDiracDistribution, CategoricalDistribution


class Evaluator():

    def __init__(self, **kwargs):
        self.env = create_env(**kwargs)
        alg_name = kwargs['algorithm']
        alg_file_name = alg_name.lower()
        file = __import__(alg_file_name)
        ApproxContainer = getattr(file, 'ApproxContainer')
        self.networks = ApproxContainer(**kwargs)
        self.render = kwargs['is_render']

        self.num_eval_episode = kwargs['num_eval_episode']
        self.action_type = kwargs['action_type']
        self.policy_func_name = kwargs['policy_func_name']
        self.save_folder = kwargs['save_folder']
        self.eval_save = kwargs.get('eval_save', True)

        if self.action_type == 'continu':
            if self.policy_func_name == 'StochaPolicy':
                self.action_distirbution_cls = GaussDistribution
            elif self.policy_func_name == 'DetermPolicy':
                self.action_distirbution_cls = DiracDistribution
        elif self.action_type == 'discret':
            if self.policy_func_name == 'StochaPolicyDis':
                self.action_distirbution_cls = CategoricalDistribution
            elif self.policy_func_name == 'DetermPolicyDis':
                self.action_distirbution_cls = ValueDiracDistribution
        self.print_time = 0
        self.print_iteration = -1

    def load_state_dict(self, state_dict):
        self.networks.load_state_dict(state_dict)

    def run_an_episode(self, iteration, render=True):
        if self.print_iteration != iteration:
            self.print_iteration = iteration
            self.print_time = 0
        else:
            self.print_time += 1
        obs_list = []
        action_list = []
        reward_list = []
        obs = self.env.reset()
        done = 0
        info = {'TimeLimit.truncated': False}
        while not (done or info['TimeLimit.truncated']):
            batch_obs = torch.from_numpy(np.expand_dims(obs, axis=0).astype('float32'))
            logits = self.networks.policy(batch_obs)
            action_distribution = self.action_distirbution_cls(logits)
            action = action_distribution.mode()
            action = action.detach().numpy()[0]
            next_obs, reward, done, info = self.env.step(action)
            obs_list.append(obs)
            action_list.append(action)
            obs = next_obs
            if 'TimeLimit.truncated' not in info.keys():
                info['TimeLimit.truncated'] = False
            # Draw environment animation
            if render:
                self.env.render()
            reward_list.append(reward)
        eval_dict = {'reward_list': reward_list, 'action_list': action_list, 'obs_list': obs_list}
        if self.eval_save:
            np.save(self.save_folder + '/evaluator/iteration{}_episode{}'.format(iteration, self.print_time), eval_dict)
        episode_return = sum(reward_list)
        return episode_return

    def run_n_episodes(self, n, iteration):
        episode_return_list = []

        for _ in range(n):
            episode_return_list.append(self.run_an_episode(iteration, self.render))
        return np.mean(episode_return_list)

    def run_evaluation(self, iteration):
        return self.run_n_episodes(self.num_eval_episode, iteration)

    def render_batch(self):
        self.env.render_init(3)
        with torch.no_grad():
            x = self.env.reset(999)
            c_mul = 1
            for i in range(80):
                u = self.networks.policy(torch.Tensor(x))
                x, r, done, info = self.env.step(u.numpy())
                c = info['constraint']
                c_mul = c_mul * np.where(c > 0, 0, 1)
                self.env.render(3)
                print(u)
            print(c_mul.mean())
        # plt.pause(11)
        # add self.writer: