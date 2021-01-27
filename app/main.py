# Import required libraries
import requests
import uvicorn
import logging
import time
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from .unifi import CheckPresence, GuestCheckPresence, UniFiClients

monitoringInterval = 5 # Interval in seconds on when to check presence of devices

updateURL = None # Initilize global variable and set initial value to NULL (to be used in checkPresence)

sched = BackgroundScheduler() # Initilize Backgroud Scheduler
sched.start() # Start Backgroup Scheduler
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING) # Set apscheduler's logging to only output warning messages

# Process data given in 'settings' POST
class STsettings(BaseModel): # Define / initilize STsettings class
    app_url: str # Process app_url as a string (is required)
    app_id: str # Process app_id as a string (is required)
    access_token: str # Process access_token as a string (is required)
    unifiAddress: str # Process unifiAddress as a string (is required)
    unifiUsername: str # Process unifiUsername as a string (is required)
    unifiPassword: str # Process unifiPassword as a string (is required)
    unifiSite: str # Process unifiSite as a string (is required)
    offlineDelay: int # Process offlineDelay as integer (is required)

# Process data given in 'monitor' POST
class UniFimonitor(BaseModel): # Define / initilize UniFimonitor class
    toMonitor: list = None # Process toMonitor as a list (is NOT required)

# Check the presence of devices we are monitoring (to be called every X seconds)
def checkPresence(): # Define checkPresence() function
    devicePresenceStatus = CheckPresence(clientMacList) # Call CheckPresence() function and pass it a list of macs we built earlier and store results as 'devicePresenceStatus'
    if devicePresenceStatus == "noconfig": # If there is no config file
        logging.info("{} - No config file was found!".format(time.asctime())) # Log that no config file was found
        return # Exit function
    if devicePresenceStatus == "unreachable": # If the UniFi Controller is unreachable
        logging.info("{} - UniFi Controller is unreachable!".format(time.asctime())) # Log that the UniFi Controller is unreachable
        return # Exit function
    if devicePresenceStatus == "unauthorized": # If unable to log into the UniFi Controller
        logging.info("{} - Unable to log into the UniFi Controller!".format(time.asctime())) # Log that we are unable to log into the UniFi Controller
        return # Exit function

    presenceChange = {} # Initilze JSON data
    presenceChange['update'] = [] # Add 'update' key to JSON data and initlize a list

    # Load data from 'monitoring.json' file to be compared with values from current presence check
    with open('monitoring.json', 'r') as file: # Open 'monitoring.json' as file with read permissions
        monitoring = json.load(file) # Load the JSON data found in file to a variable

    # Load data from 'config.json' file to get "offline_delay" value
    with open('config.json', 'r') as file: # Open 'config.json' as file with read permissions
        settings = json.load(file) # Load the JSON data found in file to a variable

    # Check to see if we are monitoring guest
    for client in monitoring['monitoring']: # For each client in 'monitoring.json' file
        if client['id'] == "unifi-guest": # If client equals "unifi-guest"
            devicePresenceStatus.append(GuestCheckPresence()) # Then add it's current presence to the 'devicePresenceStatus' list

    # Compare values from current presence check with what was found in 'monitoring.json' file and if presence changed, note it
    for device in devicePresenceStatus: # For each device in devicePresenceStatus
        for client in monitoring['monitoring']: # For each device in 'monitoring.json' file
            if device['id'] == client['id']: # If device id from devicePresenceStatus matches the device id from monitoring list
                if device['last_seen']: # If device 'last_seen' value is not NULL (NULL = offline (don't update 'last_seen' value); value = online (update 'last_seen' value to current time))
                    client['last_seen'] = device['last_seen'] # Then update client 'last_seen' value with the current time (device['last_seen'])
                if (int(time.time()) - client['last_seen']) >= int(settings['unifi'][4]['offline_delay']): # If client has been 'Away' greater than the time specified in the ST SmartApp
                    newPresenceState = False # Set newPreseneState to "False"
                else: # If client has been seen within the offline delay time
                    newPresenceState = True # Set newPreseneState to "True"
                if client['present'] != newPresenceState: # If client's existing presence does not match current presence
                    client['present'] = newPresenceState # Then set client's status to current presence
                    presenceChange['update'].append({'id': client['id'], 'present': newPresenceState}) # Append device ID and current present state to presenceChange
                client['last_check'] = (int(time.time())) # Update 'monitoring.json' file with device's last_check epoch time  

    # If changes were detected in presence, inform SmartThings SmartApp of them
    if presenceChange['update']: # If presenceChange has values
        global updateURL # Using the global variable 'updateURL' we set up in the globals section
        logging.info("{} - {}".format(time.asctime(), presenceChange)) # Log the changes that occured
        if updateURL == None: # If updateURL has not been configured
            configs = config() # Then load data from the config.json file by calling the config() function and capturing it's output as 'configs'
            updateURL = ("{}{}/update?access_token={}".format(configs['st'][0]['app_url'], configs['st'][1]['app_id'], configs['st'][2]['access_token'])) # Create the URL needed to connect to the SmartThings SmartApp to provide it the change of presence states
        headers = {'Content-type': 'application/json'} # Define headers to be used in HTTPS POST request
        requests.post(updateURL, data=json.dumps(presenceChange), headers=headers) # Use requests to POST all presence changes to SmartThings SmartApp as a list

    # Write changes in presence states to 'monitoring.json' file
    with open('monitoring.json', 'w') as file: # Open 'monitoring.json' as a file with write permissions
        json.dump(monitoring, file, indent=4) # Write updated values to 'monitoring.json' file


# Start presence check process at bootup if there are devices to monitor (running in global space)
try: # See if
    with open('monitoring.json', 'r') as file: # We can open 'monitoring.json' as file with read permissions
        data = json.load(file) # Load the JSON data found in file
        if data['monitoring']: # If the 'monitoring.json' file has devices to monitor
            clientMacList = [] # Initlize a new list
            for client in data['monitoring']: # For each client in our 'mointoring.json' file
                try: # See if
                    clientMacList.append(client['mac']) # There is a mac key. If so, append client's mac address to clientMacList list
                except: # If not
                    None # Then do nothing
                sched.add_job(checkPresence, # Add new job to scheduler to run checkPresence() every X seconds and to replace exisiting jobs if they are found
                      		'interval',
                      		seconds=monitoringInterval,
                      		id='checkPresence',
                      		replace_existing=True)
except FileNotFoundError: # Could not open 'monitoring.json' file
    logging.info("{} - No monitoring file was found!".format(time.asctime())) # Log there is no monitoring file

app = FastAPI() # Initilize FastAPI

@app.get("/", response_class=HTMLResponse) # To do when someone GET root '/' page
def root(): # Define root() function
    return """
    <html>
    <p style="text-align: center;"><img src="https://raw.githubusercontent.com/xtreme22886/SmartThings_UniFi-Presence-Sensor/master/ubiquiti.png" alt="" width="150" height="150" /></p>
    <h1 style="text-align: center;"><span style="text-decoration: underline;">UniFi Presence Controller</span></h1>
    <h3 style="text-align: center;">version 2.0</h3>
    <ul>
    <li><strong>/config</strong>
    <ul>
    <li>Access the config file</li>
    </ul>
    </li>
    <li><strong>/monitoring</strong>
    <ul>
    <li>Access the monitoring file</li>
    </ul>
    </li>
    <li><strong>/unificlients</strong>
    <ul>
    <li>Get a list of UniFi clients</li>
    <li>Will alert you if:
    <ul>
    <li>No config file was found</li>
    <li>Unable to reach the UniFi Controller</li>
    <li>Unable to authenticate with the UniFi Controller</li>
    </ul>
    </li>
    </ul>
    </li>
    </ul>
    <p>&nbsp;</p>
    <p style="text-align: center;">If you found this solution to be helpful, please consider a small donation to buy me a drink :P</p>
    <form style="text-align: center;" action="https://www.paypal.com/donate" method="post" target="_blank"><input name="hosted_button_id" type="hidden" value="HEZ9EPNJR2UYA" /> <input title="PayPal - The safer, easier way to pay online!" alt="Donate with PayPal button" name="submit" src="https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif" type="image" /> <img src="https://www.paypal.com/en_US/i/scr/pixel.gif" alt="" width="1" height="1" border="0" /></form>
    </html>"""

@app.get("/config") # To do when someone GET '/config' page
def config(): # Define config() function
    try: # See if
        with open('config.json', 'r') as file: # We can open 'config.json' as file with read permissions
            config = json.load(file) # Load JSON data found in file
            return config # Return output of file
    except FileNotFoundError: # Could not open 'config.json' file
        return "No config file was found!" # Return there is no config file

@app.get("/monitoring") # To do when someone GET '/monitoring' page
def monitoring(): # Define monitoring() function
    try: # See if
        with open('monitoring.json', 'r') as file: # We can open 'monitoring.json' as file with read permissions
            monitoring = json.load(file) # Load JSON data found in file
            return monitoring # Return output of file
    except FileNotFoundError: # Could not open 'monitoring.json' file
        return "No monitoring file was found!" # Return there is no monitoring file

@app.post("/settings") # To do when someone POST to '/settings' page
def settings(settings: STsettings): # Pass data supplied in POST to pydantic (STsettings) to be processed into objects
    data = {} # Initilize JSON data
    data['st'] = [] # Add 'st' key to JSON data and initlize a list
    data['unifi'] = [] # Add 'unifi' key to JSON data and initlize a list
    data['st'].append({'app_url': settings.app_url}) # Append app_url to 'st' key list
    data['st'].append({'app_id': settings.app_id}) # Append app_id to 'st' key list
    data['st'].append({'access_token': settings.access_token}) # Append access_token to 'st' key list
    data['unifi'].append({'address': settings.unifiAddress}) # Append address to 'unifi' key list
    data['unifi'].append({'username': settings.unifiUsername}) # Append username to 'unifi' key list
    data['unifi'].append({'password': settings.unifiPassword}) # Append password to 'unifi' key list
    data['unifi'].append({'site': settings.unifiSite}) # Append site to 'unifi' key list
    data['unifi'].append({'offline_delay': settings.offlineDelay}) # Append offline_delay to 'unifi' key list

    with open('config.json', 'w') as file: # Open 'config.json' as file with write permissions
        json.dump(data, file, indent=4, sort_keys=True) # Write 'data' JSON object to file

    # Obfuscate the UniFi password and st access token
    for setting in data['unifi']: # For each setting in the 'unifi' JSON section
        if setting == {'password': settings.unifiPassword}: # If we are able to locate the UniFi password
            setting['password'] = "<redacted>" # Then replace the password with <redacted>
    for setting in data['st']: # For each setting in the 'st' JSON section
        if setting == {'access_token': settings.access_token}: # if we are able to locate the st acess token
            setting['access_token'] = "<redacted>" # then replace the access token with <redacted>

    logging.info("{} - Received {} and saved to config.json".format(time.asctime(), data)) # Log the data that was received and save to config.json

@app.get("/unificlients") # To do when someone GET '/unificlients' page
def unificlients(): # Define unificlients() function
    clients = UniFiClients() # Call UniFiClients() function and store retuned list as clients
    if clients == "noconfig": # If there is no config file
        return "No config file was found!" # Log that no config file was found
    if clients == "unreachable": # If the UniFi Controller is unreachable
        return "UniFi Controller is unreachable" # Log that the UniFi Controller is unreachable
    if clients == "unauthorized": # If unable to log into the UniFi Controller
        return "Unable to log into the UniFi Controller" # Log that we are unable to log into the UniFi Controller

    list = [] # Initilize new list
    for client in clients: # For each client in unifiClients
        list.append(client['name']) # Append client name to list
    return list # Return final list of client names

@app.post("/monitor") # To do when someone POST to '/monitor' page
def monitor(monitor: UniFimonitor): # Pass data supplied in POST to pydantic (UniFimonitor) to be processed into objects
    sched.pause() # Pause the background scheduler
    global clientMacList # Initilizing global variable
    monitoringList = None # Initilize list

    if monitor.toMonitor: # If toMonitor list has values
        clientMacList = [] # Initilize list
        presenceCheckList = [] # Initilze list
        monitoringList = [] # Initlize list
        clients = UniFiClients() # Get list of UnifiClients
        if clients == "noconfig": # If there is no config file
            logging.info("{} - No config file was found!".format(time.asctime())) # Log that no config file was found
            return # Exit function
        if clients == "unreachable": # If the UniFi Controller is unreachable
            logging.info("{} - UniFi Controller is unreachable!".format(time.asctime())) # Log that the UniFi Controller is unreachable
            return # Exit function
        if clients == "unauthorized": # If unable to log into the UniFi Controller
            logging.info("{} - Unable to log into the UniFi Controller!".format(time.asctime())) # Log that we are unable to log into the UniFi Controller
            return # Exit function

        for monitor in monitor.toMonitor: # For each device to 'monitor' in toMonitor
            if monitor == "unifi-guest": # If device equals "unifi-guest"
                    monitoringList.append({'name': "unifi-guest", 'id': "unifi-guest", 'last_seen': 0, 'present': None, 'last_check': None}) # Then, append to monitoringList information about guest
                    presenceCheckList.append('unifi-guest') # Apend "unifi-guest" to presenceCheckList
            for client in clients: # For each client in clients
                if monitor == client['name']: # If device to 'monitor' equals a client's name found in the UniFi client list
                    monitoringList.append({'name': client['name'], 'mac': client['mac'], 'id': client['id'], 'last_seen': 0, 'present': None, 'last_check': None}) # Append to monitoringList information about this device
                    clientMacList.append(client['mac']) # Append the device's mac address to the clientMacList
                    presenceCheckList.append(client['id']) # Append the device's id to the presenceCheckList
        logging.info("{} - Starting presence checks every {} seconds for: {}".format(time.asctime(), monitoringInterval, presenceCheckList)) # Log the list of devices we are going to monitor every X seconds
        sched.resume() # Resume background scheduler
        sched.add_job(checkPresence, # Add new job to scheduler to run checkPresence() every X seconds and to replace exisiting jobs if they are found
                      'interval',
                      seconds=monitoringInterval,
                      id='checkPresence',
                      replace_existing=True)
    else: # toMonitor list is empty
        logging.info("{} - Stopping all presence checks".format(time.asctime())) # Keep backgroud scheduler paused and log that presence checks are currently disabled

    monitoringConfig = {} # Initlize JSON data
    monitoringConfig['monitoring'] = monitoringList # Add 'monitoring' key to JSON data and set value to monitoringList

    with open('monitoring.json', 'w') as file: # Open 'monitoring.json' as file with write permissions
        json.dump(monitoringConfig, file, indent=4) # Write 'monitoringConfig' JSON object to file
