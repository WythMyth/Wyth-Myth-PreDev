from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})

@register.filter
def get_item(dictionary, key):
    if dictionary and key in dictionary:
        return dictionary.get(key)
    return None