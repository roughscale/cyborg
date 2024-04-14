from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.FixedFlatStateWrapper import FixedFlatStateWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
from CybORG.Shared.Results import Results
from CybORG.Shared.State import State
from stable_baselines3.common.env_util import make_vec_env
import inspect
import psutil
import json
import sys
import time
import copy
import os
import subprocess
import signal
import argparse

def signal_handler(sig, frame):
    os.killpg(os.getpgid(msfrpcd_proc.pid),signal.SIGKILL)
    #msfrpcd.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

parser = argparse.ArgumentParser(
        prog="get_env_cfg",
        description="Get the AWS network configuration")
parser.add_argument("--env-file",dest="env_file",required=True)
args=parser.parse_args()

# start msfrcpd
msfrpcd = subprocess.Popen(["/opt/metasploit-framework/bin/msfrpcd","-P","password"],close_fds=True)
msfrpcd.wait()
# find child process
msfrpcd_proc = None
for proc in psutil.process_iter():
    if proc.name() == "ruby":
        msfrpcd_proc=proc
if msfrpcd_proc is None:
    sys.exit(1)

# wait until service is available
time.sleep(5)

num_episodes=1
total_steps=200000

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

# get emulated config from file
emu_conf_file = open(args.env_file,"r")
emu_config = json.load(emu_conf_file)
env_config.update(emu_config)

path = str(inspect.getfile(CybORG))
curr_dir = os.getcwd()

path = path[:-10] + "/Shared/Scenarios/TestMSFSessionRandomScenario.yaml"

cyborg = CybORG(path,'aws', env_config=env_config)

agent=cyborg.environment_controller.agent_interfaces["Red"]
action_env=EnumActionWrapper(cyborg)
wrapped_env = FixedFlatStateWrapper(action_env, max_params=env_config["max_params"])
env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")

observation=env.reset()
start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
done=False
step = 0
for ep in range(num_episodes):
  while not done:
    action_space=env.action_space
    action_num=agent.get_action(observation, action_space)
    print("Action Number: {0}".format(action_num))
    # wrapped step method needs an action_num (possible_actions index)
    observation, reward, done, _, info = env.step(action_num)
    print("Reward: {0}".format(reward))
    print("Done: {0}".format(done))
    print()
    step += 1
    if done:
      print("Goal succeeded in {0} steps".format(step))
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
print("Evaluation duration: {}s".format(end-start))
os.killpg(os.getpgid(msfrpcd_proc.pid),signal.SIGKILL)

