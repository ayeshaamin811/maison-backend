from django.db import models


class ContactMessage(models.Model):
    """One submission of the storefront contact form.

    Only `email` is required: the form asks for a name but a visitor who skips
    it still has something worth saying, and a reply only needs the address.
    """

    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['is_read', '-created_at'])]

    def __str__(self):
        name = ' '.join(part for part in (self.first_name, self.last_name) if part)
        return '{} <{}>'.format(name or 'Anonymous', self.email)
