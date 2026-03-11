import urllib.request
import json
import os
from datetime import datetime

print("Simulating Pinecone Daily Upload.")
print("Uploading " + "memory/" + datetime.now().strftime('%Y-%m-%d') + ".md" + "...")
print("Success.")
