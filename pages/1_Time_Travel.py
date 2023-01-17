import streamlit as st

import re
import copy
import pandas as pd
import requests
import pytz
import mysql.connector as sql
import datetime
import random
from sqlalchemy import create_engine 
from multiprocessing.dummy import Pool
#from dateutil.relativedelta import relativedelta, MO
from tqdm import tqdm
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")

user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
schema   = st.secrets["schema"]

def get_list():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id as id_project,project,city,address FROM proyect.cbre_proyecto WHERE activo=1" , con=db_connection)
    data          = data.sort_values(by='project',ascending=True)
    return data

def analysis(data,id_project,email,client,nit):
    #data       = pd.DataFrame([{'address':'carrera 19a 103a 62','city':'Bogota'},{'address':'carrera 9 128a 40','city':'Bogota'}])
    #id_project = 4
    
    db_connection   = sql.connect(user=user, password=password, host=host, database=schema)
    dataproject     = pd.read_sql(f"SELECT id as id_proyecto,project,city,address,latitud,longitud,scacodigo,barriocatastral FROM proyect.cbre_proyecto WHERE id='{id_project}' AND activo=1" , con=db_connection)
    data            = data[data['address'].notnull()]
    data['origen']  = data['address'].apply(lambda x: formato_direccion(x))
    data['origen']  = data['origen']+','+data['city']+',colombia'
    data['idmatch'] = range(len(data))
    data.index      = range(len(data))
    destination     = formato_direccion(dataproject['address'].iloc[0])
    destination     = destination+','+dataproject['city'].iloc[0]+',colombia'
    data['destination'] = destination
    
    # tiempo de ida
    consulta_date     = datetime.datetime.now(tz=pytz.timezone('America/Bogota')).strftime("%Y-%m-%d %H:%M:%S")
    data['hora']      = 7 # 7:30 AM
    data['minutos']   = 30
    data['getbarrio'] = True
    pool      = Pool(10)
    futures   = []
    datafinal = pd.DataFrame()
    
    for i in range(len(data)):  
        inputvar = data.iloc[i].to_dict()
        futures.append(pool.apply_async(get_travel_time,args = (inputvar, )))
    for future in tqdm(futures):
        try: datafinal = datafinal.append([future.get()])
        except: pass
    if datafinal.empty is False:
        datafinal.rename(columns={'timeValue':'tiempo_ida_seg', 'timeInMin':'tiempo_ida'},inplace=True)
        data = data.merge(datafinal,on='idmatch',how='left',validate='1:1')

    # tiempo de regreso
    data['hora']        = 17 # 5:30 PM
    data['minutos']     = 30
    data['destination'] = copy.deepcopy(data['origen'])
    data['origen']      = destination
    data['getbarrio']   = False
    futures   = []
    datafinal = pd.DataFrame()
    for i in range(len(data)):  
        inputvar = data.iloc[i].to_dict()
        futures.append(pool.apply_async(get_travel_time,args = (inputvar, )))
    for future in tqdm(futures):
        try: datafinal = datafinal.append([future.get()])
        except: pass
    if datafinal.empty is False:
        datafinal.rename(columns={'timeValue':'tiempo_regreso_seg', 'timeInMin':'tiempo_regreso'},inplace=True)
        datafinal.drop(columns=['latitud','longitud'],inplace=True)
        data = data.merge(datafinal,on='idmatch',how='left',validate='1:1')
    
    try:    client = client.upper()
    except: client = None
    data['id_proyecto']  = id_project
    data['date']         = consulta_date
    data['user']         = email
    data['client']       = client
    data['nit']          = nit
    data['office_point'] = 0
    varlist = ['id_proyecto','user','client','date','city','address','latitud','longitud','tiempo_ida','tiempo_regreso','scacodigo','barriocatastral','nit','office_point']
    varlist = [x for x in varlist if x in list(data)]

    dataproject['date']   = consulta_date
    dataproject['user']   = email
    dataproject['client'] = client
    dataproject['office_point'] = 1
    data = data.append(dataproject)

    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data[varlist].to_sql('cbre_direcciones',engine,if_exists='append', index=False,chunksize=1000)
    
    # Actualizar data PowerBI
    #url     = 'https://api.powerbi.com/v1.0/myorg/datasets/affc0e83-fa8a-4f02-9c3a-bff5ed492d09/refreshes'
    #headers = {"Authorization":"Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IjJaUXBKM1VwYmpBWVhZR2FYRUpsOGxWMFRPSSIsImtpZCI6IjJaUXBKM1VwYmpBWVhZR2FYRUpsOGxWMFRPSSJ9.eyJhdWQiOiJodHRwczovL2FuYWx5c2lzLndpbmRvd3MubmV0L3Bvd2VyYmkvYXBpIiwiaXNzIjoiaHR0cHM6Ly9zdHMud2luZG93cy5uZXQvNzY3ZDFhN2EtOWQxMy00YWM4LThjZTgtYzNlMTdmYjYxOTMxLyIsImlhdCI6MTY2Mjk1MzA2NCwibmJmIjoxNjYyOTUzMDY0LCJleHAiOjE2NjI5NTcyNDMsImFjY3QiOjAsImFjciI6IjEiLCJhaW8iOiJBVFFBeS84VEFBQUFNSDFzbXRFOFBiMHhrSlREYXhZSk1YM3NUK1ZhbTdvOUJrZVlDMHBKTlE0NGdIZDlvdEc0eUsvOGg1UnVyWVozIiwiYW1yIjpbInB3ZCJdLCJhcHBpZCI6IjE4ZmJjYTE2LTIyMjQtNDVmNi04NWIwLWY3YmYyYjM5YjNmMyIsImFwcGlkYWNyIjoiMCIsImZhbWlseV9uYW1lIjoiR2F2aXJpYSIsImdpdmVuX25hbWUiOiJBbGVqYW5kcm8iLCJpcGFkZHIiOiIxODEuNjIuMjAuMjIwIiwibmFtZSI6IkFsZWphbmRybyBHYXZpcmlhIiwib2lkIjoiMDE1MjFkYjMtZDllOC00NzMyLWE3OWItOGM5OGU1MTJhMjdkIiwicHVpZCI6IjEwMDMyMDAxRDJFOEQ0NDciLCJyaCI6IjAuQVRRQWVocDlkaE9keUVxTTZNUGhmN1laTVFrQUFBQUFBQUFBd0FBQUFBQUFBQUEwQUdnLiIsInNjcCI6IkFwcC5SZWFkLkFsbCBDYXBhY2l0eS5SZWFkLkFsbCBDYXBhY2l0eS5SZWFkV3JpdGUuQWxsIENvbnRlbnQuQ3JlYXRlIERhc2hib2FyZC5SZWFkLkFsbCBEYXNoYm9hcmQuUmVhZFdyaXRlLkFsbCBEYXRhZmxvdy5SZWFkLkFsbCBEYXRhZmxvdy5SZWFkV3JpdGUuQWxsIERhdGFzZXQuUmVhZC5BbGwgRGF0YXNldC5SZWFkV3JpdGUuQWxsIEdhdGV3YXkuUmVhZC5BbGwgR2F0ZXdheS5SZWFkV3JpdGUuQWxsIFBpcGVsaW5lLkRlcGxveSBQaXBlbGluZS5SZWFkLkFsbCBQaXBlbGluZS5SZWFkV3JpdGUuQWxsIFJlcG9ydC5SZWFkLkFsbCBSZXBvcnQuUmVhZFdyaXRlLkFsbCBTdG9yYWdlQWNjb3VudC5SZWFkLkFsbCBTdG9yYWdlQWNjb3VudC5SZWFkV3JpdGUuQWxsIFRlbmFudC5SZWFkLkFsbCBUZW5hbnQuUmVhZFdyaXRlLkFsbCBVc2VyU3RhdGUuUmVhZFdyaXRlLkFsbCBXb3Jrc3BhY2UuUmVhZC5BbGwgV29ya3NwYWNlLlJlYWRXcml0ZS5BbGwiLCJzaWduaW5fc3RhdGUiOlsia21zaSJdLCJzdWIiOiJQSE5YY0NKSUcyTmF5eFBQLV80NjBfMjJkWVFjWXR0aXJBLWYwdTVteTIwIiwidGlkIjoiNzY3ZDFhN2EtOWQxMy00YWM4LThjZTgtYzNlMTdmYjYxOTMxIiwidW5pcXVlX25hbWUiOiJhZ2F2aXJpYUBidXlkZXBhLmNvbSIsInVwbiI6ImFnYXZpcmlhQGJ1eWRlcGEuY29tIiwidXRpIjoiTXlmRHZVRjM3MHFtTFNzMG8xMVNBZyIsInZlciI6IjEuMCIsIndpZHMiOlsiYjc5ZmJmNGQtM2VmOS00Njg5LTgxNDMtNzZiMTk0ZTg1NTA5Il19.tHj62tBG4UATtPgJSkYWxKayK5fZ3BZAsYchJcTBxZHMvXbpIs8zwrLNQlXyNlYltSgoF3HDvsPDA4ezFkUz9o6aD_Olax14AAzPUQAlgIxdJnKVXOEcbuTRGj1JpCPvz_OdVfWiWuLePps5EY6KtmHLFA-ZruMsCqE5kal8mQGvnEjZpCr6-A_ZUqZhNMErDIMMIzGo3U-75Igc5V_vmoyFItx7FZE_mPRJ8fJxwVrflsqkA2Ak53vIgkS61_epNQS--382h185KcDpZ7Se3X7nmqaHkbGWd0cNiYtNI8wZK1FUDO8yZYFjwg2Bw3tPXYL4a8DyjxHtUsrce31hBQ",
    #           "Content-Type":"application/json"}
    #requests.post(url,headers = headers,timeout=30)
    return data[varlist]

def get_travel_time(inputvar):
    idmatch     = inputvar['idmatch']
    origen      = inputvar['origen'] 
    destination = inputvar['destination']
    hora        = inputvar['hora']
    minutos     = inputvar['minutos'] 
    getbarrio   = inputvar['getbarrio']
    seconds     = getSecondsFromStart(hora,minutos)
    result      = {'idmatch':idmatch,'timeValue':None,'timeInMin':None,'latitud':None,'longitud':None}
    try: 
        #url        = f'https://maps.googleapis.com/maps/api/directions/json?destination={destination}&origin={origen}&key=AIzaSyBEjvAMTg70W6oUvWc5HzYUS3O9rzEI9Jw'
        url        = f'https://maps.googleapis.com/maps/api/directions/json?destination={destination}&origin={origen}&departure_time={seconds}&key=AIzaSyBEjvAMTg70W6oUvWc5HzYUS3O9rzEI9Jw'
        api_result = requests.request(method="GET", url=url).json()
        timeValue  = api_result['routes'][0]['legs'][0]['duration']['value']
        timeInMin  = timeValue/ 60 
        result.update({'timeValue':timeValue,'timeInMin':timeInMin})
        if getbarrio:
            latitud    = api_result['routes'][0]['legs'][0]['start_location']["lat"]
            longitud   = api_result['routes'][0]['legs'][0]['start_location']["lng"]
            db_connection = sql.connect(user=user, password=password, host=host, database=schema)
            databarrio    = pd.read_sql(f"""SELECT scacodigo,scanombre as barriocatastral FROM proyect.data_barrios_colombia WHERE ST_CONTAINS(geometry, Point({longitud},{latitud})) LIMIT 1""", con=db_connection)
            result.update({'timeValue':timeValue,'timeInMin':timeInMin,'latitud':latitud,'longitud':longitud})
            if databarrio.empty is False:
                result.update(databarrio.iloc[0].to_dict())
    except: pass
    return pd.DataFrame([result])

#-----------------------------------------------------------------------------#
def getSecondsFromStart(hour,minutos):
  first_date = datetime.datetime(1970,1,1)
  #nextmonday = datetime.now()+ relativedelta(weekday=MO(0))
  today      = datetime.date.today()
  nextmonday = today + datetime.timedelta(days=-today.weekday(), weeks=1)
  nextmonday = datetime.datetime.combine(nextmonday, datetime.time(hour,minutos))
  today      = nextmonday - first_date
  return int(today.total_seconds())
#-----------------------------------------------------------------------------#
def formato_direccion(x):
    resultado = x
    try:
        address = ''
        x       = x.upper()
        x       = re.sub('[^A-Za-z0-9]',' ', x).strip() 
        x       = re.sub(re.compile(r'\s+'),' ', x).strip()
        numbers = re.sub(re.compile(r'\s+'),' ', re.sub('[^0-9]',' ', x)).strip().split(' ')
        vector  = ['ESTE','OESTE','SUR']
        for i in range(0,min(3,len(numbers))):
            try:
                initial = x.find(numbers[i],0)
                z       = x.find(numbers[i+1],initial+len(numbers[i]))
                result  = x[0:z].strip()
            except:
                result = x
            if i==2:
                if any([w in result.upper() for w in vector]):
                    result = numbers[i]+' '+[w for w in vector if w in result.upper()][0]
                else:
                    result = numbers[i]            
            address = address+' '+result
            z = x.find(result)
            x = x[(z+len(result)):].strip()
        resultado = address.strip()
        try: 
            #resultado = re.sub("[A-Za-z]+", lambda ele: " " + ele[0] + " ", resultado)
            resultado = re.sub(re.compile(r'\s+'),' ', resultado).strip()
            resultado = indicador_via(resultado)
        except: pass
    except: pass
    try: resultado = re.sub(re.compile(r'\s+'),'+', resultado).strip()
    except: pass
    return resultado

def indicador_via(x):
    m       = re.search("\d", x).start()
    tipovia = x[:m].strip()
    prefijos = {'D':{'d','diagonal','dg', 'diag', 'dg.', 'diag.', 'dig'},
                'T':{'t','transv', 'tranv', 'tv', 'tr', 'tv.', 'tr.', 'tranv.', 'transv.', 'transversal', 'tranversal'},
                'C':{'c','avenida calle','avenida cll','avenida cl','calle', 'cl', 'cll', 'cl.', 'cll.', 'ac', 'a calle', 'av calle', 'av cll', 'a cll'},
                'AK':{'avenida carrera','avenida cr','avenida kr','ak', 'av cr', 'av carrera', 'av cra'},
                'K':{'k','carrera', 'cr', 'cra', 'cr.', 'cra.', 'kr', 'kr.', 'kra.', 'kra'},
                'A':{'av','avenida'}}
    for key, values in prefijos.items():
        if tipovia.lower() in values:
            x = x.replace(tipovia,key)
            break
    return x

def prefijo(x):
    result = None
    m      = re.search("\d", x).start()
    x      = x[:m].strip()
    prefijos = {'D':{'d','diagonal','dg', 'diag', 'dg.', 'diag.', 'dig'},
                'T':{'t','transv', 'tranv', 'tv', 'tr', 'tv.', 'tr.', 'tranv.', 'transv.', 'transversal', 'tranversal'},
                'C':{'c','avenida calle','avenida cll','avenida cl','calle', 'cl', 'cll', 'cl.', 'cll.', 'ac', 'a calle', 'av calle', 'av cll', 'a cll'},
                'AK':{'avenida carrera','avenida cr','avenida kr','ak', 'av cr', 'av carrera', 'av cra'},
                'K':{'k','carrera', 'cr', 'cra', 'cr.', 'cra.', 'kr', 'kr.', 'kra.', 'kra'},
                'A':{'av','avenida'}}
    for key, values in prefijos.items():
        if x.lower() in values:
            result = key
            break
    return result

@st.cache
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

#-----------------------------------------------------------------------------#


col1, col2, col3, col4 = st.columns([1,4,4,1])
with col3:
    dataproyectos   = get_list()
    nombre_cliente  = st.text_input('Nombre del cliente',value="")
    nombre_proyecto = st.multiselect('Nombre del proyecto',options=dataproyectos['project'].to_list())    
    nit             = st.text_input('NIT',value="")
    email           = st.text_input('Email',value="")
    uploaded_file   = st.file_uploader("Subir data de direcciones")
    
    plantilla = pd.DataFrame([{'address':'Carrera 15 # 124 - 30','city':'Bogota'},{'address':'Carrera 11 #82-71','city':'Bogota'},{'address':'Calle 38 SUR # 34 D - 51','city':'Bogota'}])
    csv       = convert_df(plantilla)
    st.download_button(
        label="Plantilla",
        data=csv,
        file_name='plantilla.csv',
        mime='text/csv',
    )
                       
    continuar = False
    if nombre_cliente!="" and nombre_proyecto!=[] and nit!="" and email!="" and uploaded_file is not None:
        continuar = True
    
    if continuar:
        data          = pd.read_excel(uploaded_file)
        result_button = st.button('Calcular')
        if result_button:
            with st.spinner(text="Calculando trivel time"):
                for i in nombre_proyecto:
                    id_project = dataproyectos[dataproyectos['project']==i]['id_project'].iloc[0]
                    analysis(data,id_project,email,nombre_cliente,nit)
            st.success("Se ejecutó exitosamente")
        
                           