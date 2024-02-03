import json

from jose import jwt, JWTError

from django_redis import get_redis_connection

from rest_framework import authentication
from rest_framework import exceptions

from core import settings
from user.models import IAMUser, IAMAdmin


class NotAuthenticatedException:
    pass


def extract_access_token(request):
    return (request.META.get('HTTP_AUTHORIZATION').replace('Bearer ', ''
                                                           ) if request.META.get('HTTP_AUTHORIZATION').startswith(
        'Bearer '
    ) else request.META.get('HTTP_AUTHORIZATION'))


class UserJWTAuthentication(authentication.BaseAuthentication):
    """
    Overrides request.user instance on every request if you provide this authetnication for a view.
    replace djangos standard builtin user with a dummy user object which represents the user in 
    IAM application and will not be persisted in database.(IAMUser model is used only as a data container)

    Token is authenticated using redis(queried for session existance)
    """

    def authenticate(self, request):
        try:
            if not request.META.get('HTTP_AUTHORIZATION'):
                return None
            # extract the token from request headers
            jwt_token = extract_access_token(request)
            # decode and validate the jwt token
            settings.USER_RSA_PUBLIC_KEY = settings.USER_RSA_PUBLIC_KEY.replace(r"\n", "\n")
            payload = jwt.decode(
                jwt_token,
                settings.USER_RSA_PUBLIC_KEY,
                algorithms=settings.JWT_ENCRYPTION_ALGORITHM
            )
            with get_redis_connection() as redis_conn:
                # check the redis to find the extracted session(if the session
                # is valid it must be found in the redis index)
                user_data = redis_conn.get(f"user:{payload['session']}")

            if not user_data:
                raise Exception("session not found in redis")
            # load the user data from redis and create a data container for the 
            # user data so we can set this object on the request.user attribute
            user_data = json.loads(user_data)
            user = IAMUser(
                owner_id=user_data["id"],
                authentication_level=user_data["authentication_level"],
                is_authenticated=True
            )
            return (user, None)
        except (KeyError, IndexError, JWTError, Exception) as exc:
            print("1", exc.args)
            raise exceptions.AuthenticationFailed("Not authenticated")

    def authenticate_header(self, request):
        return "Bearer"


class AdminJWTAuthentication(authentication.BaseAuthentication):
    """
    it has the same purpose as user authentication backend but handles
    the admin authentication
    """
    def authenticate(self, request):
        try:
            jwt_token = extract_access_token(request)
            payload = jwt.decode(
                jwt_token,
                settings.ADMIN_RSA_PUBlIC_KEY,
                algorithms=settings.JWT_ENCRYPTION_ALGORITHM
            )
            with get_redis_connection() as redis_conn:
                admin_data = redis_conn.get(f"admin:{payload['session']}")

            if not admin_data:
                raise Exception("session not found in redis")
            admin_data = json.loads(admin_data)
            admin = IAMAdmin(
                owner_id=admin_data["id"],
                role=admin_data["role"],
                actions=admin_data["actions"],
                is_authenticated=True
            )
            return (admin, None)
        except (KeyError, IndexError, JWTError, Exception) as exc:
            print("1", exc.args)
            raise exceptions.AuthenticationFailed("Not authenticated")

    def authenticate_header(self, request):
        return "Bearer"
