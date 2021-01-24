from django.template import Library
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
 
import markdown2
 
register = Library()
 
@register.filter(is_safe=True)
@stringfilter
def markdown(value):
    text = markdown2.markdown(value,safe_mode=True).strip()
    text = text.replace('<p>', '').replace('</p>', '').replace('\n', '<br>')
    return mark_safe(text)
