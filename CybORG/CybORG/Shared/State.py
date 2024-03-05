from CybORG.Shared.Observation import Observation
import pprint
import copy
import hashlib

from ipaddress import IPv4Network, IPv4Address
from typing import List, Union, Optional
import CybORG.Shared.Enums as CyEnums

class State(Observation):

    """ This manages the State space of the Agent which is a running history of all observations """
    def __init__(self, success: bool = None):
        self.data = {"network": {}, "hosts": {}, "success": CyEnums.TrinaryEnum.UNKNOWN if success == None else CyEnums.TrinaryEnum.parse_bool(success)}
        self.raw = ''

        # keep a running total of the number of each State elements (to identify MAX requirements)
        self.num_subnets = 0
        self.num_hosts = 0
        self.num_processes = 0
        self.num_sessions = 0
        self.num_connections = 0
        self.num_interfaces = 0

    """
        Initialise the state with ALL scenario hosts so that any fixed flattened State space 
        will be consistent
    """
    def initialise_state(self, scenario):

        for hostname in scenario.hosts:
            self.data["hosts"][hostname] = {}

        self.calculate_max_elements()

    def calculate_max_elements(self):
        self.num_subnets = len(self.data["network"])
        self.num_hosts = len(self.data["hosts"])
        num_processes = 0 # num processes per host
        num_sessions = 0 # num sessions per host
        num_connections = 0 # num connections per process
        num_interfaces = 0 # num interfaces per host

        for host in self.data["hosts"]:
            num_host_processes = 0 
            num_host_sessions = 0
            num_proc_connections = 0
            num_host_interfaces = 0
            if "Processes" in self.data["hosts"][host]:
              num_host_processes += len(self.data["hosts"][host]["Processes"])
              for proc in self.data["hosts"][host]["Processes"]:
                  if "Connections" in proc:
                      num_proc_connections += 1
              if num_proc_connections > num_connections:
                  num_connections = num_proc_connections
              if num_host_processes > num_processes:
                  num_processes = num_host_processes
            if "Sessions" in self.data["hosts"][host]:
              num_host_sessions += len(self.data["hosts"][host]["Sessions"])
              if num_host_sessions > num_sessions:
                  num_sessions = num_host_sessions
            if "Interface" in self.data["hosts"][host]:
              num_host_interfaces += len(self.data["hosts"][host]["Interface"])
              if num_host_interfaces > num_interfaces:
                  num_interfaces = num_host_interfaces
        print(num_processes)
        print(num_sessions)
        print(num_connections)
        print(num_interfaces)
        
        if num_processes > self.num_processes:
          self.num_processes = num_processes

        if num_sessions > self.num_sessions:
          self.num_sessions = num_sessions

        if num_connections > self.num_connections:
          self.num_connections = num_connections

        if num_interfaces > self.num_interfaces:
          self.num_interfaces = num_interfaces

    def get_max_elements(self):
      max_elements = {}
      max_elements["subnets"] = self.num_subnets
      max_elements["hosts"] = self.num_hosts
      max_elements["processes"] = self.num_processes
      max_elements["sessions"] = self.num_sessions
      max_elements["connections"] = self.num_connections
      max_elements["interfaces"] = self.num_interfaces
      return max_elements

    # updates the State space with an Observation
    def update(self, observation: Observation, agent="Red"):
        # this already is a deepcopy!!!
        # convert Observation to dict
        if isinstance(observation, Observation):
          obs = copy.deepcopy(observation.data)
        else:
          obs = copy.deepcopy(observation)
        # merge observations
        for key, info in obs["hosts"].items():
            if "Processes" in info:
                for process in info["Processes"]:
                    # this seems to be duplicate the connection dict with top-level keys
                    # in the process dict
                    # we need to flatten the dict
                    #if 'Connections' in process:
                    #    for conn in process['Connections']:
                    #        # this will merge **process and **conn into one dict
                    #        # 
                    #        self.merge_process(hostid=key, agent=agent, **process, **conn)
                    #else:
                    #    self.merge_process(hostid=key, agent=agent, **process)
                    # the dict only needs to be flattened in the add_process function
                    self.merge_process(hostid=key, agent=agent, **process)
            # Processes need to be updated before Sessions if both are contained in the same obs
            if "Sessions" in info:
                for session_info in info["Sessions"]:
                    self.merge_session_info(hostid=key, agent=agent, **session_info)
            if "UserInfo" in info:
                for user in info["UserInfo"]:
                    self.merge_user_info(hostid=key, agent=agent, **user)
            if "Files" in info:
                for file_info in info["Files"]:
                    self.merge_file_info(hostid=key, agent=agent, **file_info)
            if "Interface" in info:
                for interface in info["Interface"]:
                    self.merge_interface_info(hostid=key, agent=agent, **interface)
            if "SystemInfo" in info:
                self.merge_system_info(hostid=key, agent=agent, **info["SystemInfo"])

        if 'subnets' in obs['network']:
            for subnet in obs['network']['subnets']:
                self.add_subnet(subnet)
        if 'success' in obs:
            self.set_success(obs["success"])

    def get_state(self):
        return copy.deepcopy(self.data)
        #return self.__str__()
        #return self

    @staticmethod
    def get_state_hash(state_vector):
        h = hashlib.new("sha256")
        h.update(state_vector.tobytes())
        return h.hexdigest()

    def merge_session_info(self, hostid, agent, **session_info):
        # check if session is effectively a duplicate
        if "Sessions" in self.data['hosts'][hostid]:
            print("merge_session_info")
            host_sessions = { k:v for k,v in enumerate(self.data['hosts'][hostid]["Sessions"]) if v != {} }
            print("host sessions")
            print(host_sessions)
            print("new session")
            print(session_info)
            # match on pid provided pid is not 0. Occurs with process number reuse due to pid rotation))
            # Could occur in some cases of privesc of the same session (NOTE: Not currently supported)
            # don't match on both processes having unknown PIDs (PID 0)
            pid_match = [ i for i,s in host_sessions.items() if ("PID" in s and s["PID"] !=0 and s["PID"]== session_info.get("PID")) ]
            if len(pid_match) > 0:
                print("matching pid")
                print(pid_match)
                for i in pid_match: 
                    # due to temporary pid rotation, we need to distinguish whether this pid match is due to privesc
                    # or pid rotation
                    # privesc this will occur if the existing session doesn't match the new session id
                    # NOTE: This doesn't always relate to privesc.  It should be an additional nonpriv user session
                    # NOTE: We no longer use PIDs in session observation as it doesn't occur in emulated case.
                    privesc = [ p for p,s in host_sessions.items() if
                            s["Agent"] == session_info.get("Agent") and \
                            s["Type"] == session_info.get("Type") and \
                            s["Username"] != session_info.get("Username") and \
                            s["PID"] != session_info.get("PID",None)]
                    if len(privesc) > 0 and session_info["Username"] not in ('root','SYSTEM'):
                        # remove current session from host
                        print("found another matching privesc session. dropping new session")
                        self.data['hosts'][hostid]["Sessions"].pop(i)
                        return
                    else:
                       print("replacing matching session pid")
                       # replace in State with updated session for that pid
                       self.data['hosts'][hostid]["Sessions"][i] = self.get_session_info(hostid=hostid,agent=agent,**session_info)
                    return

            # match on same username, agent and session_type
            match_sessions = [ i for i,s in host_sessions.items() if \
                    s["Agent"] == session_info.get("Agent") and \
                    s["Type"] == session_info.get("Type") and \
                    s["Username"] == session_info.get("Username") ]
            if len(match_sessions) > 0:
                print("replacing match session")
                print(match_sessions)
                for i in match_sessions:
                  # replace in State with most current session
                  print(session_info)
                  self.data['hosts'][hostid]["Sessions"][i] = self.get_session_info(hostid=hostid,agent=agent,**session_info)
                  return
            print(session_info.get("Active"))
            if session_info.get("Active") == False:
                print("removing inactive session")
                inactive_ident = session_info.get("ID")
                self.data['hosts'][hostid]["Sessions"].pop(inactive_ident)
                #host_sessions.pop(inactive_ident)
                return
        self.add_session_info(hostid=hostid, agent=agent, **session_info)
        # need to coalesce empty elements
        #coalesce_list = [ s for s in self.data['hosts'][hostid]["Sessions"] if s != {} ]
        #self.data['hosts'][hostid]["Sessions"] = coalesce_list

    def get_session_info(self,
                         hostid: str = None,
                         username: str = None,
                         session_id: int = None,
                         agent: str = None,
                         timeout: int = None,
                         pid: int = None,
                         session_type: str = None,
                         active: bool = True,
                         routes: list = [],
                         **kwargs):
        if hostid is None:
            hostid = str(len(self.data['hosts']))
        if hostid not in self.data['hosts']:
            self.data['hosts'][hostid] = {"Sessions": []}
        elif "Sessions" not in self.data['hosts'][hostid]:
            self.data['hosts'][hostid]["Sessions"] = []

        new_session = {}
        if username is None:
            username = kwargs.get("Username", None)
        if username is not None:
            new_session["Username"] = username
        else:
            # need to add null/unknown username
            print("session has no username")
            print(hostid, username, session_id, pid, session_type, kwargs)
            raise ValueError("session has no username")

        if session_id is None:
            session_id = kwargs.get("ID", None)
        if session_id is not None:
            new_session["ID"] = session_id

        if timeout is None:
            timeout = kwargs.get("Timeout", None)
        if timeout is not None:
            new_session["Timeout"] = timeout

        if session_type is None:
            session_type = kwargs.get("Type", None)
        if session_type is not None:
            if type(session_type) is str:
                session_type = CyEnums.SessionType.parse_string(session_type)
            new_session["Type"] = session_type

        if session_type == CyEnums.SessionType.METERPRETER:
            # add Meterpreter specific attributes
            if not bool(routes):
                routes = kwargs.get("Routes", None)
            if routes is None:
                routes = []
            new_session["Routes"] = routes

        if pid is None:
            pid = kwargs.get("PID", None)
        if pid is not None:
            new_session["PID"] = pid
            # if process already exists in this observation, need to update existing process obs
            matched_proc = False
            if "Processes" in self.data["hosts"][hostid]:
              for p_idx,proc in enumerate(self.data["hosts"][hostid]["Processes"]):
                if "PID" in proc and proc["PID"] == pid:
                    self.data["hosts"][hostid]["Processes"][p_idx].update({ "Username": username, "Type": session_type})
                    matched_proc = True

            if not matched_proc:
                # session should have an existing connection and a sessioned connection should have an identifiable PID
                #print("unable to find PID for session connection")
                self.add_process(hostid=hostid, pid=pid, username=username, type=session_type)
        else:
            # do we randomly assign a PID to the session. No, as sessions should have an existing connection with an identified PID
            print("no pid passed to the session_info")


        if agent is None:
            agent = kwargs.get("Agent", None)
            if agent is None:
                raise ValueError('Agent must be specified when a session is added to an observation')
        if agent is not None:
            new_session["Agent"] = agent

        # new session parameter.  Will default to active
        if active is None:
            active = kwargs.get("Active", "True")
        if active is not None:
            new_session["Active"] = active

        return new_session

    def merge_process(self, hostid, agent, **process):
        # check if new process information needs to be merged with existing processes
        #
        # examples of these are: 
        # duplicate observations, ie repeat scans
        # successful exploit of existing connection process
        # successful escalation of existing process - NOTE usually this results in a new session
        #
        if "Processes" not in self.data['hosts'][hostid]:
            # no existing processes
            print("no existing processes")
            if "Connections" in process:
                for conn in process["Connections"]:
                   self.add_process(hostid=hostid, agent=agent, **process, **conn)
            else:
                self.add_process(hostid=hostid,agent=agent,**process)
            return
    
        print("merging process connections into State observation")
        for p_idx, existing_process in enumerate(self.data['hosts'][hostid]["Processes"]):
           # perhaps for the moment, lets not overwrite "matching connections".
           # lets ensure they are updated properly (ie adding to the processes' connection list
           # for this to happen we need to be able to identify by PID
           
           # match by PID
           if "PID" in process and "PID" in existing_process:
                # non-connection process
                # match on pid
                proc_match = (process["PID"] == existing_process["PID"] and process["PID"] is not None)
                if proc_match:
                    print("matched on PID")
                    # we should merge the dicts
                    # we need to do deep merge due to connection subkey
                    # lets focus on connection merging first
                    if "Connections" in process and "Connections" in existing_process:
                        # for now just to a straight list extension
                        # now we identify any duplicates in the new process
                        # we should replace existing connection with new connections
                        merged_conn = copy.deepcopy(existing_process["Connections"])
                        for p in process["Connections"]:
                            match = False
                            for e_idx, e in enumerate(existing_process["Connections"]):
                                # match same hosts. connection must have local_address as
                                # a minimum. I would have thought connections with PIDs would
                                # have remote addr!!
                                if p["local_address"] == e["local_address"] and \
                                    e.get("remote_address") is not None and \
                                    p.get("remote_address") is not None and \
                                     p["remote_address"] == e["remote_address"]:
                                            # match outbound duplicates
                                            if p["remote_port"] == e["remote_port"] or \
                                                    p["local_port"] == e["local_port"]:
                                                      # add duplicate
                                                      print("found duplicate connection")
                                                      # if we replace with new
                                                      merged_conn[e_idx] = p
                                                      match = True
                                                      break
                                                      # otherwise continue
                                                      #continue
                            if not match:
                                merged_conn.append(p)
                             
                        print("merging matching PID connections")
                        # we update the new proc with the merged connections
                        process["Connections"] = merged_conn
                    # merge non-connection related attributes
                    print("merge matching PID processes")
                    print(process)
                    self.data["hosts"][hostid]["Processes"][p_idx] = process
                    return
           # match bare connections (match those with only local_port and local_address)
           # should this only occur in all cases where PID is not in existing or new process?
           # or only where PID is not in both existing and new process?
           # the following will match also connections to existing processes
           # ie. new process matches but has a remote_address
           if "Connections" in process and "Connections" in existing_process:
               # the following are copies by reference
               new_conn = process["Connections"] # list
               existing_conn = existing_process["Connections"] # list
               match_conn = []
               # following is copy by value and forms the initial new value
               merged_conn = copy.deepcopy(existing_conn)
               for n_idx, n in enumerate(new_conn):
                 match = False
                 for e_idx,e in enumerate(existing_conn):
                     # skip null elements
                     if e == {}:
                         continue
                     # match the keys
                     if n["local_address"] == e["local_address"] and n["local_port"] == e["local_port"]:
                       if e.get("remote_address") is None:
                         print("found matching bare connection")
                         # replace with new connection
                         print(e)
                         merged_conn[e_idx] = n
                         match = True
                         break
                       elif n.get("remote_address") is None:
                         # drop bare connection in favor of existing conn
                         print("drop new bare conn in favour of existing conn")
                         match = True
                         break
                       elif e["remote_address"] == n["remote_address"]:
                         print("supersede existing remote connection")
                         print(e)
                         merged_conn[e_idx] = n
                         match = True
                         break
                     elif "remote_address" in n and "remote_address" in e and \
                             n["remote_address"] == e["remote_address"] and \
                             n["remote_port"] == e["remote_port"]:
                       if e["local_address"] == n["local_address"]:
                          print("supersede existing local connection")
                          print(e)
                          merged_conn[e_ix] = n
                          match = True
                          break
                 if not match:
                     merged_conn.append(n)
                         
                 # update the new_process connections with merged connections
                 print("updating new process with bare connection details")
               process["Connections"] = merged_conn
               print(process)
               return

           else:
               # how to handle non-PID matching
               pass

        # currently, add_process needs a flattened dict.  Is this optimal?
        # can we handle the connection list within the obs itself??
        if 'Connections' in process:
            if len(process["Connections"]) == 0:
                # connections have been removed by above operations
                return
            for conn in process['Connections']:
               #print("adding connection for process")
               # this will merge **process and **conn into one dict
               # we need to be able to handle multiple connections in the add_process
               print(conn)
               self.add_process(hostid=hostid, agent=agent, **process, **conn)
               return
        #else:
        self.add_process(hostid=hostid, agent=agent, **process)
        # need to coalesce process list
        #coalesce_list = [ p for p in self.data['hosts'][hostid]["Processes"] for c in p["Connections"] if any(c) ]
        #print(coalesce_list)
        #self.data['hosts'][hostid]["Processes"] = coalesce_list



    def get_process(self,
                    hostid: str = None,
                    pid: int = None,
                    parent_pid: int = None,
                    process_name: str = None,
                    program_name: str = None,
                    service_name: str = None,
                    username: str = None,
                    path: str = None,
                    local_port: int = None,
                    remote_port: int = None,
                    local_address: Union[str, IPv4Address] = None,
                    remote_address: Union[str, IPv4Address] = None,
                    app_protocol: str = None,
                    transport_protocol: str = None,
                    status: str = None,
                    process_type: str = None,
                    process_version: str = None,
                    vulnerability: str = None,
                    properties: Optional[List[str]] = None,
                    **kwargs):
        if hostid is None:
            #print("host id is None")
            hostid = str(len(self.data['hosts']))
        if hostid not in self.data['hosts']:
            #print("if hostid not in obs.hosts")
            self.data['hosts'][hostid] = {"Processes": []}
        # hostid is in hosts
        else:
          if "Processes" not in self.data['hosts'][hostid]:
            self.data['hosts'][hostid]["Processes"] = []
          else:
            #print("{} has existing processes".format(hostid))
            pass

        new_process = {}

        pid = kwargs.get("PID", None) if pid is None else pid
        if pid is not None:
            if type(pid) is not int:
                pid = int(pid)
            if pid < 0:
                raise ValueError
            new_process["PID"] = pid

        if parent_pid is None:
            parent_pid = kwargs.get("PPID", None)
        if parent_pid is not None:
            if type(parent_pid) is not int:
                parent_pid = int(parent_pid)
            new_process["PPID"] = parent_pid

        if process_name is None:
            process_name = kwargs.get("ProcessName", None)
        if process_name is not None:
            new_process["ProcessName"] = process_name
            if isinstance(process_name, str):
                process_name = CyEnums.ProcessName.parse_string(process_name)
            # what is the purpose of "Known Process".  Doesn't seem to have any effect
            # removing from here (and from FixedFlat wrappers)
            #new_process["Known Process"] = process_name
        else:
            pass
            # can occur with connection-based processes
            # print("process without name")

        if program_name is None:
            program_name = kwargs.get("Program Name", None)
        if program_name is not None:
            if type(program_name) is str:
                program_name = CyEnums.FileType.parse_string(program_name)
            new_process["Program Name"] = program_name
        else:
            pass
            # can occur with connection-based processes
            # print("process without program_name")

        if service_name is None:
            service_name = kwargs.get("Service Name", None)
        if service_name is not None:
            new_process["Service Name"] = service_name
        else:
            pass
            # can occur with connection-based processes
            # print("process without service_name")

        if username is None:
            username = kwargs.get("Username", None)
        if username is not None:
            new_process["Username"] = username
        else:
            pass
            # can occur with connection-based processes
            # print("process without username")

        if path is None:
            path = kwargs.get("Path", None)
        if path is not None:
            new_process["Path"] = path
            new_process["Known Path"] = CyEnums.Path.parse_string(path)

        new_connection = {}
        if "Connections" not in new_process:
            new_process["Connections"] = []

        if local_port is None:
            local_port = kwargs.get("local_port", None)
        if local_port is not None:
            new_connection["local_port"] = int(local_port)

        if remote_port is None:
            remote_port = kwargs.get("remote_port", None)
        if remote_port is not None:
            new_connection["remote_port"] = int(remote_port)

        if local_address is None:
            local_address = kwargs.get("local_address", None)
        if local_address is not None:
            if type(local_address) is str:
                local_address = IPv4Address(local_address)
            new_connection["local_address"] = local_address
            self.add_interface_info(hostid=hostid, ip_address=local_address)

        if remote_address is None:
            remote_address = kwargs.get("remote_address", None)
        if remote_address is not None:
            if type(remote_address) is str:
                remote_address = IPv4Address(remote_address)
            new_connection["remote_address"] = remote_address

        if transport_protocol is not None:
            if type(transport_protocol) is str:
                transport_protocol = CyEnums.TransportProtocol.parse_string(transport_protocol)
            new_connection["Transport Protocol"] = transport_protocol

        if app_protocol is None:
            app_protocol = kwargs.get("Application Protocol", None)
        if app_protocol is not None:
            if type(app_protocol) is str:
                app_protocol = CyEnums.AppProtocol.parse_string(app_protocol)
            new_connection["Application Protocol"] = app_protocol

        if status is None:
            status = kwargs.get("Status", None)
        if status is not None:
            if isinstance(status, str):
                status = CyEnums.ProcessState.parse_string(status)
            new_connection["Status"] = status

        if new_connection != {}:
            new_process["Connections"].append(new_connection)
        elif new_process["Connections"] == []:
            new_process.pop("Connections")

        if process_type is None:
            process_type = kwargs.get("ProcessType", None)
        if process_type is not None:
            if type(process_type) is str:
                process_type = CyEnums.ProcessType.parse_string(process_type)
            new_process["ProcessType"] = process_type
        else:
            pass
            # this can occur with connection-type processe
            #print("process without process_type")

        if process_version is None:
            process_version = kwargs.get("ProcessVersion", None)
        if process_version is not None:
            if type(process_version) is str:
                process_version = CyEnums.ProcessVersion.parse_string(process_version)
            new_process["ProcessVersion"] = process_version

        if properties is None:
            properties = kwargs.get("Properties", None)
        if properties is not None:
            new_process["Properties"] = properties

        if vulnerability is None:
            vulnerability = kwargs.get("Vulnerability", None)
        if vulnerability is not None:
            if "Vulnerability" not in new_process:
                new_process["Vulnerability"] = []
            if type(vulnerability) is str:
                vulnerability = CyEnums.Vulnerability.parse_string(vulnerability)
            new_process["Vulnerability"].append(vulnerability)

        return new_process

    def merge_user_info(self, hostid, agent, **user):
        self.add_user_info(hostid=hostid, agent=agent, **user)

    def merge_file_info(self, hostid, agent, **file_info):
        self.add_file_info(hostid=hostid, agent=agent, **file_info)

    def merge_interface_info(self, hostid, agent, **interface):
        print("merge interface")
        print(interface)
        # compare interface with existing host interface list
        if "Interface" in self.data["hosts"][hostid]:
          for intf in self.data['hosts'][hostid]["Interface"]:
            # if new interface is a subset of existing interface
            # nothing to merge or add
            if interface == dict(set(interface.items()) & set(intf.items())):
                return
        self.add_interface_info(hostid=hostid, agent=agent, **interface)
        # as the above appends to a list, coalesce null elements in list
        #coalesce_list = [ i for i in self.data['hosts'][hostid]["Interface"] if i != {} ]
        #self.data['hosts'][hostid]["Interface"] = coalesce_list

    def merge_system_info(self, hostid, agent, **info):
        self.add_system_info(hostid=hostid, agent=agent, **info)



    def __str__(self):
        state_str = pprint.pformat(self.data)
        return f"{self.__class__.__name__}:\n{state_str}"
