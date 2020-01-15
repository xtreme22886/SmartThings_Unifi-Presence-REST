# Import all libraries required
import uvicorn
import json
import time
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from .unifi import CheckPresence, WiFiClients
from apscheduler.schedulers.background import BackgroundScheduler

monitoringInterval = 5 # Interval in seconds on when to check presence of devices

updateURL = None # Initilize global variable and set initial value to NULL (to be used in checkPresence)

sched = BackgroundScheduler() # Initilize Backgroud Scheduler
sched.start() # Start Backgroup Scheduler

# Process data given in 'settings' POST
class STsettings(BaseModel): # Define / initilize STsettings class
    app_url: str # Process app_url as a string (is required)
    app_id: str # Process app_id as a string (is required)
    access_token: str # Process access_token as a string (is required)
    unifiAddress: str # Process unifiAddress as a string (is required)
    unifiUsername: str # Process unifiUsername as a string (is required)
    unifiPassword: str # Process unifiPassword as a string (is required)
    unifiSite: str # Process unifiSite as a string (is required)

# Process data given in 'monitor' POST
class Unifimonitor(BaseModel): # Define / initilize Unifimonitor class
    toMonitor: list = None # Process toMonitor as a list (is NOT required)

# Check the presence of devices we are monitoring (to be called every 10 seconds)
def checkPresence(): # Define checkPresence() function
    presenceChange = {} # Initilze JSON data
    presenceChange['update'] = [] # Add 'update' key to JSON data and initlize a list
    devicePresenceStatus = CheckPresence(macList) # Call CheckPresence() function and pass it a list of macs we built earlier and store results as 'devicePresenceStatus'

    # Load data from 'monitoring.json' file to be compared with values from current presence check
    with open('monitoring.json', 'r') as file: # Open 'monitoring.json' as file with read permissions
        monitoring = json.load(file) # Load the JSON data found in file to a variable

    # Compare values from current presence check with what was found in 'monitoring.json' file and if presence changed, note it
    for device in devicePresenceStatus: # For each device in devicePresenceStatus
        for monitor in monitoring['monitoring']: # For each device we 'monitor' in the 'monitoring' list
            if device['mac'] == monitor['mac']: # If device mac from devicePresenceStatus matches the device mac from monitoring list
                if device['present'] != monitor['present']: # If the current present status is different than the present status on file
                   presenceChange['update'].append({'id': monitor['id'], 'present': device['present']}) # Append device ID and present state to presenceChange
                monitor['present'] = device.get('present') # Update 'monitoring.json' file with device's current present state
                monitor['last_check'] = (int(time.time())) # Update 'monitoring.json' file with device's last_check epoch time

    # If changes were detected in presence, inform SmartThings SmartApp of them
    if presenceChange['update']: # If presenceChange has values
        global updateURL # Using the global variable 'updateURL' we set up in the globals section
        print (presenceChange) # Print to screen the changes that occured
        if updateURL == None: # If updateURL has not been configured
            configs = config() # Load data from the config.json file by calling the config() function and capturing it's output as 'configs'
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
        if data['monitoring']: # See if 'monitoring' list has devices
            macList = [] # Initlize a new list
            for device in data['monitoring']: # For each device in our mointoring.json file
                macList.append(device['mac']) # Append device's mac address to macList list
                sched.add_job(checkPresence, # Add new job to scheduler to run checkPresence() every X seconds and to replace exisiting jobs if they are found
                      		'interval',
                      		seconds=monitoringInterval,
                      		id='checkPresence',
                      		replace_existing=True)
except FileNotFoundError: # Could not open 'monitoring.json' file
    print ("No monitoring file!") # Print to screen there is no monitoring file

app = FastAPI() # Initilize FastAPI

@app.get("/") # To do when someone GET root '/' page
def root(): # Define root() function
    return {"message": "Hello World"} # Return message

@app.get("/config") # To do when someone GET '/config' page
def config(): # Define config() function
    try: # See if
        with open('config.json', 'r') as file: # We can open 'config.json' as file with read permissions
            config = json.load(file) # Load JSON data found in file
            return config # Return output of file
    except FileNotFoundError: # Could not open 'config.json' file
        return "No config file!" # Return there is no config file

@app.get("/monitoring") # To do when someone GET '/monitoring' page
def monitoring(): # Define monitoring() function
    try: # See if
        with open('monitoring.json', 'r') as file: # We can open 'monitoring.json' as file with read permissions
            monitoring = json.load(file) # Load JSON data found in file
            return monitoring # Return output of file
    except FileNotFoundError: # Could not open 'monitoring.json' file
        return "No monitoring file!" # Return there is no monitoring file

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

    with open('config.json', 'w') as file: # Open 'config.json' as file with write permissions
        json.dump(data, file, indent=4, sort_keys=True) # Write 'data' JSON object to file
        
    # Obfuscate the Unifi password
    visablePassword = {'password': settings.unifiPassword} # Define password to obfuscate
    for setting in data['unifi']: # For each setting in the 'Unifi' JSON section
        if setting == visablePassword: # If we are able to locate the Unifi password
            setting['password'] = "<password>" # Then replace the password with <password>

    print("Received {} and saved to config.json".format(data)) # Print to screen the data that was received and save to config.json

@app.get("/wificlients") # To do when someone GET '/wificlients' page
def wificlients(): # Define wificlients() function
    print("Sending client list") # Print to screen that we are sending a list of clients to who ever requested them
    wirelessClients = WiFiClients() # Call WiFiClients() function and store retuned list as wirelessClients

    if wirelessClients: # If list is not empty
        list = [] # Initilize new list
        for client in wirelessClients: # For each client in wirelessClients
            list.append(client['name']) # Append client name to list
        return list # Return final list of client names
    else: # If list is empty
        return("No config file!") # Return that there is no settings config file

@app.post("/monitor") # To do when someone POST to '/monitor' page
def monitor(monitor: Unifimonitor): # Pass data supplied in POST to pydantic (Unifimonitor) to be processed into objects
    sched.pause() # Pause the background scheduler
    global macList # Initilizing global variable
    monitoringList = None # Initlizing variable

    if monitor.toMonitor: # If toMonitor list has values
        macList = [] # Initilize list
        monitoringList = [] # Initilize list
        for monitor in monitor.toMonitor: # For each device to 'monitor' in toMonitor
            for client in WiFiClients(): # For each client in the wireless clients list provided by WiFiClients()
                if monitor == client['name']: # If device to 'monitor' equals a client's name found in the wireless clients list
                    monitoringList.append({'name': client['name'], 'mac': client['mac'], 'id': client['id'], 'present': None, 'last_check': None}) # Append to monitoringList information about this device
                    macList.append(client['mac']) # Append the devicse's mac address to the macList
        print("Starting presence checks every {} seconds for: {}".format(monitoringInterval, macList)) # Print to screen the list of devices we are going to monitor every 10 seconds
        sched.resume() # Resume background scheduler
        sched.add_job(checkPresence, # Add new job to scheduler to run checkPresence() every X seconds and to replace exisiting jobs if they are found
                      'interval',
                      seconds=monitoringInterval,
                      id='checkPresence',
                      replace_existing=True)
    else: # toMonitor list is empty
        print("Stopping all presence checks") # Keep backgroud scheduler paused and print to screen that presence checks are currently disabled

    monitoringConfig = {} # Initlize JSON data
    monitoringConfig['monitoring'] = monitoringList # Add 'monitoring' key to JSON data and set value to monitoringList
    
    with open('monitoring.json', 'w') as file: # Open 'monitoring.json' as file with write permissions
        json.dump(monitoringConfig, file, indent=4) # Write 'monitoringConfig' JSON object to file
