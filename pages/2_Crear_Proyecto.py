import streamlit as st

import re
import pandas as pd
import requests
import pytz
import mysql.connector as sql
import datetime
import random
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")

user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
schema   = st.secrets["schema"]


def put_project(inputvar):
    #inputvar      = {'project':'WEWORK 300','city':'Bogota','address':'Carrera 11b # 99-25'}
    result        = {'status':400,'id_project':None,'project':None,'city':None,'address':None}
    project       = inputvar['project'].upper()
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql(f"SELECT id as id_project,project,city,address FROM proyect.cbre_proyecto WHERE project='{project}' AND activo=1" , con=db_connection)
    if data.empty and 'city' in inputvar and 'address' in inputvar:
        date       = datetime.datetime.now(tz=pytz.timezone('America/Bogota')).strftime("%Y-%m-%d %H:%M:%S")
        address    = formato_direccion(inputvar['address'])
        city       = inputvar['city'].lower()   
        direccion  = f'{address},{city},Colombia'
        response   = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?address={direccion}&key=AIzaSyAgT26vVoJnpjwmkoNaDl1Aj3NezOlSpKs').json()
        colorlist  = ['#012A2D','#80BBAD','#1F3866','#D1785C','#17E88F','#003F2D','#778F9C','#DBD99A','#CBCDCB']
        
        latitud         = response['results'][0]["geometry"]["location"]['lat']
        longitud        = response['results'][0]["geometry"]["location"]['lng']
        databarrio      = pd.read_sql(f"""SELECT scacodigo,scanombre as barriocatastral FROM proyect.data_barrios_colombia WHERE ST_CONTAINS(geometry, Point({longitud},{latitud})) LIMIT 1""", con=db_connection)
        scacodigo       = None
        barriocatastral = None
        if databarrio.empty is False and databarrio['scacodigo'].iloc[0] is not None:
            scacodigo   = databarrio['scacodigo'].iloc[0]
        if databarrio.empty is False and databarrio['barriocatastral'].iloc[0] is not None:
            barriocatastral = databarrio['barriocatastral'].iloc[0]

        dataexport = pd.DataFrame([{'date':date,'project':project,'address':inputvar['address'],'city':inputvar['city'],'latitud':response['results'][0]["geometry"]["location"]['lat'],'longitud':response['results'][0]["geometry"]["location"]['lng'],'direccion_formato':response['results'][0]["formatted_address"],'graph_color':random.choice(colorlist),'scacodigo':scacodigo,'barriocatastral':barriocatastral,'activo':1}])
        valores       = list(dataexport.apply(lambda x: tuple(x), axis=1).unique())
        cursor        = db_connection.cursor()
        cursor.execute("""INSERT INTO proyect.cbre_proyecto SET date=%s, project=%s, address=%s, city=%s, latitud=%s,longitud=%s,direccion_formato=%s, graph_color=%s, scacodigo=%s, barriocatastral=%s, activo=%s""",valores[0])
        db_connection.commit()
        result        = {'status':200,'id_project':cursor.lastrowid,'project':project,'city':inputvar['city'],'address':inputvar['address']}
    if data.empty is False: 
        result.update({'status':200})
        result.update(data.iloc[0].to_dict())
    return result
        
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
#-----------------------------------------------------------------------------#


col1, col2, col3, col4 = st.columns([1,4,4,1])
with col3:
    ciudad_registro            = st.selectbox('Ciudad ',options=['Bogota'])
    nombre_proyecto_registro   = st.text_input('Nombre del proyecto ',value="")
    direccion_oficina_registro = st.text_input('Dirección del proyecto ',value="")
    if nombre_proyecto_registro!="" and direccion_oficina_registro!="":
        result_button = st.button('Crear proyecto')
        if result_button:
            inputvar  = {'project':nombre_proyecto_registro.title(),'city':ciudad_registro,'address':direccion_oficina_registro}
            put_project(inputvar)
            st.success("Proyecto guardado exitosamente")