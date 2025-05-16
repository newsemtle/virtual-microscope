import logging

from django.contrib.auth import login, logout
from django.contrib.auth.models import Group
from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.serializers import LoginSerializer
from apps.accounts.models import GroupProfile

logger = logging.getLogger("django")


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            login(request, user)
            logger.info(f"User '{user}' logged in. (IP: {request.META['REMOTE_ADDR']})")
            return Response({"detail": _("Login successful.")}, status=200)
        return Response(serializer.errors, status=400)


class LogoutAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        logout(request)
        logger.info(f"User '{user}' logged out. (IP: {request.META['REMOTE_ADDR']})")
        return Response({"detail": _("Logout successful.")}, status=200)


class SessionExtendAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        request.session.modified = True
        expire = request.session.get_expiry_date().isoformat()
        return Response({"expire": expire}, status=200)


class SessionTimeAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        expire = request.session.get_expiry_date().isoformat()
        return Response({"expire": expire}, status=200)


class PublishersAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not request.user.is_admin() and not request.user.is_publisher():
            return Response(
                {"detail": _("You don't have permission to view publishers.")},
                status=403,
            )

        publisher_groups = Group.objects.filter(
            profile__type=GroupProfile.Type.PUBLISHER
        )
        publishers_by_group = [
            {
                "id": group.id,
                "name": group.name,
                "users": [
                    {
                        "id": user.id,
                        "username": user.username,
                        "full_name": user.get_full_name(),
                    }
                    for user in group.user_set.all()
                ],
            }
            for group in publisher_groups
        ]
        return Response(publishers_by_group, status=200)
