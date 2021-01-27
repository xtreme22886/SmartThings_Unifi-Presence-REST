# Import required libraries
import requests
import socket
import json
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
        return "noconfig" # Return 'noconfig'

    # UniFi Controller base URL and UniFi Site ID
    global baseURL # Initilize global variable
    baseURL = 'https://{}/'.format(settings['unifi'][0]['address']) # Define UniFi Controller URL
    global siteID # Initilize global variable
    siteID = settings['unifi'][3]['site'] # Define UniFi Site ID

    # Credentials for the UniFi Controller
    global loginCreds # Initilize global variable
    loginCreds = { # Define UniFi credentials in JSON form
        'username': settings['unifi'][1]['username'],
        'password': settings['unifi'][2]['password'],
        'remember': True
    }

    # Check if UniFi Controller is reachable
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a socket
    s.settimeout(5) # Set socket timeout to 5 seconds
    if ":" in settings['unifi'][0]['address']: # If ':' is found in the UniFi Controller address
        address = settings['unifi'][0]['address'].split(":", 1)[0] # Split the first part to grab the IP address
        port = settings['unifi'][0]['address'].split(":", 1)[1] # Split the last part to grab the port
    else: # If ':' is not found
        address = settings['unifi'][0]['address'] # Grab the IP address
        port = 443 # Set the port
    result = s.connect_ex((address,int(port))) # Attempt to connect to IP address on specified port
    if result != 0: # If connection failed
        s.close() # Close the socket
        return "unreachable" # Return 'unreachable'
    s.close() # Close the socket

    # Check for UniFi OS (UDM Pro)
    unifiOS_check = requests.head('{}'.format(baseURL), verify=False) # Get header from the UniFi Controller
    if unifiOS_check.status_code == 200: # If header returns '200'
        unifiOS = True # Then UniFi Controller is running UniFi OS (UDM Pro)
    else: # Otherwise
        unifiOS = False # It's a standard UniFi Controller

    # API URLs
    global loginURL # Initilize global variable
    global loggedinURL # Initilze global variable
    global knownClientsURL # Initilize global variable
    global hotspotManagerURL # Initilize global variable
    global macStatsURL # Initilize global variable

    if unifiOS:
        loginURL = '{}api/auth/login'.format(baseURL) # Define URL to use to log into the UniFi Controller
        loggedinURL = '{}proxy/network/api/self'.format(baseURL) # Define URL to check if we are still logged in
        knownClientsURL = '{}proxy/network/api/s/{}/rest/user'.format(baseURL, siteID) # Define URL to use to get list of known clients from the UniFi Controller
        hotspotManagerURL = '{}proxy/network/api/s/{}/stat/guest'.format(baseURL, siteID) # Define URL to use to get list of known guest VIA the hotspot manager
        macStatsURL = '{}proxy/network/api/s/{}/stat/user/'.format(baseURL, siteID) # Define URL to use to get details about a mac address
    else:
        loginURL = '{}api/login'.format(baseURL) # Define URL to use to log into the UniFi Controller
        loggedinURL = '{}api/self'.format(baseURL) # Define URL to check if we are still logged in
        knownClientsURL = '{}api/s/{}/rest/user'.format(baseURL, siteID) # Define URL to use to get list of known clients from the UniFi Controller
        hotspotManagerURL = '{}api/s/{}/stat/guest'.format(baseURL, siteID) # Define URL to use to get list of known guest VIA the hotspot manager
        macStatsURL = '{}api/s/{}/stat/user/'.format(baseURL, siteID) # Define URL to use to get details about a mac address

    return settings # Return contents of 'config.json'

getConfig() # Initilize config settings at bootup
session = requests.Session() # Initilize request session at bootup
session.verify = False # Do not verify SSL cert

# Ensure we are logged into the UniFi Controller and maintain an active session
def sessionPersist(): # Define sessionPersist() function
    check = getConfig() # Get current config settings
    if (check == "noconfig" or check == "unreachable"): # If there are any issues loading the config
        return check # Return the error
    check_session = session.get(loggedinURL) # Query an API endpoint to see if we are logged in
    if check_session.status_code == 200: # We are already logged in
        return session # Return current session
    elif check_session.status_code == 401: # If query response returns '401' (not logged in) then
        session.cookies.clear() # Clear session cookies
        login_response = session.post(loginURL, json=loginCreds) # Log into the UniFi API
        if login_response.status_code == 200: # If login was successful
            return session # Return new session
        else: # If login failed
            return "unauthorized" # Return 'unauthorized'

# Take a list of supplied client mac address' and check their presence
def CheckPresence(clientMacList): # Define CheckPresence() function
    session = sessionPersist() # Run sessionPersist() to ensure we are logged in
    if (session == "noconfig" or session == "unreachable" or session == "unauthorized"): # If there are any issues with the session
        return session # Return the error
    results = [] # Initilize list
    for mac in clientMacList: # For each mac in clientMacList
        getMacStats = macStatsURL + mac # Define URL to use to get details about given mac address
        macStatsResponse = session.get(getMacStats) # Request details of given mac address from the UniFi Controller
        data = macStatsResponse.json().get('data') # Grab the 'data' from the reply
        macStats = dict(data[0]) # Convert 'data' json list to dict (grab first element of list)
        try: # See if
            visibleToUAP = macStats['_last_seen_by_uap'] # We can pull a value from this key
            results.append({'id': "unifi-" + mac[-5:], 'last_seen': int(time.time())}) # # Update 'last_seen' time with current epoch time
        except: # If not
            results.append({'id': "unifi-" + mac[-5:], 'last_seen': None}) # Keep 'last_seen' NULL
    return results # Return results list when done

# Generate a list of hotspot client mac address' that have not expired
def HotSpotClients(): # Define HotSpotClients() function
    hotspotManagerResponse = session.get(hotspotManagerURL) # Request list of hotspot clients
    guestList = hotspotManagerResponse.json().get('data') # Grab the 'data' from the reply
    guestMacList = [] # Initilize list
    for guest in guestList: # For each guest in guestList
        if guest.get('expired') == False: # If guest has not expired
            if guest.get('mac', None) != None: # Get guest 'mac' value. If none found, use default 'None'. If 'mac' does not equal None then continue
                guestMacList.append(guest['mac']) # Append guest mac to 'guestMacList'
    return guestMacList # Return list of UniFi guest mac address'

# Get a list a hotspot clients that are not expired and check their presence
def GuestCheckPresence(): # Define CheckPresence() function
    session = sessionPersist() # Run sessionPersist() to ensure we are logged in
    if (session == "noconfig" or session == "unreachable" or session == "unauthorized"): # If there are any issues with the session
        return session # Return the error
    guestMacList = HotSpotClients() # Call HotSpotClients() and save results as 'guestMacList'
    if guestMacList: # If 'guestMacList' has values
        results = None # Initilize variable
        for mac in guestMacList: # For each mac in guestMacList
            getMacStats = macStatsURL + mac # Define URL to use to get details about given mac address
            macStatsResponse = session.get(getMacStats) # Request details of given mac address from the UniFi Controller
            data = macStatsResponse.json().get('data') # Grab the 'data' from the reply
            macStats = dict(data[0]) # Convert 'data' json list to dict (grab first element in list)
            try: # See if
                visibleToUAP = macStats['_last_seen_by_uap'] # We can pull a value from this key
                return {'id': 'unifi-guest', 'last_seen': int(time.time())} # Update 'last_seen' time with current epoch time
            except: # If not
                results = {'id': 'unifi-guest', 'last_seen': None} # Set 'last_seen' to NULL
        return results # Return results list when done
    else: # If 'guestMacList' is empty
        return {'id': 'unifi-guest', 'last_seen': None} #Set 'last_seen' to NULL

# Generate a list of known UniFi clients
def UniFiClients(): # Define UniFiClients() function
    session = sessionPersist() # Run sessionPersist() to ensure we are logged in
    if (session == "noconfig" or session == "unreachable" or session == "unauthorized"): # If there are any issues with the session
        return session # Return the error
    knownClientsResponse = session.get(knownClientsURL) # Request list of known clients
    clientList = knownClientsResponse.json().get('data') # Grab the 'data' from the reply
    knownUniFiClients = [] # Initilize list
    for client in clientList: # For each client in clientList
        if client.get('mac', None) != None: # Get client 'mac' value. If none found, use default 'None'. If 'mac' does not equal None then continue
            mac = client['mac'] # Set 'mac' to client's mac
        if client.get('name', None) != None: # Get client 'name' value. If none found, use default 'None'. If 'name' does not equal None then continue
            name = client['name'] # Set name to client's name (perfer hostname over name)
        elif client.get('hostname', None) != None: # Get client 'hostname' value. If none found, use default 'hostname'. If 'name' does not equal None then continue
            name = client['hostname'] # Set name to client's hostname (perfer hostname over name)
        else: # If unable to determine a name for the client
            name = "unknown" # Set name to 'unknown'
        knownUniFiClients.append({'name': name + " (" + mac[-5:] + ")", 'mac': mac, 'id': "unifi-" + mac[-5:]}) # Append client information to knownUniFiClients list
    return sorted(knownUniFiClients, key = lambda i: i['name']) # Return a sorted (by name) list of konwn UniFi clients
