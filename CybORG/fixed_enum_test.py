from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
import inspect
import sys
import random
import time
import copy
from pprint import pprint

# The getattr(Python Module) returns all Classes within that Module
#action_module = sys.modules['CybORG.Shared.Actions']
#print(dir(action_module))
path = str(inspect.getfile(CybORG))
#print(path)
#path = path[:-10] + "/Shared/Scenarios/Scenario1b.yaml"
# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
path = path[:-10] + "/Shared/Scenarios/TestSessionScenario.yaml"
#print(path)

cyborg = CybORG(path,'sim')
#print(dir(cyborg))

# print env controller network state
environment=cyborg.environment_controller.environment
#print("Environment state:")
#pprint(environment.get_dict())
print()
agent=cyborg.environment_controller.agent_interfaces["Red"]
unwrapped_action_space=agent.action_space.get_action_space()
#print("Unwrapped Action Space")
#pprint(unwrapped_action_space)
#print()
# cyborg class doesn't have an agent attribute
#print(cyborg.agent)
# therefore can't pass it to the EnumActionWrapper 
# which expects (env, agent) although defaults agent to None
#env = EnumActionWrapper(cyborg)
wrapped_env = FixedFlatWrapper(EnumActionWrapper(cyborg))
env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
action_obj=env.env.env
print(env)
print(dir(env))
# for EnumActionWrapper(), env.env is the CybORG object
print(env.env)
# FixedFlatWrapper(EnumActionWrapper)()) results in nested env.env.env structure?
#results = env.reset(agent="Red")
#OpenAIGymWrapper reset only provides the Observation
obs = env.reset(agent="Red")
#results = env.env.reset(agent="Red")
print("Initial Action Space follwing Environment Reset")
print(action_obj.possible_actions) # produces a list of the Action class objects of the enumerated space
# following is FixedFlatWrapper
#print(env.env.possible_actions) # produces a list of the Action class objects of the enumerated space
#print(results.action_space) # the wrapped method only returns the len of the enumerated space
#print(env.get_action_space(agent="Red")) # this returns the same as the wrapped method
print(env.action_space)
print(env.observation_space)

print("Initial Observation following Environment Reset")
obs = results.observation
print(obs)
# following is for FixedFlatWrapper
#print([ o for o in obs if o != float(-1) ])
print()
#print(env.environment_controller)
print("Red Agent Interface details")
agent = cyborg.environment_controller.agent_interfaces["Red"]
#print(env.agent) # None. Why?
#print(agent) # this is an AgentInterface
#print()
# The following lists the unwrapped agent_space
# It is not the "true" action space, ie the list of all available actions
# It lists the unwrapped action space which only lists the ActionClasses (not all 
# permutations of action parameters) as well as the agent's "internal state"
#unwrapped_action_space=agent.action_space.get_action_space()
#print("Get Agent action space:")
#pprint(action_space)
#action=env.get_action(results.observation, action_space)
#print(action)
# How do I get to choose an action from the wrapped action space??
# for now, choose a random int
action_space=results.action_space
for step in range(0,200):
  print("Step {0}".format(step))
  action_num=random.randrange(0,results.action_space)
  print("Action Number: {0}".format(action_num))
  action=action_obj.possible_actions[action_num]
  print("Action: {0}".format(action))
  # wrapped step method needs an action_num (possible_actions index)
  result = action_obj.step(agent=agent.agent_name,action=action_num)
  # result.observation is an Observation dict. With FlatFixed, it returns a fixed
  # size dict per observed host.
  print("Observation")
  # the following produce the same
  print(result.observation)
  #print(env.env.get_observation(agent="Red"))
  #print("observation change")
  #print(env.observation_change(result.observation))
  agent.update_state(result.observation)
  print("Get State() Unmarshalled")
  print(agent.get_state())
  print("Observation Change Get State() Marshalled into fixed array")
  flattened_obs = env.observation_change(copy.deepcopy(agent.get_state()))
  print(len(flattened_obs))
  print(flattened_obs)
  #print([ o for o in result.observation if o != float(-1) ])
  # following only prints number of total actions
  #pprint(result.action_space)
  print("Reward: {0}".format(result.reward))
  #pprint(result.reward)
  print("Done: {0}".format(result.done))
  action_space=results.action_space
  #print("Unwrapped Action Space")
  #pprint(agent.action_space.get_action_space())
  #time.sleep(1)
  print()
  if result.done:
      print("Goal succeeded")
      sys.exit(0)
