import json
import boto3
import jwt
import datetime
import os

def lambda_handler(event, context):
    
    headers = event.get('headers', {})
    email = headers.get('email')
    password = headers.get('password')
     
    # Check credentials against DynamoDB table
    user = check_credentials(email, password)
    
    if user:
        # Check if the email is confirmed
        if user.get('confirmed_email', 'No') == 'Yes':
            # Email is confirmed, proceed with login
            # User authenticated, generate JWT token
            payload = {
                'email': email,
                'role': user.get('role'),
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)  # Token expiration time
            }
            
            secret_key = os.environ.get('secret_key') 
            
            token = jwt.encode(payload, secret_key, algorithm='HS256')
            
            # Return the token in the response
            return {
                'statusCode': 200,
                'body': json.dumps({'token': token})
            }
        else:
            # Email is not confirmed, deny login
            return {
                'statusCode': 401,
                'body': json.dumps({'error':'Email not confirmed. Please confirm your email before logging in.'})
            }
    else:
        # Invalid credentials
        return {
            'statusCode': 401,
            'body': json.dumps({'error':'Invalid email or password. Please check your credentials and try again.'})
        }
    
def check_credentials(email, password):
    # Connect to DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('recipe-user')  # Replace 'login' with your actual table name

    # Scan DynamoDB table for the provided username and password
    response = table.scan(
        FilterExpression='email = :u and password = :p',
        ExpressionAttributeValues={
            ':u': email,
            ':p': password
        }
    )

    # Check if a matching record was found
    if len(response['Items']) > 0:
        return response['Items'][0]  # Return the user data
    else:
        return None  # User not found or invalid credentials
