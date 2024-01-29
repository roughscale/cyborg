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
        remote_sessions = [ k for k,v in sessions.items() if v["target_host"] == remote_ip ]
        #print(remote_sessions)
        if session_type is not None:
            avail_sessions = remote_sessions
            type_sessions = [ k for k,v in sessions.items() if v["type"] == session_type ]
            #print(type_sessions)
            remote_sessions = [ s for s in avail_sessions for t in type_sessions if s == t ]
            #print(remote_sessions)
        return remote_sessions

    def get_session_by_remote_cidr(self, remote_cidr: str, session_type = None):
        sessions = self.get_sessions()
        remote_sessions = [ k for k,v in sessions.items() if IPv4Address(v["target_host"]) in IPv4Network(remote_cidr) ]
        if session_type is not None:
            type_sessions = [ k for k,v in sessions.items() if v["type"] == session_type ]
            remote_sessions = [ s for s in remote_sessions for t in type_sessions if s == t ]
        #    if len(remote_sessions) > 1:
        #        priv_sessions = [ s for s in remote_sessions if s.username in [ "root", "SYSTEM"]
        #        if len(priv_sessions) > 0:
        #          remote_sessions = priv_sessions[0]
        #        else:
        #          remote_sessions = remote_sessions[0]
        #  at the moment we return all matching sessions
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
            return session["username"]

    def execute_module(self, mtype: str, mname:str, opts: dict, payload_name=None, payload_opts=None):

      output = self._execute_msf_action( mtype, mname, opts, payload_name, payload_opts)

      session_info = None
      # parse output for session information and add to session list
      for line in output.split("\n"):
        if "[*] Meterpreter session" in line:
          session_info = re.match("\[\*\]\sMeterpreter\ssession\s(\d)\sopened\s.* ",line)
        if "[*] Command shell session" in line:
            session_info = re.match("\[\*\]\sCommand\sshell\ssession\s(\d)\sopened\s.*",line)
        print(session_info)
      return output

    def execute_shell_action(self, action, session):
        # session is already checked and determined by the action class
        # no need to check for valid session by ip_address
        #if "RHOST" not in opts:
        #    return "no RHOST provided"
        #else:
        #    target_host = opts["RHOST"]
        #target_sessions = self.get_session_by_remote_ip(target_host, "meterpreter")
        #if len(target_sessions) == 0:
        #    return "no valid sessions for {}".format(target_host)
        #else:
        #     session_id = target_sessions[0]
        session_id = session
        shell = self.msfclient.sessions.session(session_id)
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
              self.msfclient.call('console.write',[self.console_id,payload_cmd])
          if payload_opts is not None:
              for p_opt_name,p_opt_vals in payload_opts.items():
                payload_opts_cmd = "set {0} {1}\n".format(p_opt_name,p_opt_vals)
                self.msfclient.call('console.write',[self.console_id,payload_opts_cmd])
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
          # deal with meterpreter sessions
          if ret["data"] != "":
            print(ret["data"])
            buffer.append(ret["data"])
            if "Meterpreter session" in ret["data"]:
              # get uid of session and ipconfig of host
              # these should be separated into separate actions
              # but for now, we do it here to match the simulated case
              #uid_cmd = "getuid\n"
              #self.msfclient.call('console.write',[self.console_id,uid_cmd])
              #ret = self.msfclient.call('console.read',[self.console_id])
              #buffer.append(ret["data"])
              #ip_cmd = "ipconfig\n"
              #self.msfclient.call('console.write',[self.console_id,ip_cmd])
              #ret = self.msfclient.call('console.read',[self.console_id])
              #buffer.apend(ret["data"])
              # background the session
              bg_cmd = "bg\n"
              self.msfclient.call('console.write',[self.console_id,bg_cmd])
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
