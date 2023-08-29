import random
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from CybORG.Shared import Results
from CybORG.Shared.Actions import PrivilegeEscalate, ExploitRemoteService, DiscoverRemoteSystems, Impact, \
    DiscoverNetworkServices


class RedRandomAgent(BaseAgent):
    # a red agent that chooses random actions
    def __init__(self):
        pass

    def train(self, results: Results):
        """allows an agent to learn a policy"""
        pass

    def get_action(self, observation, action_space):
        """gets an action from the agent selected at random from the agent's action space"""
        action = random.randrange(0,action_space.get_max_actions())

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass
