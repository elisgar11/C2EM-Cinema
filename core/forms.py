from django import forms

from .models import SiteSettings


class SiteSettingsAdminForm(forms.ModelForm):
    tmdb_api_token_input = forms.CharField(
        label="Nuevo API Read Access Token de TMDB",
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
        help_text=(
            "Pega aquí el API Read Access Token. Si lo dejas vacío se conserva el token actual. "
            "El valor guardado no vuelve a mostrarse en el formulario."
        ),
    )
    clear_tmdb_api_token = forms.BooleanField(
        label="Eliminar token TMDB guardado en el administrador",
        required=False,
        help_text="Si existe TMDB_API_TOKEN en .env, seguirá utilizándose después de eliminar el token guardado aquí.",
    )

    class Meta:
        model = SiteSettings
        fields = (
            "cinema_name",
            "logo",
            "tagline",
            "primary_color",
            "home_message",
            "ticket_footer",
            "currency_symbol",
            "metadata_provider",
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        new_token = (self.cleaned_data.get("tmdb_api_token_input") or "").strip()
        if self.cleaned_data.get("clear_tmdb_api_token"):
            instance.tmdb_api_token = ""
        elif new_token:
            instance.tmdb_api_token = new_token
        if commit:
            instance.save()
            self.save_m2m()
        return instance
