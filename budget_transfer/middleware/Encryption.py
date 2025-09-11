from django.utils.deprecation import MiddlewareMixin
from cryptography.fernet import Fernet
import base64
import os
import json
from django.http import JsonResponse

class EncryptionMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        # Generate or use a pre-existing key
        self.key = os.getenv('FIELD_ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher_suite = Fernet(self.key)
    
    def process_response(self, request, response):
        # Skip encryption for certain paths
        skip_paths = ['/admin/', '/api/docs/', '/swagger/']
        if any(request.path.startswith(path) for path in skip_paths):
            return response
            
        # Only encrypt if the response is JSON
        if hasattr(response, 'content') and isinstance(response.content, bytes):
            try:
                # Get the original content
                content = response.content
                
                # If it's JSON response, we'll structure our encrypted response
                if response.get('Content-Type', '').startswith('application/json'):
                    try:
                        # Try to parse JSON to ensure it's valid
                        json_data = json.loads(content.decode('utf-8'))
                        
                        # Encrypt the entire JSON string
                        encrypted_data = self.cipher_suite.encrypt(content)
                        
                        # Create a structured response with base64 encoded data
                        structured_response = {
                            'status': 'success',
                            'encrypted': True,
                            'data': base64.b64encode(encrypted_data).decode('utf-8'),
                            # 'algorithm': 'AES-256-Fernet'
                        }
                        
                        # Convert to JSON response
                        response = JsonResponse(structured_response)
                        response['X-Content-Encrypted'] = 'True'
                        return response
                        
                    except json.JSONDecodeError:
                        # If not JSON, proceed with regular encryption
                        pass
                
                # For non-JSON responses, do standard encryption
                encrypted_content = self.cipher_suite.encrypt(content)
                
                # Base64 encode for better transmission
                encoded_content = base64.b64encode(encrypted_content)
                
                # Set the response content
                response.content = encoded_content
                
                # Set appropriate headers
                response['Content-Type'] = 'text/plain'
                response['X-Content-Encrypted'] = 'True'
                response['X-Encryption-Method'] = 'Fernet'
                
            except Exception as e:
                # Return error information in development
                if os.getenv('DJANGO_DEBUG', 'False') == 'True':
                    error_response = {
                        'status': 'error',
                        'message': 'Encryption failed',
                        'error': str(e)
                    }
                    return JsonResponse(error_response, status=500)
                
        return response