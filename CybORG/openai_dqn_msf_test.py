from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
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
tensorboard_log="./runs/dqn"
device = "auto"  # set to "cuda" or "mps" manually if desired

# set n_envs to 1 initially. No parallelisation
n_envs=1

# set max params for observation vector size
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

path = path[:-10] + "/Shared/Scenarios/TestMSFSessionDQNScenario.yaml"

cyborg = CybORG(path,'sim', env_config=env_config)

agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatWrapper(EnumActionWrapper(cyborg), max_params=env_config["max_params"])
#env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
# wraps env in DummyVecEnv VecEnv environment
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)

# initialise agent learning
agent.agent.initialise(env,
        gamma=gamma,
        initial_eps=initial_epsilon,
        final_eps=final_epsilon,
        total_steps=total_steps,
        dueling=dueling,
        tensorboard_log=tensorboard_log,
        device=device)

callback=agent.agent.learn_callback

start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
agent.agent.model.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
# save model to file
agent.agent.model.save(curr_dir+"/exports/dqn.zip")
