from django.core.cache import cache
from django.db import models
from django_redis import get_redis_connection

from core.base_model import BaseModelClass


class BaseFollowQuerySet(models.query.QuerySet):
    def delete(self):
        return self.delete()


class CustomFollowManager(models.Manager):

    def get_query_set(self):
        return BaseFollowQuerySet(self.model, using=self._db)


class UserFollowing(BaseModelClass):
    user = models.ForeignKey(
        to='user.profile',
        on_delete=models.CASCADE,
        verbose_name='User Following',
        related_name='user_followings',
        related_query_name='user_following'
    )
    following = models.ForeignKey(
        to='user.Profile',
        verbose_name='Following',
        related_name='followings',
        related_query_name='following',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'user-followings'
        verbose_name_plural = 'user-followings'
        unique_together = (
            'user',
            'following'
        )  # TODO : Handle custom error message and remove get_or_create from serializer
        ordering = ('-id',)

    def __str__(self):
        return f'{self.user.title} follow {self.following.title}'

    def save(self,
             force_insert=False,
             force_update=False,
             using=None,
             update_fields=None):
        if force_insert:
            self.user.following_num += 1
            self.user.save()
        return super().save(
            force_insert=False,
            force_update=False,
            using=None,
            update_fields=None)


class VendorFollower(BaseModelClass):
    vendor = models.ForeignKey(
        to='user.profile',
        on_delete=models.CASCADE,
        verbose_name='Vendor',
        related_name='vendor_followers',
        related_query_name='vendor_follower'
    )
    follower = models.ForeignKey(
        to='user.Profile',
        verbose_name='Follower',
        related_name='followers',
        related_query_name='follower',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'followers'
        verbose_name_plural = 'followers'
        unique_together = (
            'vendor',
            'follower'
        )  # TODO : Handle custom error message and remove get_or_create from serializer
        ordering = ('-id',)

    def save(self,
             force_insert=False,
             force_update=False,
             using=None,
             update_fields=None):
        if force_insert:
            self.vendor.follower_num += 1
            self.vendor.save()
        return super().save(
            force_insert=False,
            force_update=False,
            using=None,
            update_fields=None)

    def __str__(self):
        return f'{self.vendor.title} with {self.follower.title} '
