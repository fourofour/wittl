import json
import comparator
import hashlib

from django.core.cache import cache
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.template import Template, Context
from django.forms import ModelForm, Form


class User(AbstractUser):
    pass


class List(models.Model):
    name = models.CharField(max_length=256)
    creator = models.ForeignKey(User, related_name="created_lists")
    users = models.ManyToManyField(User)

    def __unicode__(self):
        return "{}/{}".format(self.creator, self.name)

    def get_comparators_for_user(self, user):
        return self.listcomparator_set.filter(user=user).all()


class ListForm(ModelForm):
    class Meta:
        model = List
        fields = ["name"]


class ListItem(models.Model):
    name = models.CharField(max_length=256)
    card_image = models.CharField(max_length=256)
    list = models.ForeignKey(List)
    #JSON of object attributes
    attributes = models.TextField()

    def __unicode__(self):
        return self.name

    @property
    def decoded_attributes(self):
        return json.loads(self.attributes)


class ListComparator(models.Model):
    user = models.ForeignKey(User)
    list = models.ForeignKey(List)
    order = models.IntegerField()
    comparator_name = models.CharField(max_length="128")

    #JSON for comparator's special fields
    configuration = models.TextField()

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
            result = comparator.run_comparator_by_name(self.comparator_name, self.decoded_configuration, object)
            cache.set(cache_key, result)

        return result

    def __unicode__(self):
        return "{}/{}/{}".format(self.user, self.list, self.comparator_name)