# FlaredOpenAIAPI
A small tool to translate between Cloudflare Workers AI API and an OpenAI API Compatible Client.
This has only been tested with NextCloud Assistant but it might work elsewhere.

## Installation for NextCloud
1. Download a release and extract it to a place on your machine.
2. Edit ```config.py``` and put in your Cloudflare Account ID
3. Run ```main.py```
4. Open NextCloud and install the ```OpenAI and LocalAI integration``` app.
5. Go to Nextcloud > Administration Settings > Artificial Intelligence
6. Put in the IP of the script with the port you configured e.g. ```http://192.168.88.94:5050```
7. Put in the API Key for your Cloudflare Workers AI user.
8. Try it out!
