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
total_steps=200000
double=False
dueling=True

# set n_envs to 1 initially. No parallelisation
n_envs=1

# set max params for observation vector sizei
# other than MAX_HOSTS, they are max per host
env_config = {
   "fully_obs": True,
   "max_params": {
        "MAX_HOSTS": 5,
        "MAX_PROCESSES": 5,
        "MAX_CONNECTIONS": 2,
        "MAX_VULNERABILITIES": 1,
        "MAX_INTERFACES": 2,
        "MAX_SESSIONS": 5,
        "MAX_USERS": 5,
        "MAX_FILES": 0,
        "MAX_GROUPS": 0,
        "MAX_PATCHES": 0
   }
}

path = str(inspect.getfile(CybORG))
curr_dir = os.getcwd()

# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
path = path[:-10] + "/Shared/Scenarios/TestMSFSessionDQNScenario.yaml"
#print(path)

cyborg = CybORG(path,'sim', env_config=env_config)

# print env controller network/environment state (ie not agent state!)
#environment=cyborg.environment_controller.state
#print()
# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
#unwrapped_action_space=agent.action_space.get_action_space()
#action_env=EnumActionWrapper(cyborg)
#print("action env get action space")
#print(action_env.get_action_space(agent="Red"))
#wrapped_env = FixedFlatStateWrapper(action_env, max_params=env_config["max_params"])
#print("wrapped env get action space")
#print(wrapped_env.get_action_space(agent="Red"))
wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg), max_params=env_config["max_params"])
#env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
# wraps env in DummyVecEnv VecEnv environment
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)

# print openaigym action and observation spaces
print(env.action_space) # Discrete

# initialise agent learning
agent.agent.initialise(env,gamma,initial_epsilon,final_epsilon,total_steps,double,dueling)
callback=agent.agent.learn_callback

start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
agent.agent.model.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
# save model to file
agent.agent.dqn.save(curr_dir+"/exports/dqn.zip")

