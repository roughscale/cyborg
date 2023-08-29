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
path = path[:-10] + "/Shared/Scenarios/TestSessionKBScenario.yaml"
#print(path)

cyborg = CybORG(path,'sim')
#print(dir(cyborg))

# print env controller network state
environment=cyborg.environment_controller.environment
#print("Environment state:")
#pprint(environment.get_dict())
#print()
agent=cyborg.environment_controller.agent_interfaces["Red"]
unwrapped_action_space=agent.action_space.get_action_space()
#print("Unwrapped Action Space")
#pprint(unwrapped_action_space)
#print()
# cyborg class doesn't have an agent attribute
# therefore can't pass it to the EnumActionWrapper 
# which expects (env, agent) although defaults agent to None
env = cyborg
action_obj=env

#print(env)
#print(dir(env))
result = env.reset(agent="Red")
#print(results)
#print("Initial Action Space follwing Environment Reset")
#print(action_obj.possible_actions) # produces a list of the Action class objects of the enumerated space

#print("Initial Observation following Environment Reset")
#obs = result.observation
#print(obs)
#print()
#print("Initial State following Environment Reset")
#print(result.state)
#print(env.environment_controller)
#print("Red Agent Interface details")
agent = cyborg.environment_controller.agent_interfaces["Red"]
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
action_space=result.action_space
for step in range(0,200):
  #print("Step {0}".format(step))
  action=agent.get_action(result.next_state,result.observation,action_space)
  # keyboard agent returns Action object
  #print("Action: {0}".format(action))
  result = action_obj.step(agent=agent.agent_name,action=action)
  # result.observation is an Observation dict. With FlatFixed, it returns a fixed
  # size dict per observed host.
  #print("Observation")
  # the following produce the same
  #print(result.observation)
  #print(env.env.get_observation(agent="Red"))
  #print("observation change")
  #print(env.observation_change(result.observation))
  agent.update_state(result.observation)
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
