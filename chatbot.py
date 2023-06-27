import re
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from flask import Response
from sms_api import SMS
from NER_model import Model
from sql_db import SQLiteManager
from utils import parse_repeating_order

class ChatBot:
    def __init__(self, number):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.sms = SMS()
        self.model = Model()
        self.number = number
        self.db = SQLiteManager('user_data.db')

    def add_reminder(self, reminder_time, reminder_task, to_num, repeat=None):
        if repeat == None:
            job = self.scheduler.add_job(self.send_sms, 'date', run_date=reminder_time, args=[reminder_task, to_num])
        else:
            cron_expression = repeat

            cron_expression['hour'] = str(reminder_time.hour)
            cron_expression['minute'] = str(reminder_time.minute)
            cron_expression['second'] = str(reminder_time.second)

            job = self.scheduler.add_job(self.send_sms, 'cron', args=[reminder_task, to_num], **cron_expression, next_run_time=reminder_time)

        # add the job id and task in sql table with user number 
        pattern = r"(?<=this is your reminder for).*$"
        reminder_text = re.search(pattern, reminder_task, re.IGNORECASE)
        if reminder_text:
            task = reminder_text.group(0).strip()

        self.db.add_reminder(phone_number=to_num, job_id=job.id, task=task)

    def send_sms(self, reminder_task, to_num):
        self.sms.create_msg(body=reminder_task,
            to=to_num,
            from_=self.number
        )

    def show_reminders(self, phone_number):
        job_ids = self.db.get_reminder_jobs(phone_number)
        print(job_ids)
        # Get intersecting job IDs between reminders and BackgroundScheduler
        intersecting_job_ids = list(set(job_ids) & set([job.id for job in self.scheduler.get_jobs()]))
        intersecting_job_ids = sorted(intersecting_job_ids)

        tasks = []
        for job_id in intersecting_job_ids:
            task = self.db.get_task_by_job_id(phone_number, job_id)
            if task:
                tasks.extend(task)

        # Format tasks with numbering
        tasks_list = [f"{i + 1}. {task}" for i, task in enumerate(tasks)]

        return "\n".join(tasks_list), intersecting_job_ids

    def delete_reminders(self, indexes):
        if not len(indexes):
            return False 

        err = False
        try:
            job_ids = self.show_reminders(self.client_number)[1]
            for idx in indexes:
                job_id = job_ids[idx-1]
                
                self.scheduler.remove_job(job_id)
                # code to add done status of reminder in table
                self.db.set_reminder_done(job_id)
        except:
            err = True
        return err

    def format_timedelta(self, td):
        # Calculate the total number of seconds
        total_seconds = td.total_seconds()
        # Calculate the minutes and seconds
        minutes, seconds = divmod(total_seconds, 60)
        # Return the formatted string
        return f"{int(minutes)} minutes, {int(seconds)} seconds"

    def process_query(self, query):
        out = self.model(query)
        if 'error' in out:
            return out['error']

        print('out: ', 'entities')
        entities = out['entities']
        print(entities)

        # If no entities detected in text, reply with "its not a reminder query"
        if not len(entities):
            return "Please tell me something to remind you!"
        # if task detected save in database 
        else:
            task = entities['TASK'][0] if 'TASK' in entities else ""
            time = entities['TIME'][0] if 'TIME' in entities else "" 
            date = entities['DATE'][0] if 'DATE' in entities else ""
            self.db.update_model(self.msg_id, task, time, date)

        # No time is mentioned in query
        if not out['time_mentioned']:
            # setting order = 2; meaning we are waiting for the response of time 
            self.db.set_order(self.client_number, 2)
            return "Please also mention the time when you want me to remind you."

        else:
            # Check if last order = 2; then we check for last task 
            message_id, last_order = self.db.get_last_order(self.client_number)
            print('last order ', message_id, last_order)
            if last_order == 2:
                task, date = self.db.get_task_and_date(message_id)
                entities['TASK'] = [task] 
                if (date != None) or (date != ''):
                    entities['DATE'] = [date] 

                # process again to get new datetime object
                try:
                    date_time_combinations, time_mentioned, date_mentioned, trig_mentioned = self.model.standardize_output(entities)
                    out['datetimes'] = date_time_combinations
                    out['time_mentioned'] = time_mentioned
                    out['date_mentioned'] = date_mentioned
                    out['trig_mentioned'] = trig_mentioned
                except:
                    return {'error': 'Sorry please send a whole reminder as one message.'}


        # Fetching name of the user 
        username = self.db.get_username(self.client_number)

        if 'TASK' in entities:
            task = entities['TASK'][0]
            # reminder msg 
            reminder_task = f"Hey {username}, this is your reminder for {task}."
            timer = out['datetimes'][0]

            # reply msg 
            diff = self.format_timedelta(timer - datetime.now())
            reply_msg = f"Your reminder is set for {task} in {diff}."

            # adding reminder 
            if out['trig_mentioned']:
                if out['date_mentioned']:
                    cron_expression = parse_repeating_order(entities['DATE'])
                else:
                    cron_expression = {'day': '*'} # everyday 
                self.add_reminder(reminder_time=timer, reminder_task=reminder_task, to_num=self.client_number, repeat=cron_expression)
            else:
                self.add_reminder(reminder_time=timer, reminder_task=reminder_task, to_num=self.client_number)
            # reply sms 
            return reply_msg

        else:
            return f'Sorry {username}, could not process that reminder!'

    def Processingـincomingـmessages(self, json):
        print('json: ', type(json))
        print(json)

        query = " " + json['Body'] + " "
        phone_number = json['From']

        self.client_number = phone_number

        # Storing the user SMS
        self.msg_id = self.db.add_message(self.client_number, query, status='received')
        print('msg id', self.msg_id)

        # fetch user's name 
        user_name = self.db.get_username(self.client_number)
        print('username', user_name)
        if user_name == None:
        # check if we already sent the name request
            if not self.db.check_username_sent(self.client_number):
                # Ask for their name and store it
                reply = "Hello! What is your name?"
                self.db.add_message(self.client_number, reply, status='sent')
                return Response(reply, status=200, mimetype='text/plain')
            else:
                # Fetch last sms as Name
                name = self.db.get_last_received_message(self.client_number)
                self.db.add_user(self.client_number, name)
                reply = f"Hello {name}, You can set reminders now!"
                self.db.add_message(self.client_number, reply, status='sent')
                return Response(reply, status=200, mimetype='text/plain')

        # Checking special strings 
        if query[1]=="/":
            if "reminders" in query:
                reply, job_ids = self.show_reminders(phone_number=self.client_number)
                if len(job_ids):
                    reply += "\n to delete any reminder send /delete followed by number of reminders"
                else:
                    reply = "No reminders yet!"

            elif "delete" in query:
                integers = re.findall(r"\d+", query)
                integers = [int(x) for x in integers]
                print('int: ', integers)
                err = self.delete_reminders(integers)
                if not err:
                    reply = "Deleted task " + ", ".join([str(x) for x in integers])
                else:
                    reply = "Please give correct number of reminders"

            elif "name" in query:
                reply = f"username: {user_name}"
        else:
            # process input query
            reply = self.process_query(query)

        # send reply
        # sms_id = self.send_sms(reminder_task=reply, to_num=self.client_number)
        # print('sms ID', sms_id)

        return Response(reply, status=200, mimetype='text/plain')
