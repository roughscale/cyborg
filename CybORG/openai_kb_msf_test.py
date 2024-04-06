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

path = path[:-10] + "/Shared/Scenarios/TestMSFSessionKBScenario.yaml"

cyborg = CybORG(path,'sim',fully_obs=True)

env = cyborg

start=time.time()
result = env.reset(agent="Red")
action_space=result.action_space
#print(action_space)
for step in range(0,200):
  action=agent.get_action(result.observation,action_space)
  result = env.step(agent=agent.agent_name,action=action)
  print("Reward: {0}".format(result.reward))
  print("Done: {0}".format(result.done))
  action_space=result.action_space
  print()
  if result.done:
      print("Goal succeeded")
      sys.exit(0)

