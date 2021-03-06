import json
import comparator
import hashlib

from celery import group

from django.core.cache import cache
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.template import Template, Context
from django.forms import ModelForm, Form
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from importer import get_importer_by_name
from tasks import run_comparator


class User(AbstractUser):
    favourites = models.ManyToManyField('ListItem')

    @property
    def gravatar_url(self):
        hashed_mail = hashlib.md5(self.email).hexdigest()
        return "http://www.gravatar.com/avatar/{}?default=mm&s=1024".format(hashed_mail)


@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


class List(models.Model):
    name = models.CharField(max_length=256)
    creator = models.ForeignKey(User, related_name="created_lists")
    users = models.ManyToManyField(User)

    def __unicode__(self):
        return "{}/{}".format(self.creator, self.name)

    def get_comparators_for_user(self, user):
        return self.listcomparator_set.filter(user=user).all()

    def user_invited(self, user):
        return self.users.filter(pk=user.pk).exists()


class ListComment(models.Model):
    author = models.ForeignKey(User)
    list = models.ForeignKey(List)
    body = models.TextField()
    added = models.DateTimeField(auto_now_add=True)


class ListForm(ModelForm):
    class Meta:
        model = List
        fields = ["name"]


class ListItem(models.Model):
    name = models.CharField(max_length=256)
    subtitle = models.CharField(max_length=512)
    card_image = models.CharField(max_length=256)
    list = models.ForeignKey(List, related_name="items")
    source = models.CharField(max_length=256)
    url = models.TextField()
    # JSON of object attributes
    attributes = models.TextField()

    def __unicode__(self):
        return self.name

    @property
    def decoded_attributes(self):
        return json.loads(self.attributes)

    @property
    def sortable_attrs(self):
        decoded_attributes = self.decoded_attributes

        importer = get_importer_by_name(self.source)
        sortable_attrs = importer.SORTABLE_ATTRS
        ext_sortable = {}
        for (key, value) in sortable_attrs.items():
            if key in decoded_attributes:
                ext_sortable[value] = decoded_attributes[key]
        return ext_sortable

    def comparator_data(self, user):
        score_data = {}

        task_list = [run_comparator.s(comparator, self.decoded_attributes)
                     for comparator in self.list.get_comparators_for_user(user)]
        job = group(task_list)

        for (comparator_id, result) in job.apply_async().get():
            score_data[comparator_id] = result

        return score_data


class ListComparator(models.Model):
    user = models.ForeignKey(User)
    list = models.ForeignKey(List)
    order = models.IntegerField()
    comparator_name = models.CharField(max_length="128")

    # JSON for comparator's special fields
    configuration = models.TextField()

    class Meta:
        ordering = ['order']

    def get_comparator_class(self):
        return comparator.get_comparator_by_name(self.comparator_name)

    @property
    def title(self):
        c = Context(self.decoded_configuration)
        return Template(self.get_comparator_class().TITLE).render(c)

    @property
    def form(self):
        form = Form(self.decoded_configuration)
        form.fields = self.get_comparator_class().EXTRA_FIELDS
        return form

    @property
    def decoded_configuration(self):
        return json.loads(self.configuration)

    def get_configuration_attribute(self, attr):
        return self.decoded_configuration.get(attr)

    def get_primary_field_value(self):
        return self.get_configuration_attribute(self.get_comparator_class().PRIMARY_FIELD)

    def run(self, object):
        comparator_data = {'comparator_name': self.comparator_name}
        comparator_data.update(self.decoded_configuration)
        comparator_data.update(object)
        cache_key = hashlib.sha256(json.dumps(comparator_data)).hexdigest()

        result = cache.get(cache_key)
        if not result:
            print("cache miss")
            result = comparator.run_comparator_by_name(self.comparator_name, self.decoded_configuration, object)
            cache.set(cache_key, result)

        return result

    def __unicode__(self):
        return "{}/{}/{}".format(self.user, self.list, self.comparator_name)