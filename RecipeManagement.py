import json
import boto3
import jwt
import os
import uuid
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Recipe')

def lambda_handler(event, context):
    
    print(event)
    
    http_method = event['httpMethod']
    
    token=event['headers']['Authorization'].split(' ')[1]
    decoded_token = jwt.decode(token, os.environ.get('secret_key'), algorithms=['HS256'])
    user_role = decoded_token.get('role')
    print(user_role)
    
    print(token)
    
    if http_method == 'GET':
        response = table.scan()
        items = response.get('Items', [])
        
        # Convert Decimal objects to float
        for item in items:
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = float(value)
        
        # Sort the items by updatedAt in descending order
        sorted_items = sorted(items, key=lambda x: x.get('updatedAt', 0), reverse=True)
        
        return {
            'statusCode': 200,
            'body': json.dumps(sorted_items, default=convert_decimal)
        }
    elif http_method == 'POST':
        if user_role != 'Admin':
            return {
                'statusCode': 401,
                'body': "Not Authorized"
            }
        else:
            data = json.loads(event['body'])
            id = str(uuid.uuid4())
            current_datetime = datetime.now().isoformat()
            
            table.put_item(
                Item={
                    'ID': id,
                    'title': data['title'],
                    'description': data['description'],
                    'ingredients': data['ingredients'],
                    'instructions': data['instructions'],
                    'prepTime': data['prepTime'],
                    'cookTime': data['cookTime'],
                    'servings': data['servings'],
                    'createdAt': current_datetime,
                    'updatedAt': current_datetime
                }
            )
            
            return {
                'statusCode': 201,
                'body': json.dumps(f"{data['title']} recipe created successfully!")
            }
    elif http_method == 'DELETE':
        if user_role != 'Admin':
            return {
                'statusCode': 401,
                'body': "Not Authorized"
            }
        else:
            
            headers = event.get('headers', {})
            id = headers.get('recipe_id')
            
            if not id:
                return {
                    'statusCode': 400,
                    'body': json.dumps('Missing id parameter in the URL path')
                }
            # Delete the associated image from S3
            recipe = table.get_item(Key={'ID': id}).get('Item', {})
            table.delete_item(
                Key={'ID': id}
            )
            return {
                'statusCode': 200,
                'body': json.dumps(f"{recipe.get('title', 'Recipe')} is deleted successfully!")
            }
    elif http_method == 'PUT':
        if user_role != 'Admin':
            return {
                'statusCode': 401,
                'body': "Not Authorized"
            }
        else:
            try:
                data = json.loads(event['body'])
                headers = event.get('headers', {})
                id = headers.get('recipe_id')
                
                if not id:
                    return {
                        'statusCode': 400,
                        'body': json.dumps('Missing id parameter in the URL path')
                    }
                current_datetime = datetime.now().isoformat()
                
                # Check if the recipe with the provided ID exists
                existing_recipe = table.get_item(Key={'ID': id}).get('Item')
                if not existing_recipe:
                    return {
                        'statusCode': 404,
                        'body': json.dumps('Recipe not found')
                    }
                
                # Convert float data to Decimal
                data = convert_float_to_decimal(data)
                
                # Update the recipe attributes
                existing_recipe.update({
                    'title': data.get('title', existing_recipe.get('title')),
                    'description': data.get('description', existing_recipe.get('description')),
                    'ingredients': data.get('ingredients', existing_recipe.get('ingredients')),
                    'instructions': data.get('instructions', existing_recipe.get('instructions')),
                    'prepTime': data.get('prepTime', existing_recipe.get('prepTime')),
                    'cookTime': data.get('cookTime', existing_recipe.get('cookTime')),
                    'servings': data.get('servings', existing_recipe.get('servings'))
                })
                
                # Put the updated recipe into DynamoDB
                table.put_item(Item=existing_recipe)
                
                return {
                    'statusCode': 200,
                    'body': json.dumps(f"{existing_recipe.get('title')} recipe updated successfully!")
                }
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'body': json.dumps('Invalid JSON format in the request body')
                }
        
    
        
        
def convert_decimal(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return obj 
    
def convert_float_to_decimal(data):
    if isinstance(data, float):
        return Decimal(str(data))
    elif isinstance(data, dict):
        return {key: convert_float_to_decimal(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_float_to_decimal(item) for item in data]
    else:
        return data
    