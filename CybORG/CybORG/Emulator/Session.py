import sys
import random
from pymetasploit3.msfrpc import MsfRpcClient
from time import sleep

class Session():
   def __init__(self):
       pass
     
class MSFSessionHandler():
    # a session handler for a Metasploit Framework agent that tracks client/target session information. 
    #def __init__(self, agent):
    def __init__(self):
        # at the moment, the session handler doesn't manage sessions.
        #self.sessions = {} # a mapping of session IDs for each agent and the client/target of each session.
        #self.session[agent] = {}
        self.msfclient = None # represents the MSF RPC client interface
        self._connect_msfclient() # represents the MSF RPCD client interface
        self.console_id = self._create_console(self.msfclient) # represents the MSF Console id

    #def add_session(self, agent, session: Session):
    #    self.session[agent][session.ident] = session

    #def get_session_by_host(self, agent, hostname: str):
    #    host_sessions = [ s for s in self.sessions[agent] if s.hostname == hostname ]
    #    return host_sessions

    def execute_module(self, mtype: str, mname:str, opts: dict, payload_name=None, payload_opts=None):
        # need to use console rather than modules as msfrpc can't get the output from the module
        # see github issue https://github.com/rapid7/metasploit-framework/issues/11596
        #
        # check whether this is a passthrough command (ie session-less pingsweep)
        if mtype == "passthrough":
          # mname is the passthrough command
          run_cmd = "{}\n".format(mname)
        else:
          use_cmd = "use {0}/{1}\n".format(mtype,mname)
          #print(use_cmd)
          self.msfclient.call('console.write',[self.console_id,use_cmd])
          for opt_name,opt_vals in opts.items():
            opts_cmd = "set {0} {1}\n".format(opt_name,opt_vals)
            #print(opts_cmd)
            self.msfclient.call('console.write',[self.console_id,opts_cmd])
          #print(client.call('console.read',[console_id]))
          # TODO need to implement payload name and opts
          # execute module
          run_cmd = "run\n"
          #print(run_cmd)
        self.msfclient.call('console.write',[self.console_id,run_cmd])
        # get results
        buffer=[]
        busy=True
        # TODO implement timeout
        while busy:
          ret = self.msfclient.call('console.read',[self.console_id])
          #print(ret)
          if ret["data"] != "":
            #print(ret["data"])
            buffer.append(ret["data"])
          busy=ret["busy"]

        #print(buffer)
        # perhaps format buffer??
        # console can return multiple newlines in the buffer
        # concatenate the buffer array into one string (with embedded newlines)
        return "".join(buffer)

    def _connect_msfclient(self):
        msfrpcd_password = "password"
        # connect to msfrpcd 
        self.msfclient = MsfRpcClient(msfrpcd_password, ssl=True)

    def _create_console(self, client):
        # check to see if there is an existing console
        consoles=client.consoles
        active_consoles=consoles.list
        # don't check for existing console
        #if len(active_consoles) == 0:
        if True:
          ret = client.call('console.create')
          # id contains console_id
          if "id" in ret:
            console_id=ret["id"]
          else:
            print("unable to create console")
            sys.exit(1)
        else:
            # return first console
            console_id = active_consoles[0]["id"]
        # clear read buffer of any banner in the console
        client.call('console.read',[console_id])
        return console_id


    def _log_debug(self, output):
        print(output)
