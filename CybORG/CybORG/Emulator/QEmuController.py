# This is the EmulationController class for QEmu/Libvirt emulation
# at the moment, this relies upon an externally provisioned environment on Qemu/Libvirt system
#
# upstream supports the AWSClientController, although hasn't publicly released the implementation
#
# We will implement a platform-agnostic controller as the Red team doesn't require any platform-specific
# functionality, and can interact with any specific platform implementation (client, virtual, bare-metal)

import inspect
import yaml
from ipaddress import IPv4Network
from CybORG import CybORG
from CybORG.Shared.EnvironmentController import EnvironmentController
from CybORG.Emulator.Session import MSFSessionHandler
from CybORG.Shared.Actions.Action import Action
from CybORG.Shared.Enums import FileType, TrinaryEnum
from CybORG.Shared.Observation import Observation
from CybORG.Shared.Results import Results
#from CybORG.Simulator.State import State
from CybORG.Emulator.ParameterState import ParameterState


class QEmuController(EnvironmentController):

   def __init__(self, scenario_filepath: str = None, scenario_mod: dict = None, agents: dict = None, **kwargs):
        # As the action parameter space is deterministic and fully known by the agent
        # we need to be able to ingest all possible parameters from the emulated environment configuration
        self.parameter_state = None
        self.session_handler = MSFSessionHandler()
        self.subnets = kwargs.get("subnets",None)
        self.hosts = kwargs.get("hosts",None)
        super().__init__(scenario_filepath, scenario_mod=scenario_mod, agents=agents, **kwargs)

   def reset(self, agent=None):
        print("QEmulationController reset")
        # call _create_environment??
        self._create_environment()
        #self.hostname_ip_map = {ip: h for ip, h in self.state.ip_addresses.items()}
        #self.subnet_cidr_map = self.state.subnet_name_to_cidr
        return super(QEmuController, self).reset(agent)

   def execute_action(self, action: Action) -> Observation:
        #print("emulator execute action")
        print(action)
        #print(self.session_handler)
        action_result_raw = action.emu_execute(self.session_handler)
        # emulated observations will primarily be ip address based
        # need to do a reverse lookup to get associated hostname
        # we need to be more robust around handling this and not
        # being able to perform this kind of lookup in the emulated case
        action_result = self._transform_result(action_result_raw)
        return action_result

   def _transform_result(self, result: Observation) -> Observation:
        obs = result.data
  
        # initially this only applies to hosts
        obs_hosts = obs["hosts"]
        new_obs_hosts = {}
        for host_k,host_v in obs_hosts.items():
            # if host key is an IP address
            if host_k in self.hostname_ip_map:
                new_obs_hosts[self.hostname_ip_map[host_k]] = host_v
            else:
                new_obs_hosts[host_k] = host_v
        print(new_obs_hosts)
        # add host key values to Observation
        result.add_key_value("hosts",new_obs_hosts)

        #obs_subnets = obs["network"]["subnets"]
        #new_obs_subnets = {}
        #for subnet_k,subnet_v in obs_subnets.items():
        #    if subnet_k in self.subnet_cidr_map:
        #        new_obs_subnets[self.subnet_cidr_map[subnet_k]] = subnet_k
        #    else:
        #        new_obs_subnets[subnet_k] = subnet_v
        #result.add_key_value("network",{ "subnets": new_obs_subnets })
        return result

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
        # need to get the host ips and subnet ranges from the emulated environment
        # perhaps hardcode this for now to match the deployed environment
        #self.hostname_ip_map = {ip: h for ip, h in self.state.ip_addresses.items()}
        #self.subnet_cidr_map = self.state.subnet_name_to_cidr
        # generate from the self.subnets and self.hosts provided
        self.hostname_ip_map = {}
        self.subnet_cidr_map = {}
        for name,cidr in self.subnets.items():
            print(name,cidr)
            self.subnet_cidr_map[name] = IPv4Network(cidr)

        for subnet in self.hosts:
            for name,ip_address in self.hosts[subnet].items():
                print(name,ip_address)
                self.hostname_ip_map[ip_address] = name

        #self.hostname_ip_map = { 
        #        "10.13.37.100": "Attacker0",
        #        "10.46.64.100": "External0",
        #        "10.58.85.10": "External0",
        #        "10.58.85.100": "Internal0",
        #        "10.58.85.101": "Internal1",
        #        "10.58.85.102": "Internal2"
        #}
        #"10.46.64.100": "Attacker0",
        #"10.58.85.100": "Attacker0",
        # following values have to be in IPv4Network format
        #self.subnet_cidr_map = {
        #        "Attacker": IPv4Network("10.13.37.0/24"),
        #        "External": IPv4Network("10.46.64.0/24"),
        #        "Internal": IPv4Network("10.58.85.0/24")
        #}
        #print(self.subnet_cidr_map)
        #print(self.hostname_ip_map)
        # for the moment we need to create an object for action parameter space generation
        # we wil reuse the Simulator State object for the moment, but this will be replaced
        # by a function that can ingest this information from the emulated environment itself.
        #
        # at the moment, the following object creation ingests all parameters EXCEPT subnet and host ip addresses
        # subnet and ip_address generation is done by the _initialise_state() function.  
        # I suppose for the emulated case, it is more apt to describe it as
        # _initialise_parameter_space()
        env_config = {
                "subnets": self.subnets,
                "hosts": self.hosts
                }
        self.parameter_state = ParameterState(self.scenario, env_config)

   def get_true_state(self, info: dict) -> Observation:
        output = self.parameter_state.get_true_state(info)
        return output


