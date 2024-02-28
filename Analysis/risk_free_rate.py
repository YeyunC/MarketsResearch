import pandas as pd
import datetime as dt
import numpy as np

def read_risk_free_return():
    data = pd.read_csv('read_free_rate.csv')
    data['TIMESTAMP'] = [dt.datetime.strptime(x, "%d-%b-%Y") for x in data['Date']]
    data = data.sort_values('TIMESTAMP').set_index('TIMESTAMP')
    data['yield'] = 0.5 * (data['Ask Yield'] + data['Bid Yield'])
    data['annual_return_1'] = 1 + data['yield'] * 0.01
    data['daily_return_1'] = np.power(data['annual_return_1'], 1/365)
    data['daily_return'] = data['daily_return_1'] - 1
    data = data.resample('1D').last()
    data['daily_return'] = data['daily_return'].ffill()
    return data[['daily_return']].rename({'daily_return': 'daily_risk_free_return'}, axis=1)

if __name__ == '__main__':
    data = read_risk_free_return()