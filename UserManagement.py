import json
import boto3
import uuid
import base64
from datetime import datetime
from boto3.dynamodb.conditions import Key
import jwt
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('recipe-user')

def lambda_handler(event, context):
    
    http_method = event['httpMethod']
    headers = event.get('headers', {})
    
    authorization_header = headers.get('Authorization', '')
    
    if authorization_header:
        token=event['headers']['Authorization'].split(' ')[1] 
        decoded_token = jwt.decode(token, os.environ.get('secret_key'), algorithms=['HS256'])
        user_role = decoded_token.get('role')
      
    if http_method == 'POST':
        
            if not event['body'].strip():
                return {
                    'statusCode': 400,
                    'body': "Request body is empty"
                }
        
            data = json.loads(event['body'])
            
            # Check if data exists and if email and password are provided
            if not data or 'email' not in data or 'password' not in data:
                return {
                    'statusCode': 400,
                    'body': "Email and password are mandatory fields"
                }
            
            email = data.get('email')

           
            # Check if the email is already used
            response = table.query(
                IndexName='email-index',  # Assuming 'email' is a global secondary index
                KeyConditionExpression='email = :e',
                ExpressionAttributeValues={':e': email}
            )
            
            if response['Items']:
                return {
                    'statusCode': 400,
                    'body': json.dumps('Email already exists')
                }
                
                
            user_id = str(uuid.uuid4())
            current_datetime = datetime.now().isoformat()
            table.put_item(
                Item={
                    'user_id': user_id,
                    'email': data['email'],
                    'password': data['password'],
                    'first_name': data.get('first_name',""),
                    'last_name': data.get('last_name',""),
                    'confirmed_email': 'No',
                    'role':'User',
                    'created_at':current_datetime,
                    'updated_at':current_datetime
                }
            )
            return {
                'statusCode': 201,
                'body': json.dumps(f'{user_id} user created successfully!')
            }
    elif http_method == 'GET':
        if user_role != 'Admin':
            response = table.query(
                IndexName='email-index',  # Assuming 'email-index' is the name of the index on the 'email' attribute
                KeyConditionExpression=Key('email').eq(decoded_token.get('email'))
            )
            
            items = response.get('Items', [])
            if items:
                    return {
                        'statusCode': 200,
                        'body': json.dumps(items)
                    }
            else:
                    return {
                        'statusCode': 404,
                        'body': "User account not found"
                    }
        else:
            response = table.scan()
            items = response.get('Items', [])

            # Sort the items by createdAt in descending order
            sorted_items = sorted(items, key=lambda x: x['updated_at'], reverse=True)

            return {
                'statusCode': 200,
                'body': json.dumps(sorted_items)
            }
    elif http_method == 'PUT':
         if user_role != 'Admin':
            data = json.loads(event['body'])
            response = table.query(
                IndexName='email-index',  # Assuming 'email-index' is the name of the index on the 'email' attribute
                KeyConditionExpression=Key('email').eq(decoded_token.get('email'))
            )
            
            existing_user = response.get('Items', [])[0]
            current_datetime = datetime.now().isoformat()
            
            existing_user.update({
                    'email': data.get('email', existing_user.get('email')),
                    'first_name': data.get('first_name', existing_user.get('first_name')),
                    'last_name': data.get('last_name', existing_user.get('last_name')),
                    'password': data.get('password', existing_user.get('password')),
                    'updatedAt': current_datetime
                })
            
            table.put_item(Item=existing_user)
            return {
                    'statusCode': 200,
                    'body': json.dumps(f"{existing_user.get('user_id')}  updated successfully!")
                }
            
             
         else:
            data = json.loads(event['body'])
            user_id = headers.get('user_id')
             
            if not user_id:
                return {
                        'statusCode': 400,
                        'body': json.dumps('Missing id parameter in the URL path')
                }
            current_datetime = datetime.now().isoformat()
            
            # Check if the recipe with the provided ID exists
            existing_user = table.get_item(Key={'user_id': user_id}).get('Item')
            if not existing_user:
                return {
                        'statusCode': 404,
                        'body': json.dumps('User Id not found')
                }
            
            existing_user.update({
                    'email': data.get('email', existing_user.get('email')),
                    'first_name': data.get('first_name', existing_user.get('first_name')),
                    'last_name': data.get('last_name', existing_user.get('last_name')),
                    'password': data.get('password', existing_user.get('password')),
                    'role': data.get('role', existing_user.get('role')),
                    'confirmed_email': data.get('confirmed_email', existing_user.get('confirmed_email')),
                    'updatedAt': current_datetime
                })
            
            table.put_item(Item=existing_user)
            return {
                    'statusCode': 200,
                    'body': json.dumps(f"{existing_user.get('user_id')}  updated successfully!")
                }
    
    elif http_method == 'DELETE':
        if user_role != 'Admin':
            return {
                'statusCode': 401,
                'body': "Not Authorized"
            }
        else:
            user_id = headers.get('user_id')
            if not user_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps('Missing id parameter in the URL path')
                }
            user = table.get_item(Key={'user_id': user_id}).get('Item', {})
            table.delete_item(
                Key={'user_id': user_id}
            )
            return {
                'statusCode': 200,
                'body': json.dumps(f"{user.get('email', 'User')} is deleted successfully!")
            }
    
