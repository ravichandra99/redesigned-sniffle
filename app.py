#!flask/bin/python

"""
Cisco Meraki CMX Receiver

A simple example demonstrating how to interact with the CMX API.

How it works:
- Meraki access points will listen for WiFi clients that are searching for a network to join and log the events.
- The "observations" are then collected temporarily in the cloud where additional information can be added to
the event, such as GPS, X Y coordinates and additional client details.
- Meraki will first send a GET request to this CMX receiver, which expects to receieve a "validator" key that matches
the Meraki network's validator.
- Meraki will then send a JSON message to this application's POST URL (i.e. http://yourserver/ method=[POST])
- The JSON is checked to ensure it matches the expected secret, version and observation device type.
- The resulting data is sent to the "save_data(data)" function where it can be sent to a databse or other service
    - This example will commit the database to a mongodb server

Default port: 5000

Cisco Meraki CMX Documentation
https://documentation.meraki.com/MR/Monitoring_and_Reporting/CMX_Analytics#CMX_Location_API

Written by Cory Guynn
2016

www.InternetOfLEGO.com
Developers.Meraki.com
"""

# Libraries
from pprint import pprint
from flask import Flask,jsonify,render_template
from flask import json
from flask import request
import sys, getopt
from pymongo import MongoClient
import pandas as pd

############## USER DEFINED SETTINGS ###############
# MERAKI SETTINGS
validator = "d3297bdf535d83a11e19bc458579768528a93164"
secret = "Ivis@ivis5"
version = "2.0" # This code was written to support the CMX JSON version specified


client = MongoClient("mongodb://localhost:27017")

    
# Save CMX Data
def save_data(data):
    print("---- SAVING CMX DATA ----")
    # CHANGE ME - send 'data' to a database or storage system
    pprint(data, indent=1)

    ## Adjust data before DB insert ##
    # Add GeoJSON structure for MongoDB Compass (or similar) mapping
    for i in data["data"]["observations"]:
        print("i",i)
        data["data"]["secret"] = "hidden"
        lat = i["location"]["lat"]
        lng = i["location"]["lng"]
        clientMac = i["clientMac"]
        data["data"]["geoJSON"] = {
          "type": "Feature",
          "geometry": {
            "type": "Point",
            "coordinates": [lat,lng]
          },
          "properties": {
            "name": clientMac
          }
        }

        #data["data"]["locationGeoJSON"] = json.dumps(locationGeoJSON)
        #data["data"].append({"geoJSON":{"type": "Feature","geometry": {"type": "Point","coordinates": [i["location"]["lat"], i[["location"]["lng"], i["location"]["unc"]]},"properties": {"name": i["clientMac"]}}})


    # Commit to database
    
    db = client.test
    result = db.cmxdata.insert_one(data)
    print("MongoDB insert result: ",result )

####################################################
app = Flask(__name__)


# Respond to Meraki with validator
@app.route('/', methods=['GET'])
def get_validator():
    print("validator sent to: ",request.environ['REMOTE_ADDR'])
    return validator

# Accept CMX JSON POST
@app.route('/', methods=['POST'])
def get_cmxJSON():
    if not request.json or not 'data' in request.json:
        return("invalid data",400)
    cmxdata = request.json
    print(cmxdata)
    #pprint(cmxdata, indent=1)
    print("Received POST from ",request.environ['REMOTE_ADDR'])

    # Verify secret
    if cmxdata['secret'] != secret:
        print("secret invalid:", cmxdata['secret'])
        # return("invalid secret",403)
    else:
        print("secret verified: ", cmxdata['secret'])

    # Verify version
    if cmxdata['version'] != version:
        print("invalid version")
        # return("invalid version",400)
    else:
        print("version verified: ", cmxdata['version'])

    # Determine device type
    if cmxdata['type'] == "DevicesSeen":
        print("WiFi Devices Seen")
    elif cmxdata['type'] == "BluetoothDevicesSeen":
        print("Bluetooth Devices Seen")
    else:
        print("Unknown Device 'type'")
        # return("invalid device type",403)

    # Do something with data (commit to database)
    save_data(cmxdata)

    # Return success message
    return "CMX POST Received"


@app.route("/data")
def home():
    db = client["test"]
    data = db["cmxdata"]
    data_list =[j for i in data.find({}) for j in i['data']['observations'] if j is not None]
    df = pd.DataFrame(data_list)
    return render_template('index.html',res = df.to_html(classes = 'display',table_id = 'tbAdresse',
        header = True)) #df.to_html()

# Launch application with supplied arguments

def main(argv):
    global validator
    global secret

    try:
       opts, args = getopt.getopt(argv,"hv:s:",["validator=","secret="])
    except getopt.GetoptError:
       print ('cmxreceiver.py -v <validator> -s <secret>')
       sys.exit(2)
    for opt, arg in opts:
       if opt == '-h':
           print ('cmxreceiver.py -v <validator> -s <secret>')
           sys.exit()
       elif opt in ("-v", "--validator"):
           validator = arg
       elif opt in ("-s", "--secret"):
           secret = arg

    print ('validator: '+ validator)
    print ('secret: '+ secret)


if __name__ == '__main__':
    main(sys.argv[1:])
    app.run(port=5000,debug=False)
