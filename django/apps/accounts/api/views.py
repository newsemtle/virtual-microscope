import logging

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import GroupProfile

logger = logging.getLogger("django")


class LoginAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        form = AuthenticationForm(request, data=request.data)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info(f"User '{user}' logged in. (IP: {request.META['REMOTE_ADDR']})")
            return Response({"detail": "Login successful."}, status=status.HTTP_200_OK)

        # normalize errors to match DRF's default format
        errors = form.errors.get_json_data()
        response_errors = {}
        for key, value in errors.items():
            messages = [err["message"] for err in value]
            if key == "__all__":
                response_errors["non_field_errors"] = messages
            else:
                response_errors[key] = messages

        return Response(response_errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        logout(request)
        logger.info(f"User '{user}' logged out. (IP: {request.META['REMOTE_ADDR']})")
        return Response({"detail": "Logout successful."}, status=status.HTTP_200_OK)


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
                {"detail": "You don't have permission to view publishers."}, status=403
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
                        "full_name": user.get_korean_name(),
                    }
                    for user in group.user_set.all()
                ],
            }
            for group in publisher_groups
        ]
        return Response(publishers_by_group, status=200)
