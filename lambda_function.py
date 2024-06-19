import sys
sys.path.append('dependencies')
import os
import boto3
import json
import qrcode
from qrcode_xcolor import XStyledPilImage, XGappedSquareModuleDrawer, XRoundedModuleDrawer
from io import BytesIO
import uuid
import datetime

uuid = uuid.uuid4()
datetime = datetime.datetime.now()

# Clients
S3_CLIENT = boto3.client('s3')
DYNAMODB_CLIENT = boto3.client('dynamodb')
# Constants
BUCKET_NAME = os.environ['BUCKET_NAME']
FOLDER_NAME = os.environ['FOLDER_NAME']
DYNAMODB_TABLE_NAME = os.environ['DYNAMODB_TABLE_NAME']

FILE_NAME = f'{str(uuid)}-qr-code.png'
S3_KEY = f'{FOLDER_NAME}/{FILE_NAME}'

def lambda_handler(event, context):
    try:
        event_body = json.loads(event['body'])
        print('Event: ', event_body)

        img = generate_qr_code(event_body)
        save_file_s3(img, BUCKET_NAME, S3_KEY)
        presigned_url = generate_presigned_url(BUCKET_NAME, S3_KEY)
        put_data_dynamodb(event_body)

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

def save_file_s3(img, bucket_name, s3_key):
    buffered = BytesIO()
    img.save(buffered, format='PNG')
    buffered.seek(0)
    S3_CLIENT.upload_fileobj(buffered, bucket_name, s3_key)
    
def put_data_dynamodb(event_body):
    item = {
        'id': {'S': str(uuid)},
        'file_name': {'S': str(FILE_NAME)},
        'request_data': {'M': {key: {'S': str(value)} for key, value in event_body.items()}},
        'timestamp': {'S': str(datetime)}
    }
    response = DYNAMODB_CLIENT.put_item(TableName=DYNAMODB_TABLE_NAME, Item=item)
    
def generate_presigned_url(bucket_name, s3_key):
    url = S3_CLIENT.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': s3_key},
        ExpiresIn=3600  # Expiracion (1 hora)
    )
    return url

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


