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
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

from tqdm import tqdm
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")

user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
schema   = st.secrets["schema"]

#@st.experimental_memo
def get_list():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT * FROM proyect.cbre_proyecto WHERE activo=1" , con=db_connection)
    data          = data.sort_values(by='project',ascending=True)
    return data

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


with st.container():
    st.markdown('<div style="background-color: #f2f2f2; border: 1px solid #fff; padding: 0px; margin-bottom: 10px;"><h1 style="margin: 0; font-size: 18px; text-align: center; color: #80BBAD;">Listo de proyectos</h1></div>', unsafe_allow_html=True)
    dataproyectos   = get_list()
    variables       = [x for x in ['date','project','city','address','latitud','longitud','direccion_formato'] if x in dataproyectos]
    dataproyectos   = dataproyectos[variables]
    dataproyectos.rename(columns={'date':'Fecha','project':'Proyecto','city':'Ciudad','address':'Dirección'},inplace=True)
    dataproyectos.columns = [x.title().strip().replace('_',' ') for x in list(dataproyectos)]
    dataproyectos.index = range(len(dataproyectos))
    #st.dataframe(data=dataproyectos)
    
    gb = GridOptionsBuilder.from_dataframe(dataproyectos)
    gb.configure_default_column(enablePivot=True, enableValue=True, enableRowGroup=True)
    gb.configure_selection(selection_mode="single", use_checkbox=True) # "multiple"
    gb.configure_side_bar(filters_panel=False,columns_panel=False)
    gridoptions = gb.build()
    
    response = AgGrid(
        dataproyectos,
        height=350,
        gridOptions=gridoptions,
        enable_enterprise_modules=False,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        header_checkbox_selection_filtered_only=False,
        use_checkbox=True,
        allow_unsafe_jscode=True,  # Asegúrate de permitir JavaScript inseguro para permitir el redimensionamiento automático de las columnas
        key="unique_key",
    )
    if response['selected_rows']:
        for i in response['selected_rows']:
            print(i['Proyecto'])
            
            
            

st.write('---')
st.text('Editar proyectos')
col1, col2, col3 = st.columns(3)
with col1:
    nombre_proyecto = st.selectbox('Nombre del proyecto',options=dataproyectos['Proyecto'].to_list())
    
with col2: 
    nuevo_nombre_proyecto = st.text_input('Nuevo nombre del proyecto',value="")
    
with col3: 
    direccion   = st.text_input('Nueva dirección del proyecto',value="")
        
if nuevo_nombre_proyecto!="" or direccion!="":
    result_button = st.button('Editar')
    if result_button:
        consulta = ""
        if direccion!="":
            direccion_input = copy.deepcopy(direccion)
            address    = formato_direccion(direccion)
            city       = dataproyectos[dataproyectos['Proyecto']==nombre_proyecto]['Ciudad'].iloc[0]
            direccion  = f'{address},{city},Colombia'
            response   = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?address={direccion}&key=AIzaSyAgT26vVoJnpjwmkoNaDl1Aj3NezOlSpKs').json()
            latitud           = response['results'][0]["geometry"]["location"]['lat']
            longitud          = response['results'][0]["geometry"]["location"]['lng']
            direccion_formato = response['results'][0]["formatted_address"]
            
            db_connection   = sql.connect(user=user, password=password, host=host, database=schema)
            databarrio      = pd.read_sql(f"""SELECT scacodigo,scanombre as barriocatastral FROM proyect.data_barrios_colombia WHERE ST_CONTAINS(geometry, Point({longitud},{latitud})) LIMIT 1""", con=db_connection)
            scacodigo       = None
            barriocatastral = None
            if databarrio.empty is False and databarrio['scacodigo'].iloc[0] is not None:
                scacodigo   = databarrio['scacodigo'].iloc[0]
            if databarrio.empty is False and databarrio['barriocatastral'].iloc[0] is not None:
                barriocatastral = databarrio['barriocatastral'].iloc[0]
            consulta = f"""UPDATE `proyect`.`cbre_proyecto` SET `address` = '{direccion_input}', `latitud` = '{latitud}',  `longitud` = '{longitud}',  `scacodigo` = '{scacodigo}',  `barriocatastral` = '{barriocatastral}' ,  `direccion_formato` = '{direccion_formato}'  """
                
        if nuevo_nombre_proyecto!="":
            nuevo_nombre_proyecto = nuevo_nombre_proyecto.upper()
            if consulta=="":
                consulta = f"""UPDATE `proyect`.`cbre_proyecto` SET `project` = '{nuevo_nombre_proyecto}' """
            else:
                consulta = consulta + f""" ,`project` = '{nuevo_nombre_proyecto}'  """
        if consulta!="":
            consulta = consulta + f""" WHERE (`project` = '{nombre_proyecto}');"""
            cursor   = db_connection.cursor()
            cursor.execute(consulta)
            db_connection.commit()
            st.success("Editado exitosamente")
            
st.write('---')

st.text('Eliminar proyecto')
col1, col2 = st.columns([4,1])
with col1:
    proyecto_eliminar = st.selectbox('Nombre del proyecto a eliminar',options=dataproyectos['Proyecto'].to_list())
    
with col2: 
    delete_button = st.button('Eliminar')
    if delete_button:
        db_connection = sql.connect(user=user, password=password, host=host, database=schema)
        cursor        = db_connection.cursor()
        cursor.execute(f"""UPDATE `proyect`.`cbre_proyecto` SET `activo` = '0'  WHERE (`project` = '{proyecto_eliminar}'); """)
        db_connection.commit()
        st.success("Elininado exitosamente")
        
            
        
        
            
    
    