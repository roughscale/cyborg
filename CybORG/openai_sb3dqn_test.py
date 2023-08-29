from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.FixedFlatStateWrapper import FixedFlatStateWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
#from CybORG.Agents.SimpleAgents.RedRandomAgent import RedRandomAgent
from CybORG.Shared.Results import Results
from CybORG.Shared.State import State
import inspect
import sys
import random
import time
import copy
import hashlib
import numpy as np
from pprint import pprint


# set vars
# initialise Q learning parameters
alpha = .5    # learning rate. NOT USED. Separate LR schedule is created
gamma = .99   # discount rate
initial_epsilon = 1.0 # high explore factor
final_epsilon = 0.02  # explore/exploit factor

#step_limit_reached=200
num_episodes=1000 # NOT USED. Total steps is used
#num_evals=100

total_steps=300000
double_dqn = False
dueling_dqn = True

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
path = path[:-10] + "/Shared/Scenarios/TestSessionSB3Scenario.yaml"
#print(path)

cyborg = CybORG(path,'sim')

# print env controller network state
environment=cyborg.environment_controller.environment
#print()
# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
unwrapped_action_space=agent.action_space.get_action_space()
wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg))
env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
# EnumAction Object
action_obj=env.env.env
#OpenAIGymWrapper reset only provides the Observation
# reset is now done in learn() method
#obs = env.reset(agent="Red")
#print("Initial Action Space follwing Environment Reset")
#print(action_obj.possible_actions) # produces a list of the Action class objects of the enumerated space

# print openaigym action and observation spaces
#print(env.action_space) # Discrete
#print(env.observation_space) # Box

#print("Initial Observation following Environment Reset")
#print(obs)
#print(type(obs))
#print()
#print(env.environment_controller)
unwrapped_state=agent.get_state()
#print(unwrapped_state)
state_list=env.env.observation_change(copy.deepcopy(unwrapped_state))
# for openai operations, state needs to be ndarray not python list
#state=np.array(state_list, dtype=np.float32)
state_space=env.observation_space
action_space=env.action_space

# initialise agent learning
#total_steps = num_episodes * step_limit_reached
agent.agent.initialise(env,state_space,gamma,alpha,initial_epsilon,final_epsilon,total_steps,num_episodes)
callback=agent.agent.learn_callback

done = False
terminal_states = set([])
total_states = set([])
start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
"""
  episodic_states = set([])
  ep_unique_states = set([])
  #print("episodic states: {}".format(episodic_states))
  step = 0
"""
agent.agent.dqn.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
"""
  # call Agent end_episode()
  agent.agent.end_episode()

  #print("Episodic states: {}".format(episodic_states))
  print("Num Episodic states {0}".format(len(episodic_states)))
  # get difference of episodic and total states
  # ie those elements unique to episodic
  ep_unique_states = episodic_states.difference(total_states)
  print("Num Unique episodic states: {}".format(len(ep_unique_states)))
  total_states.update(episodic_states)
  print("Num Total States: {}".format(len(total_states)))
  print()
  env.reset(agent="Red")
  unwrapped_state=agent.get_state()
  state=np.array(env.env.observation_change(copy.deepcopy(unwrapped_state)),dtype=np.float32)
  done = False
  terminal_states.add(next_obs_hash)
"""
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
"""
print("Number of episodes: {0} took {1} seconds".format(num_episodes,(end-start)))
print("number of terminal states: {0}".format(len(terminal_states)))
print()
print()
# evaluation phase
total_states = set([])
start=time.time()
goal=0
for ev in range(num_evals):
  print("Evaluation {}".format(ev))
  evaluation_states = set([])
  ev_unique_states = set([])
  #print("episodic states: {}".format(episodic_states))
  step = 0
  while not done and step <= step_limit_reached:
    print("Step {0}".format(step))
    action_num=agent.get_action(state, action_space, egreedy=False)
    print("Action Number: {0}".format(action_num))
    action=action_obj.possible_actions[action_num]
    print("Action: {0}".format(action))
    # wrapped step method needs an action_num (possible_actions index)
    observation, reward, done, info = env.step(action=action_num)
    # update state (this should already be done in the step function)
    #
    # agent.update_state(info["unwrapped_obs"])
    flattened_state = env.env.observation_change(copy.deepcopy(agent.get_state()))
    next_state = np.array(env.observation_change(flattened_state),dtype=np.float32)
    print("Reward: {0}".format(reward))
    print("Done: {0}".format(done))
    print()
    obs_hash = State.get_state_hash(np.array(state))
    next_obs_hash = State.get_state_hash(np.array(next_state))
    evaluation_states.add(obs_hash)
    evaluation_states.add(next_obs_hash)
    last_state = state
    state = next_state
    step += 1
  if done:
      print("Goal succeeded in {0} steps".format(step))
      goal += 1
  else:
      print("Evaluation step limit reached")

  print("Num Evaluation states {0}".format(len(evaluation_states)))
  # get difference of episodic and total states
  # ie those elements unique to episodic
  ev_unique_states = evaluation_states.difference(total_states)
  print("Num Unique Evaluation states: {}".format(len(ev_unique_states)))
  total_states.update(evaluation_states)
  print("Num Total States: {}".format(len(total_states)))
  print()
  env.reset(agent="Red")
  unwrapped_state=agent.get_state()
  state=np.array(env.env.observation_change(copy.deepcopy(unwrapped_state)),dtype=np.float32)
  done = False
  terminal_states.add(next_obs_hash)

end=time.time()
print("Evaluation end: {}".format(time.ctime(end)))
print("Number of Evaluations: {0} took {1} seconds".format(num_evals,(end-start)))
print("Num Successful evaluations {0}".format(goal))
"""
