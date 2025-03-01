# CPSC 441 Assignment 2 - Meme-Generating Proxy Server 🐼
A proxy server that intercepts HTTP traffic and replaces 50% of webpage images with random memes. Includes a surprise Easter egg for specific URLs!
## Setup
1. Install Python 3.x.
2. Install dependencies:

## Features
- 🔄 Intercepts and modifies HTTP responses
- 🖼️ Replaces 50% of images with memes from a local folder
- 🎉 Easter egg response for `http://google.ca`
- 🚫 Handles HTTPS requests gracefully
- 🧵 Multi-threaded client handling


## Start the proxy server:
```
python proxy_server.py
```

## Configure Broswer:
Firefox:

Go to about:preferences#general

Scroll to Network Settings > Settings

Select "Manual proxy configuration"

HTTP Proxy: 127.0.0.1 Port: 8080

## Test with these URLs:

http://httpbin.org/html - Basic HTML test page

http://google.ca - Easter egg trigger (type exactly)
