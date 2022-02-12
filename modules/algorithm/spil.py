#   Copyright (c) 2020 ocp-tools Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Author: Baiyu Peng

#  Comments: ?


__all__ = ['SPIL']

from copy import deepcopy
import torch
import torch.nn as nn
from torch.optim import Adam
import numpy as np
import time
import warnings

from modules.create_pkg.create_apprfunc import create_apprfunc
from modules.create_pkg.create_env_model import create_env_model
from modules.utils.utils import get_apprfunc_dict
from modules.utils.tensorboard_tools import tb_tags
from modules.utils.utils import get_activation_func


def mlp(sizes, activation, output_activation=nn.Identity):
    layers = []
    for j in range(len(sizes) - 1):
        act = activation if j < len(sizes) - 2 else output_activation
        layers += [nn.Linear(sizes[j], sizes[j + 1]), act()]
    return nn.Sequential(*layers)

class Lambda(nn.Module):
    def __init__(self, kwargs):
        super().__init__()
        obs_dim = kwargs['obsv_dim']
        hidden_sizes = kwargs['hidden_sizes']
        constraint_dim = kwargs['constraint_dim']
        self.lamnet = mlp([obs_dim] + list(hidden_sizes) + [constraint_dim],
                     get_activation_func(kwargs['hidden_activation']),
                     get_activation_func(kwargs['output_activation']))

    def forward(self, obs):
        v = self.lamnet(obs)
        return v


class Prob(nn.Module):
    def __init__(self, kwargs):
        super().__init__()
        obs_dim = kwargs['obsv_dim']
        hidden_sizes = kwargs['hidden_sizes']
        constraint_dim = kwargs['constraint_dim']
        self.prob = mlp([obs_dim] + list(hidden_sizes) + [constraint_dim],
                     get_activation_func(kwargs['hidden_activation']),
                     get_activation_func(kwargs['output_activation']))

    def forward(self, obs):
        v = self.prob(obs)*0.5+0.5
        return v


class ApproxContainer(nn.Module):
    def __init__(self, **kwargs):
        super().__init__()
        # self.polyak = 1 - kwargs['tau']
        value_func_type = kwargs['value_func_type']
        policy_func_type = kwargs['policy_func_type']

        prob_args = {'obsv_dim':kwargs['obsv_dim'],'constraint_dim':kwargs['constraint_dim'],  'hidden_sizes':[128, 64, 16],
                     'hidden_activation':'elu', 'output_activation':'tanh'}
        lamnet_args = {'obsv_dim':kwargs['obsv_dim'],'constraint_dim':kwargs['constraint_dim'], 'hidden_sizes':[64, 64],
                     'hidden_activation':'elu', 'output_activation':'softplus'}

        v_args = get_apprfunc_dict('value', value_func_type, **kwargs)
        policy_args = get_apprfunc_dict('policy', policy_func_type, **kwargs)

        self.v = create_apprfunc(**v_args)
        self.policy = create_apprfunc(**policy_args)
        self.prob = Prob(prob_args)
        self.lamnet = Lambda(lamnet_args)

        self.v_target = deepcopy(self.v)
        self.policy_target = deepcopy(self.policy)
        self.prob_target = deepcopy(self.prob)
        self.lamnet_target = deepcopy(self.lamnet)

        for p in self.v_target.parameters():
            p.requires_grad = False
        for p in self.policy_target.parameters():
            p.requires_grad = False
        for p in self.prob_target.parameters():
            p.requires_grad = False
        for p in self.lamnet_target.parameters():
            p.requires_grad = False

        self.policy_optimizer = Adam(self.policy.parameters(), lr=kwargs['policy_learning_rate'])  #
        self.v_optimizer = Adam(self.v.parameters(), lr=kwargs['value_learning_rate'])
        self.prob_optimizer = Adam(self.prob.parameters(), lr=2e-2)
        self.lamnet_optimizer = Adam(self.lamnet.parameters(), lr=2e-3)

        self.net_dict = {'v': self.v, 'policy': self.policy, 'prob':self.prob, 'lamnet':self.lamnet}
        self.target_net_dict = {'v': self.v_target, 'policy': self.policy_target, 'prob':self.prob_target, 'lamnet':self.lamnet_target}
        self.optimizer_dict = {'v': self.v_optimizer, 'policy': self.policy_optimizer, 'prob':self.prob_optimizer, 'lamnet':self.lamnet_optimizer}

    def update(self, grad_info):
        tau = grad_info['tau']
        grads_dict = grad_info['grads_dict']
        for net_name, grads in grads_dict.items():
            for p, grad in zip(self.net_dict[net_name].parameters(), grads):
                p.grad = grad
            self.optimizer_dict[net_name].step()

        with torch.no_grad():
            for net_name in grads_dict.keys():
                for p, p_targ in zip(self.net_dict[net_name].parameters(), self.target_net_dict[net_name].parameters()):
                    p_targ.data.mul_(1-tau)
                    p_targ.data.add_(tau * p.data)

class SPIL:
    def __init__(self, **kwargs):
        self.networks = ApproxContainer(**kwargs)
        self.envmodel = create_env_model(**kwargs)
        self.use_gpu = kwargs['use_gpu']
        if self.use_gpu:
            self.envmodel = self.envmodel.cuda()
        self.gamma = 0.99
        self.tau = 0.005
        self.pev_step = 1
        self.pim_step = 1
        self.forward_step = 25
        self.reward_scale = 0.02

        self.n_constraint = kwargs['constraint_dim']
        self.delta_i = np.array([0.] * kwargs['constraint_dim'])

        self.Kp = 40
        self.Ki = 0.07
        self.Kd = 0

        self.tb_info = dict()

        self.chance_thre = torch.Tensor([0.99] * kwargs['constraint_dim'])
        self.safe_prob_pre = np.array([0.] * kwargs['constraint_dim'])

    def set_parameters(self, param_dict):
        for key in param_dict:
            if hasattr(self, key):
                setattr(self, key, param_dict[key])
            else:
                warning_msg = "param '" + key + "'is not defined in algorithm!"
                warnings.warn(warning_msg)

    def get_parameters(self):
        params = dict()
        params['use_gpu'] = self.use_gpu
        params['gamma'] = self.gamma
        params['tau'] = self.tau
        params['pev_step'] = self.pev_step
        params['pim_step'] = self.pim_step
        params['reward_scale'] = self.reward_scale
        params['forward_step'] = self.forward_step
        return params

    def compute_gradient(self, data, iteration):
        grad_info = dict()
        grads_dict = dict()

        start_time = time.time()
        if self.use_gpu:
            self.networks = self.networks.cuda()
            for key, value in data.items():
                data[key] = value.cuda()

        # if iteration % (self.pev_step + self.pim_step) < self.pev_step: ##TODO: 这里改成了每个iteration都包含pev和pim
        self.networks.v.zero_grad()
        loss_v, v, loss_prob, prob, loss_lamnet, lamnet = self.compute_loss_v(deepcopy(data))
        loss_v.backward(); loss_prob.backward(); loss_lamnet.backward()
        v_grad = [p.grad for p in self.networks.v.parameters()]
        self.tb_info[tb_tags["loss_critic"]] = loss_v.item()
        self.tb_info[tb_tags["critic_avg_value"]] = v.item()
        grads_dict['v'] = v_grad
        grads_dict['prob'] = [p.grad for p in self.networks.prob.parameters()]
        grads_dict['lamnet'] = [p.grad for p in self.networks.lamnet.parameters()]
        # else:
        self.networks.policy.zero_grad()
        loss_policy = self.compute_loss_policy(deepcopy(data))
        loss_policy.backward()
        policy_grad = [p.grad for p in self.networks.policy.parameters()]
        self.tb_info[tb_tags["loss_actor"]] = loss_policy.item()
        grads_dict['policy'] = policy_grad

        if self.use_gpu:
            self.networks = self.networks.cpu()
            for key, value in data.items():
                data[key] = value.cpu()

        end_time = time.time()
        self.tb_info[tb_tags["alg_time"]] = (end_time - start_time) * 1000  # ms
        self.tb_info[tb_tags["safe_probability1"]] = self.safe_prob
        self.tb_info[tb_tags["lambda1"]] = self.lam.item() #lamnet
        #self.tb_info[tb_tags["safe_probability2"]] = self.safe_prob[1].item()
        # self.tb_info[tb_tags["lambda2"]] = self.lam[1].item()

        # writer.add_scalar(tb_tags['Lambda'], self.lam, iter)
        # writer.add_scalar(tb_tags['Safe_prob'], self.safe_prob, iter)

        grad_info['tau'] = self.tau
        grad_info['grads_dict'] = grads_dict
        return grad_info, self.tb_info

        # tb_info[tb_tags["loss_critic"]] = loss_v.item()
        # tb_info[tb_tags["critic_avg_value"]] = v.item()
        # tb_info[tb_tags["alg_time"]] = (end_time - start_time) * 1000  # ms
        # tb_info[tb_tags["loss_actor"]] = loss_policy.item()
        # return v_grad + policy_grad, tb_info

    def compute_loss_v(self, data):
        o, a, r, c, o2, d = data['obs'], data['act'], data['rew'], data['con'], data['obs2'], data['done']
        v = self.networks.v(o)
        prob = self.networks.prob(o)
        lamnet = self.networks.lamnet(o)
        traj_issafe = torch.ones(o.shape[0], self.n_constraint)

        with torch.no_grad():
            for step in range(self.forward_step):
                if step == 0:
                    a = self.networks.policy(o)
                    o2, r, d, info = self.envmodel.forward(o, a, d)
                    r_sum = self.reward_scale * r
                    traj_issafe *= torch.where(info['constraint'] > 0, 0, 1)

                else:
                    o = o2
                    a = self.networks.policy(o)
                    o2, r, d, info = self.envmodel.forward(o, a, d)
                    r_sum += self.reward_scale * self.gamma ** step * r
                    traj_issafe *= torch.where(info['constraint']>0, 0, 1)

            r_sum += self.gamma ** self.forward_step * self.networks.v_target(o2)
        loss_v = ((v - r_sum) ** 2).mean()
        loss_prob = ((prob - traj_issafe) ** 2).mean()

        delta_p = (self.chance_thre - self.networks.prob_target(o))
        delta_p_sepa = torch.where(torch.abs(delta_p) > 0.1, delta_p * 0.7, delta_p)
        delta_p_sepa = torch.where(torch.abs(delta_p) > 0.2, delta_p * 0.1, delta_p_sepa)
        delta_i = torch.clamp(self.networks.lamnet_target(o) + delta_p_sepa, 0, 99999)
        #delta_d = np.clip(self.safe_prob_pre - self.safe_prob, 0, 3333)
        lam_target = torch.clamp(self.Ki * delta_i + 0*self.Kp * delta_p, 0, 3333)
        loss_lamnet = ((lamnet - lam_target) ** 2).mean()

        safe_prob = (traj_issafe).mean(0).numpy()

        # Non-NN
        self.safe_prob = safe_prob

        print('Reward:', r_sum.mean(), 'safe probability', safe_prob)
        return loss_v, torch.mean(v), loss_prob, torch.mean(prob), loss_lamnet, torch.mean(lamnet)

    def compute_loss_policy(self, data):
        o, a, r, c, o2, d = data['obs'], data['act'], data['rew'], data['con'], data['obs2'], data['done']  # TODO  解耦字典
        for step in range(self.forward_step):
            if step == 0:
                a = self.networks.policy(o)
                o2, r, d, info = self.envmodel.forward(o, a, d)
                c = info['constraint']
                c = self.Phi(c)
                r_sum = self.reward_scale * r
                c_sum = c
                c_mul = c
            else:
                o = o2
                a = self.networks.policy(o)
                o2, r, d, info = self.envmodel.forward(o, a, d)
                c = info['constraint']
                c = self.Phi(c)
                r_sum = r_sum + self.reward_scale * self.gamma ** step * r
                c_sum = c_sum + c
                c_mul = c_mul * c
        #r_sum += self.gamma ** self.forward_step * self.networks.v_target(o2)
        lam = self.networks.lamnet_target(o)
        # for non-NN
        self.spil_get_weight()
        lam = torch.Tensor(self.lam).reshape(1,1)

        w_r, w_c = 1 / (1 + lam.sum(1)), lam / (1 + lam.sum(1).unsqueeze(1))
        loss_pi = (r_sum * w_r + (c_mul*w_c).sum(1)).mean()
        return -loss_pi

    def Phi(self, y):
        # Transfer constraint to cumulative
        m1 = 1
        m2 = m1 / (1 + m1) * 0.9
        tau = 0.07
        sig = (1 + tau * m1) / (1 + m2 * tau * torch.exp(torch.clamp(y / tau, min=-10, max=5)))
        # c = torch.relu(-y)
        return sig

        # The following is for max
        # m1 = 3/2
        # m2 = m1 / (1 + m1) * 1
        # m2 = 3/2
        # tau = 0.2
        # sig = (1 + tau * m1) / (1 + m2 * tau * torch.exp(torch.clamp(y / tau, min=-5, max=5)))


    def load_state_dict(self, state_dict):
        self.networks.load_state_dict(state_dict)

    def spil_get_weight(self):
        delta_p = (self.chance_thre.numpy() - self.safe_prob)
        # integral separation
        delta_p_sepa = np.where(np.abs(delta_p) > 0.1, delta_p * 0.7, delta_p)
        delta_p_sepa = np.where(np.abs(delta_p) > 0.2, delta_p * 0, delta_p_sepa)
        self.delta_i = np.clip(self.delta_i + delta_p_sepa, 0, 99999)

        delta_d = np.clip(self.safe_prob_pre - self.safe_prob, 0, 3333)
        lam = np.clip(self.Ki * self.delta_i + self.Kp * delta_p + self.Kd * delta_d, 0, 3333)
        self.safe_prob_pre = self.safe_prob
        self.lam = lam *0 +0.



if __name__ == '__main__':
    print('11111')
