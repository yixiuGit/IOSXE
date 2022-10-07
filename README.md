# IOSXE Device information retrieving with YANG module

### Purpose
Create a Class contains methods that can retrieve different information from devices.
Using class @staticmethod to call all the class methods which will collect all information of the device and save in MongoDB.
Methods are expendable using the same script pattern

### Logic
Creating a new class object with required information(ip/hostname, login credential)
Applying class method to the new object
The class method(restconf_get_request) has 2 functions:
- connect to the device and retrieve data that provided by the YANG module
- call another method within the class to manipulate the retrieved data to get required information

restconf_get_request(self, yang_loc, inner_func, **kwargs)
yang_loc is the url of YANG module, it will be used to retrieve data from device
inner_func is the variable for another class method which will be called.
**kwargs currently is not in use, may be used for future

The hostname, credential can be entered manually through a menu interface or read from file.
It is not part of this script

### YANG module used so far
- etf-interfaces:interfaces
- Cisco-IOS-XE-platform-oper:components
- Cisco-IOS-XE-native:native
- Cisco-IOS-XE-platform-software-oper:cisco-platform-software
- Cisco-IOS-XE-device-hardware-oper:device-hardware-data
- cisco-smart-license:licensing
- Cisco-IOS-XE-interfaces-oper:interfaces