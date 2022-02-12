## Project SPIL  
### Describtion:  
This is the code repertory of Separated Proportional-Integral Lagrangian (SPIL) method for the mobile robot application (papaer:https://arxiv.org/abs/2108.11623)  
This project is based on General Optimal control Problem Solver (GOPS) Intelligent Driving Lab(iDLab) by Tsinghua University.

### Author:  
Baiyu Peng, Tsinghua University
mails: pby19@mails.tsinghua.edu.cn
### Title:  
Model-based Chance-Constrained Reinforcement Learning via Separated Proportional-Integral Lagrangian
### Abstract:  
Safety is essential for reinforcement learning (RL) applied in the real world. Adding chance constraints (or probabilistic constraints) is a suitable way to enhance RL safety under uncertainty. Existing chance-constrained RL methods like the penalty methods and the Lagrangian methods either exhibit periodic oscillations or learn an over-conservative or unsafe policy. In this paper, we address these shortcomings by proposing a separated proportional-integral Lagrangian (SPIL) algorithm. We first review the constrained policy optimization process from a feedback control perspective, which regards the penalty weight as the control input and the safe probability as the control output. Based on this, the penalty method is formulated as a proportional controller, and the Lagrangian method is formulated as an integral controller. We then unify them and present a proportional-integral Lagrangian method to get both their merits, with an integral separation technique to limit the integral value in a reasonable range. To accelerate training, the gradient of safe probability is computed in a model-based manner. We demonstrate our method can reduce the oscillations and conservatism of RL policy in a car-following simulation. To prove its practicality, we also apply our method to a real-world mobile robot navigation task, where our robot successfully avoids a moving obstacle with highly uncertain or even aggressive behaviors.


### Dependencies
pytorch>=1.9  
tensorboardx>=2.2  
ray>=1.71  
gym>=0.21  
matplotlib  

### How to train the policy
####1. Launch tensorboard (optional)
tensorboard --logdir results --port 6006
#####2. Training (select one)
   1. __Serial training__  
   run  gops/examples/spil/spil_mlp_mobilerobot_offserial.py
   2. __Asynchronous parallel training (!Require multiple CPU core)__  
   run  gops/examples/spil/spil_mlp_mobilerobot_async.py



### How to test the policy
1. edit gops/examples/spil/spil_mlp_mobilerobot_test.py, change folder directory (line 120) of the policy network
evaluator.networks.load_state_dict(torch.load('C:/Users/pengbaiyu/PycharmProjects/gops/gops/results/SPIL/__0125-143425/apprfunc/apprfunc_5000.pkl__'))
2. run gops/examples/spil/spil_mlp_mobilerobot_test.py

### File system
1. examples: 
2. modules:
   1. algorithms: spil algorithms
   2. apprfunc: approximation function, including neural network
   3. create_pkg
   4. env: environment, including the Mobile Robot environment
   5. trainer: serial trainer and parallel trainer
   6. utils: other tools
3. results
   1. SPIL: the training results and neural networks for algorithm SPIL


