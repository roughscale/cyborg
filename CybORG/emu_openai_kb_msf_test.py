from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.FixedFlatStateWrapper import FixedFlatStateWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
#from CybORG.Agents.SimpleAgents.RedRandomAgent import RedRandomAgent
from CybORG.Shared.Results import Results
from CybORG.Shared.State import State
from stable_baselines3.common.env_util import make_vec_env
import inspect
import sys
import time
import copy
import os
import psutil
import subprocess

# until we learn how to reset the msfrpcd state (ie console and session ids)
# start msfrcpd
# this is a subprocess is attached to this process so will terminate when this process terminates
msfrcpd = subprocess.call(["/opt/metasploit-framework/bin/msfrpcd","-P","password"],close_fds=True)

# set vars
# initialise Q learning parameters
gamma = .99   # discount rate
initial_epsilon = 1.0 # high explore factor
final_epsilon = 0.02  # explore/exploit factor

# given larger action space.
total_steps=1000000
double=False
dueling=True

# set n_envs to 1 initially. No parallelisation
n_envs=1

path = str(inspect.getfile(CybORG))
curr_dir = os.getcwd()

# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
path = path[:-10] + "/Shared/Scenarios/TestMSFSessionKBScenario.yaml"
#print(path)

cyborg = CybORG(path,'qemu',fully_obs=True)

# print env controller network/environment state (ie not agent state!)
#environment=cyborg.environment_controller.state
#print()
# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
unwrapped_action_space=agent.action_space.get_action_space()
print("unwrapped action space")
print(unwrapped_action_space)
enum_env = EnumActionWrapper(cyborg)
print("enum wrapped env")
print(enum_env)
#wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg))
wrapped_env = FixedFlatStateWrapper(enum_env)
print(wrapped_env)
#env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
# wraps env in DummyVecEnv VecEnv environment
# no need for wrapped OpenAiGymWrapper for KB agent
#env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)
env = cyborg
# print openaigym action and observation spaces
print(agent.action_space) # Discrete

# initialise agent learning
#agent.agent.initialise(env,gamma,initial_epsilon,final_epsilon,total_steps,double,dueling)
#callback=agent.agent.learn_callback
start=time.time()
#print("Episodes start: {}".format(time.ctime(start)))
#print()
result = env.reset(agent="Red")
#print(result)
action_space=result.action_space
#print(action_space)
for step in range(0,200):
  #print("Step {0}".format(step))
  # with fully_obs, result.observation is result.state
  action=agent.get_action(result.observation,action_space)
  # keyboard agent returns Action object
  #print("Action: {0}".format(action))
  result = env.step(agent=agent.agent_name,action=action)
  # result.observation is an Observation dict. With FlatFixed, it returns a fixed
  # size dict per observed host.
  #print("Result")
  #
  #print(result)
  #print("Observation")
  # the following produce the same
  #print(result.observation)
  #print(env.get_observation(agent="Red"))
  # disable for non-wrapped envs
  #print("observation change")
  #print(env.observation_change(result.observation))
  # this is done with env.step if fully_obs is True
  # agent.update_state(result.observation)
  #print("Get State() Unmarshalled")
  #print(agent.get_state())
  #print("Observation Change Get State() Marshalled into fixed array")
  #flattened_obs = env.observation_change(copy.deepcopy(agent.get_state()))
  #print(len(flattened_obs))
  #print(flattened_obs)
  #print([ o for o in result.observation if o != float(-1) ])
  # following only prints number of total actions
  #pprint(result.action_space)
  print("Reward: {0}".format(result.reward))
  #pprint(result.reward)
  print("Done: {0}".format(result.done))
  action_space=result.action_space
  #print("Unwrapped Action Space")
  #pprint(agent.action_space.get_action_space())
  #time.sleep(1)
  print()
  if result.done:
      print("Goal succeeded")
      sys.exit(0)

#end=time.time()
#print("Episodes end: {}".format(time.ctime(end)))

