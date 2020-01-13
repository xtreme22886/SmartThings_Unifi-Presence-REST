# SmartThings <-> Unifi Presence Sensor (BRIDGE)
Integration for SmartThings to use wireless Unifi clients as presence sensors

**Warning**: no authentication is performed. Don't expose this service to outside network.

For amd32/64

Run this image:
`docker run -d --restart always --name unifi-presence --net=host xtreme22886/unifi-presence-rest`

For arm32 (Raspberry Pi)

Run this image:
`docker run -d --restart always --name unifi-presence --net=host xtreme22886/unifi-presence-rest-arm`

1. Open Docker app in Synology Web GUI
2. Select the Registry tab in the left menu
3. Search for "xtreme22886"
4. Select and download the "xtreme22886/unifi-presence-rest" image (choose the "latest" tag for the stable version or see the Docker Versions section above for other versions/tags)
5. Select the Image tab in the left menu and wait for the image to fully download
6. Select the downloaded image and click on the Launch button
7. Give the Container a sensible name (e.g. "unifi-presence")
8. Click on Advanced Settings
9. Check the "auto-restart" checkbox in the Advanced Settings tab
10.  Check the "Use the same network as Docker Host" checkbox in the Network tab
11. Click on Apply => Next => Apply

The REST API server will listen on port `9443` by default. If you encounter any port conflicts run the container with the port option: `-p XXXX:9443`
