from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.evaluation import evaluate_policy
import inspect
import sys
import time
import copy
import json
import os
import psutil
import subprocess
import argparse
import signal

def signal_handler(sig, frame):
    msfrpcd.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

parser = argparse.ArgumentParser(
        prog="get_env_cfg",
        description="Get the AWS network configuration")
parser.add_argument("--env-file",dest="env_file",required=True)
parser.add_argument("--model-name",dest="model_name",required=True)
args=parser.parse_args()

# start msfrcpd
msfrcpd = subprocess.call(["/opt/metasploit-framework/bin/msfrpcd","-P","password"],close_fds=True)
# wait until service is available
time.sleep(5)

# number of evaulation episodes
n_eval_eps=1

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

# get emulated config from file
emu_conf_file = open(args.env_file,"r")
emu_config = json.load(emu_conf_file)
env_config.update(emu_config)

path = str(inspect.getfile(CybORG))
n_envs=1

scenario_path = path[:-10] + "/Shared/Scenarios/TestMSFSessionPPOScenario.yaml"
model_path=path[:-17] + "/exports/" + args.model_name

cyborg = CybORG(scenario_path,'aws',env_config=env_config)

agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatWrapper(EnumActionWrapper(cyborg),max_params=env_config["max_params"])
#env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
# wraps env in DummyVecEnv VecEnv environment
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)

# load agent from export file
model=agent.agent.load("PPO",model_path)

start=time.time()
print("Evaluation start: {}".format(time.ctime(start)))
print()
mean_reward, std_reward = evaluate_policy(model.model.policy, env, n_eval_episodes=n_eval_eps, deterministic=True)
end=time.time()
print(mean_reward)
print(std_reward)
print("Evaluation end: {}".format(time.ctime(end)))
print("Evaluation duration: {}s".format(end-start))

