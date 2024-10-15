import requests
import base64
import json

# Server URL
url = 'http://192.168.2.100:7860/sdapi/v1/txt2img'

payload = {
  "prompt": "ultra realistic close up portrait ((beautiful pale cyberpunk female with heavy black eyeliner))",
  "negative_prompt": "",
  "sampler_index": "Euler a",
  "width": 512,
  "height": 512,
  "batch_size": 1,
  "steps": 20,
  "seed": -1,
}

# Send said payload to said URL through the API.
response = requests.post(url=url, json=payload)
print("Status Code:", response.status_code)
print("Response Text:", response.text)
if response.status_code == 200:
    try:
        r = response.json()
        with open("output.png", 'wb') as f:
            f.write(base64.b64decode(r['images'][0]))
    except KeyError:
        print("Error: 'images' key not found in response.")
        print("Response:", response.text)
else:
    print("Failed to get a valid response from the server.")
    print("Status Code:", response.status_code)
    print("Response:", response.text)
