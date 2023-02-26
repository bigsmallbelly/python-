import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# read data
datas = pd.read_csv('carseats.csv')

#抓欄位
x = datas['Population']
y = datas['Sales']*datas['Price']

# 繪製門市人口與銷售表現的交互關係
fig,ax= plt.subplots(figsize=(10,8)) #設定畫布大小
ax.scatter(x,y)
plt.title('各分店銷量與銷售表現')
plt.xlabel('Population')
plt.ylabel('sale performance')
plt.show()


# 繪製貨架高低、投資預算、門市人口、銷售表現的圖形
Baddata = datas[datas['ShelveLoc']=='Bad']
x_B=Baddata['Population']
y_B=Baddata['Sales']*Baddata['Price']

Gooddata = datas[datas['ShelveLoc'] =='Good']
x_G = Gooddata['Population']
y_G = Gooddata['Sales']*Gooddata['Price']

Meddata = datas[datas['ShelveLoc'] =='Medium']
x_M = Meddata['Population']
y_M = Meddata['Sales']*Meddata['Price']


fig, ax = plt.subplots(figsize=(8, 8))
ax.scatter(x_B, y_B, s=(Baddata['Advertising']+1)*10, label = 'Bad')
ax.scatter(x_G, y_G, s=(Gooddata['Advertising']+1)*10, label = 'Good')
ax.scatter(x_M, y_M, s=(Meddata['Advertising']+1)*10, label = 'Medium')
plt.legend(bbox_to_anchor=(1.03, 0.8), loc=2)
plt.title('Advertising Budget')
plt.xlim(0,530) #設定x軸顯示範圍
plt.ylim(0,2000) #設定y軸顯示範圍
plt.xlabel('Population')
plt.ylabel('Sale performance')
plt.show()



# 計算出淨利的欄位
datas['Profit']=datas['Sales']*datas['Price']-datas['Advertising']


Baddata = datas[datas['ShelveLoc']=='Bad']
x_B=Baddata['Population']
y_B=Baddata['Sales']*Baddata['Price']

Gooddata = datas[datas['ShelveLoc'] =='Good']
x_G = Gooddata['Population']
y_G = Gooddata['Sales']*Gooddata['Price']

Meddata = datas[datas['ShelveLoc'] =='Medium']
x_M = Meddata['Population']
y_M = Meddata['Sales']*Meddata['Price']

# 有一些淨利算出來的圈圈太大了，統一除50調整大小
Size_B = Baddata['Profit'] / 50
Size_G = Gooddata['Profit']/ 50
Size_M = Meddata['Profit']/ 50

# 繪製貨架高低、淨利、門市人口、銷售表現的圖形
fig, ax = plt.subplots(figsize=(8, 8))
ax.scatter(x_B, y_B, s=Size_B*10, label = 'Bad')
ax.scatter(x_G, y_G, s=Size_G*10, label = 'Good')
ax.scatter(x_M, y_M, s=Size_M*10, label = 'Medium')
plt.legend(bbox_to_anchor=(1.03,0.8),loc=2)
plt.title('profit point')
plt.xlim(0,530) #設定x軸顯示範圍
plt.ylim(0,2000) #設定y軸顯示範圍
plt.xlabel('Population')
plt.ylabel('Sale performance')
plt.show()



# 計算ROI
datas['Total_cost']=datas['Sales']*datas['Price']+datas['Advertising']
datas['ROI']=datas['Profit']/datas['Total_cost']


Baddata = datas[datas['ShelveLoc']=='Bad']
x_B=Baddata['Population']
y_B=Baddata['Sales']*Baddata['Price']

Gooddata = datas[datas['ShelveLoc'] =='Good']
x_G = Gooddata['Population']
y_G = Gooddata['Sales']*Gooddata['Price']

Meddata = datas[datas['ShelveLoc'] =='Medium']
x_M = Meddata['Population']
y_M = Meddata['Sales']*Meddata['Price']

Size_B = Baddata['ROI']  
Size_G = Gooddata['ROI']
Size_M = Meddata['ROI']

# 繪製貨架高低、ROI、門市人口、銷售表現的圖形
fig, ax = plt.subplots(figsize=(8, 8))
ax.scatter(x_B, y_B, s=Size_B*200, label = 'Bad')
ax.scatter(x_G, y_G, s=Size_G*200, label = 'Good')
ax.scatter(x_M, y_M, s=Size_M*200, label = 'Medium')
lgnd = plt.legend(bbox_to_anchor=(1.03, 0.8), loc=2)
lgnd.legendHandles[0]._sizes = [30]
lgnd.legendHandles[1]._sizes = [30]
lgnd.legendHandles[2]._sizes = [30]
plt.title('ROI point')
plt.xlim(0,530) #設定x軸顯示範圍
plt.ylim(0,2000) #設定y軸顯示範圍
plt.xlabel('Population')
plt.ylabel('Sale performance')
plt.show()


 #輸出名單
'''
0. 產出bad, good, medium三種貨架資料
1. ROI大於0.5
2. ROI由大排到小
3. 僅輸出'ID', 'Sales','Advertising','total_cost', 'profit', 'ROI']這幾個欄位

'''

Baddata = Baddata.sort_values('ROI', ascending  = False)
Baddata_list = Baddata[Baddata['ROI'] > 0.5] 
Baddata_list[['ID', 'Sales','Advertising','total_cost', 'profit', 'ROI']].to_csv('Baddata_list.csv', encoding = 'cp950')

Gooddata= Gooddata.sort_values('ROI', ascending=False)
Gooddata_list= Gooddata[Gooddata['ROI']>0.5]
Gooddata_list[['ID','Sales','Advertising','total_cost','profit','ROI']].to_csv('Gooddata_list.csv', encoding='cp950')


Meddata = Meddata.sort_values('ROI', ascending  = False)
Meddata_list = Meddata[Meddata['ROI'] > 0.5] 
Meddata_list[['ID', 'Sales','Advertising','total_cost', 'profit', 'ROI']].to_csv('Meddata_list.csv', encoding = 'cp950')

