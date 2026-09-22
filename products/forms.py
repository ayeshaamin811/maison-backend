"""Admin form for Product.

The model stores `details` and `sizes` as JSON lists, which is right for the
API but wrong to put in front of whoever is adding stock: a raw JSON textarea
asks a merchandiser to get brackets, quotes and commas exactly right, and when
they do not the mistake lands silently on the live product page. These fields
present as a plain line-per-item textarea and a row of checkboxes instead, and
the JSON is assembled here.
"""
from django import forms

from .models import Product

SIZE_CHOICES = [
    ('XS', 'XS'),
    ('S', 'S'),
    ('M', 'M'),
    ('L', 'L'),
    ('XL', 'XL'),
    ('XXL', 'XXL'),
    ('Unstitched', 'Unstitched'),
    ('Free Size', 'Free Size'),
]


class LinesField(forms.CharField):
    """A JSON list of strings, edited as one item per line."""

    widget = forms.Textarea(attrs={'rows': 4, 'style': 'width: 40em'})

    def prepare_value(self, value):
        if isinstance(value, (list, tuple)):
            return '\n'.join(str(item) for item in value)
        return value

    def to_python(self, value):
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        if not value:
            return []
        return [line.strip() for line in str(value).splitlines() if line.strip()]


class SizesField(forms.MultipleChoiceField):
    """A JSON list of size labels, edited as checkboxes."""

    widget = forms.CheckboxSelectMultiple

    def to_python(self, value):
        if not value:
            return []
        return [str(item) for item in value]

    def validate(self, value):
        # Left deliberately open: a size already saved on a product stays valid
        # even if it is not one of SIZE_CHOICES, so an older row never blocks
        # an unrelated edit.
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'], code='required')


def _looks_like_json(value):
    text = (value or '').strip()
    return text.startswith(('[', '{')) and text.endswith((']', '}'))


class ProductAdminForm(forms.ModelForm):
    details = LinesField(
        required=False,
        label='Details',
        help_text='One line per bullet, e.g. "Fabric: Lawn". No brackets or quotes.',
    )
    sizes = SizesField(
        required=False,
        choices=SIZE_CHOICES,
        label='Sizes',
        help_text='Tick every size this product is sold in.',
    )

    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep any size already on the product selectable, even a one-off that
        # predates SIZE_CHOICES.
        current = (self.instance.sizes or []) if self.instance.pk else []
        known = {value for value, _ in SIZE_CHOICES}
        extra = [(size, size) for size in current if size not in known]
        if extra:
            self.fields['sizes'].choices = SIZE_CHOICES + extra

    def _reject_pasted_list(self, field):
        """Catch a details/sizes list pasted into a single-line text field."""
        value = self.cleaned_data.get(field, '')
        if _looks_like_json(value):
            raise forms.ValidationError(
                'This is a single line of text, not a list. It looks like a '
                'Details or Sizes value was pasted here by mistake - put those '
                'in their own fields below.'
            )
        return value

    def clean_shirt_detail(self):
        return self._reject_pasted_list('shirt_detail')

    def clean_composition(self):
        return self._reject_pasted_list('composition')
