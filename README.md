# SmartThings <-> Unifi Presence Sensor (BRIDGE)

**Integration for SmartThings to use Unifi wireless clients as presence sensors**

**Warning**: No authentication is performed. Don't expose this service to outside networks

This is a REST API server built with FastAPI to facilitate the communication between SmartThings and an Unifi Controller. It has been built into a Docker image which can be installed following the below.

## Installing the Docker Image

```
For x32/x64
```

Run this image:
`docker run -d --restart always --name unifi-presence -p 9443:9443 xtreme22886/unifi-presence-rest`

```
For ARM (Raspberry Pi)
```

Run this image:
`docker run -d --restart always --name unifi-presence -p 9443:9443 xtreme22886/unifi-presence-rest-arm`

To change the port Docker container is using:

The `-p` cmd tells Docker which host port to map to the container port. Container is set to use 9443 so you can either use that same port with the commands above or change the commands as follows: `-p <desired port>:9443` (where desired port is the port number you want)

### Synology NAS
To install this Docker image on a Synology NAS
1. Open Docker app in Synology Web GUI
2. Select the **Registry** tab in the left menu
3. Search for **xtreme22886**
4. Select and download the **xtreme22886/unifi-presence-rest** image
5. Select the **Image** tab in the left menu and wait for the image to fully download
6. Select the downloaded image and click on the **Launch** button
7. Give the container a sensible name (ex: **unifi-presence**)
8. Click on **Advanced Settings**
9. Check the **auto-restart** checkbox in the **Advanced Settings** tab
10.  Choose a local port to use in the **Port Settings** tab (ex: **9443**)
11. Click on **Apply** => **Next** => **Apply**

## Testing

Once you have a Docker container running the above image, you can verify things are working correctly by browsing to the IP address of your Docker with the port of the container. Browsing to that website should respond back with a *Hello World* message.

## Built With

* [FastAPI](https://fastapi.tiangolo.com/) - Web framework for building APIs

### Donate
[PayPal.me](https://www.paypal.com/donate?hosted_button_id=HEZ9EPNJR2UYA&source=url)
