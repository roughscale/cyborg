import random
import hashlib
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from gym import spaces
from CybORG.Shared import Results
from CybORG.Shared.State import State
import numpy as np
# following libraries are for Schwartz implementation
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.optim as optim
#
#from stable_baselines3.dqn.dqn import DQN


class RedDQNFCAgent(BaseAgent):

    """ a red agent that uses Double Q network with a fully connected layer """
    """ initially use Schwartz's custom pytorch implementation """
    """ then attempt to migate this to stablebaselines3 """

    def __init__(self):
        self.epsilon = 0
        self.alpha = 0
        self.gamma = 0

        self.dqn = None
        self.target_dqn = None

        self.steps_done = 0
        self.episode_num=0

    def train(self, results: Results):
        """allows an agent to learn a policy"""
        """ Results object should have observation, next_observation, action, reward"""

        # this has already been done and is in the Results object
        # next_o, r, done, env_step_limit_reached, _ = self.env.step(a)
        #self.save_transition(results.observation, results.action, results.next_observation, results.reward, results.done)
        self.replay.store(results.observation, results.action, results.next_observation, results.reward, results.done)
        self.steps_done += 1
        loss, mean_v = self.optimize()

        obs_hash = State.get_state_hash(np.array(results.observation))
        next_obs_hash = State.get_state_hash(np.array(results.next_observation))
        return obs_hash, next_obs_hash, loss, mean_v

    def get_epsilon(self):
        #if self.steps_done < self.exploration_fraction:
        #  return self.exploration_final_eps
        #return self.epsilon_schedule[self.steps_done]
        return self.epsilon_schedule[self.episode_num]

    def get_action(self, observation, action_space, egreedy=True):
        if isinstance(action_space, spaces.Discrete):
            rand=np.random.uniform()
            eps=self.get_epsilon()
            #eps=self.exploration_final_eps
            #if egreedy and np.random.uniform() < self.get_epsilon():
            if egreedy and rand < eps:
                print(rand,eps)
                action = action_space.sample()
                return action
            else:
                #print(observation)
                #print(observation.shape)
                o = torch.from_numpy(observation).float().to(self.device)
                #print(o)
                return self.dqn.get_action(o).cpu().item()

    def end_episode(self):
        self.episode_num+=1

    def set_initial_values(self, action_space, observation):
        pass

    def save_transition(self, s, a, next_s, r, done):
        self.transition = [ np.array([s], dtype=np.float32), np.array([[a]], dtype=np.int64), np.array([next_s],dtype=np.float32), np.array([r],dtype=np.float32), np.array([done],dtype=np.float32) ]

    def get_transition(self):
        return [torch.from_numpy(buf).to(self.device) for buf in self.transition]


    def initialise(self, env, state_space, gamma, alpha, initial_eps, final_eps, total_steps, num_episodes):
        """ set up DQN """
        # config should contain the hyperparameters
        #self.Q = np.zeros(action_space.n,)
        self.env = env
        self.gamma = gamma
        self.learning_rate = alpha
        self.exploration_fraction = num_episodes # decay e per episode rather than per step
        #self.exploration_fraction = total_steps # self.exploration_steps
        self.target_update_interval = 1000 # target_update_freq, schwartz default
        self.exploration_initial_eps = initial_eps
        self.exploration_final_eps = final_eps
        self.epsilon_schedule = np.linspace(self.exploration_initial_eps,
                                            self.exploration_final_eps,
                                            self.exploration_fraction)

        replay_size = int(total_steps / 2)
        self.batch_size = 32

        # specific to policy
        self.num_actions = self.env.action_space.n
        #print(self.num_actions)
        obs_dim = state_space.shape
        #print(obs_dim)
        #hidden_sizes = [64,64] # nasim default. why this?
        #hidden_sizes = [5315,5315] # match the input size. very slow, overfits
        hidden_sizes = [256] # schwartz paper 

        # dqn objects
        self.device = torch.device("cuda"
                                   if torch.cuda.is_available()
                                   else "cpu")
        self.dqn = DQN(
                input_dim=obs_dim,
                layers=hidden_sizes,
                num_actions=self.num_actions).to(self.device)
        print("DQN architecture")
        print(self.dqn)
        print(type(self.dqn))
        self.target_dqn = DQN(
                input_dim=obs_dim,
                layers=hidden_sizes,
                num_actions=self.num_actions).to(self.device)

        self.optimizer = optim.Adam(self.dqn.parameters(), lr=self.learning_rate)
        self.loss_fn = nn.SmoothL1Loss()

        # replay setup
        self.replay = ReplayMemory(replay_size,
                                   obs_dim,
                                   self.device)

    # DQN Optimize
    def optimize(self):
        # ER
        # this takes a random batch size.
        # NOTE: But doesn't seem to guarantee that the last
        # transition will be in the batch
        # this is correct. the sample needs to be random, always
        # taking the last provides an unnecessary correlation
        batch = self.replay.sample_batch(self.batch_size)
        s_batch, a_batch, next_s_batch, r_batch, d_batch = batch
        # notice that the last transition may not be in the batch
        # for non-ER, *_batch is from the last s,a,r,s' transition
        #s_batch, a_batch, next_s_batch, r_batch, d_batch = self.get_transition()
       
        # get q_vals for each state and the action performed in that state
        # self.dqn(x) is nn.Module._call_impl()
        q_vals_raw = self.dqn(s_batch)
        q_vals = q_vals_raw.gather(1, a_batch).squeeze()
        # this is the Q(s,a,0)
        print("Q vals")
        print(q_vals)

        # get target q val = max val of next state
        with torch.no_grad():
            target_q_val_raw = self.target_dqn(next_s_batch)
            target_q_val = target_q_val_raw.max(1)[0]
            # this is the r + y.max_a'.Q^(s_t+1,a',0-)
            target = r_batch + self.gamma*(1-d_batch)*target_q_val
            print("Q^ vals")
            print(target)

        # calculate loss
        loss = self.loss_fn(q_vals, target)

        # optimize the model
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        if self.steps_done % self.target_update_interval == 0:
            self.target_dqn.load_state_dict(self.dqn.state_dict())

        q_vals_max = q_vals_raw.max(1)[0]
        mean_v = q_vals_max.mean().item()
        return loss.item(), mean_v

"""
    # stable baselines 3 implementation
    def initialise(self, state_space, action-space, config: DQNConfig):
                policy="fullyconn",
                env=config.env,
                learning_rate=self.alpha,
                batch_size=1000000, # default 
                learning_starts=50000, # default
                gamma=self.gamma,
                train_freq=4, # default
                gradient_steps=3, # default
                replay_buffer_class=None, # default
                optimize_memory_usage=False, # default
                target_update_interval=10000, # default
                exploration_fraction=0.1, # default
                exploration_initial_eps=1.0, # default
                exploration_final_eps=0.05, # default
                max_grad_norm=10, # default
                device="auto" # default
            )
"""

class DQN(nn.Module):
    """A simple Deep Q-Network """

    def __init__(self, input_dim, layers, num_actions):
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(input_dim[0], layers[0])])
        for l in range(1, len(layers)):
            self.layers.append(nn.Linear(layers[l-1], layers[l]))
        self.out = nn.Linear(layers[-1], num_actions)

    def forward(self, x):
        for layer in self.layers:
            #print(layer)
            #print(x)
            #print(layer(x))
            x = F.relu(layer(x))
        x = self.out(x)
        return x

    def save_DQN(self, file_path):
        torch.save(self.state_dict(), file_path)

    def load_DQN(self, file_path):
        self.load_state_dict(torch.load(file_path))

    def get_action(self, x):
        print("egreedy action")
        with torch.no_grad():
            if len(x.shape) == 1:
               x = x.view(1, -1)
            out_vals = self.forward(x)   
            print(out_vals)
            #print(out_vals.max(1)[1])
            #return self.forward(x).max(1)[1]
            return out_vals.max(1)[1]

class ReplayMemory:

    def __init__(self, capacity, s_dims, device="cpu"):
        self.capacity = capacity
        self.device = device
        self.s_buf = np.zeros((capacity, *s_dims), dtype=np.float32)
        self.a_buf = np.zeros((capacity, 1), dtype=np.int64)
        self.next_s_buf = np.zeros((capacity, *s_dims), dtype=np.float32)
        self.r_buf = np.zeros(capacity, dtype=np.float32)
        self.done_buf = np.zeros(capacity, dtype=np.float32)
        self.ptr, self.size = 0, 0

    def store(self, s, a, next_s, r, done):
        self.s_buf[self.ptr] = s
        self.a_buf[self.ptr] = a
        self.next_s_buf[self.ptr] = next_s
        self.r_buf[self.ptr] = r
        self.done_buf[self.ptr] = done
        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size+1, self.capacity)

    def sample_batch(self, batch_size):
        sample_idxs = np.random.choice(self.size, batch_size)
        batch = [self.s_buf[sample_idxs],
                 self.a_buf[sample_idxs],
                 self.next_s_buf[sample_idxs],
                 self.r_buf[sample_idxs],
                 self.done_buf[sample_idxs]]
        return [torch.from_numpy(buf).to(self.device) for buf in batch]

