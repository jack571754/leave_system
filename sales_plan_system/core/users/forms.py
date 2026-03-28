from django import forms

from .models import User


class ProfileForm(forms.ModelForm):
    """Form for users to edit their own profile information."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-purple-400 focus:ring-2 focus:ring-purple-100 focus:outline-none transition',
                'placeholder': '名',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-purple-400 focus:ring-2 focus:ring-purple-100 focus:outline-none transition',
                'placeholder': '姓',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-purple-400 focus:ring-2 focus:ring-purple-100 focus:outline-none transition',
                'placeholder': 'email@example.com',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-purple-400 focus:ring-2 focus:ring-purple-100 focus:outline-none transition',
                'placeholder': '13800138000',
                'maxlength': '11',
            }),
        }
