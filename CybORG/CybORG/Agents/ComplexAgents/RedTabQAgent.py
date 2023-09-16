import random
import hashlib
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from gym import spaces
from CybORG.Shared import Results
from CybORG.Shared.State import State
import numpy as np


class RedTabQAgent(BaseAgent):

    """ a red agent that uses Tabular Q learning """
    def __init__(self):
        self.epsilon = 0
        self.alpha = 0
        self.gamma = 0
        self.Q = None

    def train(self, results: Results):
        """allows an agent to learn a policy"""
        """ Results object should have observation, next_observation, action, reward"""
        obs_hash = State.get_state_hash(np.array(results.observation))
        next_obs_hash = State.get_state_hash(np.array(results.next_observation))
        #oh = hashlib.new('sha256')
        #oh.update(np.array(results.observation).tobytes())
        #obs_hash = oh.hexdigest()
        #nh = hashlib.new('sha256')
        #nh.update(np.array(results.next_observation).tobytes())
        #next_obs_hash = nh.hexdigest()
        if next_obs_hash not in self.Q.keys():
            self.Q[next_obs_hash] = np.zeros(self.num_actions)
        if obs_hash not in self.Q.keys():
            self.Q[obs_hash] = np.zeros(self.num_actions)
        #print("alpha: {}".format(self.alpha))
        #print("gamma: {}".format(self.gamma))
        #print("Q(s,a): {}".format(self.Q[obs_hash][results.action]))
        #print("Q(s',a'): {}".format(np.max(self.Q[next_obs_hash])))
        #print("a * (r + g.Q(s',a') - Q(s,a')): {}".format(self.alpha * (results.reward + self.gamma *  np.max(self.Q[next_obs_hash]) - self.Q[obs_hash][results.action])))
        self.Q[obs_hash][results.action] += self.alpha * (results.reward + self.gamma * np.max(self.Q[next_obs_hash]) - self.Q[obs_hash][results.action])
        #print("Q(s,a): {}".format(self.Q[obs_hash][results.action]))
        #print("obs_hash, next_obs_hash, Q(s,:): {} {} {}".format(obs_hash,next_obs_hash,self.Q[obs_hash]))
        return obs_hash, next_obs_hash

    def get_action(self, observation, action_space, egreedy=True):

        if isinstance(action_space, spaces.Discrete):
            if egreedy and np.random.uniform() < self.epsilon:
                #print("random action")
                # built-in random sample action
                action = action_space.sample()
            else:
                h = hashlib.new('sha256')
                h.update(np.array(observation).tobytes())
                obs_hash = h.hexdigest()
                if obs_hash not in self.Q.keys():
                   #print("obs_hash not in Q function. random action")
                   action = action_space.sample()
                else:
                   #print("obs_hash in Q function. greedy action")
                   #print(self.Q[obs_hash])
                   action = np.random.choice(np.argwhere(self.Q[obs_hash] == np.max(self.Q[obs_hash])).transpose()[0])
                   #print(action)
            return action

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass

    def initialise(self, state_space, action_space, config):
        """ set up Tab Q function """
        """ use lazy loading of Q function.  we will append states to each action row """
        #self.Q = np.zeros(action_space.n,)
        self.Q = {}
        self.num_actions = action_space.n
        self.epsilon = config["epsilon"]
        self.gamma = config["gamma"]
        self.alpha = config["alpha"]


