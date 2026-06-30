import re
from typing import Optional
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class PasswordValidator:
    """
    Validates that a password meets enterprise security standards.
    """
    
    @classmethod
    def validate(cls, password: str, user=None) -> None:
        """
        Validates the password strength.
        Raises ValidationError if any check fails.
        """
        if len(password) < 12:
            raise ValidationError(_("Password must be at least 12 characters long."), code='password_too_short')
            
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_("Password must contain at least one uppercase letter."), code='password_no_upper')
            
        if not re.search(r'[a-z]', password):
            raise ValidationError(_("Password must contain at least one lowercase letter."), code='password_no_lower')
            
        if not re.search(r'[0-9]', password):
            raise ValidationError(_("Password must contain at least one digit."), code='password_no_digit')
            
        if not re.search(r'[\W_]', password):
            raise ValidationError(_("Password must contain at least one special character."), code='password_no_special')
            
        # Additional checks (e.g. against password history, common passwords) would go here
