import streamlit as st

import re
import pandas as pd
import requests
import pytz
import pymysql as sql
import datetime
import random
import streamlit.components.v1 as components
#import warnings
#warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")

user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
schema   = st.secrets["schema"]
api_key  = st.secrets['API_KEY']

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
        response   = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?address={direccion}&key={api_key}').json()
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


col1, col2 = st.columns(2)
with col1: 
    components.html("""
    <!DOCTYPE html>
    <html>

    <head>
      <title>Medición de distancias</title>
      <meta charset="UTF-8">

      <!-- CSS only -->
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/css/bootstrap.min.css" rel="stylesheet"
        integrity="sha384-gH2yIJqKdNHPEq0n4Mqa/HGKIhSkIHeL5AyhkYV8i59U5AR6csBvApHHNl/vI1Bx" crossorigin="anonymous">
    </head>

    <body>
      <div id="app">
        <img id="logo" src="https://traveltimeproject-cbre-website.s3.us-east-2.amazonaws.com/CBRE_logo_white_BG.png"
          alt="CBRE">
        <div class="container">
          <div class="row">
            <div class="col-lg-6">
              <div class="row" id="title">
                <h1>Crear proyecto en el aplicativo</h1>
                <hr />
              </div>
            </div>
          </div>
        </div>
      </div>
      <script src="https://unpkg.com/vue@1.0.28/dist/vue.js"></script>
      <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
      <!-- JavaScript Bundle with Popper -->
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/js/bootstrap.bundle.min.js"
        integrity="sha384-A3rJD856KowSb7dwlZdYEkO39Gagi7vIsF0jrRAoQmDKKtQBHUuLZ9AsSv4jD4Xa"
        crossorigin="anonymous"></script>
      <script>
        const MAX_IMAGE_SIZE = 1000000

        /* ENTER YOUR ENDPOINT HERE */

        new Vue({
          el: "#app",
          data: {
            file: '',
            uploadURL: '',
            projects: {},
            darkGreen: "#003F2D"
          },
          created: async function () {
            console.log("Renderizado al comienzo")
            const response = await axios({
                method:'POST',
                url:'https://h9qoq467cl.execute-api.us-east-2.amazonaws.com/default/getProjectsCBRE'})
                projects = response.data
                projects.forEach(element => {
                  opt = document.createElement("option");
                  opt.innerHTML =element.address
                  opt.value = element.project
                  document.getElementById("projectsList").appendChild(opt)
                });
              
          },
          methods: {
            clickDowloadTemplate(e){
              document.getElementById("downloadTempalte").style.backgroundColor="#80BBAD"
              document.getElementById("downloadTempalte").style.borderColor="#80BBAD"
            },
            onProjectChange(e){
              valor = document.getElementById("project").value
              result= projects.filter( proj => proj.project === valor)
              document.getElementById("city").value = result[0].city
              document.getElementById("address").value = result[0].address
              
            },
            onFileChange(e) {
              let files = e.target.files || e.dataTransfer.files
              if (!files.length) return
              this.createFile(files[0])
            },
            createFile(file) {
              // var image = new Image()
              let reader = new FileReader()
              reader.onload = (e) => {
                if (!e.target.result.includes('data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')) {
                  return alert('Wrong file type - Excel 2007 o superior')
                }
                if (e.target.result.length > MAX_IMAGE_SIZE) {
                  return alert('File is loo large.')
                }
                this.file = e.target.result
              }
              reader.readAsDataURL(file)
            },
            uploadFile: async function (e) {
              // Style
              document.getElementById("submitButton").disabled= true
              message = document.createElement("h5")
              message.innerHTML = "Cargando archivo... Por favor espere un momento"
              message.style.color ="#003F2D"
              parent = document.getElementById("formSection").appendChild(message);

              document.getElementById("submitButton").style.backgroundColor="#80BBAD"
              document.getElementById("submitButton").style.borderColor="#80BBAD"
              // Get the presigned URL
              const response = await axios({
                method:'POST',
                url:'https://h9qoq467cl.execute-api.us-east-2.amazonaws.com/default/uploadAddressesCBRE',
                data: JSON.stringify({
                  'project': document.getElementById("project").value,
                  'city': document.getElementById("city").value,
                  'address': document.getElementById("address").value,
                  'customer': document.getElementById("customer").value,
                  'email': document.getElementById("email").value,
                  'nit': document.getElementById("nit").value
                })
              })
              console.log(response)
              let binary = atob(this.file.split(',')[1])
              let array = []
              for (var i = 0; i < binary.length; i++) {
                array.push(binary.charCodeAt(i))
              }
              let blobData = new Blob([new Uint8Array(array)], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
              const result = await fetch(response.data.url, {
                method: 'PUT',
                body: blobData,
                headers: {
                  'x-amz-meta-customer': document.getElementById("customer").value,
                  'x-amz-meta-email': document.getElementById("email").value,
                  'x-amz-meta-nit': document.getElementById("nit").value,
                  'x-amz-meta-project': document.getElementById("project").value,
                }
              }).then( x => {
                if(response.status===200){
                  alert("El archivo se ha enviado correctamente. Pronto recibira los resultados en su correo.");
                }
                else{
                  alert("Oops ha habido un problema. Por favor refresque el navegador y cargue el archivo de nuevo.");
                }
              })
            }
          }
        })
      </script>
      <style type="text/css">
        body {
          background: #ffffff;
          padding: 20px;
        }

        button {
          color: #80BBAD;
        }

        h1 {
          font-size: 2rem;
          color: #17E88F;
          margin-bottom: 2rem;
        }

        h2 {
          font-size: 1.5rem;
          font-weight: bold;
          margin-bottom: 15px;
        }

        hr {
          width: 60% !important;
          height: 5px;
          background-color: #003F2D;
          border: 0 none;
          opacity: 1;
          margin-bottom: 2rem;
        }

        a {
          color: #42b983;
        }

        .form-label {
          margin-bottom: 0rem;
        }

        .btn-primary,
        .btn-primary:hover,
        .btn-primary:active,
        .btn-primary:visited {
          border-color: #003F2D ;
          background-color: #003F2D ;
        }
        

        #title {
          margin-top: 3rem;
        }

        #formSection {
          background-image: url("https://traveltimeproject-cbre-website.s3.us-east-2.amazonaws.com/FONDO-CUADRITO.jpg");
          background-size: cover;
          padding-top: 4.5rem;
          padding-left: 5rem;
          padding-right: 5rem;
          padding-bottom: 4.5rem;
        }

        #dashboarButton{
          margin-top: 140px;
          width: 150px;
          border-color: #003F2D !important;
          background-color: #003F2D !important;
        }


        #templateDownload{
          width: 170px;
          border-color: #003F2D !important;
          background-color: #003F2D !important;
        }
        

        #dataForm {
          margin-left: 50%;
        }

        #logo {
          height: 50px;
        }
      </style>
    </body>

    </html>
    """,height=600)
    
with col2:
    ciudad_registro            = st.selectbox('Ciudad ',options=['Bogota'])
    nombre_proyecto_registro   = st.text_input('Nombre del proyecto ',value="")
    direccion_oficina_registro = st.text_input('Dirección del proyecto ',value="")
    if nombre_proyecto_registro!="" and direccion_oficina_registro!="":
        result_button = st.button('Crear proyecto')
        if result_button:
            inputvar  = {'project':nombre_proyecto_registro.title(),'city':ciudad_registro,'address':direccion_oficina_registro}
            put_project(inputvar)
            st.success("Proyecto guardado exitosamente")
            st.cache_data()
            st.rerun()
            st.success("Proyecto guardado exitosamente")