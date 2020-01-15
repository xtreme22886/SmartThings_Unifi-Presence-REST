# Import all libraries required
import json
import requests
import time
import warnings

# Ignore self-signed cert warning
warnings.filterwarnings("ignore")

def getConfig(): # Define getConfig() function
    try: # See if
        with open('config.json', 'r') as file: # We can open 'config.json' as file with read permissions
            settings = json.load(file) # Load the JSON data found in file
    except FileNotFoundError: # Could not open 'config.json' file
        return # Return a NULL response

    # Base URL of the Unifi Controller and site:
    global baseURL # Initilize global variable
    baseURL = 'https://{}/'.format(settings['unifi'][0]['address']) # Define Unifi Controller URL
    global siteID # Initilize global variable
    siteID = settings['unifi'][3]['site'] # Define Unifi Site ID

    # Credentials for the unifi controller:
    global loginCreds # Initilize global variable
    loginCreds = { # Define Unifi credentials in JSON form
        'username': settings['unifi'][1]['username'],
        'password': settings['unifi'][2]['password']
    }

    # API URLs
    global loginURL # Initilize global variable
    loginURL = '{}api/login'.format(baseURL) # Define URL to use to log into the Unifi Controller
    global logoutURL # Initilize global variable
    logoutURL = '{}api/logout'.format(baseURL) # Define URL to use to log out of the Unifi Controller
    global knownClientsURL # Initilize global variable
    knownClientsURL = '{}api/s/{}/rest/user'.format(baseURL, siteID) # Define URL to use to get list of known clients from the Unifi Controller
    return settings # Return contents of 'config.json'

getConfig() # Initilize the config settings at bootup

# Take a list of supplied mac address' and check their presence
def CheckPresence(macList): # Define CheckPresence() function
    session = requests.Session() # Begin request session
    login_response = session.post(loginURL, data=json.dumps(loginCreds).encode('utf8'), headers={'Content-type': 'application/json'}, verify=False) # Log into Unifi API
    if login_response.status_code == 200: # If login successful, do stuff:
        results = [] # Initilize list
        for mac in macList: # For each mac in macList
            macStatsURL = '{}api/s/{}/stat/user/{}'.format(baseURL, siteID, mac) # Define URL to use to get details about given mac address
            macStatsResponse = session.get(macStatsURL) # Request details of given mac address from the Unifi Controller
            data = macStatsResponse.json().get('data') # Grab the 'data' from the reply
            macStats = dict(data[0]) # Convert 'data' json list to dict (grab first element of list)
            isWired = macStats['is_wired'] # If wireless device shows wired, it means it's offline. Stupid Unifi
            try:
                visableToUAP = macStats['_last_seen_by_uap']
            except:
                visableToUAP = None
            if visableToUAP != None and isWired == False: # Bug in Unifi Controller has 'last_seen' time updating even after device has left the network. If a wireless device is now showing 'wired' then it's a good indication that it has left the network
                results.append({'mac': mac, 'present': True}) # Append results of presence check to results list
            else:
                results.append({'mac': mac, 'present': False}) # Append results of presence check to results list
        session.get(logoutURL) # Logout from the API
        return results # Return results list when done
    else:
        return # Return NULL if unable to log into the Unifi Controller

# Log into the Unifi Controller and generate a list of known wireless clients
def WiFiClients(): # Define WiFiClients() function
    # Ensure we have latest config settings
    check = getConfig() # Load data from the config file (force a load here in case config settings have changed)
    if check: # If config file exist
        session = requests.Session() # Begin request session
        login_response = session.post(loginURL, data=json.dumps(loginCreds).encode('utf8'), headers={'Content-type': 'application/json'}, verify=False) # Log into the Unifi API

        # Start process of logging into Unifi API and gathering data
        if login_response.status_code == 200: # If login successful, do stuff:
            knownClientsResponse = session.get(knownClientsURL) # Request list of known clients
            session.get(logoutURL) # Logout from the Unifi API
            clientList = knownClientsResponse.json().get('data') # Grab the 'data' from the reply
            knownWifiClients = [] # Initilize list
            for client in clientList: # For each client in clientList
                if client.get('is_wired', None) != None: # Get client 'is_wired' value. If none found, use default 'None'. If 'is_wired' does not equal None then continue
                    if client['is_wired'] == False: # If client 'is_wired' equals False
                        wireless = True # Then, set 'wireless' to True
                    else:
                        wireless = False # Else, set 'wireless' to False
                if client.get('mac', None) != None: # Get client 'mac' value. If none found, use default 'None'. If 'mac' does not equal None then continue
                    mac = client['mac'] # Set 'mac' to clients mac
                if client.get('name', None) != None: # Get client 'name' value. If none found, use default 'None'. If 'name' does not equal None then continue
                    name = client['name'] # Set name to clients name (perfer hostname over name)
                elif client.get('hostname', None) != None: # Get client 'hostname' value. If none found, use default 'hostname'. If 'name' does not equal None then continue
                    name = client['hostname'] # Set name to clients hostname (perfer hostname over name)
                else:
                    name = "unknown" # Set name to 'unknown' if a name/hostname could not be found

                # Only add wireless clients to knownWifiClients list
                if wireless == True: # If client wireless equals True
                    knownWifiClients.append({'name': name + " (" + mac[-5:] + ")", 'mac': mac, 'id': "unifi-" + mac[-5:]}) # Append client information to knownWifiClients list
            return sorted(knownWifiClients, key = lambda i: i['name']) # Return a sorted (by name) list of konwn wireless clients
    else: # No config file
        return # Return NULL
