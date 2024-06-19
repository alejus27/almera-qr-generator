import sys
sys.path.append('dependencies')
import os
import boto3
import json
import qrcode
from qrcode_xcolor import XStyledPilImage, XGappedSquareModuleDrawer, XRoundedModuleDrawer
from io import BytesIO
import datetime
import uuid

# Clients
S3_CLIENT = boto3.client('s3')
DYNAMODB_CLIENT = boto3.client('dynamodb')

# Constants
BUCKET_NAME = os.environ['BUCKET_NAME']
FOLDER_NAME = os.environ['FOLDER_NAME']
DYNAMODB_TABLE_NAME = os.environ['DYNAMODB_TABLE_NAME']

def lambda_handler(event, context):
    try:
        event_body = json.loads(event['body'])
        print('Event: ', event_body)

        uuid_str = str(uuid.uuid4())  
        timestamp_str = str(datetime.datetime.now()) 

        img = generate_qr_code(event_body)
        save_file_s3(img, BUCKET_NAME, FOLDER_NAME, uuid_str)
        presigned_url = generate_presigned_url(BUCKET_NAME, FOLDER_NAME, uuid_str)
        put_data_dynamodb(event_body, uuid_str, timestamp_str)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Se ha generado el codigo QR de manera exitosa', 'url': presigned_url})
        }
        
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Error procesando la peticion'})
        }

def generate_qr_code(event_body):
    qr = qrcode.QRCode(
        box_size=event_body.get('box_size'),
        border=event_body.get('border'),
    )
    qr.add_data(event_body.get('content'))

    img = qr.make_image(
        image_factory=XStyledPilImage,
        back_color=hex_to_rgb(event_body.get('background_color')), 
        module_drawer=XGappedSquareModuleDrawer(
            front_color=hex_to_rgb(event_body.get('dots_color'))
        ),
        eye_drawer=XRoundedModuleDrawer(
            front_color=hex_to_rgb(event_body.get('marker_border_color')),
            inner_eye_color=hex_to_rgb(event_body.get('marker_center_color'))
        ),
        embeded_image_path='resources/logo.png'
    )
    return img

def save_file_s3(img, bucket_name, folder_name, uuid_str):
    file_name = f'{uuid_str}-qr-code.png'
    s3_key = f'{folder_name}/{file_name}'

    buffered = BytesIO()
    img.save(buffered, format='PNG')
    buffered.seek(0)
    S3_CLIENT.upload_fileobj(buffered, bucket_name, s3_key)
    
def put_data_dynamodb(event_body, uuid_str, timestamp_str):
    item = {
        'id': {'S': uuid_str},
        'file_name': {'S': f'{uuid_str}-qr-code.png'},
        'request_data': {'M': {key: {'S': str(value)} for key, value in event_body.items()}},
        'timestamp': {'S': timestamp_str}
    }
    response = DYNAMODB_CLIENT.put_item(TableName=DYNAMODB_TABLE_NAME, Item=item)
    
def generate_presigned_url(bucket_name, folder_name, uuid_str):
    s3_key = f'{folder_name}/{uuid_str}-qr-code.png'
    url = S3_CLIENT.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': s3_key},
        ExpiresIn=3600  # Expiracion (1 hora)
    )
    return url

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


