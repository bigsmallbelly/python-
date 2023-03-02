#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  1 16:30:42 2023

@author: chenpengyi
"""

import pandas as pd

orders =pd.read_csv('data.csv',encoding = "ISO-8859-1")
orders.head(5)

# 確認資料缺漏
orders.isnull().sum()
orders=orders.dropna()
orders.shape 

# 確認日期格式
orders.info()
orders['InvoiceDate']=pd.to_datetime(orders['InvoiceDate'])

# 建立Monetary
orders["Amount"]  = orders['Quantity'] * orders['UnitPrice']
monetary = orders.groupby("CustomerID")['Amount'].sum()
monetary = monetary.reset_index()


# 建立Frequency
frequency = orders.groupby("CustomerID")['InvoiceNo'].count()
frequency = frequency.reset_index()

# 以顧客id合併消費金額與消費次數兩張表，命名為fm
fm = pd.merge(monetary, frequency, on = "CustomerID", how = "inner")

# 確認第一次消費與資料表中最大值日期的間隔
maximum = max(orders.InvoiceDate)
maximum2 = maximum + pd.DateOffset(days = 1)
orders['day_diff'] = maximum2 - orders['InvoiceDate']
recency = orders.groupby('CustomerID')['day_diff'].min()
recency = recency.reset_index()

# 以顧客id合併第一次消費與fm兩張表，命名為RFM
RFM = pd.merge(fm, recency, on = "CustomerID", how = 'inner')
# 剔除多餘欄位
RFM.columns = ['CustomerID','Amount','Frequency','Recency']


# 將表格裡的recency保留天數
RFM_norm2 = RFM.copy()
RFM_norm2.Recency = RFM_norm2.Recency.dt.days

# 三大象限各賦予四個標籤
quantiles = RFM_norm2.quantile(q=[0.25,0.5,0.75])

# 因為R的數值要越少越好，因此單獨進行計算
def R_Class(x,p,d):
    if x <= d[p][0.25]:
        return 4
    elif x <= d[p][0.50]:
        return 3
    elif x <= d[p][0.75]: 
        return 2
    else:
        return 1

# 而FM的數值則越大越好
RFM_Segment = RFM_norm2.copy()
RFM_Segment['R_Quartile'] = RFM_Segment['Recency'].apply(R_Class, args=('Recency',quantiles))

def FM_Class(x,p,d):
    if x <= d[p][0.25]:
        return 1
    elif x <= d[p][0.50]:
        return 2
    elif x <= d[p][0.75]: 
        return 3
    else:
        return 4
RFM_Segment['F_Quartile'] = RFM_Segment['Frequency'].apply(FM_Class, args=('Frequency',quantiles))
RFM_Segment['M_Quartile'] = RFM_Segment['Amount'].apply(FM_Class, args=('Amount',quantiles))

# 新建一個欄位放入RFM級別
RFM_Segment['RFMClass'] = RFM_Segment.R_Quartile.map(str) \
                            + RFM_Segment.F_Quartile.map(str) \
                            + RFM_Segment.M_Quartile.map(str)
   
RFM_Segment.to_csv('RFM_Segment.csv', encoding = 'cp950')

