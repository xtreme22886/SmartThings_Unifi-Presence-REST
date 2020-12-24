# Import required libraries
import json
import requests
import time

# Ignore SSL cert warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Get the latest values from the config file and define global variables
def getConfig(): # Define getConfig() function
    try: # See if
        with open('config.json', 'r') as file: # We can open 'config.json' as file with read permissions
            settings = json.load(file) # Load the JSON data found in file
    except FileNotFoundError: # Could not open 'config.json' file
        return # Return a NUL response

    # UniFi Controller base URL and UniFi Site ID
    global baseURL # Initilize global variable
    baseURL = 'https://{}/'.format(settings['unifi'][0]['address']) # Define UniFi Controller base URL
    global siteID # Initilize global variable
    siteID = settings['unifi'][3]['site'] # Define UniFi Site ID

    # Credentials for the UniFi Controller
    global loginCreds # Initilize global variable
    loginCreds = { # Define UniFi credentials in JSON form
        'username': settings['unifi'][1]['username'],
        'password': settings['unifi'][2]['password'],
        'remember': True
    }
    
    # Check for UniFi OS (UDM Pro)
    unifiOS_check = requests.head('{}'.format(baseURL), verify=False) # Get UniFi Controller header
    if unifiOS_check.status_code == 200: # Header will return 200 if UniFi OS
        unifiOS = True
    if unifiOS_check.status_code == 302: # Header will return 302 (redirect) to /manage if this is a standard controller
        unifiOS = False

    # API URLs
    global loginURL # Initilize global variable
    global loggedinURL # Initilze global variable
    global knownClientsURL # Initilize global variable
    global hotspotManagerURL # Initilize global variable
    
    if unifiOS:
        loginURL = '{}api/auth/login'.format(baseURL) # Define URL to use to log into the UniFi Controller
        loggedinURL = '{}proxy/network/api/self'.format(baseURL) # Define URL to check if we are still logged in
        knownClientsURL = '{}proxy/network/api/s/{}/rest/user'.format(baseURL, siteID) # Define URL to use to get list of known clients from the UniFi Controller
        hotspotManagerURL = '{}proxy/network/api/s/{}/stat/guest'.format(baseURL, siteID) # Define URL to use to get list of known guest VIA the hotspot manager
    else:
        loginURL = '{}api/login'.format(baseURL) # Define URL to use to log into the UniFi Controller
        loggedinURL = '{}api/self'.format(baseURL) # Define URL to check if we are still logged in
        knownClientsURL = '{}api/s/{}/rest/user'.format(baseURL, siteID) # Define URL to use to get list of known clients from the UniFi Controller
        hotspotManagerURL = '{}api/s/{}/stat/guest'.format(baseURL, siteID) # Define URL to use to get list of known guest VIA the hotspot manager
    
    return settings # Return contents of 'config.json'

getConfig() # Initilize config settings at bootup
session = requests.Session() # Initilize request session at bootup
session.verify = False # Do not verify SSL cert

# Ensure we are logged into the UniFi Controller and maintain an active session
def sessionPersist(): # Define sessionPersist() function
    check_session = session.get(loggedinURL) # Query an API endpoint to see if we are logged in
    if check_session.status_code == 200: # We are already logged in
        return session # Return current session
    elif check_session.status_code == 401: # If query response returns '401' (not logged in) then
        session.cookies.clear() # Clear session cookies
        login_response = session.post(loginURL, json=loginCreds) # Log into the UniFi API
        if login_response.status_code == 200: # If login response was successful
            return session # Return new session

# Take a list of supplied client mac address' and check their presence
def CheckPresence(clientMacList): # Define CheckPresence() function
    session = sessionPersist() # Run sessionPersist() to ensure we are logged in
    results = [] # Initilize list
    for mac in clientMacList: # For each mac in clientMacList
        macStatsURL = '{}api/s/{}/stat/user/{}'.format(baseURL, siteID, mac) # Define URL to use to get details about given mac address
        macStatsResponse = session.get(macStatsURL) # Request details of given mac address from the UniFi Controller
        data = macStatsResponse.json().get('data') # Grab the 'data' from the reply
        macStats = dict(data[0]) # Convert 'data' json list to dict (grab first element of list)
        try: # See if
            visibleToUAP = macStats['_last_seen_by_uap'] # We can pull a value from this key
            results.append({'id': "unifi-" + mac[-5:], 'last_seen': int(time.time())}) # # Update 'last_seen' time with current epoch time
        except: # If not
            results.append({'id': "unifi-" + mac[-5:], 'last_seen': None}) # Keep 'last_seen' NULL
    return results # Return results list when done

# Get a list a hotspot clients that are not expired and check their presence
def GuestCheckPresence(): # Define CheckPresence() function
    session = sessionPersist() # Run sessionPersist() to ensure we are logged in
    guestMacList = HotSpotClients() # Call HotSpotClients() and save results as 'guestMacList'
    if guestMacList: # If 'guestMacList' has values
        results = None # Initilize variable
        for mac in guestMacList: # For each mac in guestMacList
            macStatsURL = '{}api/s/{}/stat/user/{}'.format(baseURL, siteID, mac) # Define URL to use to get details about given mac address
            macStatsResponse = session.get(macStatsURL) # Request details of given mac address from the UniFi Controller
            data = macStatsResponse.json().get('data') # Grab the 'data' from the reply
            macStats = dict(data[0]) # Convert 'data' json list to dict (grab first element of list)
            try: # See if
                visibleToUAP = macStats['_last_seen_by_uap'] # We can pull a value from this key
                return {'id': 'unifi-guest', 'last_seen': int(time.time())} # Update 'last_seen' time with current epoch time
            except: # If not
                results = {'id': 'unifi-guest', 'last_seen': None} # Keep 'last_seen' NULL
        return results # Return results list when done
    else:
        return {'id': 'unifi-guest', 'last_seen': None}

# Generate a list of known UniFi clients
def UniFiClients(): # Define UniFiClients() function
    # Ensure we have latest config settings
    check = getConfig() # Load data from the config file (force a load here in case config settings have changed)
    if check: # If config file exist
        session = sessionPersist() # Run sessionPersist() to ensure we are logged in
        knownClientsResponse = session.get(knownClientsURL) # Request list of known clients
        clientList = knownClientsResponse.json().get('data') # Grab the 'data' from the reply
        knownUniFiClients = [] # Initilize list
        for client in clientList: # For each client in clientList
            if client.get('mac', None) != None: # Get client 'mac' value. If none found, use default 'None'. If 'mac' does not equal None then continue
                mac = client['mac'] # Set 'mac' to clients mac
            if client.get('name', None) != None: # Get client 'name' value. If none found, use default 'None'. If 'name' does not equal None then continue
                name = client['name'] # Set name to clients name (perfer hostname over name)
            elif client.get('hostname', None) != None: # Get client 'hostname' value. If none found, use default 'hostname'. If 'name' does not equal None then continue
                name = client['hostname'] # Set name to clients hostname (perfer hostname over name)
            else:
                name = "unknown" # Set name to 'unknown' if a name/hostname could not be found
            knownUniFiClients.append({'name': name + " (" + mac[-5:] + ")", 'mac': mac, 'id': "unifi-" + mac[-5:]}) # Append client information to knownUniFiClients list
        return sorted(knownUniFiClients, key = lambda i: i['name']) # Return a sorted (by name) list of konwn UniFi clients
    else: # No config file
        return # Return NUL

# Generate a list of hotspot client mac address' that have not expired
def HotSpotClients(): # Define HotSpotClients() function
    # Ensure we have latest config settings
    check = getConfig() # Load data from the config file (force a load here in case config settings have changed)
    if check: # If config file exist
        session = sessionPersist() # Run sessionPersist() to ensure we are logged in
        hotspotManagerResponse = session.get(hotspotManagerURL) # Request list of hotspot clients
        guestList = hotspotManagerResponse.json().get('data') # Grab the 'data' from the reply
        guestMacList = [] # Initilize list
        for guest in guestList: # For each guest in guestList
            if guest.get('expired') == False: # If guest has not expired
                if guest.get('mac', None) != None: # Get guest 'mac' value. If none found, use default 'None'. If 'mac' does not equal None then continue
                    guestMacList.append(guest['mac']) # Append guest mac to 'guestMacList'
        return guestMacList # Return list of UniFi guest mac address'
    else: # No config file
        return # Return NUL
