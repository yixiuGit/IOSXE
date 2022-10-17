import requests
import urllib3
import json
import time
import logging
import logging.config
import yaml
from datetime import datetime
import pymongo


with open('log_config.yml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

# host = "sandbox-iosxe-recomm-1.cisco.com"


logger = logging.getLogger("applogger")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




class IOSXE_Device:
    restconf_port = 443
    restconf_base_url = "restconf/data"
    request_verify = False

    def __init__(self, device_ip, device_user, device_pw):
        self.device_ip = device_ip
        self.device_user = device_user
        self.device_pw = device_pw

    def restconf_get_request(self, yang_loc, inner_func, **kwargs):
        interfaces = {}
        try:
            headers = {'Content-Type': 'application/yang-data+json',
                      "Accept": "application/yang-data+json"}

            response = requests.request('GET',
                                        f"https://{self.device_ip}:{self.restconf_port}/{self.restconf_base_url}/{yang_loc}",
                                        headers=headers,
                                        auth=(self.device_user,self.device_pw),
                                        verify=self.request_verify)
            # print(response.text)
            if response.status_code == 200:
                logger.debug(self.device_ip + " | 200 Response: Successfully received data from" + f" {yang_loc}")
                try:
                    i = inner_func(response.json()[yang_loc])

                    return 200, i
                except:
                    pass
            elif response.status_code == 204:
                logger.warning((self.device_ip + " | 204 Response: Received no content from" + f" {yang_loc}"))

            print(response.raise_for_status())
            # print(response)
            # print(response.json()['ietf-interfaces:interfaces']['interface'])
            # print(len(response.json()['ietf-interfaces:interfaces']['interface']))
            # print(response.json()['ietf-interfaces:interfaces']['interface'][0]['name'])

        except requests.exceptions.HTTPError as errh:
            print(response.status_code)

    def dummy_fun(self, response_content):
        print("inner func test")
        timestamp = datetime.now().strftime("%d-%b-%Y %H:%M:%S")
        print(timestamp)
        response_content['interface'].insert(0, {'collecttime':timestamp})
        print(response_content)

        self.write_to_db(response_content, self.device_ip, "Interfaces")

    def restconf_iosxe_platform_oper(self, response_content):
        """
        Get data from Cisco-IOS-XE-platform-oper:components
        Add to pre-defined Django database model, best effort
        :return success: added
        :return error: None
        """
        print(response_content)
        # # add this information if not yet defined
        # if self.new_device.part_number == "":
        #     try:
        #         # get only the chassis information and iterative through the list, break early
        #         for component in response_content["component"]:
        #             if component["state"]["type"] == "comp-chassis":
        #                 self.new_device.part_number = component["state"]["part-no"]
        #                 self.new_device.serial_number = component["state"]["serial-no"]
        #                 break
        #     except:
        #         pass
        #
        # return "added"

    def restconf_iosxe_native(self, response_content):
        device_info = {}
        new_device = {}
        timestamp = datetime.now().strftime("%d-%b-%Y %H:%M:%S")
        print(timestamp)
        new_device['collecttime']= timestamp
        try:

            new_device['hostname'] = response_content['hostname']
            new_device['version'] = response_content['version']
        except:
            pass

        try:
            ios_users = []
            for user in response_content['username']:
                privilege = {user['name']: user['privilege']}
                ios_users.append(privilege)
            new_device['ios_users'] = ios_users
        except:
            pass

        try:
            new_device['domain_name'] = response_content['ip']['domain']['name']
        except:
            pass
        # self.new_device.hostname = response_content['hostname']
        # self.new_device.version = response_content['version']

        print(new_device)
        device_info['native'] = [new_device]
        print(device_info)
        self.write_to_db(device_info, self.device_ip, "Devices_Native")


    def restconf_iosxe_platform_software_oper(self, response_content):
        collectInfo = {}
        cpuInfo = {}
        parInfo = {}
        memInfo = {}
        try:
            cpu_user = 0.00
            cpu_system = 0.00
            cpu_idle = 0.00
            cores = 100
            for core in response_content["control-processes"]["control-process"][0]["per-core-stats"]["per-core-stat"]:
                cores +=100
                cpu_user += float(core['user'])
                cpu_system += float(core['system'])
                cpu_idle += float(core['idle'])
            cpuInfo['cpu_user_usage_percentage'] = round(cpu_user/cores *100, 2)
            cpuInfo['cpu_system_usage_percentage'] = round(cpu_system / cores * 100, 2)
            cpuInfo['cpu_idle_usage_percentage'] = round(cpu_idle / cores * 100, 2)
        except:
            cpuInfo['cpu_user_usage_percentage'] = "Fail to collect data"
            cpuInfo['cpu_system_usage_percentage'] = "Fail to collect data"
            cpuInfo['cpu_idle_usage_percentage'] = "Fail to collect data"

        try:
            parInfo['total_mb'] = round(int(response_content["q-filesystem"][0]["partitions"][0]['total-size'])/1000)
            parInfo['used_mb'] = round(int(response_content["q-filesystem"][0]["partitions"][0]['used-size'])/1000)
            parInfo['free_mb'] = parInfo['total_mb'] - parInfo['used_mb']
        except:
            parInfo['total_mb'] = "Fail to collect data"
            parInfo['used_mb'] = "Fail to collect data"
            parInfo['free_mb'] = "Fail to collect data"

        try:
            memInfo['status'] = response_content["control-processes"]["control-process"][0]["memory-stats"]["memory-status"]
            memInfo['total_mb'] = round(int(response_content["control-processes"]["control-process"][0]["memory-stats"]["total"])/1000)
            memInfo['free_mb'] = round(int(response_content["control-processes"]["control-process"][0]["memory-stats"]["free-number"])/1000)
            memInfo['free_percent'] = response_content["control-processes"]["control-process"][0]["memory-stats"]["free-percent"]
        except :
            memInfo['status'] = "Fail to collect data"
            memInfo['total_mb'] = "Fail to collect data"
            memInfo['free_mb'] = "Fail to collect data"
            memInfo['free_percent'] = "Fail to collect data"

        collectInfo['cpu'] = cpuInfo
        collectInfo['partition'] = parInfo
        collectInfo["memory"] = memInfo
        print(collectInfo)
        self.write_to_db(collectInfo, self.device_ip, "Devices_Native")

    def restconf_iosxe_device_hardware_oper(self, response_content):
        collectInfo = {}
        serialInfo = {}
        swInfo = {}
        upTimeInfo = {}

        try:
            serialInfo["serialNum"] = response_content[ "device-hardware"]["device-inventory"][0]["serial-number"]
        except:
            serialInfo["serialNum"] = "Fail to collect data"

        try:
            swInfo["version"] = response_content["device-hardware"]["device-system-data"]["software-version"].split(",")[2].split("Version ", 1)[1]
        except:
            swInfo["serialNum"] = "Fail to collect data"

        try:
            bootTime = datetime.strptime(response_content["device-hardware"]["device-system-data"]["boot-time"], '%Y-%m-%dT%H:%M:%S+00:00')
            currentTime = datetime.strptime(response_content["device-hardware"]["device-system-data"]["current-time"], '%Y-%m-%dT%H:%M:%S+00:00')
            upTimeInfo["bootTime"] = response_content["device-hardware"]["device-system-data"]["boot-time"]
            upTimeInfo["currentTime"] = response_content["device-hardware"]["device-system-data"]["current-time"]
            duration = currentTime - bootTime
            upTimeInfo["upTime"] = str(duration)
            print(upTimeInfo)
        except:
            upTimeInfo["bootTime"] = "Fail to collect data"
            upTimeInfo["currentTime"] = "Fail to collect data"
            upTimeInfo["upTime"] = "Fail to collect data"


    def restconf_cisco_smart_license(self, response_content):
        pass


    def restconf_iosxe_interfaces_oper(self, response_content):
        interfaces = []
        for interface in response_content["interface"]:
            try:
                appendInt = {}
                appendInt['name'] = interface['name']
                appendInt["description"] = interface["description"]
                last_change = datetime.strptime(interface["last-change"], '%Y-%m-%dT%H:%M:%S.%f+00:00')
                appendInt["last-change"] = last_change.strftime("%d.%m.%Y %H:%M:%S")
                if interface["admin-status"] == "if-state-up":
                    admin_status = "UP"
                elif interface["admin-status"] == "if-state-down":
                    admin_status = "DOWN"
                elif interface["admin-status"] == "if-state-test":
                    admin_status = "TEST"
                else:
                    admin_status = "UNKNOWN"
                appendInt["admin_status"] = admin_status
                if interface["oper-status"] == "if-oper-state-ready":
                    oper_status = "UP and CONNECTED"
                elif interface["oper-status"] == "if-oper-state-no-pass":
                    oper_status = "Administratively DOWN"
                elif interface["oper-status"] == "if-oper-state-lower-layer-down":
                    oper_status = "DOWN, ready to connect"
                elif interface["oper-status"] == "if-oper-state-invalid":
                    oper_status = "Invalid"
                elif interface["oper-status"] == "if-oper-state-dormant":
                    oper_status = "Dormant"
                elif interface["oper-status"] == "if-oper-state-not-present":
                    oper_status = "Not Present"
                else:
                    oper_status = "UNKNOWN"
                appendInt["oper_status"] = oper_status

                appendInt["phys_address"] = interface["phys-address"]
                if "ether-state" in interface:
                    appendInt["duplex_mode"] = interface["ether-state"]["negotiated-duplex-mode"]
                    appendInt["port_speed"] = interface["ether-state"]["negotiated-port-speed"]
                if "ipv4" in interface:
                    appendInt["ipv4_address"] = interface["ipv4"]
                    appendInt["ipv4_mask"] = interface["ipv4-subnet-mask"]

                interfaces.append(appendInt)
                print(interfaces)
            except:
                pass



    @staticmethod
    def collect_restconf_data(self):
        # self.restconf_get_request("ietf-interfaces:interfaces", self.dummy_fun)
        # self.restconf_get_request("Cisco-IOS-XE-platform-oper:components", self.restconf_iosxe_platform_oper)
        self.restconf_get_request("Cisco-IOS-XE-native:native", self.restconf_iosxe_native)
        self.restconf_get_request("Cisco-IOS-XE-platform-software-oper:cisco-platform-software",self.restconf_iosxe_platform_software_oper)
        # self.restconf_get_request("Cisco-IOS-XE-device-hardware-oper:device-hardware-data",
        #                            self.restconf_iosxe_device_hardware_oper)
        # self.restconf_get_request("cisco-smart-license:licensing", self.restconf_cisco_smart_license)
        self.restconf_get_request("Cisco-IOS-XE-interfaces-oper:interfaces", self.restconf_iosxe_interfaces_oper)




    def write_to_db(self, inputData,hostName, tableName):
        #this is for local testing
        myclient = pymongo.MongoClient("mongodb://localhost:27017/")
        #this is for docker mongodb://user:password@containername:27017
        myclient = pymongo.MongoClient("mongodb://root:rootpassword@code_mongodb_1:27017")
        #code_mongodb_1 -- container name
        mydb = myclient[tableName]
        mycol = mydb[hostName]
        # mongo admin -u root -p rootpassword to access mongodb container
        x = mycol.insert_one(inputData)
        print(x)


P1 = IOSXE_Device("sandbox-iosxe-latest-1.cisco.com","developer", "C1sco12345")
P1.collect_restconf_data(P1)
# P1.restconf_get_request("Cisco-IOS-XE-interfaces-oper:interfaces")