from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from .models import  MainCurrency, MainRoutesName
from .serializers import  MainCurrencySerializer, MainRoutesNameSerializer
# Create your views here.

class MainCurrencyListView(APIView):
    """List all main currencies"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        currencies = MainCurrency.objects.all().order_by('name')
        serializer = MainCurrencySerializer(currencies, many=True)
        
        return Response({
            'message': 'Main currencies retrieved successfully.',
            'data': serializer.data
        })

class MainCurrencyCreateView(APIView):
    """Create a new main currency"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = MainCurrencySerializer(data=request.data)
        if serializer.is_valid():
            currency = serializer.save()
            return Response({
                'message': 'Main currency created successfully.',
                'data': MainCurrencySerializer(currency).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Failed to create main currency.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class MainCurrencyDetailView(APIView):
    """Retrieve a specific main currency"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return MainCurrency.objects.get(pk=pk)
        except MainCurrency.DoesNotExist:
            return None
    
    def get(self, request, pk):
        currency = self.get_object(pk)
        if currency is None:
            return Response({
                'message': 'Main currency not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = MainCurrencySerializer(currency)
        return Response({
            'message': 'Main currency details retrieved successfully.',
            'data': serializer.data
        })

class MainCurrencyUpdateView(APIView):
    """Update a specific main currency"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return MainCurrency.objects.get(pk=pk)
        except MainCurrency.DoesNotExist:
            return None
    
    def put(self, request, pk):
        currency = self.get_object(pk)
        if currency is None:
            return Response({
                'message': 'Main currency not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = MainCurrencySerializer(currency, data=request.data)
        if serializer.is_valid():
            updated_currency = serializer.save()
            return Response({
                'message': 'Main currency updated successfully.',
                'data': MainCurrencySerializer(updated_currency).data
            })
        return Response({
            'message': 'Failed to update main currency.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class MainCurrencyDeleteView(APIView):
    """Delete a specific main currency"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return MainCurrency.objects.get(pk=pk)
        except MainCurrency.DoesNotExist:
            return None
    
    def delete(self, request, pk):
        currency = self.get_object(pk)
        if currency is None:
            return Response({
                'message': 'Main currency not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        currency.delete()
        return Response({
            'message': 'Main currency deleted successfully.'
        }, status=status.HTTP_204_NO_CONTENT)


# MainRoutesName views
class MainRoutesNameListView(APIView):
    """List all main routes names"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        routes = MainRoutesName.objects.all().order_by('english_name')
        serializer = MainRoutesNameSerializer(routes, many=True)
        
        return Response({
            'message': 'Main routes names retrieved successfully.',
            'data': serializer.data
        })

class MainRoutesNameCreateView(APIView):
    """Create a new main routes name"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = MainRoutesNameSerializer(data=request.data)
        if serializer.is_valid():
            route = serializer.save()
            return Response({
                'message': 'Main routes name created successfully.',
                'data': MainRoutesNameSerializer(route).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Failed to create main routes name.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class MainRoutesNameDetailView(APIView):
    """Retrieve a specific main routes name"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return MainRoutesName.objects.get(pk=pk)
        except MainRoutesName.DoesNotExist:
            return None
    
    def get(self, request, pk):
        route = self.get_object(pk)
        if route is None:
            return Response({
                'message': 'Main routes name not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = MainRoutesNameSerializer(route)
        return Response({
            'message': 'Main routes name details retrieved successfully.',
            'data': serializer.data
        })

class MainRoutesNameUpdateView(APIView):
    """Update a specific main routes name"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return MainRoutesName.objects.get(pk=pk)
        except MainRoutesName.DoesNotExist:
            return None
    
    def put(self, request, pk):
        route = self.get_object(pk)
        if route is None:
            return Response({
                'message': 'Main routes name not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = MainRoutesNameSerializer(route, data=request.data)
        if serializer.is_valid():
            updated_route = serializer.save()
            return Response({
                'message': 'Main routes name updated successfully.',
                'data': MainRoutesNameSerializer(updated_route).data
            })
        return Response({
            'message': 'Failed to update main routes name.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class MainRoutesNameDeleteView(APIView):
    """Delete a specific main routes name"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return MainRoutesName.objects.get(pk=pk)
        except MainRoutesName.DoesNotExist:
            return None
    
    def delete(self, request, pk):
        route = self.get_object(pk)
        if route is None:
            return Response({
                'message': 'Main routes name not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        route.delete()
        return Response({
            'message': 'Main routes name deleted successfully.'
        }, status=status.HTTP_204_NO_CONTENT)

