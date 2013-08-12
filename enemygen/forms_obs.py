from django import forms
from enemygen.models import Setting, Ruleset

class SettingRulesetForm(forms.Form):
    def __init__(self, request, *args, **kwargs):
        super(SettingRulesetForm, self).__init__(*args, **kwargs)
        self.request = request
        setting_choices = ((setting.id, setting.name) for setting in Setting.objects.all())
        ruleset_choices = ((ruleset.id, ruleset.name) for ruleset in Ruleset.objects.all())
        current_setting = request.session.get('setting_id', 1)
        current_ruleset = request.session.get('ruleset_id', 1)
        self.fields['setting'] = forms.ChoiceField(choices=setting_choices, initial=current_setting)
        self.fields['ruleset'] = forms.ChoiceField(choices=ruleset_choices, initial=current_ruleset)
        
    def save(self):
        # set cookies
        self.request.session['setting_id'] = self.cleaned_data['setting']
        self.request.session['ruleset_id'] = self.cleaned_data['ruleset']
