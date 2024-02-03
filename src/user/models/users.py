from django.db import models
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser, PermissionsMixin
)
from django.contrib.postgres.fields import ArrayField
from core.choice_field_types import AuthenticationLevelChoices


class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_staffuser(self, email, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.admin = True
        user.save(using=self._db)
        return user


class User(
    AbstractBaseUser,
    PermissionsMixin
):
    email = models.EmailField(
        verbose_name='Email address',
        max_length=255,
        unique=True,
    )
    is_active = models.BooleanField(default=True)
    staff = models.BooleanField(default=False)  # a admin user; non super-user
    admin = models.BooleanField(default=False)  # a superuser
    objects = UserManager()

    # notice the absence of a "Password field", that is built in.

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email & Password are required by default.

    def get_full_name(self):
        # The user is identified by their email address
        return self.email

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    def __str__(self):
        return self.email

    def has_perm(self, *args, **kwargs):
        return super().has_perm(*args, **kwargs) or self.is_admin

    def has_module_perms(self, app_label):
        return super().has_module_perms(app_label) or self.is_admin

    def has_perms(self, *args, **kwargs):
        return super().has_perms(*args, **kwargs) or self.is_admin

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        return self.staff

    @property
    def is_admin(self):
        "Is the user a admin member?"
        return self.admin


class IAMUser(models.Model):
    authentication_level = models.CharField(
        choices=AuthenticationLevelChoices.choices,
        max_length=64,
        blank=True,
    )
    owner_id = models.PositiveIntegerField()
    is_authenticated = models.BooleanField(default=False)

    class Meta:
        managed = False


class IAMAdmin(models.Model):
    role = models.CharField(
        max_length=64,
        blank=True
    )
    actions = ArrayField(
        base_field=models.CharField(max_length=128),
        default=list
    )
    owner_id = models.PositiveBigIntegerField()
    is_authenticated = models.BooleanField(default=False)

    class Meta:
        managed = False
