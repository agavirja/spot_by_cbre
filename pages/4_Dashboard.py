import streamlit as st
import folium
from streamlit_folium import st_folium
import altair as alt
import geopandas as gpd
from sqlalchemy import create_engine

import pandas as pd
import mysql.connector as sql

# MAPAS:  https://medium.com/datasciencearth/map-visualization-with-folium-d1403771717

st.set_page_config(layout="wide")

user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
schema   = st.secrets["schema"]

def main():
    add_bg_from_url() 

    #-----------------------------------------------------------------------------#
    col1, col2, col3, col4 = st.columns(4)
    with col3:
        if st.button('Refrescar información'):
            st.cache_data.clear()
            st.rerun()  
    with col4:
        dataexport = getdatadownload()
        if st.button('Descargar Excel'):
            download_excel(dataexport)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        data_project = get_list()
        ciudad       = st.selectbox(label='Ciudad',options=sorted(data_project['city'].unique()))
    with col2: 
        data_client = get_clients(ciudad)
        cliente     = st.selectbox(label='Cliente',options=sorted(data_client['client'].unique()))
    with col3:
        idj         = data_client['client']==cliente
        id_proyecto = data_client[idj]['id_project'].unique()
        idd         = (data_project['city']==ciudad) & (data_project['id_project'].isin(id_proyecto))
        proyecto    = st.selectbox(label='Proyecto',options=sorted(data_project[idd]['project'].unique()))
    with col4:
        variable_estudio = st.selectbox(label='Variable',options=['Tiempo de regreso','Tiempo de ida'])
        tipo_analisis    = 'tiempo_regreso'
        if variable_estudio=='Tiempo de ida':
            tipo_analisis = 'tiempo_ida'

    col1, col2, col3 = st.columns([5,2,5])
    with col1:
        id_project      = data_project[data_project['project']==proyecto]['id_project'].iloc[0]
        data_traveltime = get_timetravel(cliente,id_project)
        data_points     = data_traveltime[data_traveltime['office_point']==0]
        data_points["color"] = pd.cut(data_points["tiempo_regreso"], bins=[0,10,30,60,300], labels=["#012A2D", "#80BBAD", "#DBD99A","#D1785C"])
        data_points["label"] = pd.cut(data_points["tiempo_regreso"], bins=[0,10,30,60,300], labels=["0-10 min", "10-30 min", "30-60 min","60 > min"])
        data_points["order"] = pd.cut(data_points["tiempo_regreso"], bins=[0,10,30,60,300], labels=["1", "2", "3","4"])
        data_points          = data_points[(data_points['latitud'].notnull()) & (data_points['longitud'].notnull())]
        data_points          = data_points[data_points[tipo_analisis]>=0]
        data_point_office = data_traveltime[data_traveltime['office_point']==1]
        
        m = folium.Map(location=[data_traveltime["latitud"].mean(), data_traveltime["longitud"].mean()], zoom_start=11,tiles="cartodbpositron")
        
        for index, row in data_points.iterrows():
            folium.CircleMarker(location=[row["latitud"], row["longitud"]],
                                radius=4,
                                color=row["color"],
                                fill=True,
                                #fill_color=row["color"],
                                popup=row["tiempo_regreso"]).add_to(m)
        
        folium.CircleMarker(location=[data_point_office["latitud"].iloc[0], data_point_office["longitud"].iloc[0]],
                            radius=6,
                            color="#800080",
                            fill=True,
                            #fill_color=row["color"],
                            ).add_to(m)
            
        st_map = st_folium(m,height=500)
        
    with col2:
        # Direcciones unicas
        direcciones_unicas = len(data_points['address'].unique())
        st.markdown(f"""
        <div style="text-align: center; color: black; font-size: 24px; font-family: 'Segoe UI';font-weight:bold">
            {direcciones_unicas}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; color: #808080; font-size: 12px; font-family: 'Segoe UI';margin-bottom:2px;">
            Direcciones unicas
        </div>
        """, unsafe_allow_html=True)  
        st.markdown("<div style='border-top: 2px solid green;'> </div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="margin-bottom:50px;"></div>
        """, unsafe_allow_html=True) 
        
        # Barrios unicas
        barrios_unicos = len(data_points['scacodigo'].unique())
        st.markdown(f"""
        <div style="text-align: center; color: black; font-size: 24px; font-family: 'Segoe UI';font-weight:bold">
            {barrios_unicos}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; color: #808080; font-size: 12px; font-family: 'Segoe UI';;margin-bottom:2px;">
            Barrios unicos
        </div>
        """, unsafe_allow_html=True)      
        st.markdown("<div style='border-top: 2px solid green;'> </div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="margin-bottom:50px;"></div>
        """, unsafe_allow_html=True) 
        
        # Tiempo de viaje de ida promedio
        tiempo_promedio_ida = data_points['tiempo_ida'].median()
        tiempo_promedio_ida = format(tiempo_promedio_ida, '.2f')
        st.markdown(f"""
        <div style="text-align: center; color: black; font-size: 24px; font-family: 'Segoe UI';font-weight:bold">
            {tiempo_promedio_ida}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; color: #808080; font-size: 12px; font-family: 'Segoe UI';margin-bottom:2px;">
            Tiempo promedio de ida
        </div>
        """, unsafe_allow_html=True)  
        st.markdown("<div style='border-top: 2px solid green;'> </div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="margin-bottom:50px;"></div>
        """, unsafe_allow_html=True)     
        
        # Tiempo de viaje de regreso promedio
        tiempo_promedio_regreso = data_points['tiempo_regreso'].median()
        tiempo_promedio_regreso = format(tiempo_promedio_regreso, '.2f')
        st.markdown(f"""
        <div style="text-align: center; color: black; font-size: 24px; font-family: 'Segoe UI';font-weight:bold">
            {tiempo_promedio_regreso}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; color: #808080; font-size: 12px; font-family: 'Segoe UI';margin-bottom:2px;">
            Tiempo promedio de regreso
        </div>
        """, unsafe_allow_html=True)  
        st.markdown("<div style='border-top: 2px solid green;'> </div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="margin-bottom:50px;"></div>
        """, unsafe_allow_html=True)  
        
    with col3:
        data_shp      = get_shp_file()
        data_espacial = data_points[['scacodigo',tipo_analisis]]
        data_espacial = data_espacial.groupby('scacodigo')[tipo_analisis].median().reset_index()
        data_shp = data_shp.merge(data_espacial,on='scacodigo',how='left',validate='1:1')
        data_shp = data_shp[data_shp[tipo_analisis].notnull()]
        colors   = ['#ff0000', '#ff7f00', '#ffff00', '#00ff00', '#0000ff']
        
        map1 = folium.Map(location=[data_points['latitud'].mean(), data_points['longitud'].mean()], zoom_start=11,tiles="cartodbpositron")

        if not data_shp.empty:
            datashow = data_shp.copy()
            datashow.drop(columns=['geometry'],inplace=True)
            datashow = pd.DataFrame(datashow)
            geojson  = data2geopandas(datashow)
            popup    = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(map1)
        st_map = st_folium(map1,height=500)
        
    # Grafica de barras
    col1, col2, col3 = st.columns([4,1,4])
    with col1:
        st.markdown(f"""
        <div style="color: #808080; font-size: 12px; font-family: 'Segoe UI';margin-bottom:2px;">
            {variable_estudio} promedio
        </div>
        """, unsafe_allow_html=True)  
        st.markdown("<div style='border-top: 2px solid green;'> </div>", unsafe_allow_html=True)
     
        v = data_points.groupby(['label','color','order'])['id'].count().reset_index()
        v = v[v['id']>0]
        if v.empty is False:
            v = v.sort_values(by='order',ascending=True)
        
            valores = v['id'].to_list()
            nombres_barras = v['label'].to_list()
            colores = v['color'].to_list()
            
            # Crea el gráfico de barras
            chart = alt.Chart(pd.DataFrame({"values":valores,"names":nombres_barras})).mark_bar().encode(
                x='names',
                y='values',
                color=alt.Color('names', legend=None, scale=alt.Scale(range=colores))
            ).properties(
            width=400,
            height=300
        ).configure_axisX(labelAngle=0)
            
            st.altair_chart(chart)
            
    # Grafica de barras horizontales
    paleta_colores =  ["#012A2D", "#80BBAD", "#DBD99A","#D1785C","#012A2D",
                       "#012A2D", "#80BBAD", "#DBD99A","#D1785C","#012A2D",
                       "#012A2D", "#80BBAD", "#DBD99A","#D1785C","#012A2D",
                       "#012A2D", "#80BBAD", "#DBD99A","#D1785C","#012A2D"]
    with col3:

        st.markdown("""
        <div style="color: #808080; font-size: 12px; font-family: 'Segoe UI';margin-bottom:2px;">
            Referencia por proyecto
        </div>
        """, unsafe_allow_html=True)  
        st.markdown("<div style='border-top: 2px solid green;'> </div>", unsafe_allow_html=True)
     
        
        data_by_client = get_timetravel_by_client(cliente) 
        v              = data_by_client.groupby(['id_project'])[tipo_analisis].median().reset_index()
        if v.empty is False:
            v              = v.merge(data_project[['id_project','project']],on='id_project',how='left',validate='1:1')
            v              = v.sort_values(by=tipo_analisis,ascending=True)
        
            valores = v[tipo_analisis].to_list()
            nombres_barras = v['project'].to_list()
            colores = paleta_colores[0:len(valores)]
            
            # Crea el gráfico de barras
            chart = alt.Chart(pd.DataFrame({"values":valores,"names":nombres_barras})).mark_bar(orient='horizontal').encode(
                x='values',
                y='names',
                color=alt.Color('names', legend=None, scale=alt.Scale(range=colores))
            ).properties(
            width=400,
            height=300
            )
            
            st.altair_chart(chart)
            
@st.cache_data(show_spinner=False)
def get_list():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id as id_project,project,city,address FROM proyect.cbre_proyecto  WHERE activo=1" , con=db_connection)
    data          = data.sort_values(by='project',ascending=True)
    return data

@st.cache_data(show_spinner=False)
def get_clients(city):
    consulta = "office_point=1"
    if city!="":
        consulta = consulta + f" AND city='{city}'"
        
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql(f"SELECT DISTINCT client,id_proyecto as id_project FROM proyect.cbre_direcciones WHERE {consulta} " , con=db_connection)
    data          = data.sort_values(by='client',ascending=True)
    return data

@st.cache_data(show_spinner=False)
def get_timetravel(cliente,id_project):
    consulta = ""
    if cliente!="" and cliente is not None:
        consulta = consulta + f" AND client='{cliente}'"
    if id_project!="" and id_project is not None:
        consulta = consulta + f" AND id_proyecto='{id_project}'"
        
    if consulta!="":
        consulta = consulta[4:]
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql(f"SELECT * FROM proyect.cbre_direcciones WHERE {consulta} " , con=db_connection)
    if data.empty is False:
        if 'latitud' in data:
            data['latitud'] = pd.to_numeric(data['latitud'],errors='coerce')
        if 'longitud' in data:
            data['longitud'] = pd.to_numeric(data['longitud'],errors='coerce')
        if 'latitud' in data and 'longitud' in data:
            idd  = (data['latitud'].notnull()) & (data['longitud'].notnull())
            data = data[idd]
    return data

@st.cache_data(show_spinner=False)
def get_timetravel_by_client(cliente):
    consulta = ""
    if cliente!="" and cliente is not None:
        consulta = consulta + f" client='{cliente}'"

    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql(f"SELECT id_proyecto as id_project ,tiempo_regreso,tiempo_ida FROM proyect.cbre_direcciones WHERE {consulta}  AND office_point=0" , con=db_connection)
    return data

@st.cache_data(show_spinner=False)
def get_shp_file():
    #gdf = gpd.read_file(r'D:\Dropbox\Empresa\CBRE\PROYECTO_DIRECCIONES\app_streamlit_online_version\data\barrios_colombia.shp')
    gdf = gpd.read_file(r'data/barrios_colombia.shp')
    
    gdf['wkt'] = gdf['geometry'].apply(lambda x: x.wkt)
    return gdf

def add_bg_from_url():
    st.markdown(
         f"""
         <style>
         .stApp {{
             background-image: url("https://s3.us-east-2.amazonaws.com/beyondcbre.co/Background-georreferenciacion.png");
             background-attachment: fixed;
             background-size: cover
         }}
         </style>
         """,
         unsafe_allow_html=True
     )

@st.cache_data(show_spinner=False)
def getdatadownload():
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query(f"SELECT * FROM {schema}.cbre_direcciones;" , engine)
    dataP    = pd.read_sql_query(f"SELECT * FROM {schema}.cbre_proyecto;" , engine)
    engine.dispose()
    
    dataP.rename(columns={'city':'project_city','address':'project_address','latitud':'project_latitude','longitud':'project_longitude','barriocatastral':'project_barrio'},inplace=True)
    variables  = [x for x in ['id', 'project', 'project_city', 'project_address', 'project_latitude', 'project_longitude', 'project_barrio'] if x in dataP]
    dataP      = dataP[variables]
    data.drop(columns=['id'],inplace=True)
    dataresult = data.merge(dataP,left_on='id_proyecto',right_on='id',how='left',validate='m:1')
    
    idd        = dataresult['user'].isin(['agavirja@gmail.com'])
    dataresult = dataresult[~idd]
    dataresult = dataresult[dataresult['office_point']==0]
    dataresult.drop(columns=['id'],inplace=True)
    dataresult.rename(columns={'scacodigo':'codigo_barrio'},inplace=True)
    return dataresult
    
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def download_excel(df):
    excel_file = df.to_excel('data_compelta.xlsx', index=False)
    with open('data_compelta.xlsx', 'rb') as f:
        data = f.read()
    st.download_button(
        label="Descargar Data",
        data=data,
        file_name='data_compelta.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    #csv        = convert_df(dataexport)
    #st.download_button(
    #    label="Descargar Data",
    #    data=csv,
    #    file_name='data_completa.csv',
    #    mime='text/csv',
    #)

@st.cache_data(show_spinner=False)
def data2geopandas(data):
    geojson   = pd.DataFrame().to_json()
    if 'geometry' in data: 
        data = data[data['geometry'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = pd.cut(data["tiempo_regreso"], bins=[0,10,30,60,300], labels=["#012A2D", "#80BBAD", "#DBD99A","#D1785C"])
        data['popup']    = None
        data.index       = range(len(data))
        for idd,items in data.iterrows():
            popuptext = ""
            try:    popuptext += f"""<b>Barrio:</b> {items['scanombre']}<br>"""
            except: pass
            try:    popuptext += f"""<b>Tiempo:</b> {items['tiempo_regreso']:,.1f} min<br>"""
            except: pass   
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                    {popuptext}
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        geojson = data.to_json()
    return geojson

def style_function_geojson(feature):
    color = feature['properties']['color']
    return {
        'fillColor': color,
        'color': color,
        'weight': 1,
        #'fillOpacity': 0.2,
    }

if __name__ == "__main__":
    main()