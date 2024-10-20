from django_registration.backends.activation.views import RegistrationView

class MyRegistrationView(RegistrationView):
    def get_success_url(self, user):
        return "/"
        
