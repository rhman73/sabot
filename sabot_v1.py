#!/usr/bin/env python
#  -*- coding: utf-8 -*-

from flask import Flask, request
import requests
from webexteamssdk import WebexTeamsAPI, Webhook
import json
from datetime import datetime
from datetime import timedelta

# Initialize the environment
# Create the web application instance
flask_app = Flask(__name__)
# Create the Webex Teams API connection object
api = WebexTeamsAPI()


# Core bot functionality
# Your Webex Teams webhook should point to http://<serverip>:5000/events
@flask_app.route('/events', methods=['GET', 'POST'])
def webex_teams_webhook_events():
    """Processes incoming requests to the '/events' URI."""
    if request.method == 'GET':
        return ("""<!DOCTYPE html>
                   <html lang="en">
                       <head>
                           <meta charset="UTF-8">
                           <title>Webex Teams Bot served via Flask</title>
                       </head>
                   <body>
                   <p>
                   <strong>Your Flask web server is up and running!</strong>
                   </p>
                   </body>
                   </html>
                """)
    elif request.method == 'POST':
        """Respond to inbound webhook JSON HTTP POST from Webex Teams."""
        # Get the POST data sent from Webex Teams
        json_data = request.json
        print("\n")
        print("WEBHOOK POST RECEIVED:")
        print(json_data)
        print("\n")
        # Create a Webhook object from the JSON data
        webhook_obj = Webhook(json_data)
        # Get the room details
        room = api.rooms.get(webhook_obj.data.roomId)
        # Get the message details
        message = api.messages.get(webhook_obj.data.id)
        # Get the sender's details
        person = api.people.get(message.personId)
        print("NEW MESSAGE IN ROOM '{}'".format(room.title))
        print("FROM '{}'".format(person.displayName))
        print("MESSAGE '{}'\n".format(message.text))
        if person.firstName: #if they have a First Name populated on Webex Teams use that. Otherwise use their full name.
            first_name = person.firstName
        else:    
            first_name = person.displayName

        #define list of questions
        questions = ['Is this a VRD project? (Yes/No)',
            'Is this a new project? (Yes/No)',
            'Are there any integrations or non-standard elements which require billable PS? (Yes/No)',
            'Are there any on-site services? (Yes/No)',
            'Are you adding sites? (Yes/No)',
            'Are you adding any new integrations or non-standard elements which require billable PS? (Yes/No)',
            'Are there any on-site services? (Yes/No)']
        
        # Bot Loop Control
        me = api.people.me()
        if message.personId == me.id:
            # Message was sent by me (bot); do not respond.
            return 'OK'

        else:
            # Helper functions
            list_update = 0
            #import file and create dictionary
            history = {}
            with open("history_list.txt") as f:
	            history = json.load(f)
            #get current time and time of last conversation
            current_time = datetime.now()
            print(current_time)

            #check if this user is in history list
            if message.personId in history:
                user_ID = history[message.personId]
                user_history = history[message.personId]['answers']
                tracking = history[message.personId]['tracking']
                last_conv_str = history[message.personId]['last_conv']
                last_conv = datetime.strptime(last_conv_str, '%Y-%m-%d %H:%M:%S.%f')
                last_conv_print = last_conv.strftime('%m/%d/%Y')
                time_out = last_conv + timedelta(minutes=10)
                user_input = str.lower(message.text)
                user_input = remove_prefix(user_input, 'beta ')
                complete = tracking[2]
                show_results = 0
                show_list = 0
                print("Existing user: ", user_ID)
                if user_input == 'help':
                    #api.messages.create(room.id, markdown="Here are some commands you can give me:  \n**Help**: to show all valid commands  \n**Restart**: restart the questions from the beginning  \n**Results**: see the previous list of documents based on the last time you completed all questions  \n**List**: list all of the current design documents")
                    api.messages.create(room.id, markdown="Here are some commands you can give me:  \n**Help**: to show all valid commands  \n**Restart**: restart the questions from the beginning  \n**Results**: see the previous list of documents based on the last time you completed all questions")
                elif user_input == 'list':
                    show_results = 1
                    show_list = 1
                elif current_time > time_out or user_input == 'restart':
                    tracking = [0,0,0]
                    user_history = [0,0,0,0,0,0,0]
                    api.messages.create(room.id, text="Hi " + first_name + "! It's nice to hear from you again. We last spoke on " + last_conv_print + ". Let's get started.")
                    next_question = tracking[0]
                    next_question_txt = questions[next_question]
                    api.messages.create(room.id, text=next_question_txt)
                elif complete == 1:
                    if user_input == 'results':
                        api.messages.create(room.id, text='Here are the results from last time')
                        show_results = 1
                    else:
                        api.messages.create(room.id, text='Welcome back ' + first_name + '! The last time we talked I gave you links to the UCCaaS documents you needed. \
Do you want to see that again? Then reply with "Results". Or reply with "Restart" to begin again.')
                else:
                    current_answer = tracking[1]
                    if user_input == 'yes' or user_input == 'y':
                        user_history[current_answer] = 1
                        if tracking[1] == 3 or tracking[1] == 6:
                            complete = 1
                            show_results = 1
                            tracking[2] = 1
                        else:
                            tracking[1] += 1
                    elif user_input == 'no' or user_input == 'n':
                        if tracking[1] == 3 or tracking[1] == 6:
                            complete = 1
                            show_results = 1
                            tracking[2] = 1
                        else:
                            tracking[1] += 1
                    else:
                        api.messages.create(room.id, text="I'm sorry I didn't understand that response. Please reply with Yes or No. You can also reply with HELP. Here is the last question I asked you...")
                        next_question = tracking[0]
                        next_question_txt = questions[next_question]
                        api.messages.create(room.id, text=next_question_txt)
                        return 'Ok'
                    if tracking[1] == 2 and user_history[1] == 0:
                         tracking[0] = 3
                         tracking[1] = 4                
                    next_question = tracking[0] + 1
                    if complete != 1:
                        next_question_txt = questions[next_question]
                        api.messages.create(room.id, text=next_question_txt)
                        tracking[0] += 1 
                if show_results == 1:
                    api.messages.create(room.id, text="Based on your answers, you need the following design documents: (Opening your browser and logging into CrowdAround will enable you to download the documents directly)")
                    if user_history[1] == 1 or show_list == 1:
                        api.messages.create(room.id, markdown="Latest HLD version 2.01: [Link](https://crowdaround.verizon.com/servlet/JiveServlet/downloadBody/4338989-102-2-647636/HLD%20Customer%20O-xxxxxxx%20v1%20mmddyy.dotm)")
                    if user_history[0] == 0 or show_list == 1:
                        api.messages.create(room.id, markdown="Legacy SDW version 17:03: [Link](https://crowdaround.verizon.com/servlet/JiveServlet/downloadBody/4286180-102-4-589448/UC-SDW%2017-03a%20final%20CUSTOMERNAME%20O-XXXXXXX-v1-mmdd17.xlsm)")
                    elif user_history[0] == 1 or show_list == 1:
                        api.messages.create(room.id, markdown="Latest SDW version 19.03: [Link](https://crowdaround.verizon.com/servlet/JiveServlet/downloadBody/4353240-102-1-652158/SDW%2019-03%20CUSTOMERNAME%20O-XXXXXXX-v1-mmdd19.xlsm)")
                    if user_history[1] == 1 or show_list == 1:
                        api.messages.create(room.id, markdown="Latest SoR version 19.04: [Link](https://crowdaround.verizon.com/servlet/JiveServlet/downloadBody/4335312-102-6-653816/SOR%20Verizon%20UCCaaS%20PS%20MRC%20SOR%20v19_04.dotm)")
                        if user_history[2] == 1 or show_list == 1:
                            if user_history[0] == 1 or show_list == 1:
                                api.messages.create(room.id, markdown="Latest SoW (Dated 4-10-19): [Link](https://crowdaround.verizon.com/servlet/JiveServlet/downloadBody/4279389-102-5-653818/SOW%20Customer%20Project%20O-xxxxxxx%20v1%20mmdd19.dotm)")
                            elif user_history[0] == 0 or show_list == 1:
                                api.messages.create(room.id, markdown="Legacy SoW: [Link](https://crowdaround.verizon.com/servlet/JiveServlet/downloadBody/4279390-102-2-422140/Legacy%20UCCaaS%20Only%20NRC%20Addendum%20SOW%20Template%20011316.doc)")
                        if user_history[3] == 1 or show_list == 1:
                            api.messages.create(room.id, markdown="Latest Site Services SoW: [Link](https://perc.vzbi.com)")
                    elif user_history[1] == 0:
                        api.messages.create(room.id, markdown="Latest SoR version 19.04: [Link](https://crowdaround.verizon.com/servlet/JiveServlet/downloadBody/4335312-102-6-653816/SOR%20Verizon%20UCCaaS%20PS%20MRC%20SOR%20v19_04.dotm)")
                        if user_history[5] == 1 and user_history[0] == 0:
                            api.messages.create(room.id, markdown="Legacy SoW: [Link](https://crowdaround.verizon.com/servlet/JiveServlet/downloadBody/4279390-102-2-422140/Legacy%20UCCaaS%20Only%20NRC%20Addendum%20SOW%20Template%20011316.doc)")
                        elif user_history[5] == 1 and user_history[0] == 1:
                            api.messages.create(room.id, markdown="Latest SoW (Dated 4-10-19): [Link](https://crowdaround.verizon.com/servlet/JiveServlet/downloadBody/4279389-102-5-653818/SOW%20Customer%20Project%20O-xxxxxxx%20v1%20mmdd19.dotm)")
                        if user_history[6] == 1:
                            api.messages.create(room.id, markdown="Latest Site Services SoW: [Link](https://perc.vzbi.com)")

                list_update = 1
                
            else:
                print("This is a new user")
                api.messages.create(room.id, text="Hi " + first_name + "! I am the UCCaaS SA Bot. I can help you figure out which UCCaaS design documents for your project. Please answer the following questions:")
                history[message.personId] = { "last_conv": current_time,
                     "tracking": [0,0,0],
                     "answers": [0,0,0,0,0,0,0,0,0]}
                user_history = [0,0,0,0,0,0,0,0,0]
                tracking = [0,0,0]
                next_question = tracking[0]
                next_question_txt = questions[next_question]
                api.messages.create(room.id, text=next_question_txt)
                list_update = 1
               
            #write updated entries to file
            if list_update == 1:
                history[message.personId]['answers'] = user_history
                history[message.personId]['last_conv'] = current_time
                history[message.personId]['tracking'] = tracking        
                def myconverter(o):
                    if isinstance(o, datetime):
                        return o.__str__()
                with open("history_list.txt", "w") as f:
                    json.dump(history, f, default = myconverter)

    return 'Ok'

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever

if __name__ == '__main__':
    # Start the Flask web server
    flask_app.run(host='127.0.0.1', port=5000)
