import random
import hashlib
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from gymnasium import spaces
from CybORG.Shared import Results
import numpy as np
# following libraries are for Schwartz implementation
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

from stable_baselines3 import DQN
from sb3_contrib.drqn.drqn import DeepRecurrentQNetwork
from sb3_contrib.drqn.policies import DRQNetwork, DRQNPolicy
from sb3_contrib.drqn.dueling_policies import DuelingDRQNPolicy
from stable_baselines3.dqn.policies import DQNPolicy
from stable_baselines3.common.torch_layers import FlattenExtractor
from stable_baselines3.common.utils import get_linear_fn, constant_fn
from stable_baselines3.common.callbacks import BaseCallback
from sb3_contrib.per.replay_sequence_buffer import ReplaySequenceBuffer
from sb3_contrib.per.replay_partial_sequence_buffer import ReplayPartialSequenceBuffer
from sb3_contrib.per.prioritized_replay_sequence_buffer import PrioritizedReplaySequenceBuffer


class RedDRQNAgent(BaseAgent):

    """ a red agent that uses Deep Recurrent Q Network """
    """ this uses the stable_baselines3 implementation """

    def __init__(self):

        self.model = None

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass

    def initialise(self, 
            env, 
            gamma, 
            initial_eps, 
            final_eps, 
            total_steps,
            batch_size=32,
            num_prev_seq=10,
            double=None, # double not implemented yet
            dueling=None, # dueling not implement yet,
            tensorboard_log=None
            ):
        """ set up DQN """
        """ lr_schedule needs to be of Schedule type """
        self.env = env

        input_size=env.observation_space.shape[0]
        net_arch=[input_size,input_size]

        learning_rate=float(0.0001)
        # LR is provided as a schedule
        lr_schedule=constant_fn(learning_rate)

        buffer_size = int(total_steps/5)
        exploration_fraction=float(0.9)
        learning_starts = int(total_steps/200) # make it very small for testing
        target_network_update_freq = int(total_steps/5000)

        prioritized_replay_alpha=float(0.9)
        prioritized_replay_beta0=float(0.4)
        prioritized_replay_beta_iters=int(total_steps/50)

        if dueling:
            ModelClass = DeepRecurrentQNetwork
            PolicyClass = DuelingDRQNPolicy
        else:
            ModelClass = DeepRecurrentQNetwork
            PolicyClass = DRQNPolicy

        print("ModelClass: {}".format(ModelClass.__name__))
        print("PolicyClass: {}".format(PolicyClass.__name__))
        print("Hyperparameters:")
        print("Total Steps {}".format(total_steps))
        print("Input Size {}".format(input_size))
        print("Net Arch: {}".format(net_arch))
        print("Initial Epsilon: {}".format(initial_eps))
        print("Final Epsilon: {}".format(final_eps))
        print("Exploration Fraction: {}".format(exploration_fraction))
        print("Gamma: {}".format(gamma))
        #print("Double: {}".format(double))
        #print("Dueling: {}".format(dueling))
        print("Learning Rate (Constant): {}".format(learning_rate))
        print("Exp Replay Batch Size: {}".format(batch_size))
        print("PER Num Prev Transitions: {}".format(num_prev_seq))
        print("PER Alpha: {}".format(prioritized_replay_alpha))
        print("PER Beta0: {}".format(prioritized_replay_beta0))
        # Not provided in implementation
        #print("PER Beta Iterations: {}".format(prioritized_replay_beta_iters))
        print("Learning Starts {}".format(learning_starts))
        print("Replay Buffer Size {}".format(buffer_size))
        print("Target network update freq: {}".format(target_network_update_freq))
        print()

        #replay_buffer_class = ReplayPartialSequenceBuffer
        # per_buffer_args = None

        replay_buffer_class = PrioritizedReplaySequenceBuffer
        per_buffer_args = {
                "alpha": prioritized_replay_alpha,
                "beta": prioritized_replay_beta0,
                "lstm_num_layers": len(net_arch)
                }

        self.model = ModelClass(
                policy=PolicyClass,
                env=env,
                learning_rate=lr_schedule, 
                buffer_size=buffer_size,
                learning_starts=learning_starts,
                batch_size=batch_size, # default is 32
                n_prev_seq=num_prev_seq,
                tau=1.0, # default. Doesn't scale the target network values when updating
                gamma=gamma,
                train_freq=1, #default is 4
                gradient_steps=1, #default
                replay_buffer_class=replay_buffer_class, # None resolves to BufferReplay
                replay_buffer_kwargs=per_buffer_args, #default is None
                optimize_memory_usage=False, # default
                target_update_interval=target_network_update_freq, #default
                exploration_fraction=exploration_fraction, #default is 0.1
                exploration_initial_eps=initial_eps,
                exploration_final_eps=final_eps,
                max_grad_norm=10, #default
                tensorboard_log=tensorboard_log, #default is None
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

    def load(self,classtype,file):
        ModelClass = DeepRecurrentQNetwork
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
        print("Random Action" if not self.locals["computed_actions"] else "Computed Action")
        print("Action: {}".format(self.locals["actions"][0]))
        print("Reward: {}".format(self.locals["rewards"][0]))
        print("Done: {}".format(self.locals["dones"][0]))
        print()
        return True

    def _on_training_end(self):
        pass
