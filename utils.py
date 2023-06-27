import re

def parse_repeating_order(repeating_order):
    repeating_order = " ".join(repeating_order)
    cron_expression = {}

    # Detect patern `every <day of week>: every sunday | every monday`
    day_of_week_match = re.search(r'every\s+(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)', repeating_order, re.IGNORECASE)
    if day_of_week_match:
        day_of_week_value = day_of_week_match.group(1)
        day_of_week_index = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].index(day_of_week_value.capitalize())
        cron_expression['day_of_week'] = str(day_of_week_index) 

    # Detect numerical values for days of the month
    day_of_month_match = re.search(r'the (\w+|\d+)(st|nd|rd|th) of each month', repeating_order, re.IGNORECASE)
    if day_of_month_match:
        day_of_month_value = day_of_month_match.group(1)
        if day_of_month_value.isnumeric():
            cron_expression['day'] = day_of_month_value

    # Handle "every day" and "daily" keywords
    if 'every day' in repeating_order or 'every day' in repeating_order  or 'daily' in repeating_order or 'everynight' in repeating_order:
        cron_expression['day'] = '*'

    # Detect days mentioned in a list
    valid_days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    day_of_week_values = [
        str(valid_days.index(day)) 
        for day in valid_days if day.lower() in repeating_order.lower()
    ]
    if day_of_week_values:
        cron_expression['day_of_week'] = ','.join(day_of_week_values)

    return cron_expression
