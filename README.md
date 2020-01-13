# SmartThings <-> Unifi Presence Sensor (BRIDGE)
Integration for SmartThings to use Unifi wireless clients as presence sensors

**Warning**: no authentication is performed. Don't expose this service to outside network.

For x32/x64

Run this image:
`docker run -d --restart always --name unifi-presence -p 9443:9443 xtreme22886/unifi-presence-rest`

For ARM (Raspberry Pi)

Run this image:
`docker run -d --restart always --name unifi-presence -p 9443:9443 xtreme22886/unifi-presence-rest-arm`

To change the port Docker container is using:
The `-p` cmd tells Docker which host port to map to the container port. Container is set to use 9443 so you can either use that same port with the commands above or change the commands as follows: `-p <desired port>:9443` (where desired port is the port number you want)

To install this Docker image on a Synology NAS
1. Open Docker app in Synology Web GUI
2. Select the Registry tab in the left menu
3. Search for "xtreme22886"
4. Select and download the "xtreme22886/unifi-presence-rest" image (choose the "latest" tag)
5. Select the Image tab in the left menu and wait for the image to fully download
6. Select the downloaded image and click on the Launch button
7. Give the Container a sensible name (e.g. "unifi-presence")
8. Click on Advanced Settings
9. Check the "auto-restart" checkbox in the Advanced Settings tab
10.  Check the "Use the same network as Docker Host" checkbox in the Network tab
11. Click on Apply => Next => Apply

The REST API server will listen on port `9443` by default. If you encounter any port conflicts run the container with the port option: `-p XXXX:9443`
