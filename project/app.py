from flask import Flask, render_template, request, redirect, url_for,session
import random
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, db
from twilio.rest import Client

import paho.mqtt.client as mqtt
import json



app = Flask(__name__)
app.secret_key = "smart_weather_secret"




















temperature = 0
humidity = 0
air_quality = 0
pressure = 0
soil_moisture = 0
rain = "No Data"
irrigation = "🔴 Water Pump OFF"
alert = " "
last_sms_alert=" "
last_sms_time = None




















account_sid = "AC6607e8fee74e8fd6ba181ecf8cf76607"

auth_token = "47a6d065781378bd599c38e91e2e5427"

twilio_number="+19452803184"

client = Client(account_sid,auth_token)


cred = credentials.Certificate(
    
"smart-weather-monitoring-35915-firebase-adminsdk-fbsvc-8c7a9c5671.json"
)

firebase_admin.initialize_app(cred, {
    'databaseURL': 
'https://smart-weather-monitoring-35915-default-rtdb.asia-southeast1.firebasedatabase.app/'
})














def on_connect(client, userdata, flags, rc):
    print("Connected to HiveMQ")
    client.subscribe("weatherstation/temperature")
    client.subscribe("weatherstation/humidity")
    client.subscribe("weatherstation/pressure")
    client.subscribe("weatherstation/smoke")
    client.subscribe("weatherstation/rain")
    client.subscribe("weatherstation/soil")
    client.subscribe("weatherstation/pump")



def on_message(client, userdata, msg):

    global temperature
    global humidity
    global air_quality
    global pressure
    global soil_moisture
    global rain
    global irrigation
    global alert
    global last_sms_alert
    global last_sms_time


    topic = msg.topic
    value = msg.payload.decode()

    print(topic, value)

    if topic == "weatherstation/temperature":
        temperature = float(value)

    elif topic == "weatherstation/humidity":
        humidity = float(value)

    elif topic == "weatherstation/pressure":
        pressure = float(value)

    elif topic == "weatherstation/smoke":
        air_quality = int(value)

    elif topic == "weatherstation/soil":
        soil_moisture = int(value)


    elif topic == "weatherstation/pump":
        if value == "ON":
            irrigation = " 🟢 Water Pump ON "

        else:
            irrigation = " 🔴 Water Pump OFF "


    elif topic == "weatherstation/rain":

        print("RAIN VALUE =", value)

        if int(value) < 2700:
            rain = "Rain Detected"
        else:
            rain = "No Rain"

        print("RAIN STATUS =", rain)


    
    #alert logics start here


    if rain == "Rain Detected":

        alert = "⚠ Rain Detected - 🔴 Water Pump is OFF"

    elif air_quality > 50:
        alert = "⚠ Smoke Detected - Poor Air Quality (HIGH POLLUTION)"


    elif temperature > 35 and soil_moisture > 2500:

        alert = "⚠ High Temperature - Irrigation Needed"

    elif humidity > 80:

        alert = "⚠ High Humidity Alert"

    elif soil_moisture > 2500:
        alert = "⚠ Soil Is TOO DRY - 🟢 Water Pump is ON"

    
    else:

        alert = " "


    
    db.reference('/last_alert').set(alert)



    print("ALERT =", alert)




    if alert != "" and alert != " ":

        current_time = datetime.now()

        if alert != last_sms_alert or \
            last_sms_time is None or \
            current_time - last_sms_time > timedelta(minutes=5):




            print("NEW ALERT DETECTED")

            users = db.reference('/users').get()

            for username, farmer in users.items():

                crop_type = farmer.get('crop_type', 'Not Set')



                sms_message = f"""
        🌾 Smart Weather Monitoring Alert

        {alert}

        🌱 CROP TYPE : {crop_type}

        
        🌡 Temperature: {temperature}°C
        💧 Humidity: {humidity}%
        🪴 Soil Moisture: {soil_moisture}
        🌫 Air quality: {air_quality}
        🚰 Irrigation: {irrigation}

        Please check your farm.
        """

                send_sms(
                    "8123774021",
                    sms_message
                )

        

            last_sms_alert = alert
            last_sms_time = current_time





    db.reference('/weather').set({
        'temperature': temperature,
        'humidity': humidity,
        'air_quality': air_quality,
        'pressure': pressure,
        'soil_moisture': soil_moisture,
        'rain': rain,
        'irrigation': irrigation,
        'alert': alert
    })

    print("Firebase Updated")






























def send_sms(phone, message):

    try:

        client = Client(account_sid,auth_token)

        sms = client.messages.create(

            body=message,

            from_=twilio_number,   # Twilio phone number

           to="+91" + phone

        )

        print("SMS Sent Successfully")
        print("SID: ", sms.sid)



        history_ref = db.reference('/sms_history')

        history_ref.push({
            'phone': phone,
            'message': message,
            'status': 'Sent',
            'time': datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        })





    except Exception as e:

        print("SMS Error:", e)




        history_ref = db.reference('/sms_history')

        history_ref.push({
            'phone': phone,
            'message': message,
            'status': 'Failed',
            'error': str(e),
            'time': datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        })






@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        phone = request.form['phone']
        email = request.form['email']
        location = request.form['location']
        district = request.form['district']
        state = request.form['state']
        password = request.form['password']

    

        ref = db.reference('/users')

        ref.child(username).set({
            'phone': phone,
            'email': email,
            'location':location,
            'district': district,
            'state': state,
            'password': password
            
        })

        return redirect('/login')

    return render_template('register.html')




@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        phone = request.form['phone']
        password = request.form['password']

        ref = db.reference('/users/' + username)

        user = ref.get()

        if user:

            if user['phone'] == phone and user['password'] == password:
                
                session['username'] = username

                return redirect('/dashboard')

        return "Invalid Username, Phone Number or Password"

    return render_template('login.html')





@app.route('/dashboard')
def home():

    print("HOME FUNCTION IS RUNNING")

    username = session.get('username')

    user_ref = db.reference('/users/' + username)

    farmer = user_ref.get()

    crop_type = farmer['crop_type']


    #temperature = random.randint(20, 40)

    #humidity = random.randint(40, 90)

    #air_quality = random.randint(100, 400)

    #pressure = random.randint(990, 1030)

    #soil_moisture = random.randint(20, 100)

    #rain = random.choice([
    #    "Rain Detected",
    #    "No Rain"
    #])

    if temperature > 35 and rain == "No Rain":

        irrigation = "🟢 Water Pump ON"

    else:

        irrigation = "🔴 Water Pump OFF"










    crop_message = ""

    if temperature > 35 and rain == "No Rain":

        if crop_type == "Paddy":
            crop_message = f"\n⚠ High Temperature Alert!\n🌾 Paddy Crop\nTemperature = {temperature}°C\nPlease irrigate your field."

        elif crop_type == "Maize":
            crop_message = f"\n⚠ High Temperature Alert!\n🌽 Maize Crop\nTemperature = {temperature}°C\nEnsure adequate water supply."

        elif crop_type == "Groundnut":
            crop_message = f"\n⚠ High Temperature Alert!\n🥜 Groundnut Crop\nTemperature = {temperature}°C\nMulching is recommended to conserve moisture."

        elif crop_type == "Cotton":
            crop_message = f"\n⚠ High Temperature Alert!\n🌿 Cotton Crop\nTemperature = {temperature}°C\nMaintain proper soil moisture."

        elif crop_type == "Sugarcane":
            crop_message = f"\n⚠ High Temperature Alert!\n🎋 Sugarcane Crop\nTemperature = {temperature}°C\nIncrease irrigation frequency."


















    alert = ""

    

    if temperature > 35:

        alert = "⚠ High Temperature Alert"

    elif humidity > 80:

        alert = "⚠ High Humidity Alert"

    elif rain == "Rain Detected":

        alert = "⚠ Rain Detected"


    alert_ref = db.reference('/last_alert')
    previous_alert = alert_ref.get()

    print("Current Alert:", alert)
    print("Previous Alert:", previous_alert)





    if alert != "" and alert != previous_alert:

        #if alert == "⚠ High Temperature Alert":

        #    send_sms(

        #        farmer['phone'],

        #        crop_message

        #    )

        #elif alert == "⚠ High Humidity Alert":

        #    send_sms(

        #        farmer['phone'],

        #        f"\n⚠ High Humidity Alert!\nHumidity = {humidity}%.."

        #    )

        #elif alert == "⚠ Rain Detected":

        #    send_sms(

        #        farmer['phone'],

        #        "\n🌧 Rain Detected!\nNo irrigation required..\nWater Pump Is Turned OFF 🔴"

        #    )

        alert_ref.set(alert)




    ref = db.reference('/weather')

    
    print("Irrigation =", irrigation)
    



    ref.set({
        'temperature': temperature,
        'humidity': humidity,
        'air_quality': air_quality,
        'pressure':pressure,
        'soil_moisture':soil_moisture,
        'rain': rain,
        'irrigation': irrigation,
        'alert': alert
    })   


    
    username = session.get('username')

    user_ref = db.reference('/users/' + username)

    farmer = user_ref.get()



    last_alert = alert_ref.get()


    return render_template(

        'index.html',

        temperature=temperature,

        humidity=humidity,

        air_quality=air_quality,

        pressure=pressure,

        soil_moisture=soil_moisture,

        rain=rain,

        irrigation=irrigation,

        alert=alert,

        farmer=farmer,

        last_alert=last_alert,

        crop_message=crop_message

    )






@app.route('/logout')
def logout():

    session.pop('username', None)

    return redirect('/login')




@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():

    username = session.get('username')

    user_ref = db.reference('/users/' + username)

    if request.method == 'POST':

        user_ref.update({

            'location': request.form['location'],

            'district': request.form['district'],

            'state': request.form['state'],

            'email': request.form['email'],

            'crop_type': request.form['crop_type'],

            'farm_area': request.form['farm_area'],


            'phone': request.form['phone']

        })

        return redirect('/dashboard')

    farmer = user_ref.get()

    return render_template(
        'edit_profile.html',
        farmer=farmer
    )















@app.route('/sms-history')
def sms_history():

    sms_ref = db.reference('/sms_history')

    sms_data = sms_ref.get()

    return render_template(
        'sms_history.html',
        sms_data=sms_data
    )






















#@app.route('/test-sms')
#def test_sms():

#    send_sms(

#        "8123774021",

#        "🌾 Smart Weather Monitoring System SMS Test Successful!"

#    )

#    return "SMS Sent Successfully!"




















mqtt_client = mqtt.Client()

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect("broker.hivemq.com", 1883, 60)

mqtt_client.loop_start()
























if __name__ == '__main__':

    app.run(debug=True)