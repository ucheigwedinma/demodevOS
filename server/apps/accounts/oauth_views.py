from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .oauth_serializers import OAuthAuthorizeSerializer, OAuthCallbackSerializer
from .throttles import AuthRateThrottle


class OAuthAuthorizeView(generics.CreateAPIView):
    serializer_class = OAuthAuthorizeSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class OAuthCallbackView(generics.CreateAPIView):
    serializer_class = OAuthCallbackSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = serializer.save()
        return Response(tokens, status=status.HTTP_200_OK)
