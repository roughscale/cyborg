import sys
import random
from pymetasploit3.msfrpc import MsfRpcClient
from time import sleep
from ipaddress import IPv4Address, IPv4Network
import re

class Session():
   def __init__(self):
       pass
     
class MSFSessionHandler():
    # a session handler for a Metasploit Framework agent that tracks client/target session information. 
    #def __init__(self, agent):
    def __init__(self):
        # at the moment, the session handler doesn't manage sessions.
        self.sessions = {} # a mapping of session IDs to session objects.
        self.msfclient = None # represents the MSF RPC client interface
        self._connect_msfclient() # represents the MSF RPCD client interface
        self.console_id = self._create_console(self.msfclient) # represents the MSF Console id

    def get_sessions(self):
        #print("get sessions")
        #print(self.msfclient.sessions)
        #print(dir(self.msfclient.sessions))
        sessions = self.msfclient.sessions.list
        return sessions

    def get_session_by_remote_ip(self, remote_ip: str, session_type = None):
        sessions = self.get_sessions()
        # first check if there is a session with target_host that matches the remote_ip
        remote_sessions = { k:v for k,v in sessions.items() if v["target_host"] == remote_ip }
        #print(remote_sessions)
        # otherwise, check if there is a route in a session that can be used
        # why would we do this?
        # perhaps to enable remote code execution actions for hosts that are not immediately accessilbe
        # but it is causing errors for local actions - running on wrong host
        # temp disable to see the impact
        #if len(remote_sessions) == 0:
        #    remote_sessions = { k:v for k,v in sessions.items() for r in v["routes"].split(",") if r != '' and IPv4Address(remote_ip) in IPv4Network(r)}
        if session_type is not None:
            type_sessions = [ k for k,v in sessions.items() if v["type"] == session_type ]
            #print(type_sessions)
            remote_sessions = { k:v for k,v in remote_sessions.items() for t in type_sessions if k == t }
        return remote_sessions

    def get_session_by_remote_cidr(self, remote_cidr: str, session_type = None):
        sessions = self.get_sessions()
        #print(sessions)
        # first, check if session target_host is within the cidr
        remote_sessions = { k:v for k,v in sessions.items() if IPv4Network(v["target_host"]) in IPv4Network(remote_cidr) }
        #print(remote_sessions)
        # otherwise, check if there is a route in a session that can be used
        if len(remote_sessions) == 0:
            remote_sessions = { k:v for k,v in sessions.items() for r in v["routes"].split(",") if r != '' and IPv4Network(remote_cidr) == IPv4Network(r)}
            #print(remote_sessions)
        if session_type is not None:
            type_sessions = [ k for k,v in sessions.items() if v["type"] == session_type ]
            #print(type_sessions)
            remote_sessions = { k:v for k,v in remote_sessions.items() for t in type_sessions if k == t }
            #print(remote_sessions)
        return remote_sessions

    def get_session_user(self, session_id):
        sessions = self.get_sessions()
        print(session_id)
        print(sessions)
        print(sessions.keys())
        print(list(sessions.keys()))
        if str(session_id) not in list(sessions.keys()):
            return None
        else:
            session = sessions[str(session_id)]
            # session username s the username at the client end of the session
            # extract username from session info
            info = session["info"]
            user_match = re.match("(.*)@(.*)",info)
            if user_match is None:
                return session["username"]
            else:
                return user_match[1].strip() # remove whitespace

    def execute_module(self, mtype: str, mname:str, opts: dict, payload_name=None, payload_opts=None):

      output = self._execute_msf_action( mtype, mname, opts, payload_name, payload_opts)

      session_info = None
      # parse output for session information and add to session list
      for line in output.split("\n"):
        if "[*] Meterpreter session" in line:
          session_info = re.match("\[\*\]\sMeterpreter\ssession\s(\d)\sopened\s.* ",line)
        if "[*] Command shell session" in line:
            session_info = re.match("\[\*\]\sCommand\sshell\ssession\s(\d)\sopened\s.*",line)
        #print(session_info)
      return output

    def execute_shell_action(self, action, session):
        shell = self.msfclient.sessions.session(session)
        shell.write(action)
        output=shell.read()
        return output

    def _execute_msf_action(self, mtype, mname, opts, payload_name, payload_opts):
        # need to use console rather than modules as msfrpc can't get the output from the module
        # see github issue https://github.com/rapid7/metasploit-framework/issues/11596
        #
        # check whether this is a passthrough command (ie session-less pingsweep)
        if mtype == "passthrough":
          # mname is the passthrough command
          run_cmd = "{}\n".format(mname)
        # execute_shell_action is called directly
        #elif mtype == "session_cmd":
        #    return self.execute_shell_action(mname, opts)
        else:
          use_cmd = "use {0}/{1}\n".format(mtype,mname)
          #print(use_cmd)
          self.msfclient.call('console.write',[self.console_id,use_cmd])
          for opt_name,opt_vals in opts.items():
            opts_cmd = "set {0} {1}\n".format(opt_name,opt_vals)
            #print(opts_cmd)
            self.msfclient.call('console.write',[self.console_id,opts_cmd])
          if payload_name is not None:
              payload_cmd = "set PAYLOAD {}\n".format(payload_name)
              #print(payload_cmd)
              self.msfclient.call('console.write',[self.console_id,payload_cmd])
          if payload_opts is not None:
              for p_opt_name,p_opt_vals in payload_opts.items():
                payload_opts_cmd = "set {0} {1}\n".format(p_opt_name,p_opt_vals)
                #print(payload_opts_cmd)
                self.msfclient.call('console.write',[self.console_id,payload_opts_cmd])
          # execute module
          run_cmd = "run\n"
        #print(run_cmd)
        self.msfclient.call('console.write',[self.console_id,run_cmd])
        # get results
        buffer=[]
        busy=True
        # TODO implement timeout
        # is busy-ness the correct event to signal command completion?
        while busy:
          ret = self.msfclient.call('console.read',[self.console_id])
          #print(ret)
          # deal with meterpreter sessions
          if ret["data"] != "":
            #print(ret["data"])
            buffer.append(ret["data"])
            # handle edge cases
            if "Meterpreter session" in ret["data"]:
              # deal with sessions closing prematurely
              # TODO: do proper regex matching
              if "closed" in ret["data"]:
                  ret["busy"] = False
              else:
                bg_cmd = "bg\n"
                self.msfclient.call('console.write',[self.console_id,bg_cmd])
            # upgrade to meterpreter returns non-busy signal before completion
            # TODO: is this the best place to handle this kind of event
            # can it be handled within the action itself (ie fetch more data
            # from the console)
            if "Post module execution completed" in ret["data"]:
                #print(ret["busy"])
                #print("Override busy signal")
                ret["busy"] = True
            if "Waiting up to 30 seconds for the session to come back" in ret["data"]:
                #print(ret["busy"])
                #print("Waiting for 30s")
                sleep(30)
                #print("Override busy signal")
                ret["busy"] = True
          busy=ret["busy"]
        return "".join(buffer)

    def _connect_msfclient(self):
        msfrpcd_password = "password"
        # connect to msfrpcd 
        self.msfclient = MsfRpcClient(msfrpcd_password, ssl=True)
        # clear any orphaned consoles
        self._clear_consoles(self.msfclient)

    def _clear_consoles(self, client):
        consoles=client.consoles
        for c in consoles.list:
            client.call('console.destroy',c["id"])
        # clear sessions
        sessions=client.sessions
        print(sessions)
        print(sessions.list)
        for s in sessions.list:
            print(s)
            print(client.call('session.stop',[s]))
            print(client.call('session.ring_clear',[s]))

    def _create_console(self, client):
        ret = client.call('console.create')
        # id contains console_id
        if "id" in ret:
          console_id=ret["id"]
        else:
          print("unable to create console")
          sys.exit(1)
        # clear read buffer of any banner in the console
        client.call('console.read',[console_id])
        return console_id

    def _log_debug(self, output):
        print(output)
