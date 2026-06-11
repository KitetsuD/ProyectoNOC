from django import forms


class RbdSearchForm(forms.Form):
    rbd = forms.IntegerField(
        label="RBD",
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "rbd-input",
                "placeholder": "4190",
                "autocomplete": "off",
            }
        ),
    )
