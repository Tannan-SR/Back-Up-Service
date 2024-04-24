import os
from urllib import response
import pickle5 as pickle
import google.oauth2.credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
import requests
import io
import logging

log_file = 'log.txt'
if not os.path.exists(log_file):
    open(log_file, 'a').close()  

logging.basicConfig(filename=log_file, level=logging.INFO, filemode='a')



SCOPES = ['https://www.googleapis.com/auth/drive.file']
API_KEY = 'AIzaSyCptvgJb2stpfMY5w2PSbR954ZjZtayxlE'

CLIENT_ID = '156984617325-bji3k2kihlj8s1mhvnp364kgnq702h24.apps.googleusercontent.com'
CLIENT_SECRET = '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'

def authenticate():
    cred = None
    #token_file = 'backend/token.pickle'
    token_file = 'token.pickle'
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            cred = pickle.load(token)
    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())	
        else:
            flow = InstalledAppFlow.from_client_config({
                'installed': {
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uris': ['urn:ietf:wg:oauth:2.0:oob'],
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://accounts.google.com/o/oauth2/token'
                }
            }, SCOPES)
            cred = flow.run_local_server(host='localhost', port=8080)
        with open(token_file, 'wb') as token:
            pickle.dump(cred, token)
    return cred




def get_access():
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds, developerKey=API_KEY)
    return creds,service

def list_files_in_drive(service,folder_id):
    query=f"'{folder_id}' in parents and trashed=false"

    results = service.files().list(
        pageSize=10, q=query,fields="nextPageToken, files(id, name)").execute()

    items = results.get('files', [])
    if not items:
        #print('No files found.')
        return []
    else:
        
        # for item in items:
        #     print(u'{0} ({1})'.format(item['name'], item['id']))
            
        return items





def upload_file(service):
    url='https://www.googleapis.com/upload/drive/v3/files?uploadType=media'
    file_path='new_dummy.txt'
    access_token = service._http.credentials.token
    with open(file_path, "rb") as file:
        file_data = file.read()
    headers={
        "Authorization": "Bearer {}".format(access_token),
        "Content-Type":"text/plain",
        "Content-Length":str(len(file_data))
    }
    response=requests.post(url,data=file_data,headers=headers)
    #print(response.text,response.status_code)
    logging.info(f"Uploaded file {file_path}. Status code: {response.status_code}")

    

def upload_files_dir(dir_path,service,parents):
    for filename in os.listdir(dir_path):
        file_path=os.path.join(dir_path,filename)
        if os.path.isfile(file_path):
            #print("File path:", file_path)
            file_metadata={
                'name':file_path,
                'mimetype':'text/plain',
                'parents':[parents]
            }
            upload_file_multipart(service,file_metadata)
        
        else:
            raise Exception("The file ",file_path,"doesnt exist")


def create_folder(service,folder_metadata):
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')


def upload_file_multipart(service, metadata):
    #print("im here" + metadata['name'])

    file_path = metadata['name']
    filename=file_path.split("/")[-1]

    print("Got file ",filename)
    print(metadata['parents'])
    files_in_dir=list_files_in_drive(service,metadata['parents'][0])
    
    #print("Files in dir->",files_in_dir)
    media = MediaFileUpload(file_path, mimetype=metadata['mimetype'])
    file_metadata = {
        'name': filename,
        'parents': metadata.get('parents', [])
    }
    #print(file_metadata['parents'])
    flag=0
    if not files_in_dir:
        file=service.files().create(body=file_metadata,media_body=media).execute()
        #print("File written")
        logging.info(f"{filename} written")

    else:
        other_files=list_files_in_drive(service,metadata['parents'][0])
        for f in other_files:
            print("Current file->",f['name'])
            if f['name']==filename:
                #update
                file=service.files().update(fileId=f['id'],body=None,media_body=media).execute()
                print("This file exists hence updated")
                logging.info(f"{filename} exists hence updated")
                flag=1
        if flag==0:
            #print(f"This file {filename} hasnt been created yet")
            file=service.files().create(body=file_metadata,media_body=media).execute()
            logging.info(f"{filename} written")
    return 1
    

def download_files(creds,service,folder):
    items=list_files_in_drive(creds,service,folder)
    for item in items:
        file_name=item['name']
        req=service.files().get_media(fileId=item['id'])
        file = io.BytesIO()
        downloader=MediaIoBaseDownload(file,req)
        done=False
        while not done:
            status,done=downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}.")
        with open(file_name,'wb') as f:
            f.write(file.getvalue())
        print(f"File {file_name} downloaded succesfully")



if __name__ == '__main__':
    creds,service=get_access()
    dir_in_drive='18DCdiVv0URxoYJdKyB_fl4b86V5s32sx'
    upload_files_dir("Folder",service,dir_in_drive)
    #list_files_in_drive(service,dir_in_drive)

    #download_files(creds,service,dir_in_drive)
