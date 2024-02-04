from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
import random
import math

from ipaddress import IPv4Network, IPv4Address

from CybORG.Shared.Actions import UpgradeToMeterpreter, MSFAutoroute, MSFPingsweep, SSHLoginExploit, Sleep, MS17_010_PSExec, MSFPortscan, MSFSubUidShell, MSFJuicyPotato, MeterpreterIPConfig

class RedKillChainAgent(BaseAgent):

    def __init__(self, action_size=None, state_size=None):

        self.killchains = {
          "internal1_juicy":  [
                [ MSFPingsweep, { "subnet":  IPv4Network("10.46.64.0/24") } ],
                [ MSFPortscan, { "ip_address":  IPv4Address("10.46.64.100") } ],
                [ SSHLoginExploit, { "ip_address" : IPv4Address("10.46.64.100"), "port": 22 } ],
                [ MSFSubUidShell, { "ip_address": IPv4Address("10.46.64.100") } ],
                [ MeterpreterIPConfig, { "ip_address":  IPv4Address("10.46.64.100") } ],
                [ MSFAutoroute, { "ip_address": IPv4Address("10.46.64.100") } ],
                [ MSFPingsweep, { "subnet": IPv4Network("10.58.85.0/24") } ],
                [ MSFPortscan, { "ip_address": IPv4Address("10.58.85.101") } ],
                [ SSHLoginExploit, { "ip_address": IPv4Address("10.58.85.101"), "port": 22 } ],
                [ UpgradeToMeterpreter, { "ip_address": IPv4Address("10.58.85.101") } ],
                [ MSFJuicyPotato, { "ip_address": IPv4Address("10.58.85.101") } ]
          ],           
          "internal1_pexec":  [
                [ MSFPingsweep, { "subnet":  IPv4Network("10.46.64.0/24") } ],
                [ MSFPortscan, { "ip_address":  IPv4Address("10.46.64.100") } ],
                [ SSHLoginExploit, { "ip_address" : IPv4Address("10.46.64.100"), "port": 22 } ],
                [ MSFSubUidShell, { "ip_address": IPv4Address("10.46.64.100") } ],
                [ MeterpreterIPConfig, { "ip_address":  IPv4Address("10.46.64.100") } ],
                [ MSFAutoroute, { "ip_address": IPv4Address("10.46.64.100") } ],
                [ MSFPingsweep, { "subnet": IPv4Network("10.58.85.0/24") } ],
                [ MSFPortscan, { "ip_address": IPv4Address("10.58.85.101") } ],
                [ SSHLoginExploit, { "ip_address": IPv4Address("10.58.85.101"), "port": 22 } ],
                [ MS17_010_PSExec, { "ip_address": IPv4Address("10.58.85.101") } ]
           ]            
        }

        self.killchain = None
        self.count = 0

    def train(self, results):
        pass

    def get_action(self, observation, action_space, egreedy):
        self.killchain = self.killchains["internal1_juicy"]
        position = self.count % len(self.killchain)
        action_class = self.killchain[position][0]
        action_params = { "agent": "Red", "session": 0 }
        action_params.update(self.killchain[position][1])
        self.count += 1
        return action_class(**action_params)

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass

