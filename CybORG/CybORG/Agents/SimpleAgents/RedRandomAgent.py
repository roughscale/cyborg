import random
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from CybORG.Shared import Results
#from CybORG.Shared.Actions import PrivilegeEscalate, ExploitRemoteService, DiscoverRemoteSystems, Impact, \
#    DiscoverNetworkServices


class RedRandomAgent(BaseAgent):
    # a red agent that chooses random actions
    def __init__(self):
        pass

    def train(self, results: Results):
        """allows an agent to learn a policy"""
        pass

    def get_action(self, observation, action_space, egreedy):
        return action_space.sample()

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass

