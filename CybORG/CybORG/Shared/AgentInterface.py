# Copyright DST Group. Licensed under the MIT license.

import sys
import pprint

from CybORG.Shared import Scenario
from CybORG.Shared.ActionSpace import ActionSpace
from CybORG.Shared.Actions.Action import Action
from CybORG.Shared.BaselineRewardCalculator import BaselineRewardCalculator
from CybORG.Shared.BlueRewardCalculator import HybridAvailabilityConfidentialityRewardCalculator
from CybORG.Shared.Observation import Observation
from CybORG.Shared.RedRewardCalculator import DistruptRewardCalculator, PwnRewardCalculator, \
    HybridImpactPwnRewardCalculator, GoalRewardCalculator
from CybORG.Shared.Results import Results
from CybORG.Shared.RewardCalculator import RewardCalculator, EmptyRewardCalculator
from CybORG.Shared.State import State

# Unused in this Object
# MAX values are used in the ActionSpace object to determine max action space length
# and also in the FlatWrapper to determine max observation vector length
#MAX_HOSTS = 5
#MAX_PROCESSES = 10    # 50
#MAX_CONNECTIONS = 10
#MAX_VULNERABILITIES = 1
#MAX_INTERFACES = 4
#MAX_FILES = 10
#MAX_SESSIONS = 10    # 80
#MAX_USERS = 10
#MAX_GROUPS = 10
#MAX_PATCHES = 10


class AgentInterface:

    def __init__(self,
                 agent_class,
                 agent_name,
                 actions,
                 reward_calculator_type,
                 allowed_subnets,
                 external_hosts,
                 scenario,
                 fully_obs=False,
                 wrappers=None):
        # the following seem to be "internal state" attributes of the agent
        # they should be removed in favour of the Observation space
        self.hostname = {}
        self.username = {}
        self.group_name = {}
        self.process_name = {}
        self.interface_name = {}
        self.path = {}
        self.password = {}
        self.password_hash = {}
        self.file = {}
        #
        self.actions = actions
        self.reward_calculator_type = reward_calculator_type
        self.last_action = None
        self.scenario = scenario
        self.reward_calculator = self.create_reward_calculator(
            self.reward_calculator_type, agent_name, scenario
        )
        self.agent_name = agent_name
        #print("agent interface")
        #print(self.actions) # this is a list of Strings
        self.action_space = ActionSpace(self.actions, agent_name, allowed_subnets, external_hosts)
        # action space references class objects
        #print(self.action_space)
        self.agent = agent_class()
        if wrappers is not None:
            for wrapper in wrappers:
                if wrapper != 'None':
                    self.agent = getattr(sys.modules['CybORG.Agents.Wrappers'], wrapper)(agent=self.agent)
        # this method for Red Agent does nothing
        self.agent.set_initial_values(
            action_space=self.action_space.get_max_action_space(),
            observation=Observation().data
        )
        self.fully_obs = fully_obs
        if self.fully_obs:
            self.state_space = State()
            self.state_space.initialise_state(scenario)
        else:
            self.state_space = None


    def update(self, obs: dict, known=True):
        if isinstance(obs, Observation):
            obs = obs.data
        # updates the action space parameters
        self.action_space.update(obs, known)

    def update_state(self, obs):
        self.state_space.update(obs)

    def get_state(self):
        return self.state_space.get_state()

    def set_init_obs(self, init_obs, true_obs):
        if isinstance(init_obs, Observation):
            init_obs = init_obs.data
        if isinstance(true_obs, Observation):
            true_obs = true_obs.data
        # this sets "all" attributes of the agent's internal state to False/unknown
        self.update(true_obs, False)
        # this sets "specified" attributes to True/known
        self.update(init_obs, True)
        # update state if fullyobs
        if self.fully_obs
          self.update_state(init_obs)
          # not sure why these following 2 are required for reward_calculator
          # this has been removed in the reward calculator class
          # remove it not required
          #self.reward_calculator.previous_state = true_obs
          #self.reward_calculator.init_state = true_obs
        self.reward_calculator.previous_obs = init_obs
        self.reward_calculator.init_obs = init_obs

    def get_action(self, observation: Observation, action_space: ActionSpace, egreedy=True):
        """Gets an action from the agent to perform on the environment"""
        if isinstance(observation, Observation):
            observation = observation.data
        if action_space is None:
            action_space = self.action_space
        self.last_action = self.agent.get_action(observation, action_space, egreedy)
        return self.last_action

    def train(self, result: Results):
        """Trains an agent with the new tuple from the environment"""
        if isinstance(result.observation, Observation):
            result.observation = result.observation.data
        if isinstance(result.next_observation, Observation):
            result.next_observation = result.next_observation.data
        result.action = self.last_action
        obs_hash, next_obs_hash, loss, mean_v = self.agent.train(result)
        return obs_hash, next_obs_hash, loss, mean_v

    def end_episode(self):
        self.agent.end_episode()
        self.reset()

    def reset(self):
        self.hostname = {}
        self.username = {}
        self.group_name = {}
        self.process_name = {}
        self.interface_name = {}
        self.path = {}
        self.password = {}
        self.password_hash = {}
        self.file = {}
        self.reward_calculator.reset()
        self.action_space.reset(self.agent_name)
        self.agent.end_episode()
        if self.fully_obs:
          self.state_space = State()
          self.state_space.initialise_state(self.scenario)

    def create_reward_calculator(self, reward_calculator: str, agent_name: str, scenario: Scenario) -> RewardCalculator:
        calc = None
        if reward_calculator == "Baseline":
            calc = BaselineRewardCalculator(agent_name)
        elif reward_calculator == 'Pwn':
            calc = PwnRewardCalculator(agent_name, scenario)
        elif reward_calculator == 'Disrupt':
            calc = DistruptRewardCalculator(agent_name, scenario)
        elif reward_calculator == 'None' or reward_calculator is None:
            calc = EmptyRewardCalculator(agent_name)
        elif reward_calculator == 'HybridAvailabilityConfidentiality':
            calc = HybridAvailabilityConfidentialityRewardCalculator(agent_name, scenario)
        elif reward_calculator == 'HybridImpactPwn':
            calc = HybridImpactPwnRewardCalculator(agent_name, scenario)
        elif reward_calculator == 'Goal':
            calc = GoalRewardCalculator(agent_name, scenario)
        else:
            raise ValueError(f"Invalid calculator selection: {reward_calculator} for agent {agent_name}")
        return calc

    def determine_reward(self, agent_obs: dict, true_obs: dict, action: Action, done: bool) -> float:
        return self.reward_calculator.calculate_reward(current_state=true_obs, action_dict=action,
                                                       agent_observations=agent_obs, done=done)

    # The following is in the original FO implementation.  Don't think it is requried any more.
    # Commented out to test
    #def determine_reward_fullyobs(self, agent_obs: dict, true_obs: dict, action: Action, done: bool, state: dict={}, next_state: dict={}) -> float:
    #    return self.reward_calculator.calculate_reward_fullyobs(state=state, next_state=next_state, true_state=true_obs, action_dict=action,

    def get_observation_space(self):
        # returns the maximum observation space for the agent given its action set and the amount of parameters in the environment
        raise NotImplementedError

    def __str__(self):
        output = [f"{self.__class__.__name__}:"]
        for attr, v in self.__dict__.items():
            if v is None:
                continue
            if isinstance(v, dict):
                v_str = pprint.pformat(v)
            else:
                v_str = str(v)
            output.append(f"{attr}={v_str}")
        return "\n".join(output)

