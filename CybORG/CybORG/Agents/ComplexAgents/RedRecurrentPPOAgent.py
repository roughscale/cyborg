import random
import hashlib
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from gym import spaces
from CybORG.Shared import Results
import numpy as np
# following libraries are for Schwartz implementation
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

from sb3_contrib.ppo_recurrent import RecurrentPPO 
from sb3_contrib.ppo_recurrent.policies import MlpLstmPolicy
#from sb3_contrib.drqn.drqn import DeepRecurrentQNetwork
#from sb3_contrib.drqn.policies import DRQNetwork, DRQNPolicy
#from stable_baselines3.dqn.policies import DQNPolicy
from stable_baselines3.common.torch_layers import FlattenExtractor
from stable_baselines3.common.utils import get_linear_fn, constant_fn
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env
#from sb3_contrib.per.prioritized_replay_sequence_buffer import PrioritizedReplaySequenceBuffer


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
            n_steps=128, # default
            batch_size=128, # default
            n_epochs=10, # default
            clip_range=0.2, # default
            n_envs=1
            ):
        """ set up recurrent PPO """
        """ lr_schedule needs to be of Schedule type """

        # vectorise the environment for parallel agent execution
        # disabled for the moment. need to fix the wrappers around the cyborg env
        #self.env = make_vec_env(env,n_envs=n_envs)
        self.env = env

        input_size=self.env.observation_space.shape[0]
        #net_arch=[input_size]
        #net_arch=[1024,256,64]
        net_arch=[input_size,int(input_size/2)]

        learning_rate=float(0.0001)
        # LR is provided as a schedule
        lr_schedule=constant_fn(learning_rate)

        print("Hyperparameters:")
        print("Number Steps {}".format(n_steps))
        print("Input Size {}".format(input_size))
        print("Net Arch: {}".format(net_arch))
        print("Gamma: {}".format(gamma))
        print("Clip Range: {}".format(clip_range))
        print("Batch Size: {}".format(batch_size))
        print("Number of Parallel Envs: {}".format(n_envs))
        print("Learning Rate (Constant): {}".format(learning_rate))
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
                max_grad_norm=0.5, #default
                tensorboard_log=None, #default
                policy_kwargs={"net_arch": net_arch}, #default is None
                verbose=1,
                seed=None, #default
                device="auto", #default
                _init_setup_model=True # default
        )

        # specific to policy
        self.num_actions = self.env.action_space.n
        #print(self.num_actions)

        self.learn_callback = LearnCallback(self.model)

class LearnCallback(BaseCallback):

    def __init__(self, model):
        super().__init__(self)
        super().init_callback(model)
        env = None

    def _on_training_start(self):
        #print(self.globals)
        #print(self.training_env)
        #print(dir(self.training_env))
        #print(self.training_env.envs)
        self.env=self.training_env.envs[0]
        # Monitor class
        #print(dir(self.env))
        #print(self.locals)
        # OpenAIGymWrapper class
        #print(env.env)
        # FixedFlatObsWrapper class
        #print(env.env.env)
        #print(self.training_env.observation_space)
        return True

    def _on_step(self):
        #print(self.env.render)
        #self.env.render(self,mode=None,kwargs=None) 
        #print(self.locals)
        #print(self.globals)
        # see if we can print the following 3 steps
        #print("Step {}".format(int(self.locals["eps_steps"]) + 1))
        #print("Random Action" if not self.locals["computed_actions"] else "Computed Action")
        #print(action_qvals)

        #print("Num Collected Episodes: {}".format(self.locals["num_collected_episodes"]))
        #print("Num Collected Steps: {}".format(self.locals["num_collected_steps"]))
        #print()
        # infos observation is unwrapped (ie python list not a numpy array)
        #print("Infos: {}".format(self.locals["infos"]))
        #print("Obs: {}".format(self.locals["infos"][0]["state"]))
        ##print("Obs Hash: {}".format(State.get_state_hash(self.locals["infos"][0]["state"])))
        #print("New Obs: {}".format(self.locals["new_obs"][0]))
        #print("Comp Obs: {}".format(np.array_equal(self.locals["infos"][0]["state"],self.locals["new_obs"][0])))
        #diff = np.subtract(self.locals["infos"][0]["state"],self.locals["new_obs"][0])
        #print("Diff obs: {}".format(diff))
        #print("Diff shape: {}".format(diff.shape))
        ##print("New Obs Hash: {}".format(State.get_state_hash(self.locals["new_obs"][0])))
        print("Action: {}".format(self.locals["actions"][0]))
        print("Reward: {}".format(self.locals["rewards"][0]))
        print("Done: {}".format(self.locals["dones"][0]))
        print()
        return True
        #if self.locals["dones"] == True and self.locals["self"]._episode_num == 2:
        #    #print(self.locals["self"]._episode_num)
        #    #print(self.locals["self"].num_timesteps)
        #    return False
        #else:
        #    return True

    def _on_training_end(self):
        pass
        #print(dir(self.locals["self"]))
        #print(dir(self.locals["replay_buffer"]))
        #print(self.locals["replay_buffer"].observations)
        #print(self.locals["replay_buffer"].ep_start)
        #print(self.locals["replay_buffer"].ep_length)
        # take first episode length
        ##ep_length=self.locals["replay_buffer"].ep_length[0]
        #print(ep_length)
        #print(dir(self.locals["replay_buffer"]))
        #np.save("observations",self.locals["replay_buffer"].observations[0:ep_length[0]])
        #np.save("next_observations",self.locals["replay_buffer"].next_observations[0:ep_length[0]])
        #np.save("actions",self.locals["replay_buffer"].actions[0:ep_length[0]])
        #np.save("dones",self.locals["replay_buffer"].dones[0:ep_length[0]])
        #np.save("rewards",self.locals["replay_buffer"].rewards[0:ep_length[0]])