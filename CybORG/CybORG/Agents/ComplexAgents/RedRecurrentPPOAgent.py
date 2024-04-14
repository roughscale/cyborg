import random
import hashlib
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from gym import spaces
from CybORG.Shared import Results
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

from sb3_contrib.ppo_recurrent import RecurrentPPO 
from sb3_contrib.ppo_recurrent.policies import MlpLstmPolicy
from stable_baselines3.common.torch_layers import FlattenExtractor
from stable_baselines3.common.utils import get_linear_fn, constant_fn
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env

class RedRecurrentPPOAgent(BaseAgent):

    """ a red agent that uses a Recurrent Proximal Policy Optimization policy gradient algorithm """
    """ this uses the stable_baselines3 implementation """

    def __init__(self):

        self.model = None
        self.steps_done = 0

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass

    def initialise(self, 
            env, 
            gamma,
            total_timesteps,
            n_steps=128, # default
            batch_size=128, # default
            n_epochs=10, # default
            clip_range=0.2, # default
            n_envs=1,
            gae_lambda=0.95, # default
            normalize_advantage=True, # default
            ent_coef= 0.0, # default
            vf_coef=0.5, # default
            target_kl=None, # default
            net_arch = [1.0, 1.0],
            tensorboard_log = None
            ):
        """ set up recurrent PPO """
        """ lr_schedule needs to be of Schedule type """

        self.env = env

        input_size=self.env.observation_space.shape[0]
        net_arch=[ int(input_size * n) for n in net_arch ]

        learning_rate=float(0.0001)
        # LR is provided as a schedule
        lr_schedule=constant_fn(learning_rate)

        print("Model Class: {}".format(self.__class__.__name__))
        print("Hyperparameters:")
        print("Total Timesteps {}".format(total_timesteps))
        print("Number Steps {}".format(n_steps))
        print("Input Size {}".format(input_size))
        print("Net Arch: {}".format(net_arch))
        print("Gamma: {}".format(gamma))
        print("Clip Range: {}".format(clip_range))
        print("Batch Size: {}".format(batch_size))
        print("Number of Parallel Envs: {}".format(n_envs))
        print("Learning Rate (Constant): {}".format(learning_rate))
        print("GAE lambda: {}".format(gae_lambda))
        print("Normalise Advantage: {}".format(normalize_advantage))
        print("Entropy Co-efficient: {}".format(ent_coef))
        print("Value Function Co-efficient: {}".format(vf_coef))
        print("Target KL: {}".format(target_kl))
        print()


        self.model = RecurrentPPO(
                policy=MlpLstmPolicy,
                env=self.env,
                learning_rate=lr_schedule, 
                n_steps = n_steps,
                batch_size=batch_size,
                n_epochs = n_epochs,
                gamma=gamma,
                clip_range=clip_range,
                gae_lambda=gae_lambda,
                normalize_advantage=normalize_advantage,
                ent_coef=ent_coef,
                vf_coef=vf_coef,
                target_kl=target_kl,
                max_grad_norm=0.5, #default
                tensorboard_log=tensorboard_log,
                policy_kwargs={"net_arch": net_arch}, #default is None
                verbose=1,
                seed=None, #default
                device="auto", #default
                _init_setup_model=True # default
        )

        # specific to policy
        self.num_actions = self.env.action_space.n

        self.learn_callback = LearnCallback(self.model)

    def load(self,classtype,file,device="auto"):
        # RecurrentPPO only has one model class type.
        ModelClass = RecurrentPPO
        self.model = ModelClass.load(file)
        return self

class LearnCallback(BaseCallback):

    def __init__(self, model):
        super().__init__(self)
        super().init_callback(model)
        env = None

    def _on_training_start(self):
        self.env=self.training_env.envs[0]
        return True

    def _on_step(self):
        print("Action: {}".format(self.locals["actions"][0]))
        print("Reward: {}".format(self.locals["rewards"][0]))
        print("Done: {}".format(self.locals["dones"][0]))
        print()
        return True

    def _on_training_end(self):
        pass
