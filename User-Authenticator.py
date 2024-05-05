import json
import jwt
import os

def lambda_handler(event, context):
    
    authorization_header = event.get('authorizationToken', '')
    
    if not authorization_header.startswith('Bearer '):
        raise ValueError('Invalid Authorization header format')
        
    token = authorization_header.split(' ')[1]
    
    try:
        # Decode and verify JWT token
        decoded_token = jwt.decode(token, os.environ.get('secret_key'), algorithms=['HS256'])
        user_id = decoded_token.get('email')
        
        if not user_id:
            return generate_policy('user', 'Deny', event['methodArn'], "Invalid token")
        
        
        # Assuming all authenticated users have access
        return generate_policy(user_id, 'Allow', event['methodArn'])
    except jwt.ExpiredSignatureError:
        return generate_policy('user', 'Deny', event['methodArn'], "Token has expired")
    except jwt.InvalidTokenError:
        return generate_policy('user', 'Deny', event['methodArn'], "Invalid token")


def generate_policy(principal_id, effect, resource, message=None):
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        }
    }
    if message:
        policy['context'] = {'message': message}
    return policy