#  Copyright (c). All Rights Reserved.
#  General Optimal control Problem Solver (GOPS)
#  Intelligent Driving Lab(iDLab), Tsinghua University
#
#  Creator: Yao MU
#  Description: Structural definition for approximation function
#
#  Update Date: 2021-05-21, Shengbo Li: revise headline

__all__ = ['DetermPolicy', 'StochaPolicy', 'ActionValue', 'ActionValueDis', 'StateValue']

import torch
import torch.nn as nn
import torch.nn.functional as F
from modules.utils.utils import get_activation_func


def CNN(kernel_sizes, channels, strides, activation, input_channel):
    layers = []
    for j in range(len(kernel_sizes)):
        act = activation
        if j == 0:
            layers += [nn.Conv2d(input_channel, channels[j], kernel_sizes[j], strides[j]), act()]
        else:
            layers += [nn.Conv2d(channels[j - 1], channels[j], kernel_sizes[j], strides[j]), act()]
    return nn.Sequential(*layers)


def MLP(sizes, activation, output_activation=nn.Identity):
    layers = []
    for j in range(len(sizes) - 1):
        act = activation if j < len(sizes) - 2 else output_activation
        layers += [nn.Linear(sizes[j], sizes[j + 1]), act()]
    return nn.Sequential(*layers)


class DetermPolicy(nn.Module):
    def __init__(self, **kwargs):
        super(DetermPolicy, self).__init__()
        act_dim = kwargs['act_dim']
        obs_dim = kwargs['obs_dim']
        conv_type = kwargs['conv_type']
        action_high_limit = kwargs['action_high_limit']
        action_low_limit = kwargs['action_low_limit']
        self.register_buffer('act_high_lim', torch.from_numpy(action_high_limit))
        self.register_buffer('act_low_lim', torch.from_numpy(action_low_limit))
        self.hidden_activation = get_activation_func(kwargs['hidden_activation'])
        self.output_activation = get_activation_func(kwargs['output_activation'])
        if conv_type == "type_1":
            # CNN+MLP Parameters
            conv_kernel_sizes = [8, 4, 3]
            conv_channels = [32, 64, 64]
            conv_strides = [4, 2, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [512, 256]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims] + mlp_hidden_layers + [act_dim]

            self.mlp = MLP(mlp_sizes, self.hidden_activation, self.output_activation)

        elif conv_type == "type_2":
            # CNN+MLP Parameters
            conv_kernel_sizes = [4, 3, 3, 3, 3, 3]
            conv_channels = [8, 16, 32, 64, 128, 256]
            conv_strides = [2, 2, 2, 2, 1, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [128]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims] + mlp_hidden_layers + [act_dim]

            self.mlp = MLP(mlp_sizes, self.hidden_activation, self.output_activation)
        else:
            raise NotImplementedError

    def forward(self, obs):
        img = obs.permute(0, 3, 1, 2)
        img = self.conv(img)
        feature = img.view(img.size(0), -1)
        feature = self.mlp(feature)
        action = (self.act_high_lim - self.act_low_lim) / 2 * torch.tanh(feature) \
                 + (self.act_high_lim + self.act_low_lim) / 2
        return action


class StochaPolicy(nn.Module):
    def __init__(self, **kwargs):
        super(StochaPolicy, self).__init__()
        act_dim = kwargs['act_dim']
        obs_dim = kwargs['obs_dim']
        conv_type = kwargs['conv_type']
        action_high_limit = kwargs['action_high_limit']
        action_low_limit = kwargs['action_low_limit']
        self.register_buffer('act_high_lim', torch.from_numpy(action_high_limit))
        self.register_buffer('act_low_lim', torch.from_numpy(action_low_limit))
        self.hidden_activation = get_activation_func(kwargs['hidden_activation'])
        self.output_activation = get_activation_func(kwargs['output_activation'])
        self.min_log_std = kwargs['min_log_std']
        self.max_log_std = kwargs['max_log_std']

        if conv_type == "type_1":
            # CNN+MLP Parameters
            conv_kernel_sizes = [8, 4, 3]
            conv_channels = [32, 64, 64]
            conv_strides = [4, 2, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [512, 256]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims] + mlp_hidden_layers + [act_dim]

            self.mean = MLP(mlp_sizes, self.hidden_activation, self.output_activation)
            self.log_std = MLP(mlp_sizes, self.hidden_activation, self.output_activation)

        elif conv_type == "type_2":
            # CNN+MLP Parameters
            conv_kernel_sizes = [4, 3, 3, 3, 3, 3]
            conv_channels = [8, 16, 32, 64, 128, 256]
            conv_strides = [2, 2, 2, 2, 1, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [128]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims] + mlp_hidden_layers + [act_dim]

            self.mean = MLP(mlp_sizes, self.hidden_activation, self.output_activation)
            self.log_std = MLP(mlp_sizes, self.hidden_activation, self.output_activation)
        else:
            raise NotImplementedError

    def forward(self, obs):
        img = obs.permute(0, 3, 1, 2)
        img = self.conv(img)
        feature = img.view(img.size(0), -1)
        action_mean = (self.act_high_lim - self.act_low_lim) / 2 * torch.tanh(self.mean(feature)) \
                      + (self.act_high_lim + self.act_low_lim) / 2
        action_std = torch.clamp(self.log_std(feature), self.min_log_std, self.max_log_std).exp()
        return torch.cat((action_mean, action_std), dim=-1)


class ActionValue(nn.Module):
    def __init__(self, **kwargs):
        super(ActionValue, self).__init__()
        act_dim = kwargs['act_dim']
        obs_dim = kwargs['obs_dim']
        conv_type = kwargs['conv_type']
        self.hidden_activation = get_activation_func(kwargs['hidden_activation'])
        self.output_activation = get_activation_func(kwargs['output_activation'])
        if conv_type == "type_1":
            # CNN+MLP Parameters
            conv_kernel_sizes = [8, 4, 3]
            conv_channels = [32, 64, 64]
            conv_strides = [4, 2, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [512, 256]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims+act_dim] + mlp_hidden_layers + [1]

            self.mlp = MLP(mlp_sizes, self.hidden_activation, self.output_activation)

        elif conv_type == "type_2":
            # CNN+MLP Parameters
            conv_kernel_sizes = [4, 3, 3, 3, 3, 3]
            conv_channels = [8, 16, 32, 64, 128, 256]
            conv_strides = [2, 2, 2, 2, 1, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [128]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims+act_dim] + mlp_hidden_layers + [1]
            self.mlp = MLP(mlp_sizes, self.hidden_activation, self.output_activation)
        else:
            raise NotImplementedError

    def forward(self, obs, act):
        img = obs.permute(0, 3, 1, 2)
        img = self.conv(img)
        feature = torch.cat([img.view(img.size(0), -1), act], -1)
        return self.mlp(feature)


class ActionValueDis(nn.Module):
    def __init__(self, **kwargs):
        super(ActionValueDis, self).__init__()
        act_num = kwargs['act_dim']
        obs_dim = kwargs['obs_dim']
        conv_type = kwargs['conv_type']
        self.hidden_activation = get_activation_func(kwargs['hidden_activation'])
        self.output_activation = get_activation_func(kwargs['output_activation'])
        if conv_type == "type_1":
            # CNN+MLP Parameters
            conv_kernel_sizes = [8, 4, 3]
            conv_channels = [32, 64, 64]
            conv_strides = [4, 2, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [512, 256]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims] + mlp_hidden_layers + [act_num]
            self.mlp = MLP(mlp_sizes, self.hidden_activation, self.output_activation)

        elif conv_type == "type_2":
            # CNN+MLP Parameters
            conv_kernel_sizes = [4, 3, 3, 3, 3, 3]
            conv_channels = [8, 16, 32, 64, 128, 256]
            conv_strides = [2, 2, 2, 2, 1, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [128]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims] + mlp_hidden_layers + [act_num]
            self.mlp = MLP(mlp_sizes, self.hidden_activation, self.output_activation)
        else:
            raise NotImplementedError

    def forward(self, obs):
        img = obs.permute(0, 3, 1, 2)
        img = self.conv(img)
        feature = img.view(img.size(0), -1)
        return self.mlp(feature)


class StochaPolicyDis(ActionValueDis):
    pass


class StateValue(nn.Module):
    def __init__(self, **kwargs):
        super(StateValue, self).__init__()
        obs_dim = kwargs['obs_dim']
        conv_type = kwargs['conv_type']
        self.hidden_activation = get_activation_func(kwargs['hidden_activation'])
        self.output_activation = get_activation_func(kwargs['output_activation'])
        if conv_type == "type_1":
            # CNN+MLP Parameters
            conv_kernel_sizes = [8, 4, 3]
            conv_channels = [32, 64, 64]
            conv_strides = [4, 2, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [512, 256]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims] + mlp_hidden_layers + [1]
            self.mlp = MLP(mlp_sizes, self.hidden_activation, self.output_activation)

        elif conv_type == "type_2":
            # CNN+MLP Parameters
            conv_kernel_sizes = [4, 3, 3, 3, 3, 3]
            conv_channels = [8, 16, 32, 64, 128, 256]
            conv_strides = [2, 2, 2, 2, 1, 1]
            conv_activation = nn.ReLU
            conv_input_channel = obs_dim[-1]
            mlp_hidden_layers = [128]

            # Construct CNN+MLP
            self.conv = CNN(conv_kernel_sizes, conv_channels, conv_strides, conv_activation, conv_input_channel)
            conv_num_dims = self.conv(torch.ones(obs_dim).unsqueeze(0).permute(0, 3, 1, 2)).reshape(1, -1).shape[-1]
            mlp_sizes = [conv_num_dims] + mlp_hidden_layers + [1]
            self.mlp = MLP(mlp_sizes, self.hidden_activation, self.output_activation)
        else:
            raise NotImplementedError

    def forward(self, obs):
        img = obs.permute(0, 3, 1, 2)
        img = self.conv(img)
        feature = img.view(img.size(0), -1)
        return self.mlp(feature)