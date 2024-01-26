# This is the EmulationController class for QEmu/Libvirt emulation
# at the moment, this relies upon an externally provisioned environment on Qemu/Libvirt system
#
# upstream supports the AWSClientController, although hasn't publicly released the implementation
#
# We will implement a platform-agnostic controller as the Red team doesn't require any platform-specific
# functionality, and can interact with any specific platform implementation (client, virtual, bare-metal)

from CybORG.Shared.EnvironmentController import EnvironmentController
from CybORG.Emulator.Session import MSFSessionHandler
from CybORG.Shared.Actions.Action import Action
from CybORG.Shared.Enums import FileType, TrinaryEnum
from CybORG.Shared.Observation import Observation
from CybORG.Shared.Results import Results
from CybORG.Simulator.State import State


class QEmuController(EnvironmentController):

   def __init__(self, scenario_filepath: str = None, scenario_mod: dict = None, agents: dict = None, verbose=True, fully_obs=False):
        self.state = None
        self.session_handler = MSFSessionHandler()
        super().__init__(scenario_filepath, scenario_mod=scenario_mod, agents=agents, fully_obs=fully_obs)

   def reset(self, agent=None):
        print("QEmulationController reset")
        # call _create_environment??
        self._create_environment()
        #self.hostname_ip_map = {ip: h for ip, h in self.state.ip_addresses.items()}
        #self.subnet_cidr_map = self.state.subnet_name_to_cidr
        return super(EmulationController, self).reset(agent)

   def execute_action(self, action: Action) -> Observation:
        #print("emulator execute action")
        print(action)
        action_result = action.emu_execute(self.session_handler)
        return action_result

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
        self.hostname_ip_map = { 
                "10.37.37.100": "Attacker0",
                "10.46.64.100": "Attacker0",
                "10.58.85.100": "Attacker0",
                "10.46.64.101": "External0",
                "10.58.85.101": "Internal0",
                "10.37.37.100": "Internal1",
                "10.37.37.100": "Internal2"
                }
        self.subnet_cidr_map = {
                "Attacker": "10.37.37.0/24",
                "External": "10.46.64.0/24",
                "Internal": "10.58.85.0/24"
                }
        # for the moment we need to create a State object for action parameter space generation
        # this will need to be replaced by a function that can ingest this information from the
        # emulated environment itself.
        self.state = State(self.scenario)

   def get_true_state(self, info: dict) -> TrueState:
        output = self.state.get_true_state(info)
        return output


