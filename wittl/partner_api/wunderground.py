import time
import datetime
import requests
import keys


class WundergroundAPI():
    def __init__(self):
        self.base_url = 'http://api.wunderground.com/api'
        self.key = keys.WUNDERGROUND_KEY

    def get_weather(self, lat, lon, date):
        ten_day_period = datetime.datetime.today() + datetime.timedelta(days=10)
        date_formatted = time.strftime("%Y%m%d")
        if date > ten_day_period:
            #Use historical data
            request_url = '{}/{}/history_{}/q/{},{}.json'.format(self.base_url,
                                                                 self.key,
                                                                 date_formatted,
                                                                 lat, lon)
            data = requests.get(request_url).json()
            temp_data = data['history']['dailysummary'][0]
            temp_high = int(temp_data['maxtempm'])
            temp_low = int(temp_data['mintempm'])
        else:
            #Use 10 day forecast
            request_url = '{}/{}/forecast10day/q/{},{}.json'.format(self.base_url,
                                                                    self.key,
                                                                    lat, lon)
            data = requests.get(request_url).json()
            temp_data = data['forecast']['simpleforecast']['forecastday'][0]
            temp_high = int(temp_data['high']['celsius'])
            temp_low = int(temp_data['low']['celsius'])

        return (temp_high + temp_low) / 2
