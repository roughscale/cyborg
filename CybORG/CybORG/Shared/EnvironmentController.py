## The following code contains work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105.
## Additionally, we waive copyright and related rights in the utilized code worldwide through the CC0 1.0 Universal public domain dedication.

import sys
import yaml
import copy

from CybORG.Shared import Scenario
from CybORG.Shared.Actions.Action import Sleep, InvalidAction
from CybORG.Shared.Enums import FileType, OperatingSystemType
from CybORG.Shared.Results import Results
from CybORG.Shared.Observation import Observation
from CybORG.Shared.Actions import Action, FindFlag, Monitor
from CybORG.Shared.AgentInterface import AgentInterface
from CybORG.Simulator.TrueState import TrueState

import CybORG.Agents


class EnvironmentController:
    """The abstract base controller for all CybORG environment controllers.

    Provides the abstract methods which all CybORG controllers must implement. This includes setup and teardown,
    modifying the state, and pulling out data from the environment.
    When both Simulation and Emulation share common functionality, it is implemented here.


    Attributes
    ----------
    scenario_dict : dict
        the scenario data
    agent_interfaces : dict[str: AgentInterface]
        agent interface object for agents in scenario
    """

    def __init__(self, scenario_path: str, scenario_mod: dict = None, agents: dict = None, **kwargs):
        """Instantiates the Environment Controller.
        Parameters
        ----------
        scenario_path : str
            path to scenario YAML file
        agents : dict, optional
            map from agent name to agent interface of agents to be used in
            environment. If None agents will be loaded from description in
            scenario file (default=None)
        """
        # The following maps seem to have a very limited purpose
        # hostname_ip_map only seems to be used in the _filter_obs() method
        # to pass to the Observation.filter_addresses() method
        # since ip to hostname is unique (hostname to ip is not unique)
        # the map should be in the format { ip: hostname }
        self.hostname_ip_map = None
        self.subnet_cidr_map = None
        # self.scenario_dict = self._parse_scenario(scenario_path, scenario_mod=scenario_mod)
        scenario_dict = self._parse_scenario(scenario_path)
        self.scenario = Scenario(scenario_dict)
        self.fully_obs = kwargs.get("fully_obs",False)
        self._create_environment()
        self.agent_interfaces = self._create_agents(agents)
        self.reward = {}
        self.INFO_DICT = {}
        self.action = {}
        self.done = False
        self.observation = {}
        self.INFO_DICT['True'] = {"hosts": {}, "network": { "subnets": [] } }
        for subnet in self.scenario.subnets:
            # true info dict needs name of subnet not CIDR (which can change)
            #subnet_cidr = self.subnet_cidr_map[subnet]
            self.INFO_DICT['True']['network']['subnets'].append(subnet)
        for host in self.scenario.hosts:
            self.INFO_DICT['True']['hosts'][host] = {'SystemInfo': 'All', 'Sessions': 'All', 'Interfaces': 'All', 'UserInfo': 'All',
                                      'Processes': ['All']}

        # This uses the INFO_DICT as a filter to generate the complete State of the Target Environment.
        #print("INFO_DICT['True']")
        #print(self.INFO_DICT['True'])
        true_state = self.get_true_state(self.INFO_DICT['True'])
        #print("Get True State of INFO_DICT['True']")
        #print(true_state)
        # this is stripping the interface information from the true state!
        true_state_filtered_obs = self._filter_obs(true_state)
        #print("Filtered Obs of Get True State")
        #print(true_state_filtered_obs)
        #self.init_state = self._filter_obs(self.get_true_state(self.INFO_DICT['True'])).data
        self.init_state = true_state_filtered_obs.data
        # the following generates the initial information of the Target Environment of each agent into INFO_DICT[agent]
        self._get_agent_osint()

        # populate initial observations with OSINT
        #print(self.agent_interfaces.items())
        for agent_name, agent in self.agent_interfaces.items():
            #print("agent osint state")
            #print(self.get_true_state(self.INFO_DICT[agent_name]))
            self.observation[agent_name] = self._filter_obs(self.get_true_state(self.INFO_DICT[agent_name]), agent_name)
            #print("set agent init obs")
            #print(self.observation[agent_name].data)
            agent.set_init_obs(self.observation[agent_name].data, self.init_state)

    def _get_agent_osint(self):
        #print("_get_agent_osint")
        for agent in self.scenario.agents:
            self.INFO_DICT[agent] = {}
            osint_network = self.scenario.get_agent_info(agent).osint.get('Network',{})
            #print(osint_network)
            if 'Subnets' in osint_network:
                #print(osint_network['Subnets'])
                #print([v for k,v in self.subnet_cidr_map.items() if k in osint_network['Subnets']])
                self.INFO_DICT[agent]['network'] = {}
                self.INFO_DICT[agent]['network']['subnets'] = [ k for k, v in self.subnet_cidr_map.items() if k in osint_network['Subnets'] ]
            osint_hosts = self.scenario.get_agent_info(agent).osint.get('Hosts', {})
            for hostname,hostinfo in osint_hosts.items():
                self.INFO_DICT[agent]['hosts'] = {}
                # assuming OSINT only provides 1 address per hostname
                #hostip = str([ k for k,v in self.hostname_ip_map.items() if v == hostname ][0])
                hostid = hostname
                self.INFO_DICT[agent]['hosts'][hostid] = hostinfo
                #print(self.INFO_DICT[agent]['hosts'][hostid])
            for host in self.INFO_DICT[agent]['hosts'].keys():
                self.INFO_DICT[agent]['hosts'][host]['Sessions'] = agent
        #print(self.INFO_DICT[agent])

    def reset(self, agent: str = None) -> Results:
        """Resets the environment and get initial agent observation and actions.

        Parameters
        ----------
        agent : str, optional
            the agent to get initial observation for, if None will return
            initial white state (default=None)

        Returns
        -------
        Results
            The initial observation and actions of a agent or white team
        """
        self.reward = {}
        self.steps = 0
        self.done = False
        if self.fully_obs:
          pass
        #print("EnvController reset")
        #print("info dict true")
        #print(self.INFO_DICT['True'])
        self.init_state = self._filter_obs(self.get_true_state(self.INFO_DICT['True'])).data
        #print("agent init_state. filtered info dict true")
        #print(self.init_state)
        for agent_name, agent_object in self.agent_interfaces.items():
            agent_object.reset()
            # get Agent OSINT
            self._get_agent_osint()
            #print("info dict agent name")
            #print(self.INFO_DICT[agent_name])
            agent_obs = self.get_true_state(self.INFO_DICT[agent_name])
            #print(agent_obs)
            filtered_agent_obs = self._filter_obs(agent_obs, agent_name)
            #print(filtered_agent_obs)
            self.observation[agent_name] = self._filter_obs(self.get_true_state(self.INFO_DICT[agent_name]), agent_name)
            agent_object.set_init_obs(self.observation[agent_name].data, self.init_state)
            #print("agent object obs")
            #print(agent_object)
            if self.fully_obs:
              # at the moment we don't store state as object attribute due to name clash with State objects
              state = {}
              state[agent_name] = agent_object.get_state()
              #print("agent object state")
              #print(state[agent_name])
            #print("action space size: {}".format(agent_object.action_space.get_action_space_size()))

        if agent is None:
            return Results(observation=self.init_state)
        else:
            if self.fully_obs:
                # why do we need both state and next_state (is this to short circuit the reward if state doesn't change?)
                # if so, can we handle that in the reward calculation and then collapse state as observation.
                # only use state.  should also see if we can collapse into observation
                return Results(observation=self.observation[agent].data, state=state,
                           action_space=self.agent_interfaces[agent].action_space.get_action_space())
            else:
                return Results(observation=self.observation[agent].data,
                           action_space=self.agent_interfaces[agent].action_space.get_action_space())

    def step(self, agent: str = None, action: Action = None, skip_valid_action_check: bool = False) -> Results:
        """Perform a step in the environment for given agent.

        Parameters
        ----------
        agent : str, optional
            the agent to perform step for (default=None)
        action : Action/
            the action to perform

        Returns
        -------
        Results
            the result of agent performing the action
        """

        # for each agent:
        next_observation = {}
        next_state = {}
        #print("env step")
        #print("step action var")
        #print(type(action)) # of type Action but has custom __str__ method
        print(action)
        # all agents act on the state
        for agent_name, agent_object in self.agent_interfaces.items():
            # pass observation to agent to get action

            if agent is None or action is None or agent != agent_name:
                agent_action = agent_object.get_action(self.observation[agent_name])

            else:
                agent_action = action
            if not self.test_valid_action(agent_action, agent_object) and not skip_valid_action_check:
                agent_action = InvalidAction()
            self.action[agent_name] = agent_action

            # perform action on (environment) state and get an observation
            next_observation[agent_name] = self._filter_obs(self.execute_action(self.action[agent_name]), agent_name)
            #print("next observation following env.step()")
            #print(type(next_observation[agent_name]))
            print(next_observation[agent_name])
            #print("next obnservation processes")
            #if "hosts" in next_observation[agent_name].data:
            #    for h in next_observation[agent_name].data["hosts"]:
            #        if "Processes" in h:
            #            print(h["Processes"])

            if self.fully_obs:
              # why do we need to do deepcopy? Do we mutate the object in update_state??
              agent_object.update_state(copy.deepcopy(next_observation[agent_name]))
              next_state[agent_name] = agent_object.get_state()
              #print(agent_object.get_max_elements())
              #print(type(next_state[agent_name]))
              print(next_state[agent_name])

        # get true observation
        #print("get true observation")
        true_observation = self._filter_obs(self.get_true_state(self.INFO_DICT['True'])).data

        # Blue update step.
        # New idea: run the MONITOR action for the Blue agent, and update the observation.

        # pass training information to agents
        for agent_name, agent_object in self.agent_interfaces.items():

            # determine done signal for agent
            done = self.determine_done(next_observation, true_observation, self.action[agent_name])
            self.done = done or self.done
            # determine reward for agent
            if self.fully_obs:
              # see if we can remove this by treating next_observation as next_state!
              # this differs from original FO implementation as next_state should be able to be used in place
              # of next_observation in the FO case.
              reward = agent_object.determine_reward(next_state, true_observation,
                                                   self.action, self.done)
            else:
              reward = agent_object.determine_reward(next_observation, true_observation,
                                                   self.action, self.done)
            self.reward[agent_name] = reward + self.action[agent_name].cost
            # the following is commented out in the FO case.  Not sure why
            """
            if agent_name != agent:
                # train agent using obs, reward, previous observation, and done
                agent_object.train(Results(observation=self.observation[agent_name].data, reward=reward,
                                           next_observation=next_observation[agent_name].data, done=self.done))
            """
            self.observation[agent_name] = next_observation[agent_name]
            # this updates the agent parameter space to set parameters as known from the observation
            agent_object.update(self.observation[agent_name])

            # if self.verbose and type(self.action[agent_name]) != Sleep and self.observation[agent_name].dict['success'] == True:
            #    print(f"Step: {self.steps}, {agent_name}'s Action Choice: {type(self.action[agent_name]).__name__}, "
            #          f"Reward: {reward}")

        # Update Blue's observation with the latest information before returning.
        for agent_name, agent_object in self.agent_interfaces.items():
            if agent_name == 'Blue':
                agent_session = list(self.get_action_space(agent_name)['session'].keys())[0]
                agent_observation = self._filter_obs(
                    self.execute_action(Monitor(session=agent_session, agent='Blue')), agent_name)
                first_action_success = self.observation[agent_name].success
                self.observation[agent_name].combine_obs(agent_observation)
                self.observation[agent_name].set_success(first_action_success)
                agent_object.update(self.observation[agent_name])
        # if done then complete other agent's turn

        if agent is None:
            result = Results(observation=true_observation, done=self.done)
        else:
            if self.fully_obs:
               # the original FO impl passed state and next_state.  See if we can get away with just state (and more importantly, see if we
               # can return this as observation.
               # note that state is actually next_state (just as observation is actually next_observation)
               # self.observation[agent] is an Observation (contains .data attribute).  how is this generated, when next_observation[agent_name] is only a dict
               # next_state[agent] is only a dict
               # see if we can substitute state for observation
               #result = Results(observation=self.observation[agent].data, state=next_state[agent], done=self.done, reward=round(self.reward[agent], 1),
               result = Results(observation=next_state[agent].data, done=self.done, reward=round(self.reward[agent], 1),
                             action_space=self.agent_interfaces[agent].action_space.get_action_space(),
                             action=self.action[agent])
            else:
               result = Results(observation=self.observation[agent].data, done=self.done, reward=round(self.reward[agent], 1),
                             action_space=self.agent_interfaces[agent].action_space.get_action_space(),
                             action=self.action[agent])
        return result

    def execute_action(self, action: Action) -> Observation:
        """Execute an action in the environment"""
        raise NotImplementedError

    def determine_done(self,
                       agent_obs: dict,
                       true_obs: dict,
                       action: Action) -> bool:
        """Determine if environment scenario goal has been reached.

        Parameters
        ----------
        agent_obs : dict
            the agents last observation
        true_obs : dict
            the current white state
        action : Action
            the agents last action performed

        Returns
        -------
        bool
            whether goal was reached or not
        """
        # goal is to successfully escalate priv to root on Internal2 host
        obs = agent_obs["Red"].get_dict()["hosts"]
        #print("determine done obs")
        #print(obs)
        if "Internal2" in obs:
            if "Sessions" in obs["Internal2"]:
                for sess in obs["Internal2"]["Sessions"]:
                    if "Username" in sess and sess["Username"] == "root":
                           return True
        return False

    def start(self, steps: int = None, log_file=None):
        """Start the environment and run for a specified number of steps.

        Parameters
        ----------
        steps : int
            the number of steps to run for
        log_file : File, optional
            a file to write results to (default=None)

        Returns
        -------
        bool
            whether goal was reached or not
        """
        done = False
        max_steps = 0
        if steps is None:
            while not done:
                max_steps += 1
                _, _, done = self.step()
            print('Red Wins!')  # Junk Test Code
        else:
            for step in range(steps):
                max_steps += 1
                results = self.step()
                done = results.done
                if step == 500:
                    print(step)  # Junk Test Code
                if done:
                    print(f'Red Wins at step {step}')  # Junk Test Code
                    break
        for agent_name, agent in self.agent_interfaces.items():
            agent.end_episode()
            # print(f"{agent_name}'s Reward: {self.reward[agent_name]}")
        if log_file is not None:
            log_file.write(
                f"{max_steps},{self.reward['Red']},{self.reward['Blue']},"
                f"{self.agent_interfaces['Red'].agent.epsilon},"
                f"{self.agent_interfaces['Red'].agent.gamma}\n"
            )
        return done

    # Is this needed for the Emulated case??
    def get_true_state(self, info: dict) -> TrueState:
        """Get current True state

        Returns
        -------
        Observation
            current true state
        """
        raise NotImplementedError

    def get_agent_state(self, agent_name: str) -> Observation:
        return self.get_true_state(self.INFO_DICT[agent_name])

    def get_last_observation(self, agent: str) -> Observation:
        """Get the last observation for an agent

        Parameters
        ----------
        agent : str
            name of agent to get observation for

        Returns
        -------
        Observation
            agents last observation
        """
        return self.observation[agent]

    def get_action_space(self, agent: str) -> dict:
        """
        Gets the action space for a chosen agent
        agent: str
            agent selected
        """
        if agent in self.agent_interfaces:
            return self.agent_interfaces[agent].action_space.get_action_space()
        raise ValueError(f'Agent {agent} not in agent list {self.agent_interfaces.values()}')

    def get_observation_space(self, agent: str) -> dict:
        """
                Gets the observation space for a chosen agent
                agent: str
                    agent selected
                """
        if agent in self.agent_interfaces:
            return self.agent_interfaces[agent].get_observation_space()
        raise ValueError(f'Agent {agent} not in agent list {self.agent_interfaces.values()}')

    def get_last_action(self, agent: str) -> Action:
        """
                Gets the observation space for a chosen agent
                agent: str
                    agent selected
                """
        return self.action[agent] if agent in self.action else None



    def restore(self, filepath: str):
        """Restores the environment from file

        Parameters
        ----------
        filepath : str
            path to file to restore env from
        """
        raise NotImplementedError

    def save(self, filepath: str):
        """Saves the environment to file

        Parameters
        ----------
        filepath : str
            path to file to save env to
        """
        raise NotImplementedError

    def pause(self):
        """Pauses the environment"""
        pass

    def shutdown(self, teardown: bool = True) -> bool:
        """Shutdown environment, deleting/terminating resources
        as required

        Parameters
        ----------
        teardown : bool, optional
            if True environment resources will be terminated if applicable,
            otherwise resources will not be terminated (allowing them to be
            reused if desired) (default=True)

        Returns
        -------
        bool
            True if the environment was shutdown without issue
        """
        raise NotImplementedError

    def _parse_scenario(self, scenario_file_path: str, scenario_mod: dict = None):
        with open(scenario_file_path) as fIn:
            scenario_dict = yaml.load(fIn, Loader=yaml.FullLoader)
        return scenario_dict

    def _create_agents(self, agent_classes: dict = None) -> dict:
        agents = {}

        for agent_name in self.scenario.agents:
            agent_info = self.scenario.get_agent_info(agent_name)
            if agent_classes is not None and agent_name in agent_classes:
                agent_class = agent_classes[agent_name]
            else:
                agent_class = getattr(sys.modules['CybORG.Agents'],
                                      agent_info.agent_type)
            agents[agent_name] = AgentInterface(
                agent_class,
                agent_name,
                agent_info.actions,
                agent_info.reward_calculator_type,
                allowed_subnets=agent_info.allowed_subnets,
                external_hosts=agent_info.external_hosts,
                wrappers=agent_info.wrappers,
                scenario=self.scenario,
                fully_obs=self.fully_obs
            )
        return agents

    def _create_environment(self):
        raise NotImplementedError

    def _filter_obs(self, obs: Observation, agent_name=None):
        """Filter obs to contain only hosts/subnets in scenario network """
        if agent_name is not None:
            subnets = [self.subnet_cidr_map[s] for s in self.scenario.get_agent_info(agent_name).allowed_subnets]
            # need to add external_subnets as well. so that observations relating to external subnets are not filtered
            #print("filter obs external_subnets")
            #print(self.scenario.get_agent_info(agent_name).external_subnets)
            subnets.extend([self.subnet_cidr_map[s] for s in self.scenario.get_agent_info(agent_name).external_subnets])
        else:
            subnets = list(self.subnet_cidr_map.values())

        #print("_filter_obs subnets list")
        #print(subnets)
        # this is generating the proper list of subnets
        # cidrs needs to be in IPV4Network format!
        obs.filter_addresses(
            ips=self.hostname_ip_map.keys(),
            cidrs=subnets,
            include_localhost=False
        )
        return obs

    def test_valid_action(self, action: Action, agent: AgentInterface):
        # returns true if the parameters in the action are in and true in the action set else return false
        action_space = agent.action_space.get_action_space()
        #print(action)
        #print(action_space)
        #print(action.get_params())
        # first check that the action class is allowed
        if type(action) not in action_space['action'] or not action_space['action'][type(action)]:
            return False
        # next for each parameter in the action
        for parameter_name, parameter_value in action.get_params().items():
            #print(parameter_name,parameter_value)
            if parameter_name not in action_space:
                # what happens if no parameter_name is in action_space, it will return True??
                print("parameter name {} not in action_space".format(parameter_name))
                continue
            if parameter_value not in action_space[parameter_name]:
                print("parameter value {} not in parameter name {}".format(parameter_value, parameter_name))
                return False
            if not action_space[parameter_name][parameter_value]:
                print("parameter {}/{} not known".format(parameter_name,parameter_value))
                return False
        return True



