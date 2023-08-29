# Copyright DST Group. Licensed under the MIT license.
from CybORG.Shared import Scenario
from CybORG.Shared.Actions import FindFlag, Impact
from CybORG.Shared.Actions.Action import Action
from CybORG.Shared.Actions.AbstractActions.DiscoverNetworkServices import DiscoverNetworkServices
from CybORG.Shared.Actions.AbstractActions.ExploitRemoteService import ExploitRemoteService
from CybORG.Shared.Actions.AbstractActions.DiscoverRemoteSystems import DiscoverRemoteSystems
from CybORG.Shared.Actions.AbstractActions.PrivilegeEscalate import PrivilegeEscalate

from CybORG.Shared.Enums import OperatingSystemType, TrinaryEnum
from CybORG.Shared.RewardCalculator import RewardCalculator
from CybORG.Simulator.Session import RedAbstractSession
from pprint import pprint

WIN_REWARD = 0
LOSE_REWARD = 0
SESSION_REWARD = 0
ROOT_SESSION_REWARD = 0
LOSE_SESSION_REWARD = 0
LOSE_ROOT_SESSION_REWARD = 0

REWARD_MAX_DECIMAL_PLACES = 1


class GoalRewardCalculator(RewardCalculator):
    # this reward calculator provides rewards to Red related to a specific goal
    def __init__(self, agent_name: str, scenario: Scenario):
        super().__init__(agent_name)
        self.old_total = 0
        self.scenario = scenario
        self.mapping = {'None': 0.0,
                        'Low': 0.1,
                        'Medium': 1.0,
                        'High': 10.0}

        self.discovered_hosts = []
        self.compromised_hosts = []
        self.privileged_hosts = []
        self.discovered_subnets = []

    def reset(self):
        self.old_total = 0
        self.discovered_hosts = []
        self.compromised_hosts = []
        self.privileged_hosts = []
        self.discovered_subnets = []

    # assign reward when goal is done. set small penalty per action step.
    # don't set any 0 reward. this can train the agent to repeatedly prefer these actions over others
    def calculate_reward(self, state: dict, next_state: dict, true_state: dict, action_dict: dict, agent_observations: dict, done: bool):
        action = action_dict[self.agent_name]
        #print(action)
        action_success = agent_observations[self.agent_name].success
        #print(action_success)
        if done:
            reward = 100.0
        elif action_success == TrinaryEnum.TRUE:
            #print(state==next_state)
            if state == next_state:
                reward = -1.0 
            elif isinstance(action,DiscoverNetworkServices):
                if action.ip_address not in self.discovered_hosts:
                    self.discovered_hosts.append(action.ip_address)
                    reward = 1.0
                else:
                    reward = -1.0
            elif isinstance(action,ExploitRemoteService):
                if action.ip_address not in self.compromised_hosts:
                    self.compromised_hosts.append(action.ip_address)
                    reward = 1.0
                else:
                    reward = -1.0
            elif isinstance(action,DiscoverRemoteSystems):
                if action.subnet not in self.discovered_subnets:
                    self.discovered_subnets.append(action.subnet)
                    reward = 1.0
                else:
                    reward = -1.0
            elif isinstance(action,PrivilegeEscalate):
                if action.hostname not in self.privileged_hosts:
                    self.privileged_hosts.append(action.hostname)
                    reward = 1.0
                else:
                    reward = -1.0
            else:
                # at this moment, this will penalise successful Impact
                reward = -1.0
        else:
            reward = -1.0
        return round(reward, REWARD_MAX_DECIMAL_PLACES)
 
class PwnRewardCalculator(RewardCalculator):
    # this reward calculator provides a reward to Red due to changes in the number of privileged sessions
    def __init__(self, agent_name: str, scenario: Scenario):
        super().__init__(agent_name)
        self.old_total = 0
        self.scenario = scenario
        self.mapping = {'None': 0.0,
                        'Low': 0.1,
                        'Medium': 1.0,
                        'High': 10.0}

    def reset(self):
        self.old_total = 0

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool):
        root_sessions = 0
        system_sessions = 0
        #pprint(current_state['hosts'])
        for host, info in current_state['hosts'].items():
            # ignore external host processes
            if 'SystemInfo' in info and info['SystemInfo']['Hostname'] == "Attacker0":
                continue

            if 'Sessions' in info:
                for session in info['Sessions']:
                    if session['Agent'] == self.agent_name:
                        #print(host)
                        # count the number of root sessions
                        if session['Username'] == 'root' and info['SystemInfo']['OSType'] == OperatingSystemType.LINUX:
                            root_sessions += self.mapping[self.scenario.get_host(host).get('ConfidentialityValue', 'Low')]
                            break
                        # count the number of SYSTEM sessions
                        if session['Username'] == 'SYSTEM' and info['SystemInfo']['OSType'] == OperatingSystemType.WINDOWS:
                            system_sessions += self.mapping[self.scenario.get_host(host).get('ConfidentialityValue', 'Low')]
                            break

        # find the difference from the old privileged sessions
        total = root_sessions + system_sessions
        reward = total #- self.old_total
        self.old_total = total
        return round(reward, REWARD_MAX_DECIMAL_PLACES)


class DistruptRewardCalculator(RewardCalculator):
    # calculates the reward for disrupting the network
    def __init__(self, agent_name: str, scenario: Scenario):
        super(DistruptRewardCalculator, self).__init__(agent_name)
        self.scenario = scenario
        self.ots = None
        self.mapping = {'None': 0.0,
                        'Low': 0.1,
                        'Medium': 1.0,
                        'High': 10.0}

    def reset(self):
        self.ots = None

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool):
        # currently a single 1 reward is recieved if the Impact action is successful
        # TODO: Add in test to see what required services are up
        agent_action = action[self.agent_name]
        disrupted = []
        if self.ots is None:
            self.ots = []
            for host, info in current_state.items():
                if host == "Attacker0":
                    continue
                if type(info) is not dict:
                    continue
                if 'Processes' in info:
                    for proc in info['Processes']:
                        if proc['Process Name'] == 'OTService':
                            self.ots.append(info['System info']['Hostname'])
        for host,info in current_state['hosts'].items():
            working = False
            # ignore external host processes
            if 'SystemInfo' in info and info['SystemInfo']['Hostname'] == "Attacker0":
                continue
            if type(info) is not dict:
                continue
            if info['SystemInfo']['Hostname'] in self.ots:
                if 'Processes' in info:
                    for proc in info['Processes']:
                        if proc['Process Name'] == 'OTService':
                            working = True
                    if not working:
                        disrupted.append(info['System info']['Hostname'])
        # if type(agent_action) is Impact and agent_observations[self.agent_name].data['success'] == True:
        #     if agent_action.hostname not in disrupted:
        #         disrupted.append(agent_action.hostname)
        reward = sum([self.mapping[self.scenario.get_host(i).get('AvailabilityValue', 'Low')] for i in disrupted])
        return round(reward, REWARD_MAX_DECIMAL_PLACES)


class HybridImpactPwnRewardCalculator(RewardCalculator):
    # Hybrid of availability and confidentiality reward calculator
    def __init__(self, agent_name: str, scenario: Scenario):
        super(HybridImpactPwnRewardCalculator, self).__init__(agent_name)
        self.pwn_calculator = PwnRewardCalculator(agent_name, scenario)
        self.disrupt_calculator = DistruptRewardCalculator(agent_name, scenario)

    def reset(self):
        self.pwn_calculator.reset()
        self.disrupt_calculator.reset()

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool) -> float:
        reward = self.pwn_calculator.calculate_reward(current_state, action, agent_observations, done) \
                 + self.disrupt_calculator.calculate_reward(current_state, action, agent_observations, done)

        return round(reward, REWARD_MAX_DECIMAL_PLACES)
