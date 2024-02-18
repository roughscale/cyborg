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
from stable_baselines3.dqn.policies import DQNPolicy
from stable_baselines3.common.torch_layers import FlattenExtractor
from stable_baselines3.common.utils import get_linear_fn, constant_fn
from stable_baselines3.common.callbacks import BaseCallback
from sb3_contrib.per.replay_sequence_buffer import ReplaySequenceBuffer


class RedSB3DRQNAgent(BaseAgent):

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
            double=None, # double not implemented yet
            dueling=None, # dueling not implement yet,
            ):
        """ set up DQN """
        """ lr_schedule needs to be of Schedule type """
        self.env = env

        input_size=env.observation_space.shape[0]
        #net_arch=[input_size]
        #net_arch=[1024,256,64]
        #net_arch=[input_size, int(input_size/2)]
        net_arch=[input_size]

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
        print("PER Alpha: {}".format(prioritized_replay_alpha))
        print("PER Beta0: {}".format(prioritized_replay_beta0))
        # Not provided in implementation
        #print("PER Beta Iterations: {}".format(prioritized_replay_beta_iters))
        print("Learning Starts {}".format(learning_starts))
        print("Replay Buffer Size {}".format(buffer_size))
        print("Target network update freq: {}".format(target_network_update_freq))
        print()


        per_buffer_args = {
                "alpha": prioritized_replay_alpha,
                "beta": prioritized_replay_beta0
                }

        self.model = ModelClass(
                policy=PolicyClass,
                env=env,
                learning_rate=lr_schedule, 
                buffer_size=buffer_size,
                learning_starts=learning_starts,
                batch_size=batch_size, # default is 32
                tau=1.0, # default. Doesn't scale the target network values when updating
                gamma=gamma,
                train_freq=1, #default is 4
                gradient_steps=1, #default
                replay_buffer_class=ReplaySequenceBuffer, # None resolves to BufferReplay
                #replay_buffer_kwargs=per_buffer_args, #default is None
                replay_buffer_kwargs=None, #default is None
                optimize_memory_usage=False, # default
                target_update_interval=target_network_update_freq, #default
                exploration_fraction=exploration_fraction, #default is 0.1
                exploration_initial_eps=initial_eps,
                exploration_final_eps=final_eps,
                max_grad_norm=10, #default
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
        print("Random Action" if not self.locals["computed_actions"] else "Computed Action")
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
