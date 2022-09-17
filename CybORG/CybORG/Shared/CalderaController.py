# Copyright DST Group. Licensed under the MIT license.
import copy
import inspect
from ipaddress import IPv4Network
from math import log2
from random import sample, choice
import yaml

from CybORG import CybORG
from CybORG.Shared.Actions import FindFlag, ShellSleep, SambaUsermapScript, UpgradeToMeterpreter, MSFEternalBlue, GetShell, \
    PingSweep
from CybORG.Shared.Actions.Action import Action
from CybORG.Shared.Enums import FileType, TrinaryEnum
from CybORG.Shared.EnvironmentController import EnvironmentController
from CybORG.Shared.Observation import Observation
from CybORG.Shared.Results import Results
from CybORG.Simulator.State import State


class CalderaController(EnvironmentController):
    """The class that interfaces with the Emulated Environment via the Caldera C2 framework.

    Inherits from Environment Controller then implements simulation-specific functionality.
    """
    def __init__(self, scenario_filepath: str = None, scenario_mod: dict = None, agents: dict = None, verbose=True):
        # not sure if we need this state (which is the Target environment FSM)
        #self.state = None
        super().__init__(scenario_filepath, scenario_mod=scenario_mod, agents=agents)

    def reset(self, agent=None):
        # need to reset the hostname_ip_maps and the subnet_cidr_map (most likely from 
        # a pre-generated file once the environment has been provisioned)
        #self.state.reset()
        self.hostname_ip_map = {h: ip for ip, h in self.state.ip_addresses.items()}
        self.subnet_cidr_map = self.state.subnet_name_to_cidr
        return super(SimulationController, self).reset(agent)

    def pause(self):
        pass

    def execute_action(self, action: Action) -> Observation:
        # this seems to be where the action is performed.

        # this is the old NASIM code. needs to be updated for CybOrg.
        if action.is_subnet_scan():
          # this is a remote action
          # where the action.target is actually the agent to run
          # the scan from
 
          # need to get the ability_name from the action:ability_name
          ability = action.name
          agent = get_agent(action.target)
          # we will assume single-homed host
          # take subnet space from the 1st interface (if there are more than 1)
          # however external_agent has a custom target subnet address space


          # this gets the untrimmed actions
          raw_action = await self._get_links(agent=agent, ability=ability)
          # now need to add the relevant facts to the link
          raw_action.facts=[Fact(trait='target.ip',value='192.168.121.8',score=1)]
          # and use planning_svc.add_test_variants to populate the commands vars
          # and generate link id
          actions = await self.planning_svc.add_test_variants([raw_action], agent, facts=raw_action.facts,
            operation=self.operation, trim_unset_variables=True, trim_missing_requirements=True)
          action = actions[0]
        else:
          agent = self.operation.agents[random.randrange(0,len(self.operation.agents))]
          possible_agent_links = await self._get_links(agent=agent)
          action = possible_agent_links[random.randrange(0,len(possible_agent_links))]

        if action:
          next_link=[]

          next_link.append(await self.operation.apply(action))

          await self.operation.wait_for_links_completion(next_link)

        #return action.sim_execute(self.state)
        # what does this return (a Results object??)

    def restore(self, file: str):
        pass

    def save(self, file: str):
        pass

    def get_true_state(self, info: dict) -> Observation:
        output = self.state.get_true_state(info)
        return output

    def shutdown(self, **kwargs):
        pass

    def _parse_scenario(self, scenario_filepath: str, scenario_mod: dict = None):
        scenario_dict = super()._parse_scenario(scenario_filepath, scenario_mod=scenario_mod)
        images_file_path = str(inspect.getfile(CybORG))
        images_file_path = images_file_path[:-10] + '/Shared/Scenarios/images/'
        with open(images_file_path + 'images.yaml') as fIn:
            images_dict = yaml.load(fIn, Loader=yaml.FullLoader)
        if scenario_dict is not None:
            for hostname, image in scenario_dict["Hosts"].items():
                if 'path' in images_dict[image["image"]]:
                    with open(images_file_path + images_dict[image["image"]]['path'] + '.yaml') as fIn2:
                        scenario_dict["Hosts"][hostname].update(
                            yaml.load(fIn2, Loader=yaml.FullLoader).pop('Test_Host'))
                    image.pop('image')
                else:
                    scenario_dict["Hosts"][hostname] = copy.deepcopy(images_dict[image["image"]])
        return scenario_dict

    def _create_environment(self):
        # generate the hostname_ip_map and subnet_cidr_map from a pre-generated YAML file
        # once the target emulation environment has been provisioned
        #self.state = State(self.scenario)
        self.hostname_ip_map = {h: ip for ip, h in self.state.ip_addresses.items()}
        self.subnet_cidr_map = self.state.subnet_name_to_cidr

    def run_schtasks(self):
        for host in self.hosts:
            host.run_scheduled_tasks(self.step)

    def get_last_observation(self, agent):
        return self.observation[agent]
