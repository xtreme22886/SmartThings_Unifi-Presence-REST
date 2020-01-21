# Import all libraries required
import json
import requests
import warnings

# Ignore self-signed cert warning
warnings.filterwarnings("ignore")

# Get the latest values from the config file and define global variables
def getConfig(): # Define getConfig() function
    try: # See if
        with open('config.json', 'r') as file: # We can open 'config.json' as file with read permissions
            settings = json.load(file) # Load the JSON data found in file
    except FileNotFoundError: # Could not open 'config.json' file
        return # Return a NUL response

    # Base URL of the Unifi Controller and site:
    global baseURL # Initilize global variable
    baseURL = 'https://{}/'.format(settings['unifi'][0]['address']) # Define Unifi Controller URL
    global siteID # Initilize global variable
    siteID = settings['unifi'][3]['site'] # Define Unifi Site ID

    # Credentials for the unifi controller:
    global loginCreds # Initilize global variable
    loginCreds = { # Define Unifi credentials in JSON form
        'username': settings['unifi'][1]['username'],
        'password': settings['unifi'][2]['password'],
        'remember': True
    }

    # API URLs
    global loginURL # Initilize global variable
    loginURL = '{}api/login'.format(baseURL) # Define URL to use to log into the Unifi Controller
    global loggedinURL # Initilze global variable
    loggedinURL = '{}api/self'.format(baseURL) # Define URL to check if we are still logged in
    global logoutURL # Initilize global variable
    logoutURL = '{}api/logout'.format(baseURL) # Define URL to use to log out of the Unifi Controller
    global knownClientsURL # Initilize global variable
    knownClientsURL = '{}api/s/{}/rest/user'.format(baseURL, siteID) # Define URL to use to get list of known clients from the Unifi Controller
    return settings # Return contents of 'config.json'

getConfig() # Initilize config settings at bootup
session = requests.Session() # Initilize request session at bootup

# Take a list of supplied mac address' and check their presence
def CheckPresence(macList): # Define CheckPresence() function
    session = sessionPersist() # Run sessionPersist() to ensure we are logged in
    results = [] # Initilize list
    for mac in macList: # For each mac in macList
        macStatsURL = '{}api/s/{}/stat/user/{}'.format(baseURL, siteID, mac) # Define URL to use to get details about given mac address
        macStatsResponse = session.get(macStatsURL) # Request details of given mac address from the Unifi Controller
        data = macStatsResponse.json().get('data') # Grab the 'data' from the reply
        macStats = dict(data[0]) # Convert 'data' json list to dict (grab first element of list)
        try: # See if
            visableToUAP = macStats['_last_seen_by_uap'] # We can pull a value from this key
            results.append({'mac': mac, 'present': True}) # If we can, mark device as 'online'
        except: # If not
            results.append({'mac': mac, 'present': False}) # Mark device as 'offline'
    return results # Return results list when done

# Ensure we are logged into the Unifi Controller and maintain an active session
def sessionPersist(): # Define sessionPersist() function 
    check_session = session.get(loggedinURL, verify=False) # Query an API endpoint to see if we are logged in
    if check_session.status_code == 200: # We are already logged in
        return session # Return current session
    elif check_session.status_code == 401: # If query response returns '401' (not logged in) then
        login_response = session.post(loginURL, data=json.dumps(loginCreds).encode('utf8'), headers={'Content-type': 'application/json'}, verify=False) # Log into the Unifi API
        if login_response.status_code == 200: # If login response was successful
            return session # Return new session

# Generate a list of known wireless clients
def WiFiClients(): # Define WiFiClients() function
    # Ensure we have latest config settings
    check = getConfig() # Load data from the config file (force a load here in case config settings have changed)
    if check: # If config file exist
        session = sessionPersist() # Run sessionPersist() to ensure we are logged in
        knownClientsResponse = session.get(knownClientsURL) # Request list of known clients
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
        return # Return NUL
