import spacy
import re

from dateparser import parse
from parsedatetime import Calendar
from datetime import datetime, timedelta
import itertools

class Model():
    def __init__(self):
        # Load spaCy's English NLP model
        self.nlp = spacy.load("en_core_web_trf") # en_core_web_lg # en_core_web_trf

    def process_input(self, user_input):
        # Parse the user input with spaCy
        doc = self.nlp(user_input)

        # Extract entities and their corresponding labels
        entities = {}
        for ent in doc.ents:
            if not ent.label_ in entities:
                entities[ent.label_] = []

            entities[ent.label_].append(ent.text)

        # Patch to make 'daily reminder' as date entity
        if not 'DATE' in entities:
          if 'daily' in user_input.lower():
            entities['DATE'] = ['daily']
          elif 'every day' in user_input.lower():
            entities['DATE'] = ['everyday']
          elif 'every night' in user_input.lower():
            entities['DATE'] = ['everynight']

        # Extract the task (not a named entity) and remove leading/trailing whitespace
        task_start_keywords = ['reminder', 'remind', 'schedule', 'set', 'to', 'for']
        task_start_regex = "|".join(r'\b{}\b'.format(keyword) for keyword in task_start_keywords)
        task_start_matches = [match.end() for match in re.finditer(task_start_regex, user_input)]

        task_end_keywords = ['at', 'in', 'every']
        task_end_regex = "|".join(r'\b{}\b'.format(keyword) for keyword in task_end_keywords)
        task_end_regex += "|\.|\,"
        task_end_matches = [match.start() for match in re.finditer(task_end_regex, user_input)]
        if len(task_end_matches) == 0:
          task_end_matches.append(len(user_input)-1)

        task_intervals = [(start, end) for start in task_start_matches for end in task_end_matches if start < end]

        # Sort intervals by length and choose the shortest interval (if available) which is not zero
        task_intervals.sort(key=lambda x: x[1] - x[0])

        task = None
        for interval in task_intervals:
            if interval[1] - interval[0] > 2:
                task = user_input[interval[0]:interval[1]].strip()

                # Remove parts of the task that are recognized as other entities
                for ent_type, ent_values in entities.items():
                    for value in ent_values:
                        task = task.replace(value, "").strip()

                # Remove any full stops, commas, articles from the task string
                remove_patterns = [r'^\.', r'\.$', r'^,', r',$', r'^the\b', r'\bthe\b', r'^a\b', r'\ba\b', r'^an\b', r'\ban\b', r'\bat$', r'\bon$', r'\bby$']
                for pattern in remove_patterns:
                    task = re.sub(pattern, '', task).strip()

                # Remove all the start and end keywords from the task
                keywords = task_start_keywords + task_end_keywords
                keywords_regex = "|".join(r'\b{}\b'.format(keyword) for keyword in task_start_keywords)
                task = re.sub(keywords_regex, '', task)

                if len(task) > 3:
                  break

        # Store the task as its own entity
        if task and len(task)>3:
            # removing extra spaces
            task = re.sub(r'\s+', ' ', task)
            entities['TASK'] = [task]

         # Repeating of reminder requested or not
        pattern = r"\b(every|each|daily)\b"
        if bool(re.search(pattern, user_input, re.IGNORECASE)):
            entities['TRIG'] = True

        return entities

        
    def standardize_output(self, ner_output):
        cal = Calendar()
        time_mentioned = 'TIME' in ner_output
        date_mentioned = 'DATE' in ner_output
        trig_mentioned = 'TRIG' in ner_output

        date_time_combinations = []
        if time_mentioned and date_mentioned:
            # Generate all combinations of dates and times
            for date_str, time_str in itertools.product(ner_output['DATE'], ner_output['TIME']):
                dt_str = f"{date_str} {time_str}"
                print('dt string: ', dt_str)
                dt_struct, parse_status = cal.parse(dt_str)
                print('date decided: ', dt_struct)
                if parse_status != 0:  # if the time string was successfully parsed
                    dt = datetime(*dt_struct[:6])
                    
                    # patch to fix the issue of wrong future casting 
                    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    if any(day in dt_str.lower() for day in weekdays):
                        today = datetime.now()
                        if ((dt - today).days >= 7) and ((dt - today).seconds > 1):
                            dt += -timedelta(days=7)
                    #################################################

                    if dt < datetime.now():
                        if ('every' in dt_str.lower()) or ('daily' in dt_str.lower()):
                            dt += timedelta(days=1)
                        else:
                            raise Exception('unexpected error of datetime in past!')
                    date_time_combinations.append(dt)

        elif time_mentioned:
            # If only time is mentioned, parse it as relative to today's date
            for time_str in ner_output['TIME']:
                dt_struct, parse_status = cal.parse(time_str)
                if parse_status != 0:  # if the time string was successfully parsed
                    dt = datetime(*dt_struct[:6])
                    if dt.time() < datetime.now().time():
                        dt = dt.replace(day=dt.day+1)
                    date_time_combinations.append(dt)

        elif date_mentioned:
            # If only date is mentioned, parse it as relative to current time
            for date_str in ner_output['DATE']:
                dt_struct, parse_status = cal.parse(date_str)
                if parse_status != 0:  # if the date string was successfully parsed
                    dt = datetime(*dt_struct[:6])
                    date_time_combinations.append(dt)

        else:
            # If neither date nor time is mentioned, return the current time
            date_time_combinations.append(datetime.now())

        # raise exception if empty
        if not len(date_time_combinations):
            raise Exception('could not understand date and time!')

        return date_time_combinations, time_mentioned, date_mentioned, trig_mentioned


    def __call__(self, user_input):
        entities = self.process_input(user_input)
        try:
            date_time_combinations, time_mentioned, date_mentioned, trig_mentioned = self.standardize_output(ner_output=entities)
        except Exception as e:
            if e.args[0] == 'unexpected error of datetime in past!':
                return {'error': 'Time seemes to be of past, please check again.'}

            if e.args[0] == 'could not understand date and time!':
                return {'error': 'Problem in understand date and time, please make it simpler.'}
                
            return {'error': 'There seems to be some error, Please try simple reminders.'}

        return {
        'datetimes'     : date_time_combinations,
        'time_mentioned': time_mentioned, 
        'date_mentioned': date_mentioned, 
        'trig_mentioned': trig_mentioned, 
        'entities'      : entities
        }
